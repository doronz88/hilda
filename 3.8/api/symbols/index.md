# Symbols & Objective-C

## Symbol

## hilda.symbol

### SymbolFormatField

Bases: `FormatField`

A Symbol wrapper for construct

Source code in `hilda/symbol.py`

```
class SymbolFormatField(FormatField):
    """
    A Symbol wrapper for construct
    """

    def __init__(self, client):
        super().__init__("<", "Q")
        self._client = client

    def _parse(self, stream, context, path):
        return self._client.symbol(FormatField._parse(self, stream, context, path))
```

### Symbol

Bases: `int`

Hilda's class representing a symbol (not necessarily an LLDB symbol).

Source code in `hilda/symbol.py`

```
class Symbol(int):
    """
    Hilda's class representing a symbol (not necessarily an LLDB symbol).
    """

    PROXY_METHODS: ClassVar = ["peek", "poke", "peek_str", "monitor", "bp", "disass", "po", "objc_call"]

    @classmethod
    def create(
        cls,
        value: int,
        client,
        lldb_symbol: Optional[lldb.SBSymbol] = None,
        lldb_address: Optional[lldb.SBAddress] = None,
        lldb_type: Optional[int] = None,
    ) -> None:
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
            getattr(symbol.__class__, method_name).__doc__ = getattr(client, method_name).__doc__

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
        return Class(self._client, self.objc_call("class"))

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
        symbol_info = int(self._client.po(f"[{self._client._object_identifier} symbolForAddress:{self}]", "__int128"))
        arg1 = symbol_info & 0xFFFFFFFFFFFFFFFF
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
        """Construct compliance."""
        pass

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> None:
        """Construct compliance."""
        if whence == os.SEEK_CUR:
            self._offset += offset
        elif whence == os.SEEK_SET:
            self._offset = offset - self
        else:
            raise OSError("Unsupported whence")

    def read(self, count: int) -> bytes:
        """Construct compliance."""
        val = (self + self._offset).peek(count)
        self._offset += count
        return val

    def write(self, buf: bytes) -> int:
        """Construct compliance."""
        val = (self + self._offset).poke(buf)
        self._offset += len(buf)
        return val

    def tell(self) -> int:
        """Construct compliance."""
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
            struct.unpack(self._client.endianness + fmt, self._client.peek(addr, self.item_size))[0]
        )

    def __setitem__(self, item, value):
        fmt = ADDRESS_SIZE_TO_STRUCT_FORMAT[self.item_size]
        value = struct.pack(self._client.endianness + fmt, int(value))
        self._client.poke(self + item * self.item_size, value)

    def __repr__(self):
        address = int(self)
        name = self.lldb_name
        if name is not None:
            return f"Symbol({name}, 0x{address:016X})"
        else:
            return f"AnonymousSymbol(0x{address:016X})"

    def __str__(self):
        return f"0x{int(self):016x}"

    def __call__(self, *args, **kwargs):
        return self._client.call(self, args)
```

#### file_address

```
file_address: int
```

Get symbol file address (address without ASLR)

Returns:

| Type  | Description  |
| ----- | ------------ |
| `int` | File address |

#### objc_class

```
objc_class: Class
```

Get the objc class of the respected symbol

Returns:

| Type    | Description |
| ------- | ----------- |
| `Class` | Class       |

#### objc_symbol

```
objc_symbol
```

Get an ObjectiveC symbol of the same address

Returns:

| Type | Description                               |
| ---- | ----------------------------------------- |
|      | Object representing the ObjectiveC symbol |

#### cf_description

```
cf_description: str
```

Get output from CFCopyDescription()

Returns:

| Type  | Description                              |
| ----- | ---------------------------------------- |
| `str` | CFCopyDescription()'s output as a string |

#### create

```
create(value: int, client, lldb_symbol: Optional[SBSymbol] = None, lldb_address: Optional[SBAddress] = None, lldb_type: Optional[int] = None) -> None
```

Create a Symbol object.

Parameters:

| Name          | Type          | Description     | Default    |
| ------------- | ------------- | --------------- | ---------- |
| `value`       | `int`         | Symbol address. | *required* |
| `client`      | `HildaClient` | Hilda client.   | *required* |
| `lldb_symbol` | `SBSymbol`    | LLDB symbol.    | `None`     |

Returns:

| Type     | Description    |
| -------- | -------------- |
| `Symbol` | Symbol object. |

Source code in `hilda/symbol.py`

```
@classmethod
def create(
    cls,
    value: int,
    client,
    lldb_symbol: Optional[lldb.SBSymbol] = None,
    lldb_address: Optional[lldb.SBAddress] = None,
    lldb_type: Optional[int] = None,
) -> None:
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
        getattr(symbol.__class__, method_name).__doc__ = getattr(client, method_name).__doc__

    return symbol
```

#### change_item_size

```
change_item_size(new_item_size: int) -> None
```

Temporarily change item size

Parameters:

| Name            | Type  | Description         | Default    |
| --------------- | ----- | ------------------- | ---------- |
| `new_item_size` | `int` | Temporary item size | *required* |

Source code in `hilda/symbol.py`

```
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
```

#### close

```
close() -> None
```

Construct compliance.

Source code in `hilda/symbol.py`

```
def close(self) -> None:
    """Construct compliance."""
    pass
```

#### seek

```
seek(offset: int, whence: int = os.SEEK_SET) -> None
```

Construct compliance.

Source code in `hilda/symbol.py`

```
def seek(self, offset: int, whence: int = os.SEEK_SET) -> None:
    """Construct compliance."""
    if whence == os.SEEK_CUR:
        self._offset += offset
    elif whence == os.SEEK_SET:
        self._offset = offset - self
    else:
        raise OSError("Unsupported whence")
```

#### read

```
read(count: int) -> bytes
```

Construct compliance.

Source code in `hilda/symbol.py`

```
def read(self, count: int) -> bytes:
    """Construct compliance."""
    val = (self + self._offset).peek(count)
    self._offset += count
    return val
```

#### write

```
write(buf: bytes) -> int
```

Construct compliance.

Source code in `hilda/symbol.py`

```
def write(self, buf: bytes) -> int:
    """Construct compliance."""
    val = (self + self._offset).poke(buf)
    self._offset += len(buf)
    return val
```

#### tell

```
tell() -> int
```

Construct compliance.

Source code in `hilda/symbol.py`

```
def tell(self) -> int:
    """Construct compliance."""
    return self + self._offset
```

## Symbols container

## hilda.symbols

### SymbolIdentifier

Name + file address + size tuple for bulk symbol creation.

Source code in `hilda/symbols.py`

```
@dataclass(frozen=True)
class SymbolIdentifier:
    """Name + file address + size tuple for bulk symbol creation."""

    symbol_name: str
    file_address: int
    symbol_size: int
```

### SymbolList

Manager for `Symbol` objects, each one representing a symbol.

`Symbol`s are either regular (i.e., named) symbols or anonymous symbols. Only regular symbols are managed by this class, though anonymous symbols can be created by this class (using the function `add`).

Source code in `hilda/symbols.py`

