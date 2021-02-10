import pytest

from hilda.exceptions import GettingObjectiveCClassError
from hilda.objective_c_symbol import ObjectiveCSymbol
from hilda.symbol import Symbol


def test_detecting_objective_c_members(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    dictionary = hilda_client.evaluate_expression('@{@"one": @1, @"two": @2}').objc_symbol
    assert isinstance(dictionary._used, Symbol) and not isinstance(dictionary._used, ObjectiveCSymbol)
    assert isinstance(dictionary.description, ObjectiveCSymbol)


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
    temp_dir_url = hilda_client.objc_get_class('NSFileManager').defaultManager().objc_symbol.temporaryDirectory
    temp_url = temp_dir_url.URLByAppendingPathComponent_(hilda_client.cf('temp.txt')).objc_symbol
    c_file_path = temp_url.path.cString()
    file_path = c_file_path.peek_str().decode()
    file_handle = hilda_client.symbols.mkstemp(c_file_path)
    max_path_len = hilda_client.evaluate_expression('PATH_MAX')
    try:
        with hilda_client.safe_malloc(max_path_len) as real_path:
            hilda_client.symbols.realpath(file_path, real_path)
            assert hilda_client.lsof()[file_handle] == real_path.peek_str().decode()
    finally:
        hilda_client.symbols.close(file_handle)
        hilda_client.symbols.unlink(file_path)


def test_is_objc_type(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    file_manager = hilda_client.objc_get_class('NSFileManager').defaultManager()
    assert hilda_client.is_objc_type(file_manager)
    temp_dir_url = file_manager.objc_symbol.temporaryDirectory.path.cString()
    assert not hilda_client.is_objc_type(temp_dir_url)


def test_is_objc_type_invalid_address(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert not hilda_client.is_objc_type(hilda_client.symbol(0))
