import logging
from pathlib import Path
from typing import List, Mapping, Optional

import click
import coloredlogs

from hilda import launch_lldb
from hilda._version import version

DEFAULT_HILDA_PORT = 1234

coloredlogs.install(level=logging.DEBUG)


@click.group()
def cli():
    pass


startup_files_option = click.option('-f', '--startup_files', multiple=True, default=None, help='Files to run on start')


def parse_envp(ctx: click.Context, param: click.Parameter, value: List[str]) -> List[str]:
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
@click.argument('port', type=click.INT, default=DEFAULT_HILDA_PORT)
@startup_files_option
def remote(hostname: str, port: int, startup_files: Optional[List[str]] = None) -> None:
    """ Connect to remote debugserver at given address """
    launch_lldb.remote(hostname, port, startup_files)


@cli.command('attach')
@click.option('-n', '--name', help='process name to attach')
@click.option('-p', '--pid', type=click.INT, help='pid to attach')
@startup_files_option
def attach(name: str, pid: int, startup_files: Optional[List[str]] = None) -> None:
    """ Attach to given process and start a lldb shell """
    launch_lldb.attach(name=name, pid=pid, startup_files=startup_files)


@cli.command('launch')
@click.argument('exec_path')
@click.option('--argv', multiple=True, help='Command line arguments to pass to the process')
@click.option('--envp', multiple=True, callback=parse_envp, help='Environment variables in the form KEY=VALUE')
@click.option('--stdin', type=str, help='Redirect stdin from this file path')
@click.option('--stdout', type=str, help='Redirect stdout to this file path')
@click.option('--stderr', type=str, help='Redirect stderr to this file path')
@click.option('--cwd', type=str, help='Set the working directory for the process')
@click.option('--flags', type=click.INT, default=0, help='Launch flags (bitmask)')
@startup_files_option
def launch(exec_path: str, argv: Optional[List] = None, envp: Optional[Mapping] = None,
           stdin: Optional[Path] = None,
           stdout: Optional[Path] = None, stderr: Optional[Path] = None, cwd: Optional[Path] = None,
           flags: Optional[int] = 0,
           startup_files: Optional[List[str]] = None) -> None:
    """ Attach to a given process and start a lldb shell """
    argv = list(argv) if argv else None
    envp = list(envp) if envp else None
    launch_lldb.launch(exec_path, argv, envp, stdin, stdout, stderr, cwd, flags, startup_files)


@cli.command('bare')
def cli_bare():
    """ Just start a lldb shell """
    commands = [f'command script import {Path(__file__).resolve().parent / "lldb_entrypoint.py"}']
    commands = '\n'.join(commands)
    launch_lldb.execute(f'lldb --one-line "{commands}"')


@cli.command('version')
def cli_version():
    """Show the version information."""
    click.echo(version)
