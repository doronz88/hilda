import pytest

from hilda.hilda_client import HildaClient
from hilda.launch_lldb import create_hilda_client_using_attach_by_name

PROCESS = 'sysmond'


@pytest.fixture(scope='function')
def hilda_client() -> HildaClient:
    with create_hilda_client_using_attach_by_name(PROCESS) as hilda_client:
        yield hilda_client
