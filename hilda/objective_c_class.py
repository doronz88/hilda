import json
import os
import time
from collections import namedtuple
from functools import partial
from pathlib import Path
from uuid import uuid4

from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from hilda.exceptions import GettingObjectivCClassError
from hilda.objective_c_type_decoder import decode_type, decode_type_with_tail

Ivar = namedtuple('Ivar', 'name type_ offset')
Method = namedtuple('Method', 'name address type_ return_type is_class args_types')
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

    type_, tail = decode_type_with_tail(encoded[1:])
    attributes = []
    synthesize = None
    for attr in filter(None, tail.lstrip(',').split(',')):
        if attr[0] in conversions:
            attributes.append(conversions[attr[0]](attr))
        elif attr[0] == 'V':
            synthesize = attr[1:]

    return PropertyAttributes(type_=type_, synthesize=synthesize, list=attributes)


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
        :param hilda.hilda_client.HildaClient client:
        """
        with open(os.path.join(Path(__file__).resolve().parent, 'get_objectivec_class_description.fm'), 'r') as f:
            obj_c_code = f.read()
        obj_c_code = obj_c_code.format(address=0, class_name=class_name)
        class_symbol = Class(client, class_data=json.loads(client.po(obj_c_code)))
        if class_symbol.name != class_name:
            raise GettingObjectivCClassError()
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
        with open(os.path.join(Path(__file__).resolve().parent, 'get_objectivec_class_description.fm'), 'r') as f:
            obj_c_code = f.read()
        obj_c_code = obj_c_code.format(address=self._class_object, class_name=self.name)
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

        def hook(hilda, frame, bp_loc, options):
            hilda.log_info(f'self object has been stolen from {options["name"]}')
            hilda.log_info(f'removing breakpoints')
            for bp_id, bp in list(hilda.breakpoints.items()):
                if 'group_uuid' in bp.options and bp.options.get('group_uuid', '') == options['group_uuid']:
                    hilda.remove_hilda_breakpoints(bp_id)
            captured = hilda.registers.x0
            if hilda.is_objc_type(captured):
                captured = captured.objc_symbol
            hilda.captured_objects[options['name'].split(' ')[0].split('[')[1]] = captured
            hilda.cont()

        group_uuid = str(uuid4())
        self.bp(hook, group_uuid=group_uuid)

        if sync:
            class_name = self.name
            self._client.cont()
            self._client.log_debug('Waiting for desired object to be captured...')
            while class_name not in self._client.captured_objects:
                time.sleep(1)

            return self._client.captured_objects[class_name]

    def monitor(self, **kwargs):
        """
        Proxy for monitor command.
        """
        for method in self.methods:
            kwargs['name'] = f'[{self.name} {method.name}]'
            method.address.monitor(**kwargs)

    def bp(self, **kwargs):
        """
        Proxy for bp command.
        """
        for method in self.methods:
            kwargs['name'] = f'[{self.name} {method.name}]'
            method.address.bp(**kwargs)

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
            Ivar(name=ivar['name'], type_=decode_type(ivar['type']), offset=ivar['offset'])
            for ivar in data['ivars']
        ]
        self.properties = [
            Property(name=prop['name'], attributes=convert_encoded_property_attributes(prop['attributes']))
            for prop in data['properties']
        ]
        self.methods = [
            Method(name=method['name'],
                   address=self._client.symbol(method['address']),
                   type_=method['type'],
                   return_type=decode_type(method['return_type']),
                   is_class=method['is_class'],
                   args_types=list(map(decode_type, method['args_types'])))
            for method in data['methods']
        ]

    def __dir__(self):
        result = set()

        for method in self.methods:
            if method.is_class:
                result.add(method.name.replace(':', '_'))

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.is_class:
                    result.add(method.name.replace(':', '_'))

        result.update(list(super(Class, self).__dir__()))
        return list(result)

    def __str__(self):
        protocol_buf = f'<{",".join(self.protocols)}>' if self.protocols else ''

        buf = f'@interface {self.name}: {self.super.name} {protocol_buf}\n'

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
            if ':' in method.name:
                args_names = method.name.split(':')
                name = ' '.join(['{}:({})'.format(*arg) for arg in zip(args_names, method.args_types[2:])])
            else:
                name = method.name
            prefix = '+' if method.is_class else '-'
            buf += f'{prefix} {name}; // 0x{int(method.address):x} (returns: {method.return_type})\n'

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
