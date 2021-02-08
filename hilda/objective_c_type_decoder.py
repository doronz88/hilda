SIMPLE_TYPES = {
    'c': 'char',
    'i': 'int',
    's': 'short',
    'l': 'long',
    'q': 'long long',
    'C': 'unsigned char',
    'I': 'unsigned int',
    'S': 'unsigned short',
    'L': 'unsigned long',
    'Q': 'unsigned long long',
    'f': 'float',
    'd': 'double',
    'B': 'BOOL',
    'v': 'void',
    '*': 'char *',
    '@': 'id',
    '#': 'Class',
    ':': 'SEL',
    'b': 'int',  # TODO: parse to bit fields
    '?': '<unknown-type>',
}

TYPE_SPECIFIERS = {
    'r': 'const',
    'n': 'in',
    'N': 'inout',
    'o': 'out',
    'O': 'bycopy',
    'R': 'byref',
    'V': 'oneway'
}


def index_of_closing_char(s: str, open_: str, close: str) -> int:
    depth = 0
    for i in range(len(s)):
        depth += {open_: 1, close: -1}.get(s[i], 0)
        if not depth:
            return i


# Decoders

def decode_pointer(encoded):
    decoded = decode_type_recursive(encoded[1:])
    return {'kind': 'pointer', 'type': decoded, 'tail': decoded['tail']}


def decode_type_specifier(encoded):
    decoded = decode_type_recursive(encoded[1:])
    return {'kind': 'specifier', 'type': decoded, 'tail': decoded['tail'], 'specifier': TYPE_SPECIFIERS[encoded[0]]}


def decode_struct(encoded: str):
    close_index = index_of_closing_char(encoded, '{', '}')
    struct_str = encoded[1:close_index]
    try:
        name = struct_str[:struct_str.index('=')]
    except ValueError:
        name = ''
    else:
        struct_str = struct_str[len(name) + 1:]
    long_tail = encoded[close_index + 1:]
    types_in_struct = []
    while struct_str:
        decoded = decode_type_recursive(struct_str)
        types_in_struct.append(decoded)
        struct_str = decoded['tail']
    return {'kind': 'struct', 'types': types_in_struct, 'name': name, 'tail': long_tail}


def decode_array(encoded: str):
    tail = encoded[1:-1]
    digits = ''
    for i in range(len(tail)):
        if tail[i].isdigit():
            digits += tail[i]
        else:
            break
    tail = tail[len(digits):]
    # If the type is omitted, assume 'void *'
    decoded = decode_type_recursive(tail if tail else '^v')
    return {'kind': 'array', 'count': digits, 'type': decoded, 'tail': decoded['tail']}


def decode_name(encoded):
    close_index = encoded.index('"', 1)
    return {'kind': 'name', 'name': encoded[1:close_index], 'tail': encoded[close_index + 1:]}


def decode_type_recursive(encoded: str):
    if encoded[0] in SIMPLE_TYPES:
        return {'kind': 'simple', 'type': SIMPLE_TYPES[encoded[0]], 'tail': encoded[1:]}
    elif encoded[0] in TYPE_SPECIFIERS:
        return decode_type_specifier(encoded)
    elif encoded[0] == '^':
        return decode_pointer(encoded)
    elif encoded[0] == '{':
        return decode_struct(encoded)
    elif encoded[0] == '[':
        return decode_array(encoded)
    elif encoded[0] == '"':
        return decode_name(encoded)
    return decode_name(f'"{encoded}"')


# Descriptions

def description_for_pointer(type_dictionary):
    return description_for_type(type_dictionary['type']) + ' *'


def description_for_specifier(type_dictionary):
    return type_dictionary['specifier'] + ' ' + description_for_type(type_dictionary['type'])


def description_for_simple(type_dictionary):
    tail = type_dictionary['tail']
    if type_dictionary['type'] == 'id' and tail:
        if tail[0] == '"':
            name = decode_type_recursive(tail)['name']
            return name + ' *'
        elif tail[0] == '?':
            return 'id /* block */'
    return type_dictionary['type']


def description_for_struct(type_dictionary):
    name = (type_dictionary['name'] + ' ') if type_dictionary['name'] != '?' else ''
    desc = 'struct ' + name + '{ '
    for i, type_ in enumerate(type_dictionary['types']):
        desc += description_for_type(type_) + f' x{i}; '
    desc += '}'
    return desc


def description_for_array(type_dictionary):
    return description_for_type(type_dictionary['type']) + f' x[{type_dictionary["count"]}]'


def description_for_name(type_dictionary):
    return type_dictionary['name']


def description_for_type(type_dictionary):
    return {
        'pointer': description_for_pointer,
        'specifier': description_for_specifier,
        'simple': description_for_simple,
        'struct': description_for_struct,
        'array': description_for_array,
        'name': description_for_name
    }[type_dictionary['kind']](type_dictionary)


def decode_type(encoded):
    return description_for_type(decode_type_recursive(encoded))


def decode_type_with_tail(encoded):
    decoded = decode_type_recursive(encoded)
    return description_for_type(decoded), decoded.get('tail')