```
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
        if not hasattr(hilda, "symbols"):
            self._global = self
        else:
            self._global = hilda.symbols
        self._manual_lldb_symbols = {}

    def __iter__(self) -> Iterator[Symbol]:
        """Iterate over cached symbols, populating the cache if needed."""
        self._populate_cache()

        yield from self._symbols.values()

    def __len__(self) -> int:
        """Return the number of symbols in the list."""
        return sum(1 for _ in self)

    def __contains__(
        self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]
    ) -> bool:
        """Return True if a symbol can be resolved by address/name/ID/instance."""
        return self.get(address_or_name_or_id_or_symbol) is not None

    def __getitem__(
        self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]
    ) -> Symbol:
        """
        Get a symbol by address or name or ID (or the symbol itself, though it usually makes little sense)

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        """
        symbol = self.get(address_or_name_or_id_or_symbol)
        if symbol is None:
            raise SymbolAbsentError(f"no such symbol: {address_or_name_or_id_or_symbol}")
            # raise KeyError(address_or_name_or_id_or_symbol)
        return symbol

    def __delitem__(
        self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]
    ) -> None:
        """
        Remove a symbol (unless this is the global symbol list - see remove())

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        """
        self.remove(address_or_name_or_id_or_symbol)

    def __repr__(self) -> str:
        """Human-readable representation, special-casing the global list."""
        if self._global is self:
            return f"<{self.__class__.__name__} GLOBAL>"
        else:
            return repr(list(self))

    def __str__(self) -> str:
        """Alias for __repr__."""
        return repr(self)

    def get(
        self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]
    ) -> Optional[Symbol]:
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
        """Populate the global cache lazily, optionally filtering by module UUID."""
        if self._global is self:
            modules = self._hilda.target.modules
            modules_not_cached = [module for module in modules if module.GetUUIDString() not in self._modules]
            if module_uuid_filter is not None:
                modules_not_cached = [module for module in modules if module.GetUUIDString() == module_uuid_filter]
            if len(modules_not_cached) != 0:
                for lldb_module in tqdm(modules_not_cached, desc="Populating Hilda symbols cache"):
                    for lldb_symbol in lldb_module.symbols:
                        _ = self.get(lldb_symbol)
                    self._modules.add(lldb_module.GetUUIDString())

    def force_refresh(self, module_range=None, module_filename_filter=""):
        """
        Force a refresh of symbols
        :param module_range: index range for images to load in the form of [start, end]
        :param module_filename_filter: filter only images containing given expression
        """
        self.log_debug("Force symbols")

        if self._global is not self:
            self._hilda.log_error("Cannot refresh a non-global symbol list")
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
        """Insert a symbol into the internal caches."""
        self._symbols[sym_id] = symbol
        name, _address = sym_id
        if name is not None and re.match(r"^[a-zA-Z0-9_]+$", name):
            ids = self._symbols_by_name.get(name)
            if ids is not None:
                ids.append(sym_id)
            else:
                self._symbols_by_name[name] = [sym_id]

    def add(
        self,
        value: Union[int, Symbol],
        symbol_name: Optional[str] = None,
        symbol_type: Optional[str] = None,
        symbol_size: Optional[int] = None,
    ) -> Symbol:
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
        if (
            isinstance(value, Symbol)
            and (symbol_type, symbol_size) == (None, None)
            and value.lldb_symbol is not None
            and
            # TODO: Is it an error to add again, providing the same name?
            (symbol_name is None or symbol_name == value.lldb_name)
        ):
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
        global_symbol = (
            self._global.get(symbol_address)
            if symbol_name is None
            else (self._global.get((symbol_name, symbol_address)))
        )
        if global_symbol is not None:
            if (symbol_type, symbol_size) != (None, None):
                raise ValueError()
            return self.add(global_symbol)

        # Check if this is an anonymous symbol
        if symbol_name is None:
            # Anonymous symbols need not be added to _symbols.
            return Symbol.create(symbol_address, self._hilda, None)

        # Add a new global symbol
        symbols = self._global._add_lldb_symbols([
            (
                symbol_name,
                symbol_address,
                symbol_type if symbol_type is not None else "code",
                symbol_size if symbol_size is not None else 8,
            )
        ])
        if len(symbols) != 1:
            raise HildaException("Symbol could not be added")
        return self.add(symbols[0])

    def add_multiple_file_symbols(
        self,
        symbol_identifiers: list[SymbolIdentifier],
        symbol_type: Optional[str] = None,
        module_name: Optional[str] = None,
    ) -> list[Symbol]:
        """
        Add multiple symbols by file address.
        Expects SymbolIdentifier entries (tuple inputs are accepted for compatibility).
        """
        symbol_type = symbol_type if symbol_type is not None else "code"
        fixed_identifiers = []
        for identifier in symbol_identifiers:
            if isinstance(identifier, tuple):
                identifier = SymbolIdentifier(*identifier)
            symbol_name = identifier.symbol_name
            file_address = identifier.file_address
            symbol_size = identifier.symbol_size
            file_symbol = self._hilda.file_symbol(file_address, module_name)
            if file_symbol.lldb_name is not None and "lldb_unnamed_symbol" not in file_symbol.lldb_name:
                # There is already an lldb symbol that is not one of the unnamed symbols - skip
                self._hilda.log_warning(
                    f"Not adding {symbol_name}@0x{int(file_symbol):016X} (because it is already {file_symbol.lldb_name}"
                )
                continue
            fixed_identifiers.append((symbol_name, int(file_symbol), symbol_type, symbol_size))
        symbols = self._global._add_lldb_symbols(fixed_identifiers)
        return [self.add(symbol) for symbol in symbols]

    def _remove(self, sym_id: HildaSymbolId) -> None:
        """Remove a symbol from internal caches (caller must validate)."""
        del self._symbols[sym_id]
        name, _address = sym_id
        if name is not None and re.match(r"^[a-zA-Z0-9_]+$", name):
            ids = self._symbols_by_name[name]
            if sym_id in ids:
                ids.remove(sym_id)
            if not ids:
                del self._symbols_by_name[name]

    def remove(self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) -> None:
        """
        Remove a symbol.

        :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
        """
        if self._global is self:
            raise HildaException("Cannot remove from the global symbols list")

        symbol = self[address_or_name_or_id_or_symbol]
        self._remove(symbol.id)

    def items(self) -> Iterator[tuple[HildaSymbolId, Symbol]]:
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
        # Avoid hijacking Python/introspection magic attributes.
        if attribute_name.startswith("__") and attribute_name.endswith("__"):
            raise AttributeError(attribute_name)
        match = re.fullmatch(r"x(?:0x)?([0-9a-fA-F]{6,16})", attribute_name)
        if match:
            address = int(match[1], base=0x10)
            return self.add(address)
        value = self.get(attribute_name)
        if value is None:
            raise SymbolAbsentError(f"SymbolList object has no attribute '{attribute_name}'")
        return value

    def __dir__(self):
        """Return dir() results including known symbol names."""
        self._populate_cache()

        # Return normal attributes and symbol names
        return chain(super().__dir__(), self._symbols_by_name.keys())

    def _get_lldb_symbol_from_name(
        self, name: str, address: Optional[int] = None
    ) -> Optional[tuple[lldb.SBSymbol, lldb.SBAddress, str, int, int]]:
        """Resolve a symbol by name (and optionally address) from LLDB."""
        lldb_symbol_context_list = list(self._hilda.target.FindSymbols(name))

        if not lldb_symbol_context_list:
            for func in self._hilda.target.FindFunctions(name):
                if func.symbol.name == name:
                    lldb_symbol_context_list.append(func)

        if address is not None:
            for lldb_symbol_context in list(lldb_symbol_context_list):
                lldb_symbol_context_address = lldb_symbol_context.symbol.GetStartAddress().GetLoadAddress(
                    self._hilda.target
                )
                if lldb_symbol_context_address != address:
                    lldb_symbol_context_list.remove(lldb_symbol_context)
                    self._hilda.log_debug(
                        f"Ignoring symbol {name}@0x{lldb_symbol_context_address:016X} "
                        f"(beacause address is not 0x{address:016X})"
                    )

        symbols = []
        for lldb_symbol_context in lldb_symbol_context_list:
            symbol = self._get_lldb_symbol(lldb_symbol_context.symbol)
            if symbol is None:
                # Ignoring symbol - failed to convert
                continue

            if address is not None:
                _lldb_symbol, _lldb_address, _symbol_name, symbol_address, _symbol_type = symbol
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

    def _get_lldb_symbol(
        self, value: Union[int, str, HildaSymbolId, Symbol, lldb.SBAddress, lldb.SBSymbol]
    ) -> Optional[tuple[lldb.SBSymbol, lldb.SBAddress, str, int, int]]:
        """Normalize inputs to an LLDB symbol tuple or return None if not resolvable."""
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
            lldb_symbol_context = self._hilda.target.ResolveSymbolContextForAddress(
                lldb_address, lldb.eSymbolContextEverything
            )
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
            if symbol_name in ("<redacted>",):
                return None

            # Ignore symbols not having a real address
            lldb_address = lldb_symbol.GetStartAddress()
            symbol_address = lldb_address.GetLoadAddress(self._hilda.target)
            if symbol_address == 0xFFFFFFFFFFFFFFFF:
                return None

            # Ignore symbols not having a useful type
            symbol_type = lldb_symbol.GetType()
            if symbol_type not in (
                lldb.eSymbolTypeCode,
                lldb.eSymbolTypeRuntime,
                lldb.eSymbolTypeData,
                lldb.eSymbolTypeObjCMetaClass,
            ):
                return None

            return (lldb_symbol, lldb_address, symbol_name, symbol_address, symbol_type)
        else:
            raise TypeError()

    def _add_lldb_symbols(self, symbol_identifiers: list[tuple[str, int, str, int]]) -> list[lldb.SBSymbol]:
        """Add LLDB symbols in bulk using a generated symbol JSON file."""
        if len(symbol_identifiers) == 0:
            return []
        with NamedTemporaryFile(mode="w+", suffix=".json") as symbols_file:
            first_address = symbol_identifiers[0][1]
            first_lldb_address = self._hilda.target.ResolveLoadAddress(first_address)
            lldb_module = first_lldb_address.module
            if not lldb_module:
                raise HildaException("Failed to find module. Please provide it manually")

            lldb_module_uuid = lldb_module.GetUUIDString()
            if lldb_module_uuid not in self._manual_lldb_symbols:
                # Create a symbol dictionary
                self._manual_lldb_symbols[lldb_module_uuid] = {
                    "triple": lldb_module.GetTriple(),
                    "uuid": lldb_module_uuid,
                    "symbols": [],
                }

            num_symbols_to_add = 0
            for symbol_name, symbol_address, _symbol_type, _symbol_size in symbol_identifiers:
                # Skip symbols that are already there
                if len(lldb_module.FindSymbols(symbol_name)) != 0:
                    continue

                lldb_address = self._hilda.target.ResolveLoadAddress(symbol_address)
                if lldb_module != lldb_address.module:
                    raise HildaException("All symbols must belong to the same module")
                symbol_file_address = lldb_address.GetFileAddress()

                # Add the symbol to the dictionary
                self._manual_lldb_symbols[lldb_module_uuid]["symbols"].append({
                    "name": symbol_name,
                    "type": _symbol_type,
                    "size": _symbol_size,
                    "address": symbol_file_address,
                })
                num_symbols_to_add += 1

            json.dump(self._manual_lldb_symbols[lldb_module_uuid], symbols_file)
            symbols_file.flush()

            result = self._hilda.lldb_handle_command(
                f"target symbols add {shlex.quote(symbols_file.name)}", capture_output=True
            )
            if result is None:
                raise HildaException(f"Failed to add symbols to {lldb_module.file}")
            expected_result = f"symbol file '{symbols_file.name}' has been added to '{lldb_module.file}'\n"
            if expected_result != result:
                raise HildaException(
                    f"Failed to add symbols to {lldb_module.file}"
                    f" (expected: {json.dumps(expected_result)}, output: {json.dumps(result)})"
                )

            # Verify the symbols were added and create a symbol for each
            new_symbols = []
            for symbol_name, symbol_address, _symbol_type, _symbol_size in symbol_identifiers:
                symbols_after = lldb_module.FindSymbols(symbol_name)
                if len(symbols_after) == 0:
                    continue
                new_symbols.append(self.get((symbol_name, symbol_address)))
            if len(new_symbols) != num_symbols_to_add:
                raise HildaException("Failed to add all symbols")
            return new_symbols

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
        for (name, address), _symbol in self.items():
            options = args.copy()
            if name is None:
                continue
            if self._hilda.configs.objc_verbose_monitor:
                arg_count = name.count(":")
                if arg_count > 0:
                    arg_count = min(6, arg_count)
                    options["expr"] = {f"$arg{i + 3}": "po" for i in range(arg_count)}
            name = options.get("name", name)
            self._hilda.symbol(address).monitor(name=name, **options)

    # Filters

    def __sub__(self, other: "SymbolList") -> "SymbolList":
        """Return a new SymbolList with symbols present in self but not in other."""
        retval = SymbolList(self._hilda)
        for v in self.values():
            if v not in other:
                retval.add(v)
        return retval

    def __add__(self, other: "SymbolList") -> "SymbolList":
        """Return a new SymbolList containing symbols from both lists."""
        retval = SymbolList(self._hilda)
        for v in other.values():
            retval.add(v)
        for v in self.values():
            retval.add(v)
        return retval

    def filter_by_module(self, substring: str) -> "SymbolList":
        """
        Filter symbols whose module name contains the provided substring.
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

    def filter_symbol_type(self, lldb_type) -> "SymbolList":
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

    def filter_code_symbols(self) -> "SymbolList":
        """
        Filter only code symbols
        :return: symbols with type lldb.eSymbolTypeCode
        """
        return self.filter_symbol_type(lldb.eSymbolTypeCode)

    def filter_data_symbols(self) -> "SymbolList":
        """
        Filter only data symbols
        :return: symbols with type lldb.eSymbolTypeData
        """
        return self.filter_symbol_type(lldb.eSymbolTypeData)

    def filter_objc_classes(self) -> "SymbolList":
        """
        Filter only objc meta classes
        :return: symbols with type lldb.eSymbolTypeObjCMetaClass
        """
        return self.filter_symbol_type(lldb.eSymbolTypeObjCMetaClass)

    def filter_startswith(self, exp: str, case_sensitive: bool = True) -> "SymbolList":
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

    def filter_endswith(self, exp: str, case_sensitive: bool = True) -> "SymbolList":
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

    def filter_name_contains(
        self, exp: str, case_sensitive: bool = True, use_bare_lldb_api: bool = False
    ) -> "SymbolList":
        """
        Filter symbols containing a given expression

        :param exp: given expression
        :param case_sensitive: is case sensitive
        :param use_bare_lldb_api: Use bare lldb api (Using `FindFunctions()`)
        :return: reduced symbol list
        """
        if not case_sensitive:
            exp = exp.lower()

            if use_bare_lldb_api:
                raise ValueError("Cannot use bare lldb api with case_sensitive=False")

        retval = SymbolList(self._hilda)
        for v in (
            self.values()
            if not use_bare_lldb_api
            else ([
                self._hilda.symbol(f.symbol.GetStartAddress().GetLoadAddress(self._hilda.target))
                for f in self._hilda.target.FindFunctions(exp)
            ])
        ):
            name = v.lldb_name
            if not case_sensitive:
                name = name.lower()
            if exp in name:
                retval.add(v)
        return retval
```

