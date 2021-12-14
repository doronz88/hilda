import os
from pathlib import Path

import click
from hilda import launch_lldb


@click.command()
@click.argument('process')
@click.argument('ssh_port', type=click.INT)
@click.option('--debug-port', type=click.INT, default=1234)
@click.option('--hostname', default='localhost')
def main(process, ssh_port, debug_port, hostname):
    """ Start debugserver at remote device and connect using lldb """
    launch_lldb.start_remote(debug_port, ssh_port, process, hostname,
                             os.path.join(Path(__file__).resolve().parent, "lldb_entrypoint.py"))


if __name__ == '__main__':
    launch_lldb.remote()
