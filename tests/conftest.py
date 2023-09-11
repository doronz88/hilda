import lldb
import pytest

from hilda.hilda_client import HildaClient


@pytest.fixture(scope='function')
def hilda_client(lldb_debugger):
    client = HildaClient(lldb_debugger)
    lldb.hilda_client = client
    client.init_dynamic_environment()
    with client.stopped():
        yield client