#### get

```
get(address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, SBSymbol, Symbol]) -> Optional[Symbol]
```

Get a symbol by address or name or ID (or the symbol itself, though it usually makes little sense)

Parameters:

| Name                              | Type                                               | Description                                  | Default    |
| --------------------------------- | -------------------------------------------------- | -------------------------------------------- | ---------- |
| `address_or_name_or_id_or_symbol` | `Union[int, str, HildaSymbolId, SBSymbol, Symbol]` | Address or name or ID (or the symbol itself) | *required* |

Returns:

| Type               | Description                             |
| ------------------ | --------------------------------------- |
| `Optional[Symbol]` | Symbol if one exists, or None otherwise |

Source code in `hilda/symbols.py`

```
def get(
    self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]
) -> Optional[Symbol]:
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
```

#### force_refresh

```
force_refresh(module_range=None, module_filename_filter='')
```

Force a refresh of symbols

Parameters:

| Name                     | Type | Description                                                | Default |
| ------------------------ | ---- | ---------------------------------------------------------- | ------- |
| `module_range`           |      | index range for images to load in the form of [start, end] | `None`  |
| `module_filename_filter` |      | filter only images containing given expression             | `''`    |

Source code in `hilda/symbols.py`

```
def force_refresh(self, module_range=None, module_filename_filter=""):
    """
    Force a refresh of symbols
    :param module_range: index range for images to load in the form of [start, end]
    :param module_filename_filter: filter only images containing given expression
    """
    self.log_debug("Force symbols")

    if self._global is not self:
        self._hilda.log_error("Cannot refresh a non-global symbol list")
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
```

