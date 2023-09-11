from datetime import datetime, timezone

import pytest

from hilda.exceptions import ConvertingFromNSObjectError


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
    :param source: CFSTR to be converted to Python string.
    """
    cfstr = hilda_client.evaluate_expression(f'@"{source}"')
    assert cfstr
    assert hilda_client.decode_cf(cfstr) == source


def test_ns_data(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    data = b'\x01\x00asdasd\xff\xfe58'
    with hilda_client.safe_malloc(len(data)) as buffer:
        buffer.write(data)
        ns_data = hilda_client.evaluate_expression(f'[NSData dataWithBytes:(char *)0x{buffer:x} length:{len(data)}]')
        assert hilda_client.decode_cf(ns_data) == data


def test_ns_data_in_dict(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    data = b'\x01\x00asdasd\xff\xfe58'
    with hilda_client.safe_malloc(len(data)) as buffer:
        buffer.write(data)
        ns_dict = hilda_client.evaluate_expression(
            f'@{{"a": [NSData dataWithBytes:(char *)0x{buffer:x} length:{len(data)}]}}'
        )
        assert hilda_client.decode_cf(ns_dict) == {"a": data}


def test_ns_data_in_array(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    data = b'\x01\x00asdasd\xff\xfe58'
    with hilda_client.safe_malloc(len(data)) as buffer:
        buffer.write(data)
        ns_dict = hilda_client.evaluate_expression(
            f'@[[NSData dataWithBytes:(char *)0x{buffer:x} length:{len(data)}]]'
        )
        assert hilda_client.decode_cf(ns_dict) == [data]


@pytest.mark.parametrize('day, month, year', [(1, 1, 1970), (11, 10, 2021)])
def test_ns_date(hilda_client, day: int, month: int, year: int):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param day: Date day.
    :param month: Date month.
    :param year: Date year.
    """
    date = hilda_client.evaluate_expression(f'''
        NSDateComponents *comps = [NSDateComponents new];
        [comps setDay:{day}];
        [comps setMonth:{month}];
        [comps setYear:{year}];
        [comps setTimeZone:[NSTimeZone timeZoneWithAbbreviation:@"UTC"]];
        [[NSCalendar currentCalendar] dateFromComponents:comps];
    ''')
    assert hilda_client.decode_cf(date) == datetime(day=day, month=month, year=year, tzinfo=timezone.utc)


@pytest.mark.parametrize('source, result', [
    # Dictionaries
    ('@{@1:@1,@234234:@"asdasd",@"a":@[@0,@0],@"asdasd":@234234}',
     {'asdasd': 234234, 234234: 'asdasd', 1: 1, 'a': [0, 0]}),
    ('@{}', {}),
    ('@{"asdasds":324234}', {'asdasds': 324234}),
    ('@{[NSNull null]:324234}', {None: 324234}),
    ('@{@{"a":1}:324234}', {(("a", 1),): 324234}),
    ('@{@["a",1]:324234}', {("a", 1): 324234}),
    ('@{1:@{2:@{3:"a"}}}', {1: {2: {3: 'a'}}}),
    # Arrays
    ('@[@"asdasd",@234234,@1,@1,@{@"a":@0}]', ['asdasd', 234234, 1, 1, {'a': 0}]),
    ('@[]', []),
    ('@["asdasds",324234]', ['asdasds', 324234]),
    ('@[1,@[2,@[3,"a"]]]', [1, [2, [3, 'a']]]),
    # Sets
    ('[NSSet setWithArray: @[@"1", @42]]', ['1', 42])
])
def test_ns_nested_objects(hilda_client, source: str, result):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: NS object expression to be converted to Python object.
    :param result: Python object.
    """
    ns_object = hilda_client.evaluate_expression(source)
    assert ns_object
    assert hilda_client.decode_cf(ns_object) == result


def test_ns_none(hilda_client):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    """
    ns_object = hilda_client.evaluate_expression('[NSNull null]')
    assert hilda_client.decode_cf(ns_object) is None


@pytest.mark.parametrize('source', [0, 1, -1, 1.5, -1.5, 0xfffffffffffffffffff, -0xfffffffffffffffffff, 1 / 3])
def test_ns_number(hilda_client, source):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Number to convert from NS object.
    """
    ns_number = hilda_client.evaluate_expression(f'[NSDecimalNumber decimalNumberWithString:@"{source}"]')
    assert hilda_client.decode_cf(ns_number) == source


@pytest.mark.parametrize('source', [
    '[NSObject new]',
    '0x33',
])
def test_error_converting_from_ns(hilda_client, source):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param source: Expression to convert to python object.
    """
    with pytest.raises(ConvertingFromNSObjectError):
        hilda_client.decode_cf(hilda_client.evaluate_expression(source))
