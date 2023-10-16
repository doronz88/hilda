import pytest

from hilda.exceptions import GettingObjectiveCClassError


def test_get_objc_class_error(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    with pytest.raises(GettingObjectiveCClassError):
        hilda_client.objc_get_class('classthatdoesntexist')


def test_call_symbol_with_bytes(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    b = bytes(range(0x100))
    with hilda_client.safe_malloc(len(b)) as a:
        hilda_client.symbols.memcpy(a, b, len(b))
        assert a.peek(len(b)) == b


def test_lsof(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    temp_dir_url = hilda_client.objc_get_class('NSFileManager').defaultManager().objc_call('temporaryDirectory')
    temp_url = temp_dir_url.objc_call('URLByAppendingPathComponent:', hilda_client.ns('temp.txt')).objc_symbol
    c_file_path = temp_url.path.objc_call('cString')
    file_path = c_file_path.peek_str()
    file_handle = hilda_client.symbols.mkstemp(c_file_path)
    max_path_len = hilda_client.evaluate_expression('PATH_MAX')
    try:
        with hilda_client.safe_malloc(max_path_len) as real_path:
            hilda_client.symbols.realpath(file_path, real_path)
            assert hilda_client.lsof()[file_handle] == real_path.peek_str()
    finally:
        hilda_client.symbols.close(file_handle)
        hilda_client.symbols.unlink(file_path)
