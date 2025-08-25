import pytest

from hilda.exceptions import SymbolAbsentError
from hilda.symbols import SymbolList


def test_filter_by_module(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    assert 'isdigit' in libsystem_c_symbols

    libobjc_symbols = hilda_client.symbols.filter_by_module('libobjc')
    assert 'isdigit' not in libobjc_symbols

    assert 'isdigit' in hilda_client.symbols


def test_iter(hilda_client):
    # Test that iteration does not fail
    i = 0
    for symbol in hilda_client.symbols:
        i += 1


def test_getitem(hilda_client):
    isdigit = hilda_client.symbols['isdigit']
    assert not isdigit(0x10)
    assert isdigit(0x30)


def test_delitem(hilda_client):
    symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    assert 'isdigit' in symbols

    isdigit = symbols.isdigit
    del symbols[isdigit]

    assert 'isdigit' not in symbols

    try:
        del symbols[isdigit]
        assert False
    except:  # noqa: E722
        pass

    assert 'isdigit' in hilda_client.symbols


def test_get(hilda_client):
    isdigit = hilda_client.symbols.get('isdigit')
    assert isdigit is not None

    assert hilda_client.symbols.get(int(isdigit)) is isdigit
    assert hilda_client.symbols.get('isdigit') is isdigit
    assert hilda_client.symbols.get(isdigit.id) is isdigit
    assert hilda_client.symbols.get(isdigit.lldb_symbol) is isdigit
    assert hilda_client.symbols.get(isdigit) is isdigit
    assert hilda_client.symbols.isdigit is isdigit

    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    assert libsystem_c_symbols.get(isdigit) is isdigit

    assert hilda_client.symbols.get(isdigit + 4) is None
    assert libsystem_c_symbols.get(isdigit + 4) is None


def test_get_absent_symbol(hilda_client):
    with pytest.raises(SymbolAbsentError):
        hilda_client.symbols.symbol_that_doesnt_exist


def test_add_symbol(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    isdigit = libsystem_c_symbols.isdigit

    assert libsystem_c_symbols.get(isdigit + 4) is None
    libsystem_c_symbols.add(isdigit + 4, 'test_symbol_in_isdigit_added_to_libsystem_c')
    assert libsystem_c_symbols.get(isdigit + 4) is not None
    assert libsystem_c_symbols.get('test_symbol_in_isdigit_added_to_libsystem_c') is not None

    assert hilda_client.symbols.get(isdigit + 4) is not None
    assert hilda_client.symbols.get('test_symbol_in_isdigit_added_to_libsystem_c') is not None


def test_getattr(hilda_client):
    assert hilda_client.symbols.x11223344 is not None
    assert hilda_client.symbols.x0x11223344 is not None
    assert hilda_client.symbols.malloc is not None


def test_sub_symbol_lists(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    l1 = SymbolList(hilda_client)
    l1.add(libsystem_c_symbols.isdigit)
    l2 = libsystem_c_symbols - l1
    assert libsystem_c_symbols.isdigit not in l2


def test_add_symbol_lists(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')

    l1 = SymbolList(hilda_client)
    l1.add(libsystem_c_symbols.isdigit)
    l2 = SymbolList(hilda_client)
    l3 = l2 + l1
    assert libsystem_c_symbols.isdigit in l3


def test_filter_symbol_type(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    assert libsystem_c_symbols.isdigit in libsystem_c_symbols.filter_code_symbols()
    assert libsystem_c_symbols.isdigit not in libsystem_c_symbols.filter_data_symbols()


def test_filter_startswith(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    filtered = libsystem_c_symbols.filter_startswith('is')
    assert libsystem_c_symbols.isdigit in filtered
    assert libsystem_c_symbols.isalpha in filtered
    assert libsystem_c_symbols.rand not in filtered


def test_filter_endswith(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    filtered = libsystem_c_symbols.filter_endswith('digit')
    assert libsystem_c_symbols.isdigit in filtered
    assert libsystem_c_symbols.isalpha not in filtered
    assert libsystem_c_symbols.rand not in filtered


def test_filter_name_contains(hilda_client):
    libsystem_c_symbols = hilda_client.symbols.filter_by_module('libsystem_c')
    filtered = libsystem_c_symbols.filter_name_contains('dig')
    assert libsystem_c_symbols.isdigit in filtered
    assert libsystem_c_symbols.isalpha not in filtered
    assert libsystem_c_symbols.rand not in filtered
    assert libsystem_c_symbols.isdigit in libsystem_c_symbols.filter_name_contains('is')
