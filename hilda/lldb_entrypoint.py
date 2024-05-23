#!/usr/bin/xcrun python3

import logging

import coloredlogs
import lldb

from hilda.hilda_client import HildaClient

lldb.hilda_client = None


def hilda(debugger, command, result, internal_dict):
    coloredlogs.install(level=logging.DEBUG)

    if lldb.hilda_client is None:
        lldb.hilda_client = HildaClient(debugger)

    additional_namespace = {'ui': lldb.hilda_client.ui_manager}
    lldb.hilda_client.interact(additional_namespace=additional_namespace)


def __lldb_init_module(debugger, internal_dict):
    debugger.SetAsync(True)
    debugger.HandleCommand('command script add -f lldb_entrypoint.hilda hilda')
    print('''
    👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇👇
    Use `hilda` command to get into Hilda interactive shell.
    If you "continue" before doing so, you cannot do it later.
    👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆👆
    ''')
