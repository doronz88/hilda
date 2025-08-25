import base64
import builtins
import importlib
import importlib.util
import json
import logging
import os
import struct
import sys
import time
import typing
from collections import namedtuple
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import cached_property, wraps
from pathlib import Path
from typing import Any, Callable, Optional, Union

import click
import hexdump
import IPython
from IPython.core.magic import register_line_magic  # noqa: F401
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import XmlLexer
from tqdm import tqdm
from traitlets.config import Config

from hilda import objective_c_class
from hilda.breakpoints import BreakpointList, HildaBreakpoint, WhereType
from hilda.common import CfSerializable, selection_prompt
from hilda.exceptions import AccessingMemoryError, AccessingRegisterError, ConvertingFromNSObjectError, \
    ConvertingToNsObjectError, CreatingObjectiveCSymbolError, DisableJetsamMemoryChecksError, \
    EvaluatingExpressionError, HildaException, InvalidThreadIndexError, SymbolAbsentError
from hilda.ipython_extensions.keybindings import get_keybindings
from hilda.lldb_importer import lldb
from hilda.objective_c_symbol import ObjectiveCSymbol
from hilda.registers import Registers
from hilda.snippets.mach import CFRunLoopServiceMachPort_hooks
from hilda.symbol import Symbol
from hilda.symbols import SymbolList
from hilda.ui.ui_manager import UiManager
from hilda.watchpoints import WatchpointList

lldb.KEYSTONE_SUPPORT = True
try:
    from keystone import KS_ARCH_ARM64, KS_ARCH_X86, KS_MODE_64, KS_MODE_LITTLE_ENDIAN, Ks
except ImportError:
    lldb.KEYSTONE_SUPPORT = False
    print('failed to import keystone. disabling some features')


def disable_logs() -> None:
    logging.getLogger('asyncio').disabled = True
    logging.getLogger('parso.cache').disabled = True
    logging.getLogger('parso.cache.pickle').disabled = True
    logging.getLogger('parso.python.diff').disabled = True
    logging.getLogger('blib2to3.pgen2.driver').disabled = True
    logging.getLogger('hilda.launch_lldb').setLevel(logging.INFO)


SerializableSymbol = namedtuple('SerializableSymbol', 'address type_ filename')


@dataclass
class HelpSnippet:
    """ Small snippet line to occur from `HildaClient.show_help()` """

    key: str
    description: str

    def __str__(self) -> str:
        return click.style(self.key.ljust(8), bold=True, fg='magenta') + click.style(self.description, bold=True)


@dataclass
class Configs:
    """ Configuration settings for evaluation and monitoring. """
    evaluation_unwind_on_error: bool = field(default=False,
                                             metadata={'doc': 'Whether to unwind on error during evaluation.'})
    evaluation_ignore_breakpoints: bool = field(default=False,
                                                metadata={'doc': 'Whether to ignore breakpoints during evaluation.'})
    nsobject_exclusion: bool = field(default=False, metadata={
        'doc': 'Whether to exclude NSObject during evaluation - reduce ipython autocomplete results.'})
    objc_verbose_monitor: bool = field(default=False, metadata={
        'doc': 'When set to True, using monitor() will automatically print objc methods arguments.'})
    enable_stdout_stderr: bool = field(default=True, metadata={
        'doc': 'When set to True, will enable process stdout and stderr.'})

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        config_str = 'Configuration settings:\n'
        max_len = max(len(field_name) for field_name in self.__dataclass_fields__) + 2

        for field_name, field_info in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            doc = field_info.metadata.get('doc', 'No docstring available')
            config_str += f'\t{field_name.ljust(max_len)}: {str(value).ljust(5)} | {doc}\n'

        return config_str


