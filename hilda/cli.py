from pathlib import Path
from typing import Callable, List, Mapping, Optional

import click

from hilda import launch_lldb


@click.group()
def cli():
    pass


def common_options(func: Callable) -> Callable:
    """ Decorator to add common options to commands """

    @click.option('-f', '--startup_files', multiple=True, default=None, help='Files to run on start')
    @click.pass_context
    def new_func(ctx, *args, **kwargs):
        return ctx.invoke(func, *args, **kwargs)

    return new_func


def parse_envp(ctx, param, value):
    env_list = []
    for item in value:
        try:
            key, val = item.split('=', 1)
            env_list.append(f'{key}={val}')
        except ValueError:
            raise click.BadParameter(f'Invalid format for --envp: {item}. Expected KEY=VALUE.')
    return env_list


@cli.command('remote')
@click.argument('hostname', default='localhost')
@click.argument('port', type=click.INT, default=1234)
@common_options
def remote(hostname: str, port: int, startup_files: Optional[List[str]] = None) -> None:
    """ Connect to remote debugserver at given address """
    launch_lldb.remote(hostname, port, startup_files)


@cli.command('attach')
@click.option('-n', '--name', help='process name to attach')
@click.option('-p', '--pid', type=click.INT, help='pid to attach')
@common_options
def attach(name: str, pid: int, startup_files: Optional[List[str]] = None) -> None:
    """ Attach to given process and start a lldb shell """
    launch_lldb.attach(name=name, pid=pid, startup_files=startup_files)


@cli.command('launch')
@click.argument('exec_path')
@click.option('--argv', multiple=True, default=None, help='Command line arguments to pass to the process')
@click.option('--envp', multiple=True, callback=parse_envp, help='Environment variables in the form KEY=VALUE')
@click.option('--stdin', type=Path, help='Redirect stdin from this file path')
@click.option('--stdout', type=Path, help='Redirect stdout to this file path')
@click.option('--stderr', type=Path, help='Redirect stderr to this file path')
@click.option('--wd', type=Path, help='Set the working directory for the process')
@click.option('--flags', type=int, default=0, help='Launch flags (bitmask)')
@click.option('--stop-at-entry', is_flag=True, help='Stop the process at the entry point')
@common_options
def launch(exec_path: str, argv: Optional[List] = None, envp: Optional[Mapping] = None,
           stdin: Optional[Path] = None,
           stdout: Optional[Path] = None, stderr: Optional[Path] = None, wd: Optional[Path] = None,
           flags: Optional[int] = 0, stop_at_entry: Optional[bool] = False,
           startup_files: Optional[List[str]] = None) -> None:
    """ Attach to given process and start a LLDB shell """
    if not argv:
        argv = None
    if not envp:
        envp = None
    launch_lldb.launch(exec_path, argv, envp, stdin, stdout, stderr, wd, flags, stop_at_entry, startup_files)


@cli.command('bare')
def cli_bare():
    """ Just start a lldb shell """
    # connect local LLDB client
    commands = [f'command script import {Path(__file__).resolve().parent / "lldb_entrypoint.py"}']
    commands = '\n'.join(commands)
    launch_lldb.execute(f'lldb --one-line "{commands}"')
