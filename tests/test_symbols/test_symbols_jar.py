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
