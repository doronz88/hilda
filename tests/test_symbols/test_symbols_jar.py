import pytest

from hilda.exceptions import SymbolAbsentError


def test_lazy_symbol_getattr(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.symbols.rand()


def test_lazy_symbol_getitem(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.symbols['rand']()


def test_get_absent_symbol(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    with pytest.raises(SymbolAbsentError):
        hilda_client.symbols.symbol_that_doesnt_exist


def test_find(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert 'malloc' not in hilda_client.symbols, 'expected malloc to not be present'

    # populate the jar
    hilda_client.symbols.malloc
    hilda_client.symbols.rand

    assert 1 == len(hilda_client.symbols.clean().find('malloc')), 'expected to find only one'