#### add

```
add(value: Union[int, Symbol], symbol_name: Optional[str] = None, symbol_type: Optional[str] = None, symbol_size: Optional[int] = None) -> Symbol
```

Add a symbol. Returns existing symbol if a matching regular (i.e., non-anonymous) symbol exists.

Parameters:

| Name          | Type                 | Description                                                           | Default    |
| ------------- | -------------------- | --------------------------------------------------------------------- | ---------- |
| `value`       | `Union[int, Symbol]` | The address of the symbol (in memory) or and existing Symbol.         | *required* |
| `symbol_name` | `Optional[str]`      | The name of the symbol.                                               | `None`     |
| `symbol_type` | `Optional[str]`      | The type of the symbol (either 'code' of 'data', defaults to 'code'). | `None`     |
| `symbol_size` | `Optional[int]`      | The size of the symbol (defaults to 8 bytes).                         | `None`     |

Returns:

| Type     | Description |
| -------- | ----------- |
| `Symbol` | The symbol  |

Source code in `hilda/symbols.py`

```
def add(
    self,
    value: Union[int, Symbol],
    symbol_name: Optional[str] = None,
    symbol_type: Optional[str] = None,
    symbol_size: Optional[int] = None,
) -> Symbol:
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
    if (
        isinstance(value, Symbol)
        and (symbol_type, symbol_size) == (None, None)
        and value.lldb_symbol is not None
        and
        # TODO: Is it an error to add again, providing the same name?
        (symbol_name is None or symbol_name == value.lldb_name)
    ):
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
    global_symbol = (
        self._global.get(symbol_address)
        if symbol_name is None
        else (self._global.get((symbol_name, symbol_address)))
    )
    if global_symbol is not None:
        if (symbol_type, symbol_size) != (None, None):
            raise ValueError()
        return self.add(global_symbol)

    # Check if this is an anonymous symbol
    if symbol_name is None:
        # Anonymous symbols need not be added to _symbols.
        return Symbol.create(symbol_address, self._hilda, None)

    # Add a new global symbol
    symbols = self._global._add_lldb_symbols([
        (
            symbol_name,
            symbol_address,
            symbol_type if symbol_type is not None else "code",
            symbol_size if symbol_size is not None else 8,
        )
    ])
    if len(symbols) != 1:
        raise HildaException("Symbol could not be added")
    return self.add(symbols[0])
```

#### add_multiple_file_symbols

```
add_multiple_file_symbols(symbol_identifiers: list[SymbolIdentifier], symbol_type: Optional[str] = None, module_name: Optional[str] = None) -> list[Symbol]
```

Add multiple symbols by file address. Expects SymbolIdentifier entries (tuple inputs are accepted for compatibility).

Source code in `hilda/symbols.py`

```
def add_multiple_file_symbols(
    self,
    symbol_identifiers: list[SymbolIdentifier],
    symbol_type: Optional[str] = None,
    module_name: Optional[str] = None,
) -> list[Symbol]:
    """
    Add multiple symbols by file address.
    Expects SymbolIdentifier entries (tuple inputs are accepted for compatibility).
    """
    symbol_type = symbol_type if symbol_type is not None else "code"
    fixed_identifiers = []
    for identifier in symbol_identifiers:
        if isinstance(identifier, tuple):
            identifier = SymbolIdentifier(*identifier)
        symbol_name = identifier.symbol_name
        file_address = identifier.file_address
        symbol_size = identifier.symbol_size
        file_symbol = self._hilda.file_symbol(file_address, module_name)
        if file_symbol.lldb_name is not None and "lldb_unnamed_symbol" not in file_symbol.lldb_name:
            # There is already an lldb symbol that is not one of the unnamed symbols - skip
            self._hilda.log_warning(
                f"Not adding {symbol_name}@0x{int(file_symbol):016X} (because it is already {file_symbol.lldb_name}"
            )
            continue
        fixed_identifiers.append((symbol_name, int(file_symbol), symbol_type, symbol_size))
    symbols = self._global._add_lldb_symbols(fixed_identifiers)
    return [self.add(symbol) for symbol in symbols]
```

#### remove

```
remove(address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, SBSymbol, Symbol]) -> None
```

Remove a symbol.

Parameters:

| Name                              | Type                                               | Description                                  | Default    |
| --------------------------------- | -------------------------------------------------- | -------------------------------------------- | ---------- |
| `address_or_name_or_id_or_symbol` | `Union[int, str, HildaSymbolId, SBSymbol, Symbol]` | Address or name or ID (or the symbol itself) | *required* |

Source code in `hilda/symbols.py`

```
def remove(self, address_or_name_or_id_or_symbol: Union[int, str, HildaSymbolId, lldb.SBSymbol, Symbol]) -> None:
    """
    Remove a symbol.

    :param address_or_name_or_id_or_symbol: Address or name or ID (or the symbol itself)
    """
    if self._global is self:
        raise HildaException("Cannot remove from the global symbols list")

    symbol = self[address_or_name_or_id_or_symbol]
    self._remove(symbol.id)
```

#### items

```
items() -> Iterator[tuple[HildaSymbolId, Symbol]]
```

Get a symbol ID and symbol object tuple for every symbol

Source code in `hilda/symbols.py`

