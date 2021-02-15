from datetime import datetime, timezone

import pytest

from hilda.exceptions import ConvertingToCfObjectError


@pytest.mark.parametrize('source', [
    '',
    '3123123',
    'asdsdasd',
    '12312sadasd',
    'The quick brown fox jumps over the lazy frog123',
])
def test_cfstr(hilda_client, source: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Python string to be converted to CFSTR.
    """
    cfstr = hilda_client.CFSTR(source)
    assert cfstr
    po = cfstr.po()
    assert po == source or (not source and po == '<object returned empty description>')
    assert source in cfstr.cf_description
    assert 'NSString' in list(map(lambda sup: sup.name, cfstr.objc_class.iter_supers()))


def test_cf_data(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    data = b'\x01\x00asdasd\xff\xfe58'
    cf_data = hilda_client.cf(data).objc_symbol
    assert cf_data.bytes.read(len(data)) == data


@pytest.mark.parametrize('day, month, year', [(1, 1, 1970), (11, 10, 2021)])
def test_ns_date(hilda_client, day: int, month: int, year: int):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param day: Date day.
    :param month: Date month.
    :param year: Date year.
    """
    date_po = f'{year:04d}-{month:02d}-{day:02d} 00:00:00 +0000'
    assert hilda_client.cf(datetime(day=day, month=month, year=year, tzinfo=timezone.utc)).po() == date_po


@pytest.mark.parametrize('source, result', [
    ({'asdasd': 234234, 234234: 'asdasd', 1: True, 'a': [False, False]}, '{1=1;234234=asdasd;a=(0,0);asdasd=234234;}'),
    ({}, '{}'),
    ({'asdasds': 324234}, '{asdasds=324234;}'),
    ({1: {2: {3: 'a'}}}, '{1={2={3=a;};};}'),
    ({1: b'\x00\x01'}, '{1={length=2,bytes=0x0001};}'),
    ({1: datetime(1970, 1, 1, tzinfo=timezone.utc)}, '{1="1970-01-0100:00:00+0000";}'),
])
def test_cf_dict(hilda_client, source: dict, result: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Python object to be converted to CF object.
    :param result: PO result.
    """
    cf_object = hilda_client.cf(source)
    assert ''.join(cf_object.po().split()) == result
    assert 'NSDictionary' in list(map(lambda sup: sup.name, cf_object.objc_class.iter_supers()))


def test_cf_none(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    cf_object = hilda_client.cf(None)
    assert cf_object.po() == '<null>'
    assert cf_object.objc_class.name == 'NSNull'


@pytest.mark.parametrize('source, result', [
    (['asdasd', 234234, 1, True, {'a': False}], '(asdasd,234234,1,1,{a=0;})'),
    ([], '()'),
    (['asdasds', 324234], '(asdasds,324234)'),
    ([1, [2, [3, 'a']]], '(1,(2,(3,a)))'),
    (['asdasds', b'324234'], '(asdasds,{length=6,bytes=0x333234323334})'),
    (['asdasds', datetime(2014, 4, 1, tzinfo=timezone.utc)], '(asdasds,"2014-04-0100:00:00+0000")'),
])
def test_cf_array(hilda_client, source, result: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Python object to be converted to CF object.
    :param result: PO result.
    """
    cf_object = hilda_client.cf(source)
    assert ''.join(cf_object.cf_description.split()) == result
    assert 'NSArray' in list(map(lambda sup: sup.name, cf_object.objc_class.iter_supers()))


@pytest.mark.parametrize('source', [0, 1, -1, 1.5, -1.5, 0xfffffffffffffffffff, -0xfffffffffffffffffff, 1 / 3])
def test_cf_number(hilda_client, source):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Number to convert to CF object.
    """
    cf_object = hilda_client.cf(source)
    assert cf_object.po() == str(source)
    assert 'NSNumber' in list(map(lambda sup: sup.name, cf_object.objc_class.iter_supers()))


@pytest.mark.parametrize('source', [
    object(),
    {'aa', 123},
])
def test_error_converting_to_cf(hilda_client, source):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Python object to convert to CF object.
    """
    with pytest.raises(ConvertingToCfObjectError):
        hilda_client.cf(source)
