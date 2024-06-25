import logging
from pathlib import Path
from typing import List, Optional

import click
import coloredlogs

from hilda import launch_lldb
from hilda._version import version
from hilda.launch_lldb import create_hilda_client_using_attach_by_name, create_hilda_client_using_attach_by_pid, \
    create_hilda_client_using_launch, create_hilda_client_using_remote_attach

DEFAULT_HILDA_PORT = 1234

coloredlogs.install(level=logging.DEBUG)


@click.group()
def cli():
    pass


startup_files_option = click.option('-f', '--startup_files', multiple=True, help='Files to run on start')


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
def remote(hostname: str, port: int, startup_files: List[str]) -> None:
    """ Connect to remote debugserver at given address """
    with create_hilda_client_using_remote_attach(hostname, port) as hilda_client:
        hilda_client.interact(startup_files=startup_files)


@cli.command('attach')
@click.option('-n', '--name', help='process name to attach')
@click.option('-p', '--pid', type=click.INT, help='pid to attach')
@startup_files_option
def attach(name: Optional[str], pid: Optional[int], startup_files: List[str]) -> None:
    """ Attach to given process and start a lldb shell """
    if name is not None:
        hilda_client = create_hilda_client_using_attach_by_name(name)
    elif pid is not None:
        hilda_client = create_hilda_client_using_attach_by_pid(name)
    else:
        raise click.UsageError('You must specify a process name or pid')
    hilda_client.interact(startup_files=startup_files)
    hilda_client.detach()


@cli.command('bare')
def cli_bare() -> None:
    """ Just start a lldb shell """
    commands = [f'command script import {Path(__file__).resolve().parent / "lldb_entrypoint.py"}']
    commands = '\n'.join(commands)
    launch_lldb.execute(f'lldb --one-line "{commands}"')


@cli.command('launch')
@click.argument('exec_path')
@click.option('--argv', multiple=True, help='Command line arguments to pass to the process')
@click.option('--envp', multiple=True, callback=parse_envp, help='Environment variables in the form KEY=VALUE')
@click.option('--stdin', help='Redirect stdin from this file path')
@click.option('--stdout', help='Redirect stdout to this file path')
@click.option('--stderr', help='Redirect stderr to this file path')
@click.option('--cwd', help='Set the working directory for the process')
@click.option('--flags', type=click.INT, default=0, help='Launch flags (bitmask)')
@startup_files_option
def launch(exec_path: str, argv: List[str], envp: List[str], stdin: Optional[Path],
           stdout: Optional[Path], stderr: Optional[Path], cwd: Optional[Path], flags: Optional[int],
           startup_files: List[str]) -> None:
    """ Attach to a given process and start a lldb shell """
    argv = list(argv)
    envp = list(envp)
    with create_hilda_client_using_launch(
            exec_path, argv, envp, stdin, stdout, stderr, cwd, flags) as hilda_client:
        hilda_client.interact(startup_files=startup_files)


@cli.command('version')
def cli_version() -> None:
    """Show the version information."""
    click.echo(version)