```
def items(self) -> Iterator[tuple[HildaSymbolId, Symbol]]:
    """
    Get a symbol ID and symbol object tuple for every symbol
    """
    return ((symbol.id, symbol) for symbol in self)
```

#### keys

```
keys() -> Iterator[HildaSymbolId]
```

Get the symbol ID for every symbol

Source code in `hilda/symbols.py`

```
def keys(self) -> Iterator[HildaSymbolId]:
    """
    Get the symbol ID for every symbol
    """
    return (symbol.id for symbol in self)
```

#### values

```
values() -> Iterator[Symbol]
```

Get the symbol object for every symbol

Source code in `hilda/symbols.py`

```
def values(self) -> Iterator[Symbol]:
    """
    Get the symbol object for every symbol
    """
    return (symbol for symbol in self)
```

#### bp

```
bp(callback=None, **args)
```

Place a breakpoint on all symbols in current list. Look for the bp command for more details.

Parameters:

| Name       | Type | Description                                  | Default |
| ---------- | ---- | -------------------------------------------- | ------- |
| `callback` |      | callback function to be executed upon an hit | `None`  |
| `args`     |      | optional args for the bp command             | `{}`    |

Source code in `hilda/symbols.py`

```
def bp(self, callback=None, **args):
    """
    Place a breakpoint on all symbols in current list.
    Look for the bp command for more details.
    :param callback:  callback function to be executed upon an hit
    :param args: optional args for the bp command
    """
    for v in self.values():
        v.bp(callback, **args)
```

#### monitor

```
monitor(**args)
```

Perform monitor for all symbols in current list. See monitor command for more details.

Parameters:

| Name   | Type | Description                         | Default |
| ------ | ---- | ----------------------------------- | ------- |
| `args` |      | given arguments for monitor command | `{}`    |

Source code in `hilda/symbols.py`

```
def monitor(self, **args):
    """
    Perform monitor for all symbols in current list.
    See monitor command for more details.
    :param args: given arguments for monitor command
    """
    for (name, address), _symbol in self.items():
        options = args.copy()
        if name is None:
            continue
        if self._hilda.configs.objc_verbose_monitor:
            arg_count = name.count(":")
            if arg_count > 0:
                arg_count = min(6, arg_count)
                options["expr"] = {f"$arg{i + 3}": "po" for i in range(arg_count)}
        name = options.get("name", name)
        self._hilda.symbol(address).monitor(name=name, **options)
```

#### filter_by_module

```
filter_by_module(substring: str) -> SymbolList
```

Filter symbols whose module name contains the provided substring.

Returns:

| Type         | Description         |
| ------------ | ------------------- |
| `SymbolList` | reduced symbol list |

Source code in `hilda/symbols.py`

```
def filter_by_module(self, substring: str) -> "SymbolList":
    """
    Filter symbols whose module name contains the provided substring.
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
```

#### filter_symbol_type

```
filter_symbol_type(lldb_type) -> SymbolList
```

Filter by LLDB symbol types (for example: lldb.eSymbolTypeCode, lldb.eSymbolTypeData, ...)

Parameters:

| Name        | Type | Description                  | Default    |
| ----------- | ---- | ---------------------------- | ---------- |
| `lldb_type` |      | symbol type from LLDB consts | *required* |

Returns:

| Type         | Description                      |
| ------------ | -------------------------------- |
| `SymbolList` | symbols matching the type filter |

Source code in `hilda/symbols.py`

```
def filter_symbol_type(self, lldb_type) -> "SymbolList":
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
```

#### filter_code_symbols

```
filter_code_symbols() -> SymbolList
```

Filter only code symbols

Returns:

| Type         | Description                            |
| ------------ | -------------------------------------- |
| `SymbolList` | symbols with type lldb.eSymbolTypeCode |

Source code in `hilda/symbols.py`

```
def filter_code_symbols(self) -> "SymbolList":
    """
    Filter only code symbols
    :return: symbols with type lldb.eSymbolTypeCode
    """
    return self.filter_symbol_type(lldb.eSymbolTypeCode)
```

#### filter_data_symbols

```
filter_data_symbols() -> SymbolList
```

Filter only data symbols

Returns:

| Type         | Description                            |
| ------------ | -------------------------------------- |
| `SymbolList` | symbols with type lldb.eSymbolTypeData |

Source code in `hilda/symbols.py`

```
def filter_data_symbols(self) -> "SymbolList":
    """
    Filter only data symbols
    :return: symbols with type lldb.eSymbolTypeData
    """
    return self.filter_symbol_type(lldb.eSymbolTypeData)
```

#### filter_objc_classes

```
filter_objc_classes() -> SymbolList
```

Filter only objc meta classes

Returns:

| Type         | Description                                     |
| ------------ | ----------------------------------------------- |
| `SymbolList` | symbols with type lldb.eSymbolTypeObjCMetaClass |

Source code in `hilda/symbols.py`

```
def filter_objc_classes(self) -> "SymbolList":
    """
    Filter only objc meta classes
    :return: symbols with type lldb.eSymbolTypeObjCMetaClass
    """
    return self.filter_symbol_type(lldb.eSymbolTypeObjCMetaClass)
```

#### filter_startswith

```
filter_startswith(exp: str, case_sensitive: bool = True) -> SymbolList
```

Filter only symbols with given prefix

Parameters:

| Name             | Type   | Description       | Default    |
| ---------------- | ------ | ----------------- | ---------- |
| `exp`            | `str`  | prefix            | *required* |
| `case_sensitive` | `bool` | is case sensitive | `True`     |

Returns:

| Type         | Description         |
| ------------ | ------------------- |
| `SymbolList` | reduced symbol list |

Source code in `hilda/symbols.py`

```
def filter_startswith(self, exp: str, case_sensitive: bool = True) -> "SymbolList":
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
```

#### filter_endswith

```
filter_endswith(exp: str, case_sensitive: bool = True) -> SymbolList
```

Filter only symbols with given prefix

Parameters:

| Name             | Type   | Description       | Default    |
| ---------------- | ------ | ----------------- | ---------- |
| `exp`            | `str`  | prefix            | *required* |
| `case_sensitive` | `bool` | is case sensitive | `True`     |

Returns:

| Type         | Description         |
| ------------ | ------------------- |
| `SymbolList` | reduced symbol list |

Source code in `hilda/symbols.py`

```
def filter_endswith(self, exp: str, case_sensitive: bool = True) -> "SymbolList":
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
```

#### filter_name_contains

```
filter_name_contains(exp: str, case_sensitive: bool = True, use_bare_lldb_api: bool = False) -> SymbolList
```

Filter symbols containing a given expression

Parameters:

| Name                | Type   | Description                               | Default    |
| ------------------- | ------ | ----------------------------------------- | ---------- |
| `exp`               | `str`  | given expression                          | *required* |
| `case_sensitive`    | `bool` | is case sensitive                         | `True`     |
| `use_bare_lldb_api` | `bool` | Use bare lldb api (Using FindFunctions()) | `False`    |

Returns:

| Type         | Description         |
| ------------ | ------------------- |
| `SymbolList` | reduced symbol list |

Source code in `hilda/symbols.py`

