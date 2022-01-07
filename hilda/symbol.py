from construct import FormatField
from contextlib import contextmanager
import struct
import os

from hilda.objective_c_class import Class

ADDRESS_SIZE_TO_STRUCT_FORMAT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}


class SymbolFormatField(FormatField):
    """
    A Symbol wrapper for construct
    """

    def __init__(self, client):
        super(SymbolFormatField, self).__init__('<', 'Q')
        self._client = client

    def _parse(self, stream, context, path):
        return self._client.symbol(FormatField._parse(self, stream, context, path))


class Symbol(int):
    PROXY_METHODS = ['peek', 'poke', 'peek_str', 'monitor', 'bp',
                     'disass', 'po', 'objc_call']

    @classmethod
    def create(cls, value: int, client):
        """
        Create a Symbol object.
        :param value: Symbol address.
        :param hilda.hilda_client.HildaClient client: Hilda client.
        :return: Symbol object.
        :rtype: Symbol
        """
        if not isinstance(value, int):
            raise TypeError()

        value &= 0xFFFFFFFFFFFFFFFF

        symbol = cls(value)

        # public properties
        symbol.retval_bit_count = client.RETVAL_BIT_COUNT
        symbol.is_retval_signed = True
        symbol.item_size = 8

        # private members
        symbol._client = client
        symbol._offset = 0
        symbol._file_address = None

        # getting more data out from lldb
        lldb_symbol = client.target.ResolveLoadAddress(int(symbol) & 0xFFFFFFFFFFFFFFFF)
        file_address = lldb_symbol.file_addr
        type_ = lldb_symbol.symbol.type
        filename = lldb_symbol.module.file.basename

        symbol._file_address = file_address
        symbol.type_ = type_
        symbol.filename = filename
        symbol.lldb_symbol = lldb_symbol

        for method_name in Symbol.PROXY_METHODS:
            getattr(symbol.__class__, method_name).__doc__ = \
                getattr(client, method_name).__doc__

        return symbol

    @property
    def file_address(self) -> int:
        """
        Get symbol file address (address without ASLR)
        :return: File address
        """
        return self._file_address

    @property
    def objc_class(self):
        """
        Get the objc class of the respected symbol
        :return: Class
        """
        return Class(self._client, self.objc_call('class'))

    @property
    def objc_symbol(self):
        """
        Get an ObjectiveC symbol of the same address
        :return: Object representing the ObjectiveC symbol
        """
        return self._client.objc_symbol(self)

    @property
    def cf_description(self):
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        return self._client.symbols.CFCopyDescription(self).po()

    @contextmanager
    def change_item_size(self, new_item_size: int):
        """
        Temporarily change item size
        :param new_item_size: Temporary item size
        """
        save_item_size = self.item_size
        self.item_size = new_item_size
        try:
            yield
        finally:
            self.item_size = save_item_size

    def peek(self, count):
        return self._client.peek(self, count)

    def poke(self, buf):
        return self._client.poke(self, buf)

    def peek_str(self, encoding=None):
        return self._client.peek_str(self, encoding)

    def monitor(self, **args):
        return self._client.monitor(self, **args)

    def bp(self, callback=None, **args):
        return self._client.bp(self, callback, **args)

    def disass(self, size, **args):
        return self._client.disass(self, self.peek(size), **args)

    def po(self, cast=None):
        return self._client.po(self, cast=cast)

    def objc_call(self, selector, *params):
        return self._client.objc_call(self, selector, *params)

    def close(self):
        """ Construct compliance. """
        pass

    def seek(self, offset, whence):
        """ Construct compliance. """
        if whence == os.SEEK_CUR:
            self._offset += offset
        elif whence == os.SEEK_SET:
            self._offset = offset - self
        else:
            raise IOError('Unsupported whence')

    def read(self, count):
        """ Construct compliance. """
        val = (self + self._offset).peek(count)
        self._offset += count
        return val

    def write(self, buf):
        """ Construct compliance. """
        val = (self + self._offset).poke(buf)
        self._offset += len(buf)
        return val

    def tell(self):
        """ Construct compliance. """
        return self + self._offset

    def __add__(self, other):
        try:
            return self._client.symbol(int(self) + other)
        except TypeError:
            return int(self) + other

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        try:
            return self._client.symbol(int(self) - other)
        except TypeError:
            return int(self) - other

    def __rsub__(self, other):
        try:
            return self._client.symbol(other - int(self))
        except TypeError:
            return other - int(self)

    def __mul__(self, other):
        try:
            return self._client.symbol(int(self) * other)
        except TypeError:
            return int(self) * other

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self._client.symbol(int(self) / other)

    def __floordiv__(self, other):
        return self._client.symbol(int(self) // other)

    def __mod__(self, other):
        return self._client.symbol(int(self) % other)

    def __and__(self, other):
        return self._client.symbol(int(self) & other)

    def __or__(self, other):
        return self._client.symbol(int(self) | other)

    def __xor__(self, other):
        return self._client.symbol(int(self) ^ other)

    def __getitem__(self, item):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        addr = self + item * self.item_size
        return self._client.symbol(
            struct.unpack(self._client.endianness + fmt, self._client.peek(addr, self.item_size))[0])

    def __setitem__(self, item, value):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self._client.endianness + fmt, int(value))
        self._client.poke(self + item * self.item_size, value)

    def __repr__(self):
        return f'<{type(self).__name__}: {hex(self)}>'

    def __str__(self):
        return hex(self)

    def __call__(self, *args, **kwargs):
        return self._client.call(self, args)
