import logging
import os
from abc import ABC, abstractmethod
from threading import Thread
from typing import List, Optional

from hilda.exceptions import LLDBError
from hilda.hilda_client import HildaClient
from hilda.lldb_importer import lldb

TIMEOUT = 1
lldb.hilda_client = None

logger = logging.getLogger(__name__)


def execute(cmd: str) -> int:
    logging.debug(f'executing: {cmd}')
    return os.system(cmd)


class LLDBListenerThread(Thread, ABC):

    def __init__(self):
        super().__init__()
        lldb.SBDebugger.Initialize()
        self.debugger: lldb.SBDebugger = lldb.SBDebugger.Create()
        self.listener: lldb.SBListener = self.debugger.GetListener()
        self.error: lldb.SBError = lldb.SBError()
        self.debugger.SetAsync(True)
        self.target: lldb.SBTarget = self._create_target()
        self.process: lldb.SBProcess = self._create_process()
        self._check_success()
        self.should_quit = False

    @abstractmethod
    def _create_target(self) -> lldb.SBTarget:
        pass

    @abstractmethod
    def _create_process(self) -> lldb.SBProcess:
        pass

    def _check_success(self) -> None:
        if self.error.Success():
            return
        raise LLDBError(self.error.description)

    def run(self):
        event = lldb.SBEvent()
        last_state = lldb.eStateStopped
        while not self.should_quit:
            if not self.listener.WaitForEvent(TIMEOUT, event):
                continue
            if not lldb.SBProcess.EventIsProcessEvent(event):
                continue
            state = self.process.GetStateFromEvent(event)
            if state == lldb.eStateDetached:
                logger.debug('Process Detached')
                self.should_quit = True
            elif state == lldb.eStateExited:
                logger.info(f'Process Exited with status {self.process.GetExitStatus()}')
                self.should_quit = True
            elif state == lldb.eStateRunning and last_state == lldb.eStateStopped:
                logger.debug('Process Continued')
            elif state == lldb.eStateStopped and last_state == lldb.eStateRunning:
                logger.debug('Process Stopped')
                for thread in self.process:
                    frame = thread.GetFrameAtIndex(0)
                    stop_reason = thread.GetStopReason()
                    logger.debug(f'tid = {hex(thread.GetThreadID())} pc = {frame.GetPC()}')
                    if stop_reason not in [lldb.eStopReasonSignal, lldb.eStopReasonException,
                                           lldb.eStopReasonBreakpoint,
                                           lldb.eStopReasonWatchpoint, lldb.eStopReasonPlanComplete,
                                           lldb.eStopReasonTrace,
                                           lldb.eStopReasonSignal]:
                        continue
                    self.process.SetSelectedThread(thread)
                    break

            last_state = state


class LLDBRemote(LLDBListenerThread):
    def __init__(self, address: str, port: int = 1234):
        self.url_connect = f'connect://{address}:{port}'
        super().__init__()

    def _create_target(self) -> lldb.SBTarget:
        return self.debugger.CreateTarget('')

    def _create_process(self) -> lldb.SBProcess:
        logger.debug(f'Connecting to "{self.url_connect}"')
        return self.target.ConnectRemote(self.listener, self.url_connect, None, self.error)


class LLDBAttachPid(LLDBListenerThread):

    def __init__(self, pid: int):
        self.pid = pid
        super().__init__()

    def _create_target(self) -> lldb.SBTarget:
        return self.debugger.CreateTargetWithFileAndArch(None, None)

    def _create_process(self) -> lldb.SBProcess:
        logger.debug(f'Attaching to {self.pid}')
        return self.target.AttachToProcessWithID(self.listener, self.pid, self.error)


class LLDBAttachName(LLDBListenerThread):

    def __init__(self, proc_name: str, wait_for: bool = False):
        self.proc_name = proc_name
        self.wait_for = wait_for
        super().__init__()

    def _create_target(self) -> lldb.SBTarget:
        return self.debugger.CreateTargetWithFileAndArch(None, None)

    def _create_process(self) -> lldb.SBProcess:
        logger.debug(f'Attaching to {self.proc_name}')
        return self.target.AttachToProcessWithName(self.listener, self.proc_name, self.wait_for, self.error)


class LLDBLaunch(LLDBListenerThread):
    def __init__(self, exec_path: str, argv: Optional[List[str]] = None, envp: Optional[List[str]] = None,
                 stdin: Optional[str] = None,
                 stdout: Optional[str] = None, stderr: Optional[str] = None, wd: Optional[str] = None,
                 flags: Optional[int] = 0):
        self.exec_path = exec_path
        self.stdout = stdout
        self.stdin = stdin
        self.stderr = stderr
        self.flags = flags
        self.argv = argv
        self.envp = envp
        self.working_directory = wd
        super().__init__()

    def _create_target(self) -> lldb.SBTarget:
        return self.debugger.CreateTargetWithFileAndArch(self.exec_path, lldb.LLDB_ARCH_DEFAULT)

    def _create_process(self) -> lldb.SBProcess:
        # Launch(SBTarget self, SBListener listener, char const ** argv, char const ** envp,
        # char const * stdin_path, char const * stdout_path, char const * stderr_path, char const * working_directory,
        # uint32_t launch_flags, bool stop_at_entry, SBError error) -> SBProcess
        logger.debug(f'Lunching process  {self.exec_path}')
        return self.target.Launch(self.listener, self.argv, self.envp,
                                  self.stdin, self.stdout, self.stderr, self.working_directory,
                                  self.flags, True,
                                  self.error)


def _get_hilda_client_from_sbdebugger(debugger: lldb.SBDebugger) -> HildaClient:
    hilda_client = HildaClient(debugger)
    lldb.hilda_client = hilda_client
    hilda_client.init_dynamic_environment()
    return hilda_client


def create_hilda_client_using_remote_attach(
        hostname: str, port: int) -> HildaClient:
    lldb_t = LLDBRemote(hostname, port)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)


def create_hilda_client_using_launch(
        exec_path: str, argv: Optional[List] = None, envp: Optional[List] = None, stdin: Optional[str] = None,
        stdout: Optional[str] = None, stderr: Optional[str] = None, wd: Optional[str] = None,
        flags: Optional[int] = 0) -> HildaClient:
    lldb_t = LLDBLaunch(exec_path, argv, envp, stdin, stdout, stderr, wd, flags)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)


def create_hilda_client_using_attach_by_pid(pid: Optional[int] = None) -> HildaClient:
    lldb_t = LLDBAttachPid(pid)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)


def create_hilda_client_using_attach_by_name(name: Optional[str] = None, wait_for: bool = False) -> HildaClient:
    lldb_t = LLDBAttachName(name, wait_for)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)