```
def filter_name_contains(
    self, exp: str, case_sensitive: bool = True, use_bare_lldb_api: bool = False
) -> "SymbolList":
    """
    Filter symbols containing a given expression

    :param exp: given expression
    :param case_sensitive: is case sensitive
    :param use_bare_lldb_api: Use bare lldb api (Using `FindFunctions()`)
    :return: reduced symbol list
    """
    if not case_sensitive:
        exp = exp.lower()

        if use_bare_lldb_api:
            raise ValueError("Cannot use bare lldb api with case_sensitive=False")

    retval = SymbolList(self._hilda)
    for v in (
        self.values()
        if not use_bare_lldb_api
        else ([
            self._hilda.symbol(f.symbol.GetStartAddress().GetLoadAddress(self._hilda.target))
            for f in self._hilda.target.FindFunctions(exp)
        ])
    ):
        name = v.lldb_name
        if not case_sensitive:
            name = name.lower()
        if exp in name:
            retval.add(v)
    return retval
```

## Objective-C classes

## hilda.objective_c_class

### Method

Source code in `hilda/objective_c_class.py`

```
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
    class_name: str = field(compare=False)

    @staticmethod
    def from_data(class_name: str, data: dict, client) -> "Method":
        """
        Create Method object from raw data.
        :param class_name: ObjC class name
        :param data: Data as loaded from get_objectivec_symbol_data.m.
        :param hilda.hilda_client.HildaClient client: Hilda client.
        """
        return Method(
            name=data["name"],
            client=client,
            address=client.symbol(data["address"]),
            imp=client.symbol(data["imp"]),
            type_=data["type"],
            return_type=decode_type(data["return_type"]),
            is_class=data["is_class"],
            args_types=list(map(decode_type, data["args_types"])),
            class_name=class_name,
        )

    def set_implementation(self, new_imp: int):
        self.client.symbols.method_setImplementation(self.address, new_imp)
        self.imp = self.client.symbol(new_imp)

    def monitor(self, **args) -> None:
        """
        Perform monitor on method's IMP.
        See monitor command for more details.
        :param args: given arguments for monitor command
        """
        self.client.symbol(self.imp).monitor(**args)

    def bp(self, **args) -> None:
        """
        Place a breakpoint on method's IMP.
        See bp command for more details.
        :param args: given arguments for bp command
        """
        self.client.symbol(self.imp).bp(**args)

    def __str__(self) -> str:
        if ":" in self.name:
            args_names = self.name.split(":")
            name = " ".join(["{}:({})".format(*arg) for arg in zip(args_names, self.args_types[2:])])
        else:
            name = self.name
        prefix = "+" if self.is_class else "-"
        return f"{prefix} {name}; // 0x{self.address:x} (returns: {self.return_type})\n"
```

#### from_data

```
from_data(class_name: str, data: dict, client) -> Method
```

Create Method object from raw data.

Parameters:

| Name         | Type          | Description                                       | Default    |
| ------------ | ------------- | ------------------------------------------------- | ---------- |
| `class_name` | `str`         | ObjC class name                                   | *required* |
| `data`       | `dict`        | Data as loaded from get_objectivec_symbol_data.m. | *required* |
| `client`     | `HildaClient` | Hilda client.                                     | *required* |

Source code in `hilda/objective_c_class.py`

```
@staticmethod
def from_data(class_name: str, data: dict, client) -> "Method":
    """
    Create Method object from raw data.
    :param class_name: ObjC class name
    :param data: Data as loaded from get_objectivec_symbol_data.m.
    :param hilda.hilda_client.HildaClient client: Hilda client.
    """
    return Method(
        name=data["name"],
        client=client,
        address=client.symbol(data["address"]),
        imp=client.symbol(data["imp"]),
        type_=data["type"],
        return_type=decode_type(data["return_type"]),
        is_class=data["is_class"],
        args_types=list(map(decode_type, data["args_types"])),
        class_name=class_name,
    )
```

#### monitor

```
monitor(**args) -> None
```

Perform monitor on method's IMP. See monitor command for more details.

Parameters:

| Name   | Type | Description                         | Default |
| ------ | ---- | ----------------------------------- | ------- |
| `args` |      | given arguments for monitor command | `{}`    |

Source code in `hilda/objective_c_class.py`

```
def monitor(self, **args) -> None:
    """
    Perform monitor on method's IMP.
    See monitor command for more details.
    :param args: given arguments for monitor command
    """
    self.client.symbol(self.imp).monitor(**args)
```

#### bp

```
bp(**args) -> None
```

Place a breakpoint on method's IMP. See bp command for more details.

Parameters:

| Name   | Type | Description                    | Default |
| ------ | ---- | ------------------------------ | ------- |
| `args` |      | given arguments for bp command | `{}`    |

Source code in `hilda/objective_c_class.py`

```
def bp(self, **args) -> None:
    """
    Place a breakpoint on method's IMP.
    See bp command for more details.
    :param args: given arguments for bp command
    """
    self.client.symbol(self.imp).bp(**args)
```

### MethodList

Bases: `UserList`

Source code in `hilda/objective_c_class.py`

```
class MethodList(UserList):
    def __init__(self, class_name: str, methods: list[Method]) -> None:
        super().__init__()
        self._class_name = class_name
        self.data = methods

    def get(self, name: str) -> Optional[Method]:
        """
        Get a specific method implementation.
        :param name: Method name.
        :return: Method.
        """
        for method in self.data:
            if method.name == name:
                return method
        return None

    # Actions

    def bp(self, callback=None, **kwargs):
        """
        Place a breakpoint on all symbols in the method list.
        Look for the bp command for more details.
        :param callback:  callback function to be executed upon an hit
        :param kwargs: optional kwargs for the bp command
        """
        for method in self.data:
            kwargs["name"] = f"[{self._class_name} {method.name}]"
            method.imp.bp(callback, **kwargs)

    def monitor(self, **kwargs):
        """
        Perform monitor for all symbols in the method list.
        See monitor command for more details.
        :param kwargs: given arguments for monitor command
        """
        for method in self.data:
            method_kwargs = kwargs.copy()
            method_kwargs["name"] = f"{'+' if method.is_class else '-'}[{method.class_name} {method.name}]"
            method.imp.monitor(**method_kwargs)

    # Filters

    def filter_startswith(self, exp, case_sensitive=True):
        """
        Filter only methods with given prefix
        :param exp: prefix
        :param case_sensitive: is case sensitive
        :return: reduced method list
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = []
        for v in self.data:
            name = v.name
            if not case_sensitive:
                name = name.lower()
            if name.startswith(exp):
                retval.append(v)
        return MethodList(self._class_name, retval)

    def filter_name_contains(self, exp, case_sensitive=True):
        """
        Filter methods containing a given expression
        :param exp: given expression
        :param case_sensitive: is case sensitive
        :return: reduced method list
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = []
        for v in self.data:
            name = v.name
            if not case_sensitive:
                name = name.lower()
            if exp in name:
                retval.append(v)
        return MethodList(self._class_name, retval)
```

#### get

```
get(name: str) -> Optional[Method]
```

Get a specific method implementation.

Parameters:

| Name   | Type  | Description  | Default    |
| ------ | ----- | ------------ | ---------- |
| `name` | `str` | Method name. | *required* |

Returns:

| Type               | Description |
| ------------------ | ----------- |
| `Optional[Method]` | Method.     |

Source code in `hilda/objective_c_class.py`

```
def get(self, name: str) -> Optional[Method]:
    """
    Get a specific method implementation.
    :param name: Method name.
    :return: Method.
    """
    for method in self.data:
        if method.name == name:
            return method
    return None
```

#### bp

```
bp(callback=None, **kwargs)
```

