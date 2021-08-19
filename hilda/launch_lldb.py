import logging
import os
import time
from pathlib import Path

import click
import coloredlogs

coloredlogs.install(level=logging.DEBUG)
logging.getLogger('asyncio').disabled = True
logging.getLogger('parso.cache').disabled = True
logging.getLogger('parso.cache.pickle').disabled = True
logging.getLogger('parso.python.diff').disabled = True
logging.getLogger('humanfriendly.prompts').disabled = True


def tunnel_local_port(port):
    execute(f'pymobiledevice3 lockdown forward {port} {port} -d')


def execute(cmd):
    logging.debug(f'executing: {cmd}')
    return os.system(cmd)


@click.group()
def cli():
    pass


@cli.command('remote')
@click.argument('process')
@click.argument('ssh_port', type=click.INT)
@click.option('--debug-port', type=click.INT, default=1234)
def remote(process, ssh_port, debug_port):
    """ Start debugserver at remote device and connect using lldb """
    tunnel_local_port(debug_port)
    assert not execute(
        f'ssh -i ~/.ssh/id_rsa -p {ssh_port} root@localhost "debugserver localhost:{debug_port} --attach={process}"&')

    # wait for it to load
    time.sleep(1)

    # connect local LLDB client
    commands = [f'process connect connect://localhost:{debug_port}',
                f'command script import {os.path.join(Path(__file__).resolve().parent, "lldb_entrypoint.py")}']
    commands = '\n'.join(commands)
    execute(f'lldb --one-line "{commands}"')


@cli.command('bare')
def bare():
    """ Just start an lldb shell """
    # connect local LLDB client
    commands = [f'command script import {os.path.join(Path(__file__).resolve().parent, "lldb_entrypoint.py")}']
    commands = '\n'.join(commands)
    execute(f'lldb --one-line "{commands}"')


if __name__ == '__main__':
    cli()
