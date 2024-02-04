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
    single_key_dictionary = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    with pytest.raises(AttributeError):
        assert single_key_dictionary.attribute_that_doesnt_exist


def test_get_objective_c_ivar(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    assert single_key_dictionary._key.po() == 'one'


def test_change_objective_c_ivar(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
    single_key_dictionary._key = hilda_client.ns('two')
    assert single_key_dictionary.description.po() == '{\n    two = 1;\n}'
    assert single_key_dictionary._key.po() == 'two'


def test_call_objective_c_property(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    single_key_dictionary = hilda_client.evaluate_expression('@{@"one": @1}').objc_symbol
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


def test_call_objective_c_method_returns_native_symbol(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    string1 = hilda_client.ns('asdasd').objc_symbol
    assert not isinstance(string1.UTF8String(), ObjectiveCSymbol)


@pytest.mark.parametrize('selector', [
    'alloc',  # Test super class methods.
    'init',  # Test super instance methods.
    'dictionaryWithObjects_forKeys_',  # Test class methods.
    'objectForKey_',  # Test instance methods.
    'allKeys',  # Test instance properties.
])
def test_symbol_dir(hilda_client, selector: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param selector: Superclass selector to test.
    """
    dict_dir = dir(hilda_client.ns({1: 2}).objc_symbol)
    assert dict_dir.count(selector) == 1


@pytest.mark.parametrize('sub_str', [
    '@interface NSObject',
    '+ alloc;',
    'Class isa = 0x',
    '@property (readonly,copy) NSString * description;',
])
def test_symbol_without_super_str(hilda_client, sub_str: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param sub_str: Substring that should appear in the str.
    """
    assert str(hilda_client.objc_get_class('NSObject').new().objc_symbol).count(sub_str) == 1


@pytest.mark.parametrize('sub_str', [
    '@interface',  # Class declaration.
    'NSMutableDictionary',  # Class type.
    'Class isa = 0x',  # Ivar.
    '@property (readonly,copy) NSString * description;',  # Property.
    '+ automaticallyNotifiesObserversForKey:(id);',  # Class method.
    '- removeAllObjects;',  # Instance method.
])
def test_symbol_str(hilda_client, sub_str: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param sub_str: Substring that should appear in the str.
    """
    assert hilda_client.ns({1: 2, 3: 4}).objc_symbol._to_str().count(sub_str) == 1


def test_symbol_str_not_recursive(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert '+ alloc;' not in hilda_client.ns({1: 2, 3: 4}).objc_symbol._to_str(False)


def test_symbol_str_recursive(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    assert '+ alloc;' in hilda_client.ns({1: 2, 3: 4}).objc_symbol._to_str(True)


def test_set_implementation(hilda_client):
    pid = hilda_client.symbols.getpid()

    hilda_client.objc_get_class('NSJSONSerialization').get_method('isValidJSONObject:').set_implementation(
        hilda_client.symbols.getpid)
    assert hilda_client.objc_get_class('NSJSONSerialization').isValidJSONObject_() == pid
