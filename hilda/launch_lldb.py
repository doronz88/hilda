from pathlib import Path
import subprocess
import time
import sys
import os

import click


sys.path.append(subprocess.check_output(['lldb', '-P']).decode('utf8').strip())
import lldb


def tunnel_local_port(port):
    os.system(f'nohup iproxy {port} {port} >/dev/null 2>&1 &')


@click.command()
@click.argument('process')
@click.argument('ssh_port', type=click.INT)
@click.option('--debug-port', type=click.INT, default=1234)
def main(process, ssh_port, debug_port):
    # startup debugserver at remote
    tunnel_local_port(debug_port)
    assert not os.system(f'ssh -p {ssh_port} root@localhost "debugserver localhost:{debug_port} --attach={process} &"&')

    # wait for it to load
    time.sleep(1)

    # format target triple
    REMOTE_URL = f'connect://localhost:{debug_port}'

    # create new debugger connection
    debugger = lldb.SBDebugger.Create()
    debugger.SetAsync(False)

    # get reusable lldb vars
    error = lldb.SBError()
    listener = debugger.GetListener()

    # setup lldb platform/target
    target = debugger.CreateTarget(
        '', None, None, True, error)
    if not target.IsValid() or not error.Success():
        print(error)
        return

    # connect to remote target
    process = target.ConnectRemote(listener, REMOTE_URL, None, error)
    if not process.IsValid() or not error.Success():
        print(error)
        return

    # Make sure the launch went ok
    if process and process.GetProcessID() != lldb.LLDB_INVALID_PROCESS_ID:
        pid = process.GetProcessID()

        done = False
        while not done:
            event = lldb.SBEvent()
            if listener.WaitForEvent(20, event):
                if lldb.SBProcess.EventIsProcessEvent(event):
                    state = lldb.SBProcess.GetStateFromEvent(event)
                    print("process state changed event: %s" % (lldb.SBDebugger.StateAsCString(state)))

                    if state == lldb.eStateStopped:
                        break
                    else:
                        print('unsupported state')
                        return

    # get active (only) thread
    thread = process.GetSelectedThread()
    if not thread.IsValid():
        print('failed getting current thread')
        return

    lldb.debugger = debugger
    lldb.process = process
    lldb.target = target
    lldb.thread = thread

    debugger.SetAsync(False)

    from hilda.lldb_entrypoint import hilda
    hilda(debugger, None, None, None)

    # # connect local LLDB client
    # commands = [f'process connect connect://localhost:{debug_port}',
    #             f'command script import {os.path.join(Path(__file__).resolve().parent, "lldb_entrypoint.py")}']
    #
    # if script:
    #     exec_code = f'with open(\"{script}\") as f:' \
    #                 f'    exec(f.read())'
    #     commands.append(f'script {exec_code}')
    #     commands.append('exit')
    #
    # commands = '\n'.join(commands)
    # os.system(f'lldb --one-line "{commands}"')


if __name__ == '__main__':
    main()
