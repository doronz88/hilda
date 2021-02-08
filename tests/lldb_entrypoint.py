#!/usr/bin/xcrun python3

import logging

import lldb
import pytest

logging.getLogger('parso.cache').disabled = True
logging.getLogger('parso.cache.pickle').disabled = True
logging.getLogger('parso.python.diff').disabled = True
logging.getLogger('humanfriendly.prompts').disabled = True

lldb.hilda_client = None


class AddDebuggerPlugin:
    def __init__(self, debugger):
        self.__name__ = 'AddDebuggerPlugin'
        self.debugger = debugger

    @pytest.fixture(scope='session')
    def lldb_debugger(self, request):
        return request.config.pluginmanager.get_plugin('AddDebuggerPlugin').debugger


def run_tests(debugger, command, result, internal_dict):
    pytest.main(command.split(), plugins=[AddDebuggerPlugin(debugger)])


def __lldb_init_module(debugger, internal_dict):
    debugger.SetAsync(True)
    debugger.HandleCommand('command script add -f lldb_entrypoint.run_tests run_tests')
    print('Use "run_tests" command')
