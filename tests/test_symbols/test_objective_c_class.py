import pytest

from hilda.objective_c_class import PropertyAttributes, convert_encoded_property_attributes


def test_calling_class_method_by_method_name(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    NSDictionary = hilda_client.objc_get_class('NSDictionary')
    dictionary = NSDictionary.dictionaryWithObjects_forKeys_count_(0, 0, 0)
    assert dictionary.po() == '{\n}'
    dictionary = NSDictionary['dictionaryWithObjects:forKeys:count:'](0, 0, 0)
    assert dictionary.po() == '{\n}'


def test_calling_class_method_via_objc_call(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    NSDictionary = hilda_client.objc_get_class('NSDictionary')
    dictionary = NSDictionary.objc_call('dictionaryWithObjects:forKeys:count:', 0, 0, 0)
    assert dictionary.po() == '{\n}'


def test_getting_class_method(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    NSDictionary = hilda_client.objc_get_class('NSDictionary')
    assert 'dictionaryWithObjects_forKeys_count_' in dir(NSDictionary)


def test_calling_super_class_method(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    NSDictionary = hilda_client.objc_get_class('NSDictionary')
    dictionary = NSDictionary.new()
    assert dictionary.po() == '{\n}'


def test_getting_super_class_method(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    NSDictionary = hilda_client.objc_get_class('NSDictionary')
    assert 'new' in dir(NSDictionary)


@pytest.mark.parametrize('encoded, result', [
    ('Tc,VcharDefault', PropertyAttributes(synthesize='charDefault', type_='char', list=[])),
    ('T{YorkshireTeaStruct=ic},VstructDefault',
     PropertyAttributes(synthesize='structDefault', type_='struct YorkshireTeaStruct { int x0; char x1; }', list=[])),
    ('T@,R,&,VidReadonlyRetainNonatomic',
     PropertyAttributes(synthesize='idReadonlyRetainNonatomic', type_='id', list=['readonly', 'strong'])),
    ('T^v', PropertyAttributes(synthesize=None, type_='void *', list=[])),
])
def test_convert_encoded_property_attributes(encoded: str, result: PropertyAttributes):
    """
    :param encoded: Property encoding.
    :param result: Parsed property data.
    """
    assert convert_encoded_property_attributes(encoded) == result


@pytest.mark.parametrize('sub_str', [
    '@interface NSObject',
    '+ alloc;',
    '@property (readonly,copy) NSString * description;',
])
def test_class_without_super_str(hilda_client, sub_str: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param sub_str: Substring that should appear in the str.
    """
    assert str(hilda_client.objc_get_class('NSObject')).count(sub_str) == 1
