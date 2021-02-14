import json
import os
from collections import namedtuple
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from hilda.exceptions import HildaException
from hilda.objective_c_class import Class, convert_encoded_property_attributes, Method, Property
from hilda.objective_c_type_decoder import decode_type
from hilda.symbol import Symbol

Ivar = namedtuple('Ivar', 'name value type_ offset')


class SettingIvarError(HildaException):
    """ Raise when trying to set an Ivar too early or when the Ivar doesn't exist. """
    pass


@dataclass
class Ivar:
    name: str
    value: Symbol
    type_: str
    offset: int


class ObjectiveCSymbol(Symbol):
    """
    Wrapper object for an objective-c symbol.
    Allowing easier access to its properties, methods and ivars.
    """

    @classmethod
    def create(cls, value: int, client):
        """
        Create an ObjectiveCSymbol object.
        :param value: Symbol address.
        :param hilda.hilda_client.HildaClient client: hilda client.
        :return: ObjectiveCSymbol object.
        :rtype: ObjectiveCSymbol
        """
        symbol = super(ObjectiveCSymbol, cls).create(value, client)
        symbol.ivars = []
        symbol.properties = []
        symbol.methods = []
        symbol.class_ = None  # type: Class
        symbol.reload()
        return symbol

    def reload(self):
        """
        Reload object's in-memory layout.
        """
        self.ivars.clear()
        self.properties.clear()
        self.methods.clear()
        self.class_ = None

        with open(os.path.join(Path(__file__).resolve().parent, 'get_objectivec_symbol_data.fm'), 'r') as f:
            obj_c_code = f.read()

        obj_c_code = obj_c_code.format(address=int(self))
        data = json.loads(self._client.po(obj_c_code))

        self._reload_ivars(data['ivars'])
        self._reload_properties(data['properties'])
        self._reload_methods(data['methods'])

        data['name'] = data['class_name']
        data['address'] = data['class_address']
        data['super'] = data['class_super']
        self.class_ = Class(self._client, self._client.symbol(data['class_address']), data)

    def show(self):
        """
        Print to terminal the highlighted class description.
        """
        print(highlight(str(self), ObjectiveCLexer(), TerminalTrueColorFormatter(style='native')))

    def objc_call(self, selector: str, *params):
        """
        Make objc_call() from self return ObjectiveCSymbol when it's an objc symbol.
        :param selector: Selector to execute.
        :param params: Additional parameters.
        :return: ObjectiveCSymbol when return type is an objc symbol.
        """
        symbol = super(ObjectiveCSymbol, self).objc_call(selector, *params)
        return symbol.objc_symbol if self._client.is_objc_type(symbol) else symbol

    def _reload_ivars(self, ivars_data):
        raw_ivars = sorted(ivars_data, key=lambda ivar: ivar['offset'])
        for i, ivar in enumerate(raw_ivars):
            ivar_type = decode_type(ivar['type'])
            value = ivar['value']
            if i < len(raw_ivars) - 1:
                # The .fm file returns a 64bit value, regardless of the real size.
                size = raw_ivars[i + 1]['offset'] - ivar['offset']
                value = value & ((2 ** (size * 8)) - 1)
            ivar_value = self._client.symbol(value)
            self.ivars.append(Ivar(name=ivar['name'], type_=ivar_type, offset=ivar['offset'], value=ivar_value))

    def _reload_properties(self, properties_data):
        for prop in properties_data:
            prop_attributes = convert_encoded_property_attributes(prop['attributes'])
            self.properties.append(Property(name=prop['name'], attributes=prop_attributes))

    def _reload_methods(self, methods_data):
        self.methods = [
            Method(name=method['name'],
                   address=self._client.symbol(method['address']),
                   type_=method['type'],
                   return_type=decode_type(method['return_type']),
                   is_class=method['is_class'],
                   args_types=list(map(decode_type, method['args_types'])))
            for method in methods_data
        ]

    def __dir__(self):
        result = []

        for ivar in self.ivars:
            result.append(ivar.name)

        for method in self.methods:
            result.append(method.name.replace(':', '_'))

        for sup in self.class_.iter_supers():
            for method in sup.methods:
                result.append(method.name.replace(':', '_'))

        result += list(super(ObjectiveCSymbol, self).__dir__())
        return result

    def __getitem__(self, item):  # noqa: C901

        if isinstance(item, int):
            return super(ObjectiveCSymbol, self).__getitem__(item)

        # Ivars
        for ivar in self.ivars:
            if ivar.name == item:
                if self._client.is_objc_type(ivar.value):
                    return ivar.value.objc_symbol
                return ivar.value

        # Properties
        for prop in self.properties:
            if prop.name == item:
                return self.objc_call(item)

        # Methods
        for method in self.methods:
            if method.name == item:
                return partial(self.class_.objc_call, item) if method.is_class else partial(self.objc_call, item)

        for sup in self.class_.iter_supers():
            for method in sup.methods:
                if method.name == item:
                    return partial(self.class_.objc_call, item) if method.is_class else partial(self.objc_call, item)

        raise AttributeError(f''''{self.class_.name}' has no attribute {item}''')

    def __getattr__(self, item: str):
        return self[self.class_.sanitize_name(item)]

    def _set_ivar(self, name, value):
        try:
            ivars = self.__getattribute__('ivars')
            class_name = self.__getattribute__('class_').name
        except AttributeError as e:
            raise SettingIvarError from e

        for i, ivar in enumerate(ivars):
            if ivar.name == name:
                size = self.item_size
                if i < len(self.ivars) - 1:
                    size = ivars[i + 1].offset - ivar.offset
                with self.change_item_size(size):
                    self[ivar.offset // size] = value
                    ivar.value = value
                return
        raise SettingIvarError(f'Ivar "{name}" does not exist in "{class_name}"')

    def __setitem__(self, key, value):
        if isinstance(key, int):
            super(ObjectiveCSymbol, self).__setitem__(key, value)
            return

        with suppress(SettingIvarError):
            self._set_ivar(key, value)
            return

    def __setattr__(self, key, value):
        try:
            key = self.__getattribute__('class_').sanitize_name(key)
        except AttributeError:
            pass
        try:
            self._set_ivar(key, value)
        except SettingIvarError:
            super(ObjectiveCSymbol, self).__setattr__(key, value)

    def __str__(self):
        protocols_buf = f'<{",".join(self.class_.protocols)}>' if self.class_.protocols else ''

        buf = f'@interface {self.class_.name}: {self.class_.super.name} {protocols_buf}\n'

        # Add ivars
        buf += '{\n'
        for ivar in self.ivars:
            buf += f'\t{ivar.type_} {ivar.name} = 0x{int(ivar.value):x}; // 0x{ivar.offset:x}\n'
        buf += '}\n'

        # Add properties
        for prop in self.properties:
            attrs = prop.attributes
            buf += f'@property ({",".join(attrs.list)}) {prop.attributes.type_} {prop.name};\n'

            if attrs.synthesize is not None:
                buf += f'@synthesize {prop.name} = {attrs.synthesize};\n'

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
