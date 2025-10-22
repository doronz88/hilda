import json
import re
import shlex
from itertools import chain
from tempfile import NamedTemporaryFile
from typing import Iterator, Optional, Tuple, Union

from tqdm import tqdm

from hilda.exceptions import SymbolAbsentError
from hilda.lldb_importer import lldb
from hilda.symbol import HildaSymbolId, Symbol


class SymbolList:
    """
    Manager for `Symbol` objects, each one representing a symbol.

    `Symbol`s are either regular (i.e., named) symbols or anonymous symbols.
    Only regular symbols are managed by this class, though anonymous
    symbols can be created by this class (using the function `add`).
    """

    def __init__(self, hilda) -> None:
        """
        Initialize a symbol list.

        :param hilda.hilda_client.HildaClient hilda: Hilda client
        """
        self._hilda = hilda
        self._modules = set()
        self._symbols = {}
        self._symbols_by_name = {}

        # There should be only one "global" symbol list instance, and it should be referenced by the HildaClient class.
        # The global symbols list contains (lazily) all symbols (from all modules).
        if not hasattr(hilda, 'symbols'):
            self._global = self
        else:
            self._global = hilda.symbols

    def __iter__(self) -> Iterator[Symbol]:
        self._populate_cache()

        for symbol in self._symbols.values():
            yield symbol

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __contains__(self,
                     address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) -> bool:
        return self.get(address_or_name_or_id_or_symbol) is not None

    def __getitem__(self,
                    address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) -> Symbol:
        """
        Get a symbol by address or name or ID (or the symbol itself, though it usually makes little sense)

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        """
        symbol = self.get(address_or_name_or_id_or_symbol)
        if symbol is None:
            raise SymbolAbsentError(f'no such symbol: {address_or_name_or_id_or_symbol}')
            # raise KeyError(address_or_name_or_id_or_symbol)
        return symbol

    def __delitem__(self,
                    address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) -> None:
        """
        Remove a symbol (unless this is the global symbol list - see remove())

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        """
        self.remove(address_or_name_or_id_or_symbol)

    def __repr__(self) -> str:
        if self._global is self:
            return (f'<{self.__class__.__name__} GLOBAL>')
        else:
            return repr(list(self))

    def __str__(self) -> str:
        return repr(self)

    def get(self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) \
            -> Optional[Symbol]:
        """
        Get a symbol by address or name or ID (or the symbol itself, though it usually makes little sense)

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        :return: `Symbol` if one exists, or `None` otherwise
        """
        symbol = self._get_lldb_symbol(address_or_name_or_id_or_symbol)
        if symbol is None:
            return None

        lldb_symbol, lldb_address, name, address, type_ = symbol
        sym_id = (name, address)
        if sym_id not in self._symbols and self._global is self:
            symbol = Symbol.create(address, self._hilda, lldb_symbol, lldb_address, type_)
            self._add(sym_id, symbol)
            return symbol

        return self._symbols.get(sym_id)

    def _populate_cache(self, module_uuid_filter=None) -> None:
        if self._global is self:
            modules = self._hilda.target.modules
            modules_not_cached = [module for module in modules if module.GetUUIDString() not in self._modules]
            if module_uuid_filter is not None:
                modules_not_cached = [module for module in modules if module.GetUUIDString() == module_uuid_filter]
            if len(modules_not_cached) != 0:
                for lldb_module in tqdm(modules_not_cached, desc='Populating Hilda symbols cache'):
                    for lldb_symbol in lldb_module.symbols:
                        _ = self.get(lldb_symbol)
                    self._modules.add(lldb_module.GetUUIDString())

    def force_refresh(self, module_range=None, module_filename_filter=''):
        """
        Force a refresh of symbols
        :param module_range: index range for images to load in the form of [start, end]
        :param module_filename_filter: filter only images containing given expression
        """
        self.log_debug('Force symbols')

        if self._global is not self:
            self._hilda.log_error('Cannot refresh a non-global symbol list')
            return

        for i, lldb_module in enumerate(tqdm(self._hilda.target.modules)):
            filename = lldb_module.file.basename

            if module_filename_filter not in filename:
                continue

            if module_range is not None and (i < module_range[0] or i > module_range[1]):
                continue

            for lldb_symbol in lldb_module.symbols:
                # Getting the symbol would insert it if it does not exist
                _ = self.get(lldb_symbol)

    def _add(self, sym_id: HildaSymbolId, symbol: Symbol) -> None:
        self._symbols[sym_id] = symbol
        name, address = sym_id
        if name is not None and re.match(r'^[a-zA-Z0-9_]+$', name):
            ids = self._symbols_by_name.get(name)
            if ids is not None:
                ids.append(sym_id)
            else:
                self._symbols_by_name[name] = [sym_id]

    def add(self, value: Union[int, Symbol], symbol_name: Optional[str] = None, symbol_type: Optional[str] = None,
            symbol_size: Optional[int] = None) -> Symbol:
        """
        Add a symbol.
        Returns existing symbol if a matching regular (i.e., non-anonymous) symbol exists.

        :param value: The address of the symbol (in memory) or and existing `Symbol`.
        :param symbol_name: The name of the symbol.
        :param symbol_type: The type of the symbol (either 'code' of 'data', defaults to 'code').
        :param symbol_size: The size of the symbol (defaults to 8 bytes).
        :return: The symbol
        """
        # Check if we already created the symbol
        if (isinstance(value, Symbol) and
                (symbol_type, symbol_size) == (None, None) and
                value.lldb_symbol is not None and

                # TODO: Is it an error to add again, providing the same name?
                (symbol_name is None or symbol_name == value.lldb_name)):
            self._add(value.id, value)
            return value

        # Adding an existing anonymous symbol. Ignore the fact that this is actually a symbol.
        if isinstance(value, Symbol) and value.lldb_name is None:
            value = int(value)

        # Adding an existing symbol. Do not provide any other arguments.
        if isinstance(value, Symbol) and (symbol_name, symbol_type, symbol_size) != (None, None, None):
            raise ValueError()

        # Adding a new symbol without specifying a name. Symbol type and size are not (currently) supported.
        if isinstance(value, int) and symbol_name is None and (symbol_type, symbol_size) != (None, None):
            raise ValueError()

        # Add

        # Check if we can get a global symbol
        symbol_address = value
        global_symbol = self._global.get(symbol_address) if symbol_name is None else (
            self._global.get((symbol_name, symbol_address)))
        if global_symbol is not None:
            if (symbol_type, symbol_size) != (None, None):
                raise ValueError()
            return self.add(global_symbol)

        # Check if this is an anonymous symbol
        if symbol_name is None:
            # Anonymous symbols need not be added to _symbols.
            return Symbol.create(symbol_address, self._hilda, None)

        # Add a new global symbol
        symbol = self._global._add_lldb_symbol(
            symbol_name,
            symbol_address,
            symbol_type if symbol_type is not None else 'code',
            symbol_size if symbol_size is not None else 8)
        return self.add(symbol)

    def _remove(self, sym_id: HildaSymbolId) -> None:
        del self._symbols[sym_id]
        name, address = sym_id
        if name is not None and re.match(r'^[a-zA-Z0-9_]+$', name):
            ids = self._symbols_by_name[name]
            if len(ids) == 1:
                ids.remove(sym_id)
            else:
                del self._symbols_by_name[name]

    def remove(self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) -> None:
        """
        Remove a symbol.

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        """
        if self._global is self:
            raise Exception('Cannot remove from the global symbols list')

        symbol = self[address_or_name_or_id_or_symbol]
        self._remove(symbol.id)

    def items(self) -> Iterator[Tuple[HildaSymbolId, Symbol]]:
        """
        Get a symbol ID and symbol object tuple for every symbol
        """
        return ((symbol.id, symbol) for symbol in self)

    def keys(self) -> Iterator[HildaSymbolId]:
        """
        Get the symbol ID for every symbol
        """
        return (symbol.id for symbol in self)

    def values(self) -> Iterator[Symbol]:
        """
        Get the symbol object for every symbol
        """
        return (symbol for symbol in self)

    def __getattr__(self, attribute_name: str) -> Symbol:
        """
        Returns a symbol appropriate to the attribute requested.

        For example:
            support a `symbols.malloc()` syntax.
            support a `symbols.x0x11223344` syntax.
            support a `symbols.x11223344` syntax.
        """
        match = re.fullmatch(r'x(?:0x)?([0-9a-fA-F]{6,16})', attribute_name)
        if match:
            address = int(match[1], base=0x10)
            return self.add(address)
        value = self.get(attribute_name)
        if value is None:
            raise SymbolAbsentError(f"SymbolList object has no attribute '{attribute_name}'")
        return value

    def __dir__(self):
        self._populate_cache()

        # Return normal attributes and symbol names
        return chain(super().__dir__(), self._symbols_by_name.keys())

    def _get_lldb_symbol_from_name(self, name: str, address: Optional[int] = None) \
            -> Optional[Tuple[lldb.SBSymbol, lldb.SBAddress, str, int, int]]:
        lldb_symbol_context_list = list(self._hilda.target.FindSymbols(name))

        if address is not None:
            for lldb_symbol_context in list(lldb_symbol_context_list):
                lldb_symbol_context_address = lldb_symbol_context.symbol.GetStartAddress().GetLoadAddress(
                    self._hilda.target)
                if lldb_symbol_context_address != address:
                    lldb_symbol_context_list.remove(lldb_symbol_context)
                    self._hilda.log_debug(f'Ignoring symbol {name}@0x{lldb_symbol_context_address:016X} '
                                          f'(beacause address is not 0x{address:016X})')

        symbols = []
        for lldb_symbol_context in lldb_symbol_context_list:
            symbol = self._get_lldb_symbol(lldb_symbol_context.symbol)
            if symbol is None:
                # Ignoring symbol - failed to convert
                continue

            if address is not None:
                lldb_symbol, lldb_address, symbol_name, symbol_address, symbol_type = symbol
                if address != symbol_address:
                    continue

            symbols.append(symbol)

        if len(symbols) == 0:
            return None

        # TODO: Should we really pick the first? Maybe the last? Something else?
        # if len(lldb_symbols) != 1:
        #     # Error out if we found multiple symbols with the same name and same address
        #     raise KeyError((name, address))

        return symbols[0]

    def _get_lldb_symbol(self, value: Union[int, str, HildaSymbolId, Symbol, lldb.SBAddress, lldb.SBSymbol]) \
            -> Optional[Tuple[lldb.SBSymbol, lldb.SBAddress, str, int, int]]:
        if isinstance(value, Symbol):
            symbol = value
            return self._get_lldb_symbol(symbol.id)
        elif isinstance(value, int):
            address = value & 0xFFFFFFFFFFFFFFFF
            lldb_address = self._hilda.target.ResolveLoadAddress(address)
            return self._get_lldb_symbol(lldb_address)
        elif isinstance(value, tuple):  # HildaSymbolId
            if len(value) != 2:
                raise TypeError()
            name, address = value
            if not (name is None or isinstance(name, str)):
                raise TypeError()
            if not (isinstance(address, int)):
                raise TypeError()

            if name is None:
                return self._get_lldb_symbol(address)
            else:
                return self._get_lldb_symbol_from_name(name, address)
        elif isinstance(value, str):
            name = value
            return self._get_lldb_symbol_from_name(name)
        elif isinstance(value, lldb.SBAddress):
            lldb_address = value
            lldb_symbol_context = self._hilda.target.ResolveSymbolContextForAddress(lldb_address,
                                                                                    lldb.eSymbolContextEverything)
            lldb_symbol = lldb_symbol_context.symbol

            address = lldb_address.GetLoadAddress(self._hilda.target)
            lldb_symbol_address = lldb_symbol.GetStartAddress().GetLoadAddress(self._hilda.target)
            if address != lldb_symbol_address:
                return None

            return self._get_lldb_symbol(lldb_symbol)
        elif isinstance(value, lldb.SBSymbol):
            lldb_symbol = value

            # Ignore symbols not having a real name
            symbol_name = lldb_symbol.GetName()
            if symbol_name in ('<redacted>',):
                return None

            # Ignore symbols not having a real address
            lldb_address = lldb_symbol.GetStartAddress()
            symbol_address = lldb_address.GetLoadAddress(self._hilda.target)
            if symbol_address == 0xffffffffffffffff:
                return None

            # Ignore symbols not having a useful type
            symbol_type = lldb_symbol.GetType()
            if symbol_type not in (lldb.eSymbolTypeCode,
                                   lldb.eSymbolTypeRuntime,
                                   lldb.eSymbolTypeData,
                                   lldb.eSymbolTypeObjCMetaClass):
                return None

            return (lldb_symbol, lldb_address, symbol_name, symbol_address, symbol_type)
        else:
            raise TypeError()

    def _add_lldb_symbol(self, symbol_name: str, symbol_address: int, symbol_type: str, symbol_size) -> lldb.SBSymbol:
        with NamedTemporaryFile(mode='w+', suffix='.json') as symbols_file:
            lldb_address = self._hilda.target.ResolveLoadAddress(symbol_address)
            lldb_module = lldb_address.module
            symbol_file_address = lldb_address.GetFileAddress()

            # Create symbol file
            data = {
                "triple": lldb_module.GetTriple(),
                "uuid": lldb_module.GetUUIDString(),
                "symbols": [{
                    "name": symbol_name,
                    "type": symbol_type,
                    "size": symbol_size,
                    "address": symbol_file_address,
                }],
            }
            json.dump(data, symbols_file)
            symbols_file.flush()

            # Add symbol from file
            symbols_before = lldb_module.FindSymbols(symbol_name)
            if len(symbols_before) != 0:
                raise Exception(
                    f'Failed to add symbol {symbol_name} to {lldb_module.file}'
                    f' (symbol already exists {symbols_before})')

            result = self._hilda.lldb_handle_command(f'target symbols add {shlex.quote(symbols_file.name)}',
                                                     capture_output=True)

            # Verify command executed as expected
            if result is None:
                raise Exception(f'Failed to add symbol {symbol_name} to {lldb_module.file}')
            expected_result = f"symbol file '{symbols_file.name}' has been added to '{lldb_module.file}'\n"
            if expected_result != result:
                raise Exception(
                    f'Failed to add symbol {symbol_name} to {lldb_module.file}'
                    f' (expected: {json.dumps(expected_result)}, output: {json.dumps(result)})')

            # Verify the symbol was added
            symbols_after = lldb_module.FindSymbols(symbol_name)
            if len(symbols_after) != 1:
                raise Exception(f'Failed to add symbol {symbol_name} to {lldb_module.file}')

            return self.get((symbol_name, symbol_address))

    # Actions

    def bp(self, callback=None, **args):
        """
        Place a breakpoint on all symbols in current list.
        Look for the bp command for more details.
        :param callback:  callback function to be executed upon an hit
        :param args: optional args for the bp command
        """
        for v in self.values():
            v.bp(callback, **args)

    def monitor(self, **args):
        """
        Perform monitor for all symbols in current list.
        See monitor command for more details.
        :param args: given arguments for monitor command
        """
        for (name, address), symbol in self.items():
            options = args.copy()
            if name is None:
                continue
            if self._hilda.configs.objc_verbose_monitor:
                arg_count = name.count(':')
                if arg_count > 0:
                    arg_count = min(6, arg_count)
                    options['expr'] = {f'$arg{i + 3}': 'po' for i in range(arg_count)}
            name = options.get('name', name)
            self._hilda.symbol(address).monitor(name=name, **options)

    # Filters

    def __sub__(self, other: 'SymbolList') -> 'SymbolList':
        retval = SymbolList(self._hilda)
        for v in self.values():
            if v not in other:
                retval.add(v)
        return retval

    def __add__(self, other: 'SymbolList') -> 'SymbolList':
        retval = SymbolList(self._hilda)
        for v in other.values():
            retval.add(v)
        for v in self.values():
            retval.add(v)
        return retval

    def filter_by_module(self, substring: str) -> 'SymbolList':
        """
        Filter symbols who's module name contains the provided substring
        :return: reduced symbol list
        """

        def optimized_iter():
            if self._global is self:
                for lldb_module in self._hilda.target.modules:
                    if substring not in lldb_module.file.basename:
                        continue

                    for lldb_symbol in lldb_module.symbols:
                        symbol = self.get(lldb_symbol)

                        if symbol is None:
                            # This should only happen if we do not want to expose certain symbols
                            continue

                        yield symbol
            else:
                for symbol in self:
                    yield symbol

        retval = SymbolList(self._hilda)
        for symbol in optimized_iter():
            if substring in symbol.filename:
                retval.add(symbol)

        return retval

    def filter_symbol_type(self, lldb_type) -> 'SymbolList':
        """
        Filter by LLDB symbol types (for example: lldb.eSymbolTypeCode,
        lldb.eSymbolTypeData, ...)
        :param lldb_type: symbol type from LLDB consts
        :return: symbols matching the type filter
        """
        retval = SymbolList(self._hilda)
        for v in self.values():
            if v.type_ == lldb_type:
                retval.add(v)
        return retval

    def filter_code_symbols(self) -> 'SymbolList':
        """
        Filter only code symbols
        :return: symbols with type lldb.eSymbolTypeCode
        """
        return self.filter_symbol_type(lldb.eSymbolTypeCode)

    def filter_data_symbols(self):
        """
        Filter only data symbols
        :return: symbols with type lldb.eSymbolTypeCode
        """
        return self.filter_symbol_type(lldb.eSymbolTypeData)

    def filter_objc_classes(self):
        """
        Filter only objc meta classes
        :return: symbols with type lldb.eSymbolTypeObjCMetaClass
        """
        return self.filter_symbol_type(lldb.eSymbolTypeObjCMetaClass)

    def filter_startswith(self, exp, case_sensitive=True):
        """
        Filter only symbols with given prefix
        :param exp: prefix
        :param case_sensitive: is case sensitive
        :return: reduced symbol list
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = SymbolList(self._hilda)
        for v in self.values():
            name = v.lldb_name
            if not case_sensitive:
                name = name.lower()
            if name.startswith(exp):
                retval.add(v)
        return retval

    def filter_endswith(self, exp, case_sensitive=True):
        """
        Filter only symbols with given prefix
        :param exp: prefix
        :param case_sensitive: is case sensitive
        :return: reduced symbol list
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = SymbolList(self._hilda)
        for v in self.values():
            name = v.lldb_name
            if not case_sensitive:
                name = name.lower()
            if name.endswith(exp):
                retval.add(v)
        return retval

    def filter_name_contains(self, exp, case_sensitive=True):
        """
        Filter symbols containing a given expression
        :param exp: given expression
        :param case_sensitive: is case sensitive
        :return: reduced symbol list
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = SymbolList(self._hilda)
        for v in self.values():
            name = v.lldb_name
            if not case_sensitive:
                name = name.lower()
            if exp in name:
                retval.add(v)
        return retval