Place a breakpoint on all symbols in the method list. Look for the bp command for more details.

Parameters:

| Name       | Type | Description                                  | Default |
| ---------- | ---- | -------------------------------------------- | ------- |
| `callback` |      | callback function to be executed upon an hit | `None`  |
| `kwargs`   |      | optional kwargs for the bp command           | `{}`    |

Source code in `hilda/objective_c_class.py`

```
def bp(self, callback=None, **kwargs):
    """
    Place a breakpoint on all symbols in the method list.
    Look for the bp command for more details.
    :param callback:  callback function to be executed upon an hit
    :param kwargs: optional kwargs for the bp command
    """
    for method in self.data:
        kwargs["name"] = f"[{self._class_name} {method.name}]"
        method.imp.bp(callback, **kwargs)
```

#### monitor

```
monitor(**kwargs)
```

Perform monitor for all symbols in the method list. See monitor command for more details.

Parameters:

| Name     | Type | Description                         | Default |
| -------- | ---- | ----------------------------------- | ------- |
| `kwargs` |      | given arguments for monitor command | `{}`    |

Source code in `hilda/objective_c_class.py`

```
def monitor(self, **kwargs):
    """
    Perform monitor for all symbols in the method list.
    See monitor command for more details.
    :param kwargs: given arguments for monitor command
    """
    for method in self.data:
        method_kwargs = kwargs.copy()
        method_kwargs["name"] = f"{'+' if method.is_class else '-'}[{method.class_name} {method.name}]"
        method.imp.monitor(**method_kwargs)
```

#### filter_startswith

```
filter_startswith(exp, case_sensitive=True)
```

Filter only methods with given prefix

Parameters:

| Name             | Type | Description       | Default    |
| ---------------- | ---- | ----------------- | ---------- |
| `exp`            |      | prefix            | *required* |
| `case_sensitive` |      | is case sensitive | `True`     |

Returns:

| Type | Description         |
| ---- | ------------------- |
|      | reduced method list |

Source code in `hilda/objective_c_class.py`

```
def filter_startswith(self, exp, case_sensitive=True):
    """
    Filter only methods with given prefix
    :param exp: prefix
    :param case_sensitive: is case sensitive
    :return: reduced method list
    """
    if not case_sensitive:
        exp = exp.lower()

    retval = []
    for v in self.data:
        name = v.name
        if not case_sensitive:
            name = name.lower()
        if name.startswith(exp):
            retval.append(v)
    return MethodList(self._class_name, retval)
```

#### filter_name_contains

```
filter_name_contains(exp, case_sensitive=True)
```

Filter methods containing a given expression

Parameters:

| Name             | Type | Description       | Default    |
| ---------------- | ---- | ----------------- | ---------- |
| `exp`            |      | given expression  | *required* |
| `case_sensitive` |      | is case sensitive | `True`     |

Returns:

| Type | Description         |
| ---- | ------------------- |
|      | reduced method list |

Source code in `hilda/objective_c_class.py`

```
def filter_name_contains(self, exp, case_sensitive=True):
    """
    Filter methods containing a given expression
    :param exp: given expression
    :param case_sensitive: is case sensitive
    :return: reduced method list
    """
    if not case_sensitive:
        exp = exp.lower()

    retval = []
    for v in self.data:
        name = v.name
        if not case_sensitive:
            name = name.lower()
        if exp in name:
            retval.append(v)
    return MethodList(self._class_name, retval)
```

### Class

Wrapper for ObjectiveC Class object.

Source code in `hilda/objective_c_class.py`

```
class Class:
    """
    Wrapper for ObjectiveC Class object.
    """

    def __init__(self, client, class_object=0, class_data: Optional[dict] = None):
        """
        :param hilda.hilda_client.HildaClient client:
        :param hilda.symbol.Symbol class_object:
        """
        self._client = client
        self._class_object = class_object
        self.protocols = []
        self.ivars = []
        self.properties = []
        self.name = ""
        self.methods = MethodList(self.name, [])
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
        obj_c_code = (client._hilda_root / "objective_c" / "get_objectivec_class_description.m").read_text()
        obj_c_code = obj_c_code.replace("__class_address__", "0").replace("__class_name__", class_name)
        class_symbol = Class(client, class_data=json.loads(client.po(obj_c_code)))
        if class_symbol.name != class_name:
            raise GettingObjectiveCClassError()
        return class_symbol

    @staticmethod
    def sanitize_name(name: str):
        """
        Sanitize python name to ObjectiveC name.
        """
        name = "_" + name[1:].replace("_", ":") if name.startswith("_") else name.replace("_", ":")
        return name

    def reload(self):
        """
        Reload class object data.
        Should be used whenever the class layout changes (for example, during method swizzling)
        """
        obj_c_code = (self._client._hilda_root / "objective_c" / "get_objectivec_class_description.m").read_text()
        obj_c_code = obj_c_code.replace("__class_address__", f"{self._class_object:d}")
        obj_c_code = obj_c_code.replace("__class_name__", self.name)
        self._load_class_data(json.loads(self._client.po(obj_c_code)))

    def show(self):
        """
        Print to terminal the highlighted class description.
        """
        print(highlight(str(self), ObjectiveCLexer(), TerminalTrueColorFormatter(style="native")))

    def objc_call(self, sel: str, *args):
        """
        Invoke a selector on the given class object.
        :param sel: Selector name.
        :return: whatever the selector returned as a symbol.
        """
        return self._class_object.objc_call(sel, *args)

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

        group_bp_list = []

        def hook(hilda, frame, bp_loc, hilda_bp):
            hilda.log_info(f"self object has been captured for {class_name}")
            hilda.log_info("removing breakpoints")
            for bp in group_bp_list:
                bp.remove()

            captured = hilda.evaluate_expression("$arg1")
            captured = captured.objc_symbol
            captured.retain()
            hilda.captured_objects[class_name] = captured
            hilda.cont()

        for method in self.methods:
            if not method.is_class:
                # only instance methods are relevant for capturing self
                group_bp_list.append(method.imp.bp(hook))

        if sync:
            self._client.cont()
            self._client.log_debug("Waiting for desired object to be captured...")
            while class_name not in self._client.captured_objects:
                time.sleep(1)

            return self._client.captured_objects[class_name]

    def monitor(self, **kwargs):
        """
        Proxy for monitor command.
        """
        self.methods.monitor(**kwargs)

    def bp(self, callback=None, **kwargs):
        """
        Proxy for bp command.
        """
        self.methods.bp(callback, **kwargs)

    def iter_supers(self):
        """
        Iterate over the super classes of the class.
        """
        sup = self.super
        while sup is not None:
            yield sup
            sup = sup.super

    @property
    def bundle_path(self) -> Path:
        return Path(
            self._client.symbols
            .objc_getClass("NSBundle")
            .objc_call("bundleForClass:", self._class_object)
            .objc_call("bundlePath")
            .py()
        )

    def _load_class_data(self, data: dict):
        self._class_object = self._client.symbol(data["address"])
        self.super = Class(self._client, data["super"]) if data["super"] else None
        self.name = data["name"]
        self.protocols = data["protocols"]
        self.ivars = [
            Ivar(
                name=ivar["name"],
                type_=decode_type(ivar["type"]) if ivar["type"] else "unknown_type_t",
                offset=ivar["offset"],
            )
            for ivar in data["ivars"]
        ]
        self.properties = [
            Property(name=prop["name"], attributes=convert_encoded_property_attributes(prop["attributes"]))
            for prop in data["properties"]
        ]
        self.methods = MethodList(
            self.name, [Method.from_data(self.name, method, self._client) for method in data["methods"]]
        )

    def __dir__(self):
        result = set()

        for method in self.methods:
            if method.is_class:
                result.add(method.name.replace(":", "_"))

        for sup in self.iter_supers():
            if self._client.configs.nsobject_exclusion and sup.name == "NSObject":
                continue
            for method in sup.methods:
                if method.is_class:
                    result.add(method.name.replace(":", "_"))

        result.update(list(super().__dir__()))
        return list(result)

    def __str__(self):
        protocol_buf = f"<{','.join(self.protocols)}>" if self.protocols else ""

        if self.super is not None:
            buf = f"@interface {self.name}: {self.super.name} {protocol_buf}\n"
        else:
            buf = f"@interface {self.name} {protocol_buf}\n"

        # Add ivars
        buf += "{\n"
        for ivar in self.ivars:
            buf += f"\t{ivar.type_} {ivar.name}; // 0x{ivar.offset:x}\n"
        buf += "}\n"

        # Add properties
        for prop in self.properties:
            buf += f"@property ({','.join(prop.attributes.list)}) {prop.attributes.type_} {prop.name};\n"

            if prop.attributes.synthesize is not None:
                buf += f"@synthesize {prop.name} = {prop.attributes.synthesize};\n"

        # Add methods
        for method in self.methods:
            buf += str(method)

        buf += "@end"
        return buf

    def __repr__(self):
        return f'<objC Class "{self.name}">'

    def __getitem__(self, item):
        for method in self.methods:
            if method.name == item:
                if method.is_class:
                    return partial(self.objc_call, item)
                else:
                    raise AttributeError(f"{self.name} class has an instance method named {item}, not a class method")

        for sup in self.iter_supers():
            for method in sup.methods:
                if method.name == item:
                    if method.is_class:
                        return partial(self.objc_call, item)
                    else:
                        raise AttributeError(
                            f"{self.name} class has an instance method named {item}, not a class method"
                        )

        raise AttributeError(f"""'{self.name}' class has no attribute {item}""")

    def __getattr__(self, item: str):
        return self[self.sanitize_name(item)]
```

