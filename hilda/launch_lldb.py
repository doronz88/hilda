import logging
import os
from pathlib import Path
from typing import Optional

import click
import coloredlogs

coloredlogs.install(level=logging.DEBUG)


def disable_logs() -> None:
    logging.getLogger('asyncio').disabled = True
    logging.getLogger('parso.cache').disabled = True
    logging.getLogger('parso.cache.pickle').disabled = True
    logging.getLogger('parso.python.diff').disabled = True
    logging.getLogger('humanfriendly.prompts').disabled = True
    logging.getLogger('blib2to3.pgen2.driver').disabled = True


def execute(cmd: str) -> None:
    logging.debug(f'executing: {cmd}')
    return os.system(cmd)


@click.group()
def cli():
    pass


def start_remote(hostname: str, port: int, rc_script: str) -> None:
    # connect local LLDB client
    commands = [f'process connect connect://{hostname}:{port}',
                f'command script import {rc_script}']
    commands = '\n'.join(commands)
    execute(f'lldb --one-line "{commands}"')


def attach(name: Optional[str] = None, pid: Optional[int] = None, rc_script: Optional[str] = None) -> None:
    """ Attach to given process and start an lldb shell """
    commands = []
    if name is not None:
        commands.append(f'process attach -n {name}')
    elif pid is not None:
        commands.append(f'process attach -p {pid}')
    else:
        print('missing either process name or pid for attaching')
        return

    commands.append(f'command script import {os.path.join(Path(__file__).resolve().parent, "lldb_entrypoint.py")}')
    if rc_script is not None:
        commands.append(f'command script import {rc_script}')
    commands = '\n'.join(commands)

    execute(f'lldb --one-line "{commands}"')


@cli.command('remote')
@click.argument('hostname', default='localhost')
@click.argument('port', type=click.INT, default=1234)
def remote(hostname: str, port: int) -> None:
    """ Connect to remote debugserver at given address """
    start_remote(hostname, port, Path(__file__).resolve().parent / 'lldb_entrypoint.py')


@cli.command('bare')
def cli_bare():
    """ Just start an lldb shell """
    # connect local LLDB client
    commands = [f'command script import {Path(__file__).resolve().parent / "lldb_entrypoint.py"}']
    commands = '\n'.join(commands)
    execute(f'lldb --one-line "{commands}"')


@cli.command('attach')
@click.option('-n', '--name', help='process name to attach')
@click.option('-p', '--pid', type=click.INT, help='pid to attach')
def cli_attach(name: str, pid: int):
    """ Attach to given process and start an lldb shell """
    attach(name=name, pid=pid)


if __name__ == '__main__':
    disable_logs()
    cli()
