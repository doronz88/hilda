import pytest

from hilda.symbol import Symbol


def test_create_symbol_from_int(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    rand = hilda_client.symbols.rand
    assert rand() != Symbol.create(int(rand), hilda_client)()


def test_sanity(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    rand = hilda_client.symbols.rand
    assert rand() != rand()


def test_itemsize(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    addressing_sizes = [8, 4, 2, 1]
    rand = hilda_client.symbols.rand  # type: Symbol
    for i in range(len(addressing_sizes) - 1):
        rand.item_size = addressing_sizes[i]
        long_item = rand[0]
        rand.item_size = addressing_sizes[i + 1]
        short_item = rand[0]
        assert long_item & ((0x100 ** rand.item_size) - 1) == short_item


@pytest.mark.parametrize('augend, addend, result', [
    (1, 1, 2),
    (0, 1, 1),
    (1, 0, 1),
    (1, 1.5, 2.5),
])
def test_symbol_add(hilda_client, augend, addend, result):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    sum_ = hilda_client.symbol(augend) + addend
    reverse_sum = addend + hilda_client.symbol(augend)
    assert reverse_sum == sum_ == result


@pytest.mark.parametrize('minuend, subtrahend, difference', [
    (2, 1, 1),
    (1, 1, 0),
    (1, 0, 1),
])
def test_symbol_sub(hilda_client, minuend, subtrahend, difference):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    diff = hilda_client.symbol(minuend) - subtrahend
    reverse_diff = minuend - hilda_client.symbol(subtrahend)
    assert reverse_diff == diff == difference


@pytest.mark.parametrize('minuend, subtrahend, difference', [
    (2.5, 1, 1.5),
])
def test_symbol_rsub(hilda_client, minuend, subtrahend, difference):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    diff = minuend - hilda_client.symbol(subtrahend)
    assert diff == difference


@pytest.mark.parametrize('multiplier, multiplicand, product', [
    (1, 1, 1),
    (0, 1, 0),
    (1, 2, 2),
    (1, 1.5, 1.5),
])
def test_symbol_mul(hilda_client, multiplier, multiplicand, product):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    prod = hilda_client.symbol(multiplier) * multiplicand
    reverse_prod = multiplicand * hilda_client.symbol(multiplier)
    assert reverse_prod == prod
    assert prod == product


@pytest.mark.parametrize('value, fmt', [
    (1, '0x{:8x}'),
    (0x1122334455667788, '(intptr_t)0x{:x}'),
])
def test_formatting_symbol(hilda_client, value: int, fmt: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param value: Symbol's value.
    :param fmt: How to format symbol.
    """
    symbol = hilda_client.symbol(value)
    assert fmt.format(symbol) == fmt.format(value)


def test_po_cfstr(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.ns('ABC').po() == 'ABC'


def test_po_nsobject(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.objc_get_class('NSObject').new().po().startswith('<NSObject: ')


def test_cf_description_cfstr(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.CFSTR('ABC').cf_description == 'ABC'


def test_cf_description_nsobject(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert hilda_client.objc_get_class('NSObject').new().cf_description.startswith('<NSObject: ')