def stop_is_needed(func: Callable):
    """Decorator to check if the process must be stopped before proceeding."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        is_running = self.process.GetState() == lldb.eStateRunning
        if is_running:
            self.logger.error(f'Cannot {func.__name__.replace("_", "-")}: Process must be stopped first.')
            return
        return func(self, *args, **kwargs)

    return wrapper


class HildaClient:
    RETVAL_BIT_COUNT = 64

    def __init__(self, debugger: lldb.SBDebugger) -> None:
        self.logger = logging.getLogger(__name__)
        self.endianness = '<'
        self.debugger = debugger
        self.target = debugger.GetSelectedTarget()
        self.process = self.target.GetProcess()
        self.symbols = SymbolList(self)
        self.breakpoints = BreakpointList(self)
        self.watchpoints = WatchpointList(self)
        self.captured_objects = {}
        self.registers = Registers(self)
        self.arch = self.target.GetTriple().split('-')[0]
        self.ui_manager = UiManager(self)
        self.configs = Configs()
        self._dynamic_env_loaded = False
        self._symbols_loaded = False
        self.globals: typing.MutableMapping[str, Any] = globals()
        self._hilda_root = Path(__file__).parent

        # the frame called within the context of the hit BP
        self._bp_frame = None

        self._add_global('symbols', self.symbols, [])
        self._add_global('registers', self.registers, [])

        self.log_info(f'Target: {self.target}')
        self.log_info(f'Process: {self.process}')

    def hd(self, buf: bytes) -> None:
        """
        Print hexdump representation for given buffer.

        :param buf: buffer to print in hexdump form
        """
        hexdump.hexdump(buf)

    def lsof(self) -> dict[int, Any]:
        """
        Get dictionary of all open FDs
        :return: Mapping between open FDs and their paths
        """
        data = (self._hilda_root / 'objective_c' / 'lsof.m').read_text()
        result = json.loads(self.po(data))
        # convert FDs into int
        return {int(k): v for k, v in result.items()}

    def bt(self, should_print: bool = False, depth: Optional[int] = None) -> list[Union[str, lldb.SBFrame]]:
        """ Print an improved backtrace. """
        backtrace = []
        for i, frame in enumerate(self.thread.frames):
            if i == depth:
                break
            row = ''
            row += click.style(f'0x{frame.addr.GetFileAddress():x} ', fg='cyan')
            row += str(frame)
            if i == 0:
                # first line
                row += ' 👈'
            backtrace.append([f'0x{frame.addr.file_addr:016x}', frame])
            if should_print:
                print(row)
        return backtrace

    def disable_jetsam_memory_checks(self):
        """
        Disable jetsam memory checks, prevent raising:
        `error: Execution was interrupted, reason: EXC_RESOURCE RESOURCE_TYPE_MEMORY (limit=15 MB, unused=0x0).`
        when evaluating expression.
        """
        # 6 is for MEMORYSTATUS_CMD_SET_JETSAM_TASK_LIMIT
        result = self.symbols.memorystatus_control(6, self.process.GetProcessID(), 0, 0, 0)
        if result:
            raise DisableJetsamMemoryChecksError()

    def symbol(self, address: int) -> Symbol:
        """
        Get symbol object for a given address
        :param address:
        :return: Hilda's symbol object
        """
        return self.symbols.add(address)

    def objc_symbol(self, address: int) -> ObjectiveCSymbol:
        """
        Get objc symbol wrapper for given address
        :param address:
        :return: Hilda's objc symbol object
        """
        try:
            return ObjectiveCSymbol.create(int(address), self)
        except HildaException as e:
            raise CreatingObjectiveCSymbolError from e

    def inject(self, filename: str) -> SymbolList:
        """
        Inject a single library into currently running process.

        :param filename: library to inject (dylib)
        :return: SymbolList
        """
        module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
        if module.file.basename is not None:
            self.log_warning(f'file {filename} has already been loaded')

        injected = SymbolList(self)
        handle = self.symbols.dlopen(filename, 10)  # RTLD_GLOBAL|RTLD_NOW

        if handle == 0:
            self.log_critical(f'failed to inject: {filename}')

        module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
        for symbol in module.symbols:
            load_addr = symbol.addr.GetLoadAddress(self.target)
            if load_addr == 0xffffffffffffffff:
                # skip those not having a real address
                continue

            name = symbol.name
            type_ = symbol.GetType()

            if name in ('<redacted>',) or (type_ not in (lldb.eSymbolTypeCode,
                                                         lldb.eSymbolTypeData,
                                                         lldb.eSymbolTypeObjCMetaClass)):
                # ignore unnamed symbols and those which are not: data, code or objc classes
                continue

            injected.add(self.symbol(load_addr), name)
        return injected

    @stop_is_needed
    def poke(self, address, buf: bytes):
        """
        Write data at given address
        :param address:
        :param buf:
        """
        err = lldb.SBError()
        retval = self.process.WriteMemory(address, buf, err)

        if not err.Success():
            raise AccessingMemoryError()

        return retval

    @stop_is_needed
    def poke_text(self, address: int, code: str) -> int:
        """
        Write instructions to address.
        :param address:
        :param code:
        """
        if not lldb.KEYSTONE_SUPPORT:
            raise NotImplementedError('Not supported without keystone')
        bytecode, count = self._ks.asm(code, as_bytes=True)
        return self.poke(address, bytecode)

    @stop_is_needed
    def peek(self, address, size: int) -> bytes:
        """
        Read data at given address
        :param address:
        :param size:
        :return:
        """
        if size == 0:
            return b''

        err = lldb.SBError()
        retval = self.process.ReadMemory(address, int(size), err)

        if not err.Success():
            raise AccessingMemoryError()

        return retval

    @stop_is_needed
    def peek_str(self, address: Symbol) -> str:
        """
        Peek a buffer till null termination
        :param address:
        :return:
        """
        return address.po('char *')[1:-1]  # strip the ""

    @stop_is_needed
    def peek_std_str(self, address: Symbol) -> str:
        """
        Peek a std::string
        :param address: Address to read the std::string from
        :return: Python string
        """
        return self._std_string(address)

    def stop(self, *args) -> None:
        """ Stop process. """
        self.debugger.SetAsync(False)

        is_running = self.process.GetState() == lldb.eStateRunning
        if not is_running:
            self.log_debug('already stopped')
            return

        if not self.process.Stop().Success():
            self.log_critical('failed to stop process')

    def run_for(self, seconds: float) -> None:
        """
        Run the process for a given time
        :return:
        """
        self.cont()
        self.logger.info(f'Running for {seconds} seconds')
        time.sleep(seconds)
        self.stop()

    def cont(self, *args) -> None:
        """ Continue process. """
        is_running = self.process.GetState() == lldb.eStateRunning

        if is_running:
            self.log_debug('already running')
            return

        # bugfix:   the debugger may become in sync state, so we make sure
        #           it isn't before trying to continue
        self.debugger.SetAsync(True)

        if not self.process.Continue().Success():
            self.log_critical('failed to continue process')

    def detach(self) -> None:
        """
        Detach from process.

        Useful in order to exit gracefully so process doesn't get killed
        while you exit
        """
        if not self.process.is_alive:
            return
        if not self.process.Detach().Success():
            self.log_critical('failed to detach')
            return
        self.log_info('Process Detached')

    @stop_is_needed
    def disass(self, address: int, buf: bytes, flavor: str = 'intel',
               should_print: bool = False) -> lldb.SBInstructionList:
        """
        Print disassembly from a given address
        :param flavor:
        :param address:
        :param buf:
        :param should_print:
        :return:
        """
        inst = self.target.GetInstructionsWithFlavor(lldb.SBAddress(address, self.target), flavor, buf)
        if should_print:
            print(inst)
        return inst

    def file_symbol(self, address: int, module_name: Optional[str] = None) -> Symbol:
        """
        Calculate symbol address without ASLR
        :param address: address as can be seen originally in Mach-O
        :param module_name: Module name to resolve the symbol from
        """
        if module_name is None:
            module = self.target
        else:
            module = self.target.FindModule(lldb.SBFileSpec(module_name))

        return self.symbol(module.ResolveFileAddress(address).GetLoadAddress(self.target))

    def get_register(self, name: str) -> Union[float, Symbol]:
        """
        Get value for register by its name. Value can either be an Symbol (int) or a float.

        :param name: Register name
        :return: Register value
        """
        register_value = self.frame.register[name.lower()]
        if register_value is None:
            raise AccessingRegisterError()
        return self._get_symbol_or_float_from_sbvalue(register_value)

    def set_register(self, name: str, value: Union[float, int]) -> None:
        """
        Set value for register by its name.

        :param name: Register name
        :param value: Register value
        """
        register = self.frame.register[name.lower()]
        if register is None:
            raise AccessingRegisterError()
        if isinstance(value, int):
            register.value = hex(value)
        else:
            register.value = str(value)

    def objc_call(self, obj: int, selector: str, *params):
        """
        Simulate a call to an objc selector.

        :param obj: obj to pass into `objc_msgSend`
        :param selector: selector to execute
        :param params: any other additional parameters the selector requires
        :return: invocation returned value
        """
        # On object `obj`
        args = self._serialize_call_params([obj])
        # Call selector (by its uid)
        args.append(self._generate_call_expression(self.symbols.sel_getUid, self._serialize_call_params([selector])))
        # With params
        args.extend(self._serialize_call_params(params))
        call_expression = self._generate_call_expression(self.symbols.objc_msgSend, args)
        with self.stopped():
            return self.evaluate_expression(call_expression)

    def call(self, address, argv: Optional[list] = None):
        """
        Call function at given address with given parameters
        :param address:
        :param argv: parameter list
        :return: function's return value
        """
        if argv is None:
            argv = []
        call_expression = self._generate_call_expression(address, self._serialize_call_params(argv))
        with self.stopped():
            return self.evaluate_expression(call_expression)

    def monitor(self, address, condition: str = None, **options) -> HildaBreakpoint:
        """
        Monitor every time a given address is called

        Alias of self.breakpoints.add_monitor()
        """
        return self.breakpoints.add_monitor(address, condition, **options)

    def show_current_source(self) -> None:
        """ print current source code if possible """
        self.lldb_handle_command('f')

    def finish(self):
        """ Run current frame till its end. """
        with self.sync_mode():
            self.thread.StepOutOfFrame(self.frame)
            self._bp_frame = None

    @stop_is_needed
    def step_into(self, *args):
        """ Step into current instruction. """
        with self.sync_mode():
            self.thread.StepInto()
        if self.ui_manager.active:
            self.ui_manager.show()

    @stop_is_needed
    def step_over(self, *args):
        """ Step over current instruction. """
        with self.sync_mode():
            self.thread.StepOver()
        if self.ui_manager.active:
            self.ui_manager.show()

    def force_return(self, value: int = 0) -> None:
        """
        Prematurely return from a stack frame, short-circuiting exection of newer frames and optionally
        yielding a specified value.
        :param value:
        :return:
        """
        self.finish()
        self.set_register('x0', value)

    def proc_info(self) -> None:
        """ Print information about currently running mapped process. """
        print(self.process)

    def print_proc_entitlements(self) -> None:
        """ Get the plist embedded inside the process' __LINKEDIT section. """
        linkedit_section = self.target.modules[0].FindSection('__LINKEDIT')
        linkedit_data = self.symbol(linkedit_section.GetLoadAddress(self.target)).peek(linkedit_section.size)

        # just look for the xml start inside the __LINKEDIT section. should be good enough since wer'e not
        # expecting any other XML there
        entitlements = str(linkedit_data[linkedit_data.find(b'<?xml'):].split(b'\xfa', 1)[0], 'utf8')
        print(highlight(entitlements, XmlLexer(), TerminalTrueColorFormatter()))

    def bp(self, address_or_name: WhereType, callback: Optional[Callable] = None, condition: Optional[str] = None,
           guarded: bool = False, description: Optional[str] = None, **options) -> HildaBreakpoint:
        """
        Add a breakpoint

        Alias of self.breakpoints.add()

        :param address_or_name: Where to place the breakpoint
        :param condition: set as a conditional breakpoint using lldb expression
        :param callback: callback(hilda, *args) to be called
        :param guarded: whether the breakpoint should be protected frm usual removal.
        :param description: Attach a breakpoint description
        :param options: can contain an `override` keyword to specify if to override an existing BP
        :return: native LLDB breakpoint
        """
        return self.breakpoints.add(address_or_name, callback, condition, guarded, description=description, **options)

    def po(self, expression: str, cast: Optional[str] = None) -> str:
        """
        Print given object using LLDB's po command

        Can also run big chunks of native code:

        po('NSMutableString *s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')

        :param expression: either a symbol or string the execute
        :param cast: object type
        :raise EvaluatingExpressionError: LLDB failed to evaluate the expression
        :return: LLDB's po output
        """
        casted_expression = ''
        if cast is not None:
            casted_expression += '(%s)' % cast
        casted_expression += f'0x{expression:x}' if isinstance(expression, int) else str(expression)

        res = lldb.SBCommandReturnObject()
        self.debugger.GetCommandInterpreter().HandleCommand(f'expression -i 0 -lobjc -O -- {casted_expression}', res)
        if not res.Succeeded():
            raise EvaluatingExpressionError(res.GetError())
        return res.GetOutput().strip()

    def globalize_symbols(self) -> None:
        """
        Make all symbols in python's global scope
        """
        reserved_names = list(globals().keys()) + dir(builtins)
        for name, value in tqdm(self.symbols.items()):
            if ':' not in name \
                    and '[' not in name \
                    and '<' not in name \
                    and '(' not in name \
                    and '.' not in name:
                self._add_global(name, value, reserved_names)

    def jump(self, symbol: int) -> None:
        """ jump to given symbol """
        self.lldb_handle_command(f'j *{symbol}')

    def lldb_handle_command(self, cmd: str, capture_output: bool = False) -> Optional[str]:
        """
        Execute an LLDB command

        For example:
            lldb_handle_command('register read')

        :param cmd: LLDB command
        :param capture_output: True if capturing the command output
        :return: The output if capture was requested, None if not or the command failed
        """
        if capture_output:
            result = lldb.SBCommandReturnObject()
            self.debugger.GetCommandInterpreter().HandleCommand(cmd, result)
            return result.GetOutput() if result.Succeeded() else None
        else:
            self.debugger.HandleCommand(cmd)

    def objc_get_class(self, name: str, module_name: Optional[str] = None) -> objective_c_class.Class:
        """
        Get ObjC class object
        :param module_name:
        :param name:
        :return:
        """
        if module_name is not None:
            ret = self.symbol(self._get_module_class_list(module_name)[name]).objc_class
        else:
            ret = objective_c_class.Class.from_class_name(self, name)
        return ret

    def CFSTR(self, symbol: int) -> Symbol:
        """ Create CFStringRef object from given string """
        return self.cf(symbol)

    def cf(self, data: CfSerializable) -> Symbol:
        """
        Create NSObject from given data (same as ns())
        :param data: Data representing the NSObject, must by JSON serializable
        :return: Pointer to a NSObject
        """
        return self.ns(data)

    def ns(self, data: CfSerializable) -> Symbol:
        """
        Create NSObject from given data (same as cf())
        :param data: Data representing the NSObject, must by JSON serializable
        :return: Pointer to a NSObject
        """
        try:
            json_data = json.dumps({'root': data}, default=self._to_ns_json_default)
        except TypeError as e:
            raise ConvertingToNsObjectError from e
        obj_c_code = (self._hilda_root / 'objective_c' / 'to_ns_from_json.m').read_text()
        expression = obj_c_code.replace('__json_object_dump__', json_data.replace('"', r'\"'))
        try:
            return self.evaluate_expression(expression)
        except EvaluatingExpressionError as e:
            raise ConvertingToNsObjectError from e

    def decode_cf(self, address: Union[int, str]) -> CfSerializable:
        """
        Create python object from NS object.
        :param address: NS object.
        :return: Python object.
        """
        obj_c_code = (self._hilda_root / 'objective_c' / 'from_ns_to_json.m').read_text()
        address = f'0x{address:x}' if isinstance(address, int) else address
        expression = obj_c_code.replace('__ns_object_address__', address)
        try:
            json_dump = self.po(expression)
        except EvaluatingExpressionError as e:
            raise ConvertingFromNSObjectError from e
        return json.loads(json_dump, object_hook=self._from_ns_json_object_hook)['root']

    def evaluate_expression(self, expression: str) -> Union[float, Symbol]:
        """
        Wrapper for LLDB's EvaluateExpression.
        Used for quick code snippets.

        Feel free to use local variables inside the expression using format string.
        For example:
            currentDevice = objc_get_class('UIDevice').currentDevice
            evaluate_expression(f'[[{currentDevice} systemName] hasPrefix:@"2"]')

        :param expression: Expression to evaluate
        :return: Returned value (either float or a Symbol)
        """
        # prepending a prefix so LLDB knows to return an int type
        if isinstance(expression, int):
            formatted_expression = f'(intptr_t)0x{expression:x}'
        else:
            formatted_expression = str(expression)

        options = lldb.SBExpressionOptions()
        options.SetIgnoreBreakpoints(self.configs.evaluation_ignore_breakpoints)
        options.SetTryAllThreads(True)
        options.SetUnwindOnError(self.configs.evaluation_unwind_on_error)

        sbvalue = self.frame.EvaluateExpression(formatted_expression, options)

        if not sbvalue.error.Success():
            raise EvaluatingExpressionError(str(sbvalue.error))

        return self._get_symbol_or_float_from_sbvalue(sbvalue)

    def import_module(self, filename: str, name: Optional[str] = None) -> Any:
        """
        Import & reload given python module (intended mainly for external snippets)
        :param filename: Python filename to import
        :param name: Optional module name, or otherwise use the filename
        :return: Python module
        """
        filename = os.path.expanduser(filename)
        if name is None:
            name = os.path.splitext(os.path.basename(filename))[0]
        spec = importlib.util.spec_from_file_location(name, filename)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def set_selected_thread(self, idx: Optional[int] = None) -> None:
        if idx is None:
            thread = selection_prompt(self.process.threads)
        else:
            try:
                thread = [t for t in self.process.threads if t.idx == idx][0]
            except IndexError:
                raise InvalidThreadIndexError()
        self.process.SetSelectedThread(thread)

    def unwind(self) -> bool:
        """ Unwind the stack (useful when get_evaluation_unwind() == False) """
        return self.thread.UnwindInnermostExpression().Success()

    @cached_property
    def pid(self) -> int:
        return self.process.GetProcessID()

    @property
    def thread(self):
        """ Current active thread. """
        if self._bp_frame is not None:
            return self._bp_frame.GetThread()
        return self.process.GetSelectedThread()

    @property
    def frame(self):
        """ Current active frame. """
        if self._bp_frame is not None:
            return self._bp_frame
        return self.thread.GetSelectedFrame()

    @contextmanager
    def stopped(self, interval: int = 0):
        """
        Context-Manager for execution while process is stopped.
        If interval is supplied, then if the device is in running state, it will sleep for the interval
        given before and after execution.
        """
        is_running = self.process.GetState() == lldb.eStateRunning

        if is_running:
            self.stop()
            time.sleep(interval)

        try:
            yield
        finally:
            if is_running:
                time.sleep(interval)
                self.cont()

    @contextmanager
    def safe_malloc(self, size: int):
        """
        Context-Manager for allocating a block of memory which is freed afterwards
        :param size:
        :return:
        """
        block = self.symbols.malloc(size)
        if block == 0:
            raise OSError(f'failed to allocate memory of size: {size} bytes')

        try:
            yield block
        finally:
            self.symbols.free(block)

    @contextmanager
    def sync_mode(self):
        """ Context-Manager for execution while LLDB is in sync mode. """
        is_async = self.debugger.GetAsync()
        self.debugger.SetAsync(False)
        try:
            yield
        finally:
            self.debugger.SetAsync(is_async)

    def init_dynamic_environment(self):
        """ Init session-scoped process dynamic dependencies. """
        self.log_debug('init dynamic environment')
        self._dynamic_env_loaded = True

        self.log_debug('disable mach_msg receive errors')
        try:
            CFRunLoopServiceMachPort_hooks.disable_mach_msg_errors()
        except SymbolAbsentError:
            self.log_warning('failed to disable mach_msg errors')

        objc_code = """
        @import ObjectiveC;
        @import Foundation;
        """
        try:
            self.po(objc_code)
        except EvaluatingExpressionError:
            # first time is expected to fail. bug in LLDB?
            pass

    def log_warning(self, message):
        """ Log at warning level """
        self.logger.warning(message)

    def log_debug(self, message):
        """ Log at debug level """
        self.logger.debug(message)

    def log_error(self, message):
        """ Log at error level """
        self.logger.error(message)

    def log_critical(self, message):
        """ Log at critical level """
        self.logger.critical(message)
        raise HildaException(message)

    def log_info(self, message):
        """ Log at info level """
        self.logger.info(message)

    def wait_for_module(self, expression: str) -> None:
        """ Wait for a module to be loaded using `dlopen` by matching given expression """
        self.log_info(f'Waiting for module name containing "{expression}" to be loaded')

        def bp(client: HildaClient, frame, bp_loc, options) -> None:
            loading_module_name = client.evaluate_expression('$arg1').peek_str()
            client.log_info(f'Loading module: {loading_module_name}')
            if expression not in loading_module_name:
                client.cont()
                return
            client.finish()
            client.log_info(f'Desired module has been loaded: {expression}. Process remains stopped')
            bp_id = bp_loc.GetBreakpoint().GetID()
            client.breakpoints.remove(bp_id)

        self.bp('dlopen', bp)
        self.cont()

    def show_help(self, *_) -> None:
        """
        Show banner help message
        """
        help_snippets = [HelpSnippet(key='p', description='Global to access all features')]
        for keybinding in get_keybindings(self):
            help_snippets.append(HelpSnippet(key=keybinding.key.upper(), description=keybinding.description))

        for help_snippet in help_snippets:
            click.echo(help_snippet)

    def interact(self, additional_namespace: Optional[typing.Mapping] = None,
                 startup_files: Optional[list[str]] = None) -> None:
        """ Start an interactive Hilda shell """
        if not self._dynamic_env_loaded:
            self.init_dynamic_environment()

        # Show greeting
        click.secho('Hilda has been successfully loaded! 😎', bold=True)
        click.secho('Usage:', bold=True)
        self.show_help()
        click.echo(click.style('Have a nice flight ✈️! Starting an IPython shell...', bold=True))

        # Configure and start IPython shell
        ipython_config = Config()
        ipython_config.IPCompleter.use_jedi = False
        ipython_config.BaseIPythonApplication.profile = 'hilda'
        ipython_config.InteractiveShellApp.extensions = ['hilda.ipython_extensions.magics',
                                                         'hilda.ipython_extensions.events',
                                                         'hilda.ipython_extensions.keybindings']
        ipython_config.InteractiveShellApp.exec_lines = ['disable_logs()']
        if startup_files is not None:
            ipython_config.InteractiveShellApp.exec_files = startup_files
            self.log_debug(f'Startup files - {startup_files}')

        namespace = self.globals
        namespace['p'] = self
        namespace['ui'] = self.ui_manager
        namespace['cfg'] = self.configs
        if additional_namespace is not None:
            namespace.update(additional_namespace)
        sys.argv = ['a']
        IPython.start_ipython(config=ipython_config, user_ns=namespace)

    def toggle_enable_stdout_stderr(self, *args) -> None:
        self.configs.enable_stdout_stderr = not self.configs.enable_stdout_stderr
        self.logger.info(f'Changed stdout and stderr status to: {self.configs.enable_stdout_stderr}')

    def __enter__(self) -> 'HildaClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.detach()

    def _add_global(self, name: str, value: Any, reserved_names=None) -> None:
        if reserved_names is None or name not in reserved_names:
            # don't override existing symbols
            self.globals[name] = value

    @staticmethod
    def _get_saved_state_filename():
        return '/tmp/cache.hilda'

    @staticmethod
    def _to_ns_json_default(obj):
        if isinstance(obj, bytes):
            return f'__hilda_magic_key__|NSData|{base64.b64encode(obj).decode()}'
        elif isinstance(obj, datetime):
            return f'__hilda_magic_key__|NSDate|{obj.timestamp()}'
        raise TypeError

    @staticmethod
    def _from_ns_json_object_hook(obj: dict):
        parsed_object = {}
        for key, value in obj.items():
            parsed_object[HildaClient._from_ns_parse_function(key)] = HildaClient._from_ns_parse_function(value)
        return parsed_object

    @staticmethod
    def _from_ns_parse_function(obj):
        if isinstance(obj, list):
            return list(map(HildaClient._from_ns_parse_function, obj))
        if not isinstance(obj, str) or not obj.startswith('__hilda_magic_key__'):
            return obj
        _, type_, data = obj.split('|')
        if type_ == 'NSData':
            return base64.b64decode(data)
        if type_ == 'NSDictionary':
            return tuple(json.loads(data, object_hook=HildaClient._from_ns_json_object_hook).items())
        if type_ == 'NSArray':
            return tuple(json.loads(data, object_hook=HildaClient._from_ns_json_object_hook))
        if type_ == 'NSNumber':
            return eval(data)
        if type_ == 'NSNull':
            return None
        if type_ == 'NSDate':
            return datetime.fromtimestamp(eval(data), timezone.utc)

    def _serialize_call_params(self, argv):
        args_conv = []
        for arg in argv:
            if isinstance(arg, str) or isinstance(arg, bytes):
                if isinstance(arg, str):
                    arg = arg.encode()
                arg = ''.join([f'\\x{b:02x}' for b in arg])
                args_conv.append(f'(intptr_t)"{arg}"')
            elif isinstance(arg, int) or isinstance(arg, Symbol):
                arg = int(arg) & 0xffffffffffffffff
                args_conv.append(f'0x{arg:x}')
            else:
                raise NotImplementedError('cannot serialize argument')
        return args_conv

    def _generate_call_expression(self, address, params):
        args_type = ','.join(['intptr_t'] * len(params))
        args_conv = ','.join(params)

        if self.arch == 'arm64e':
            address = f'ptrauth_sign_unauthenticated((void *){address}, ptrauth_key_asia, 0)'

        return f'((intptr_t(*)({args_type}))({address}))({args_conv})'

    @staticmethod
    def _std_string(value: Symbol) -> str:
        if struct.unpack("b", (value + 23).peek(1))[0] >= 0:
            return value.peek_str()
        else:
            return value[0].peek_str()

    @cached_property
    def _object_identifier(self) -> Symbol:
        return self.symbols.objc_getClass('VMUObjectIdentifier').objc_call('alloc').objc_call(
            'initWithTask:', self.symbols.mach_task_self())

    @cached_property
    def _ks(self) -> Optional['Ks']:
        if not lldb.KEYSTONE_SUPPORT:
            return False
        platforms = {'arm64': Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN),
                     'arm64e': Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN),
                     'x86_64h': Ks(KS_ARCH_X86, KS_MODE_64)}
        return platforms.get(self.arch)

    def _get_module_class_list(self, module_name: str):
        for m in self.target.module_iter():
            if module_name != m.file.basename:
                continue
            objc_classlist = m.FindSection('__DATA').FindSubSection('__objc_classlist')
            objc_classlist_addr = self.symbol(objc_classlist.GetLoadAddress(self.target))
            obj_c_code = (self._hilda_root / 'objective_c' / 'get_objectivec_class_by_module.m').read_text()
            obj_c_code = obj_c_code.replace('__count_objc_class', f'{objc_classlist.size // 8}').replace(
                '__objc_class_list',
                f'{objc_classlist_addr}')
            return json.loads(self.po(obj_c_code))

    def _get_symbol_or_float_from_sbvalue(self, value: lldb.SBValue) -> Union[float, Symbol]:
        # The `value` attribute of an SBValue stores a string representation of the actual value
        # in a python-compatible format, so we can eval it to get the native python value
        value = eval(value.value)
        if isinstance(value, float):
            return value
        return self.symbol(value)
