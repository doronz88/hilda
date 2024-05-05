import lldb
import pytest

from hilda.exceptions import LLDBException
from hilda.hilda_client import HildaClient
from hilda.launch_lldb import LLDBAttachName

PROCESS = 'sysmond'


@pytest.fixture(scope='session')
def lldb_debugger(request):
    lldb_t = None
    try:
        lldb_t = LLDBAttachName(PROCESS)
        lldb_t.start()
        yield lldb_t.debugger
    except LLDBException as e:
        pytest.exit(f'{e.message} - Try use sudo')
    finally:
        if lldb_t:
            lldb_t.process.Detach()
            lldb_t.join()


@pytest.fixture(scope='function')
def hilda_client(lldb_debugger):
    client = HildaClient(lldb_debugger)
    lldb.hilda_client = client
    client.init_dynamic_environment()
    with client.stopped():
        yield client
