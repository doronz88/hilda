import lldb
import pytest

from hilda.hilda_client import HildaClient


@pytest.fixture(scope='function')
def hilda_client(lldb_debugger):
    client = HildaClient(lldb_debugger)
    client.init_dynamic_environment()
    lldb.hilda_client = client
    with client.stopped():
        yield client


@pytest.fixture(scope='session', autouse=True)
def disable_jetsam_memory_checks(lldb_debugger):
    client = HildaClient(lldb_debugger)
    lldb.hilda_client = client
    client.init_dynamic_environment()
    client.disable_jetsam_memory_checks()
