import os
import struct
from contextlib import contextmanager
from functools import cached_property
from typing import Any, Optional, Tuple

from construct import FormatField

from hilda.common import CfSerializable
from hilda.lldb_importer import lldb
from hilda.objective_c_class import Class

ADDRESS_SIZE_TO_STRUCT_FORMAT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}


class SymbolFormatField(FormatField):
    """
    A Symbol wrapper for construct
    """

    def __init__(self, client):
        super().__init__('<', 'Q')
        self._client = client

    def _parse(self, stream, context, path):
        return self._client.symbol(FormatField._parse(self, stream, context, path))


"""
A value identifying a `HildaSymbol`.

`HildaSymbol`s are either regular (i.e., named) symbols or anonymous symbols.

Regular symbols are uniquely identified by a `HildaSymbolId` (i.e., no two
instances of `HildaSymbol` have the same ID).
Note that several regular symbols may have the same address (with different names).

Anonymous symbols are not uniquely identified by a `HildaSymbolId`.
"""
HildaSymbolId = Tuple[Optional[str], int]


class Symbol(int):
    """
    Hilda's class representing a symbol (not necessarily an LLDB symbol).
    """

    PROXY_METHODS = ['peek', 'poke', 'peek_str', 'monitor', 'bp',
                     'disass', 'po', 'objc_call']

    @classmethod
    def create(cls, value: int, client, lldb_symbol: Optional[lldb.SBSymbol] = None,
               lldb_address: Optional[lldb.SBAddress] = None, lldb_type: Optional[int] = None) -> None:
        """
        Create a Symbol object.
        :param value: Symbol address.
        :param hilda.hilda_client.HildaClient client: Hilda client.
        :param lldb.SBSymbol lldb_symbol: LLDB symbol.
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
        if lldb_address is None:
            lldb_address = client.target.ResolveLoadAddress(int(symbol) & 0xFFFFFFFFFFFFFFFF)
        if lldb_type is None:
            lldb_type = lldb_address.symbol.type
        symbol.type_ = lldb_type
        symbol.lldb_address = lldb_address
        symbol.lldb_symbol = lldb_symbol

        for method_name in Symbol.PROXY_METHODS:
            getattr(symbol.__class__, method_name).__doc__ = \
                getattr(client, method_name).__doc__

        return symbol

    @property
    def id(self) -> HildaSymbolId:
        return (self.lldb_name, int(self))

    @property
    def lldb_name(self) -> Optional[str]:
        return self.lldb_symbol.GetName() if self.lldb_symbol is not None else None

    @cached_property
    def file_address(self) -> int:
        """
        Get symbol file address (address without ASLR)
        :return: File address
        """
        return self.lldb_address.file_addr

    @cached_property
    def filename(self):
        return self.lldb_address.module.file.basename

    @property
    def objc_class(self) -> Class:
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
    def cf_description(self) -> str:
        """
        Get output from CFCopyDescription()
        :return: CFCopyDescription()'s output as a string
        """
        return self._client.symbols.CFCopyDescription(self).po()

    @property
    def name(self) -> str:
        symbol_info = int(self._client.po(f'[{self._client._object_identifier} symbolForAddress:{self}]', '__int128'))
        arg1 = symbol_info & 0xffffffffffffffff
        arg2 = symbol_info >> 64
        return self._client.symbols.CSSymbolGetName(arg1, arg2).peek_str()

    @contextmanager
    def change_item_size(self, new_item_size: int) -> None:
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

    def py(self) -> CfSerializable:
        return self._client.decode_cf(self)

    def peek(self, count: int):
        return self._client.peek(self, count)

    def poke(self, buf: bytes) -> None:
        return self._client.poke(self, buf)

    def poke_text(self, code: str) -> int:
        return self._client.poke_text(self, code)

    def peek_str(self) -> str:
        return self._client.peek_str(self)

    def peek_std_str(self) -> str:
        return self._client.peek_std_str(self)

    def monitor(self, **args):
        return self._client.monitor(self, **args)

    def watch(self, **args):
        return self._client.watchpoints.add(self, **args)

    def bp(self, callback=None, **args):
        return self._client.bp(self, callback, **args)

    def disass(self, size, **args) -> lldb.SBInstructionList:
        return self._client.disass(self, self.peek(size), **args)

    def po(self, cast: Optional[str] = None) -> str:
        return self._client.po(self, cast=cast)

    def objc_call(self, selector: str, *params) -> Any:
        return self._client.objc_call(self, selector, *params)

    def close(self) -> None:
        """ Construct compliance. """
        pass

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> None:
        """ Construct compliance. """
        if whence == os.SEEK_CUR:
            self._offset += offset
        elif whence == os.SEEK_SET:
            self._offset = offset - self
        else:
            raise OSError('Unsupported whence')

    def read(self, count: int) -> bytes:
        """ Construct compliance. """
        val = (self + self._offset).peek(count)
        self._offset += count
        return val

    def write(self, buf: bytes) -> int:
        """ Construct compliance. """
        val = (self + self._offset).poke(buf)
        self._offset += len(buf)
        return val

    def tell(self) -> int:
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
        address = int(self)
        name = self.lldb_name
        if name is not None:
            return f'Symbol({name}, 0x{address:016X})'
        else:
            return f'AnonymousSymbol(0x{address:016X})'

    def __str__(self):
        return hex(self)

    def __call__(self, *args, **kwargs):
        return self._client.call(self, args)
