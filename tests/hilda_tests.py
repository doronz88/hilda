from pathlib import Path

import click

from hilda import launch_lldb

PROCESS = 'sysmond'


@click.command()
def main():
    """ Start debugserver at remote device and connect using lldb """
    launch_lldb.attach(name=PROCESS, rc_script=str(Path(__file__).resolve().parent / 'lldb_entrypoint.py'))


if __name__ == '__main__':
    launch_lldb.remote()
