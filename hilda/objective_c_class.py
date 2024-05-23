import json
import time
from collections import namedtuple
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any
from uuid import uuid4

from objc_types_decoder.decode import decode as decode_type
from objc_types_decoder.decode import decode_with_tail
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from hilda.exceptions import GettingObjectiveCClassError
from hilda.symbols_jar import SymbolsJar

Ivar = namedtuple('Ivar', 'name type_ offset')
Property = namedtuple('Property', 'name attributes')
PropertyAttributes = namedtuple('PropertyAttributes', 'synthesize type_ list')


def convert_encoded_property_attributes(encoded):
    conversions = {
        'R': lambda x: 'readonly',
        'C': lambda x: 'copy',
        '&': lambda x: 'strong',
        'N': lambda x: 'nonatomic',
        'G': lambda x: 'getter=' + x[1:],
        'S': lambda x: 'setter=' + x[1:],
        'd': lambda x: 'dynamic',
        'W': lambda x: 'weak',
        'P': lambda x: '<garbage-collected>',
        't': lambda x: 'encoding=' + x[1:],
    }

    type_, tail = decode_with_tail(encoded[1:])
    attributes = []
    synthesize = None
    for attr in filter(None, tail.lstrip(',').split(',')):
        if attr[0] in conversions:
            attributes.append(conversions[attr[0]](attr))
        elif attr[0] == 'V':
            synthesize = attr[1:]

    return PropertyAttributes(type_=type_, synthesize=synthesize, list=attributes)


@dataclass
class Method:
    name: str
    client: Any = field(compare=False)
    address: int = field(compare=False)
    imp: int = field(compare=False)
    type_: str = field(compare=False)
    return_type: str = field(compare=False)
    is_class: bool = field(compare=False)
    args_types: list = field(compare=False)

    @staticmethod
    def from_data(data: dict, client):
        """
        Create Method object from raw data.
        :param data: Data as loaded from get_objectivec_symbol_data.m.
        :param hilda.hilda_client.HildaClient client: Hilda client.
        """
        return Method(
            name=data['name'],
            client=client,
            address=client.symbol(data['address']),
            imp=client.symbol(data['imp']),
            type_=data['type'],
            return_type=decode_type(data['return_type']),
            is_class=data['is_class'],
            args_types=list(map(decode_type, data['args_types']))
        )

    def set_implementation(self, new_imp: int):
        self.client.symbols.method_setImplementation(self.address, new_imp)
        self.imp = self.client.symbol(new_imp)

    def __str__(self):
        if ':' in self.name:
            args_names = self.name.split(':')
            name = ' '.join(['{}:({})'.format(*arg) for arg in zip(args_names, self.args_types[2:])])
        else:
            name = self.name
        prefix = '+' if self.is_class else '-'
        return f'{prefix} {name}; // 0x{self.address:x} (returns: {self.return_type})\n'