#### from_class_name

```
from_class_name(client, class_name: str)
```

Create ObjectiveC Class from given class name.

Parameters:

| Name         | Type          | Description   | Default    |
| ------------ | ------------- | ------------- | ---------- |
| `client`     | `HildaClient` | Hilda client. | *required* |
| `class_name` | `str`         | Class name.   | *required* |

Source code in `hilda/objective_c_class.py`

```
@staticmethod
def from_class_name(client, class_name: str):
    """
    Create ObjectiveC Class from given class name.
    :param hilda.hilda_client.HildaClient client: Hilda client.
    :param class_name: Class name.
    """
    obj_c_code = (client._hilda_root / "objective_c" / "get_objectivec_class_description.m").read_text()
    obj_c_code = obj_c_code.replace("__class_address__", "0").replace("__class_name__", class_name)
    class_symbol = Class(client, class_data=json.loads(client.po(obj_c_code)))
    if class_symbol.name != class_name:
        raise GettingObjectiveCClassError()
    return class_symbol
```

#### sanitize_name

```
sanitize_name(name: str)
```

Sanitize python name to ObjectiveC name.

Source code in `hilda/objective_c_class.py`

```
@staticmethod
def sanitize_name(name: str):
    """
    Sanitize python name to ObjectiveC name.
    """
    name = "_" + name[1:].replace("_", ":") if name.startswith("_") else name.replace("_", ":")
    return name
```

#### reload

```
reload()
```

Reload class object data. Should be used whenever the class layout changes (for example, during method swizzling)

Source code in `hilda/objective_c_class.py`

```
def reload(self):
    """
    Reload class object data.
    Should be used whenever the class layout changes (for example, during method swizzling)
    """
    obj_c_code = (self._client._hilda_root / "objective_c" / "get_objectivec_class_description.m").read_text()
    obj_c_code = obj_c_code.replace("__class_address__", f"{self._class_object:d}")
    obj_c_code = obj_c_code.replace("__class_name__", self.name)
    self._load_class_data(json.loads(self._client.po(obj_c_code)))
```

#### show

```
show()
```

Print to terminal the highlighted class description.

Source code in `hilda/objective_c_class.py`

```
def show(self):
    """
    Print to terminal the highlighted class description.
    """
    print(highlight(str(self), ObjectiveCLexer(), TerminalTrueColorFormatter(style="native")))
```

#### objc_call

```
objc_call(sel: str, *args)
```

Invoke a selector on the given class object.

Parameters:

| Name  | Type  | Description    | Default    |
| ----- | ----- | -------------- | ---------- |
| `sel` | `str` | Selector name. | *required* |

Returns:

| Type | Description                                 |
| ---- | ------------------------------------------- |
|      | whatever the selector returned as a symbol. |

Source code in `hilda/objective_c_class.py`

```
def objc_call(self, sel: str, *args):
    """
    Invoke a selector on the given class object.
    :param sel: Selector name.
    :return: whatever the selector returned as a symbol.
    """
    return self._class_object.objc_call(sel, *args)
```

#### capture_self

```
capture_self(sync: bool = False)
```

Capture the first called `self` from this class. Access using `self.captured_objects`

Parameters:

| Name   | Type   | Description                                    | Default |
| ------ | ------ | ---------------------------------------------- | ------- |
| `sync` | `bool` | Should wait until captured object is returned? | `False` |

Returns:

| Type | Description                                     |
| ---- | ----------------------------------------------- |
|      | Captured object if sync is True, None otherwise |

Source code in `hilda/objective_c_class.py`

```
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

    group_bp_list = []

    def hook(hilda, frame, bp_loc, hilda_bp):
        hilda.log_info(f"self object has been captured for {class_name}")
        hilda.log_info("removing breakpoints")
        for bp in group_bp_list:
            bp.remove()

        captured = hilda.evaluate_expression("$arg1")
        captured = captured.objc_symbol
        captured.retain()
        hilda.captured_objects[class_name] = captured
        hilda.cont()

    for method in self.methods:
        if not method.is_class:
            # only instance methods are relevant for capturing self
            group_bp_list.append(method.imp.bp(hook))

    if sync:
        self._client.cont()
        self._client.log_debug("Waiting for desired object to be captured...")
        while class_name not in self._client.captured_objects:
            time.sleep(1)

        return self._client.captured_objects[class_name]
```

#### monitor

```
monitor(**kwargs)
```

Proxy for monitor command.

Source code in `hilda/objective_c_class.py`

```
def monitor(self, **kwargs):
    """
    Proxy for monitor command.
    """
    self.methods.monitor(**kwargs)
```

#### bp

```
bp(callback=None, **kwargs)
```

Proxy for bp command.

Source code in `hilda/objective_c_class.py`

```
def bp(self, callback=None, **kwargs):
    """
    Proxy for bp command.
    """
    self.methods.bp(callback, **kwargs)
```

#### iter_supers

```
iter_supers()
```

Iterate over the super classes of the class.

Source code in `hilda/objective_c_class.py`

```
def iter_supers(self):
    """
    Iterate over the super classes of the class.
    """
    sup = self.super
    while sup is not None:
        yield sup
        sup = sup.super
```
