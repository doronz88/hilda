import json
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from objc_types_decoder.decode import decode as decode_type
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import ObjectiveCLexer

from hilda.exceptions import HildaException
from hilda.objective_c_class import Class, Method, Property, convert_encoded_property_attributes
from hilda.symbol import Symbol
from hilda.symbols_jar import SymbolsJar


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
        symbol.ivars = []  # type: List[Ivar]
        symbol.properties = []  # type: List[Property]
        symbol.methods = []  # type: List[Method]
        symbol.class_ = None  # type: Optional[Class]
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

        obj_c_code = (Path(__file__).parent / 'objective_c' / 'get_objectivec_symbol_data.m').read_text()
        obj_c_code = obj_c_code.replace('__symbol_address__', f'{self:d}')
        data = json.loads(self._client.po(obj_c_code))

        self._reload_ivars(data['ivars'])
        self._reload_properties(data['properties'])
        self.methods = [Method.from_data(method, self._client) for method in data['methods']]

        data['name'] = data['class_name']
        data['address'] = data['class_address']
        data['super'] = data['class_super']
        self.class_ = Class(self._client, self._client.symbol(data['class_address']), data)

    def show(self, recursive: bool = False):
        """
        Print to terminal the highlighted class description.
        :param recursive: Show methods of super classes.
        """
        print(highlight(self._to_str(recursive), ObjectiveCLexer(), TerminalTrueColorFormatter(style='native')))

    def _reload_ivars(self, ivars_data):
        raw_ivars = sorted(ivars_data, key=lambda ivar: ivar['offset'])
        for i, ivar in enumerate(raw_ivars):
            ivar_type = ivar['type']
            if ivar_type:
                ivar_type = decode_type(ivar_type)
            else:
                ivar_type = 'unknown_type_t'
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

    def _to_str(self, recursive=False):
        protocols_buf = f'<{",".join(self.class_.protocols)}>' if self.class_.protocols else ''

        if self.class_.super is not None:
            buf = f'@interface {self.class_.name}: {self.class_.super.name} {protocols_buf}\n'
        else:
            buf = f'@interface {self.class_.name} {protocols_buf}\n'

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
        methods = self.methods.copy()

        # Add super methods.
        if recursive:
            for sup in self.class_.iter_supers():
                for method in filter(lambda m: m not in methods, sup.methods):
                    methods.append(method)

        # Print class methods first.
        methods.sort(key=lambda m: not m.is_class)

        for method in methods:
            buf += str(method)

        buf += '@end'
        return buf

    @property
    def symbols_jar(self) -> SymbolsJar:
        """ Get a SymbolsJar object for quick operations on all methods """
        jar = SymbolsJar.create(self._client)

        for m in self.methods:
            jar[m.name] = m.address

        return jar

    def __dir__(self):
        result = set()

        for ivar in self.ivars:
            result.add(ivar.name)

        for method in self.methods:
            result.add(method.name.replace(':', '_'))

        for sup in self.class_.iter_supers():
            if self._client.configs.nsobject_exclusion and sup.name == 'NSObject':
                continue
            for method in sup.methods:
                result.add(method.name.replace(':', '_'))

        result.update(list(super(ObjectiveCSymbol, self).__dir__()))
        return list(result)

    def __getitem__(self, item):
        if isinstance(item, int):
            return super(ObjectiveCSymbol, self).__getitem__(item)

        # Ivars
        for ivar in self.ivars:
            if ivar.name == item:
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
        return self._to_str(False)

    def __repr__(self):
        return f'<{self.__class__.__name__} 0x{int(self):x} Class: {self.class_.name}>'