class Class(object):
    """
    Wrapper for ObjectiveC Class object.
    """

    def __init__(self, client, class_object=0, class_data: dict = None):
        """
        :param hilda.hilda_client.HildaClient client:
        :param hilda.symbol.Symbol class_object:
        """
        self._client = client
        self._class_object = class_object
        self.protocols = []
        self.ivars = []
        self.properties = []
        self.methods = []
        self.name = ''
        self.super = None
        if class_data is None:
            self.reload()
        else:
            self._load_class_data(class_data)

    @staticmethod
    def from_class_name(client, class_name: str):
        """
        Create ObjectiveC Class from given class name.
        :param hilda.hilda_client.HildaClient client: Hilda client.
        :param class_name: Class name.
        """
        obj_c_code = (Path(__file__).parent / 'objective_c' / 'get_objectivec_class_description.m').read_text()
        obj_c_code = obj_c_code.replace('__class_address__', '0').replace('__class_name__', class_name)
        class_symbol = Class(client, class_data=json.loads(client.po(obj_c_code)))
        if class_symbol.name != class_name:
            raise GettingObjectiveCClassError()
        return class_symbol

    @staticmethod
    def sanitize_name(name: str):
        """
        Sanitize python name to ObjectiveC name.
        """
        if name.startswith('_'):
            name = '_' + name[1:].replace('_', ':')
        else:
            name = name.replace('_', ':')
        return name

    def reload(self):
        """
        Reload class object data.
        Should be used whenever the class layout changes (for example, during method swizzling)
        """
        obj_c_code = (Path(__file__).parent / 'objective_c' / 'get_objectivec_class_description.m').read_text()
        obj_c_code = obj_c_code.replace('__class_address__', f'{self._class_object:d}')
        obj_c_code = obj_c_code.replace('__class_name__', self.name)
        self._load_class_data(json.loads(self._client.po(obj_c_code)))

    def show(self):
        """
        Print to terminal the highlighted class description.
        """
        print(highlight(str(self), ObjectiveCLexer(), TerminalTrueColorFormatter(style='native')))

    def objc_call(self, sel: str, *args):
        """
        Invoke a selector on the given class object.
        :param sel: Selector name.
        :return: whatever the selector returned as a symbol.
        """
        return self._class_object.objc_call(sel, *args)

    def get_method(self, name: str):
        """
        Get a specific method implementation.
        :param name: Method name.
        :return: Method.
        """
        for method in self.methods:
            if method.name == name:
                return method

    def capture_self(self, sync: bool = False):
        """
        Capture the first called `self` from this class.
        Access using `self.captured_objects`
        :param sync: Should wait until captured object is returned?
        :return: Captured object if sync is True, None otherwise
        """
        class_name = self.name

        if class_name in self._client.captured_objects:
            del self._client.captured_objects[class_name]

        def hook(hilda, frame, bp_loc, options):
            hilda.log_info(f'self object has been captured from {options["name"]}')
            hilda.log_info('removing breakpoints')
            for bp_id, bp in list(hilda.breakpoints.items()):
                if 'group_uuid' in bp.options and bp.options.get('group_uuid', '') == options['group_uuid']:
                    hilda.remove_hilda_breakpoint(bp_id)
            captured = hilda.evaluate_expression('$arg1')
            captured = captured.objc_symbol
            hilda.captured_objects[options['name'].split(' ')[0].split('[')[1]] = captured
            hilda.cont()

        group_uuid = str(uuid4())

        for method in self.methods:
            if not method.is_class:
                # only instance methods are relevant for capturing self
                method.imp.bp(hook, group_uuid=group_uuid,
                              name=f'-[{class_name} {method.name}]')

        if sync:
            self._client.cont()
            self._client.log_debug('Waiting for desired object to be captured...')
            while class_name not in self._client.captured_objects:
                time.sleep(1)

            return self._client.captured_objects[class_name]

    def monitor(self, **kwargs):
        """
        Proxy for monitor command.
        """
        self.symbols_jar.monitor(**kwargs)

    def bp(self, callback=None, **kwargs):
        """
        Proxy for bp command.
        """
        for method in self.methods:
            kwargs['name'] = f'[{self.name} {method.name}]'
            method.imp.bp(callback, **kwargs)

    def iter_supers(self):
        """
        Iterate over the super classes of the class.
        """
        sup = self.super
        while sup is not None:
            yield sup
            sup = sup.super

    def _load_class_data(self, data: dict):
        self._class_object = self._client.symbol(data['address'])
        self.super = Class(self._client, data['super']) if data['super'] else None
        self.name = data['name']
        self.protocols = data['protocols']
        self.ivars = [
            Ivar(name=ivar['name'], type_=decode_type(ivar['type']) if ivar['type'] else 'unknown_type_t',
                 offset=ivar['offset'])
            for ivar in data['ivars']
        ]
        self.properties = [
            Property(name=prop['name'], attributes=convert_encoded_property_attributes(prop['attributes']))
            for prop in data['properties']
        ]
        self.methods = [Method.from_data(method, self._client) for method in data['methods']]

    @property
    def symbols_jar(self) -> SymbolsJar:
        """ Get a SymbolsJar object for quick operations on all methods """
        jar = SymbolsJar.create(self._client)

        for m in self.methods:
            jar[f'[{self.name} {m.name}]'] = m.imp

        return jar

    def __dir__(self):
        result = set()

        for method in self.methods:
            if method.is_class:
                result.add(method.name.replace(':', '_'))

        for sup in self.iter_supers():
            if self._client.configs.nsobject_exclusion and sup.name == 'NSObject':
                continue
            for method in sup.methods:
                if method.is_class:
                    result.add(method.name.replace(':', '_'))

        result.update(list(super(Class, self).__dir__()))
        return list(result)

    def __str__(self):
        protocol_buf = f'<{",".join(self.protocols)}>' if self.protocols else ''

        if self.super is not None:
            buf = f'@interface {self.name}: {self.super.name} {protocol_buf}\n'
        else:
            buf = f'@interface {self.name} {protocol_buf}\n'

        # Add ivars
        buf += '{\n'
        for ivar in self.ivars:
            buf += f'\t{ivar.type_} {ivar.name}; // 0x{ivar.offset:x}\n'
        buf += '}\n'

        # Add properties
        for prop in self.properties:
            buf += f'@property ({",".join(prop.attributes.list)}) {prop.attributes.type_} {prop.name};\n'

            if prop.attributes.synthesize is not None:
                buf += f'@synthesize {prop.name} = {prop.attributes.synthesize};\n'

        # Add methods
        for method in self.methods:
            buf += str(method)

        buf += '@end'
        return buf

    def __repr__(self):
        return f'<objC Class "{self.name}">'

    def __getitem__(self, item):
        for method in self.methods:
            if method.name == item:
                if method.is_class:
                    return partial(self.objc_call, item)
                else:
                    raise AttributeError(f'{self.name} class has an instance method named {item}, '
                                         f'not a class method')

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.name == item:
                    if method.is_class:
                        return partial(self.objc_call, item)
                    else:
                        raise AttributeError(f'{self.name} class has an instance method named {item}, '
                                             f'not a class method')

        raise AttributeError(f''''{self.name}' class has no attribute {item}''')

    def __getattr__(self, item: str):
        return self[self.sanitize_name(item)]
