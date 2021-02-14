import pytest

from hilda.exceptions import CreatingObjectiveCSymbolError
from hilda.objective_c_symbol import ObjectiveCSymbol


@pytest.mark.parametrize('literal, result', [
    ('@{@"one": @1}', '{\n    one = 1;\n}'),
    ('@{}', '{\n}'),
])
def test_create_objective_c_symbol(hilda_client, literal: str, result: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param literal: ObjectiveC object literal.
    :param result: Object po.
    """
    assert hilda_client.evaluate_expression(literal).objc_symbol.po() == result


def test_fail_create_objective_c_symbol(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    with pytest.raises(CreatingObjectiveCSymbolError):
        hilda_client.symbol(1).objc_symbol


def test_access_missing_attribute(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = \
        hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    with pytest.raises(AttributeError):
        assert single_key_dictionary.attribute_that_doesnt_exist


def test_get_objective_c_ivar(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = \
        hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    assert single_key_dictionary._key.po() == 'one'


def test_change_objective_c_ivar(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = \
        hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    single_key_dictionary._key = hilda_client.cf('two')
    assert single_key_dictionary.description.po() == '{\n    two = 1;\n}'
    assert single_key_dictionary._key.po() == 'two'


def test_call_objective_c_property(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = \
        hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    assert single_key_dictionary.description.po() == '{\n    one = 1;\n}'


def test_call_objective_c_method_by_method_name(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    dictionary1 = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    dictionary2 = hilda_client.evaluate_expression('@{@"one": @2}').objc_symbol
    assert dictionary1.isEqualToDictionary_(dictionary1)
    assert not dictionary1.isEqualToDictionary_(dictionary2)


def test_call_objective_c_method_by_objc_call(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    dictionary1 = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    dictionary2 = hilda_client.evaluate_expression('@{@"one": @2}').objc_symbol
    assert dictionary1.objc_call('isEqualToDictionary:', dictionary1)
    assert not dictionary1.objc_call('isEqualToDictionary:', dictionary2)


def test_call_objective_c_property_returns_objc_object(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    dictionary1 = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    assert isinstance(dictionary1.description, ObjectiveCSymbol)


def test_call_objective_c_method_returns_objc_object(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    dictionary1 = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    assert isinstance(dictionary1.objectForKey_(hilda_client.cf('one')),
                      ObjectiveCSymbol)


def test_call_objective_c_method_returns_native_symbol(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    string1 = hilda_client.cf('asdasd').objc_symbol
    assert not isinstance(string1.UTF8String(), ObjectiveCSymbol)


@pytest.mark.parametrize('selector', [
    'alloc',  # Test super class methods.
    'init',  # Test super instance methods.
])
def test_super_method_in_symbol_dir(hilda_client, selector: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param selector: Superclass selector to test.
    """
    dict_dir = dir(hilda_client.cf({1: 2}).objc_symbol)
    assert selector in dict_dir
