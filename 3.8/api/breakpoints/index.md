# Breakpoints & watchpoints

## Breakpoints

## hilda.breakpoints

### HildaBreakpoint

Hilda's class representing an LLDB breakpoint, with some optional additional properties

Source code in `hilda/breakpoints.py`

```
class HildaBreakpoint:
    """
    Hilda's class representing an LLDB breakpoint, with some optional additional properties
    """

    def __init__(
        self,
        hilda,
        lldb_breakpoint: lldb.SBBreakpoint,
        where: Optional[WhereType] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Initialize a HildaBreakpoint.

        :param hilda.hilda_client.HildaClient hilda: Hilda client
        :param lldb.SBBreakpoint lldb_breakpoint: LLDB breakpoint to wrap
        :param WhereType where: Where the breakpoint is located
        :param description: Description of the breakpoint to appear upon `hilda.breakpoints.show()`
        """
        self._hilda = hilda
        self._where = where
        self._callback = None

        # Actual breakpoint from LLDB API
        self.lldb_breakpoint = lldb_breakpoint

        # If true, breakpoint will not be removed unless `remove_guarded` is requested
        self.guarded = False

        # Attach a description to the breakpoint
        self.description = description

    @property
    def where(self) -> Optional[WhereType]:
        """Where the breakpoint was set (when it was created)."""
        return self._where

    @property
    def id(self) -> int:
        """A number identifying the breakpoint."""
        return self.lldb_breakpoint.GetID()

    @property
    def callback(self) -> Optional[Callable]:
        """
        A callback that will be executed when the breakpoint is hit.
        Note that unless the callback explicitly continues (by calling `cont()`), the program will not continue.
        The callback will be invoked as `callback(hilda, *args)`, where hilda is the `HildaClient`.
        """
        return self._callback

    @callback.setter
    def callback(self, callback: Optional[Callable]) -> None:
        self._callback = callback

        if callback is not None:
            self.lldb_breakpoint.SetScriptCallbackFunction(
                "lldb.hilda_client.breakpoints._dispatch_breakpoint_callback"
            )

    @property
    def condition(self) -> Optional[str]:
        """An LLDB expression to make this a conditional breakpoint."""
        return self.lldb_breakpoint.GetCondition()

    @condition.setter
    def condition(self, condition: Optional[str]) -> None:
        self.lldb_breakpoint.SetCondition(condition)

    @property
    def locations(self) -> list[lldb.SBBreakpointLocation]:
        """LLDB locations array the breakpoint relates to."""
        return self.lldb_breakpoint.locations

    @property
    def name(self) -> Optional[str]:
        """
        A name for the breakpoint.
        When getting, if the breakpoint has multiple names, raises an exception.
        """
        names = self.names
        if len(names) == 0:
            return None
        if len(names) != 1:
            raise ValueError(f"Breakpoint {self.id} has multiple names {names}")

        (name,) = names
        return name

    @name.setter
    def name(self, name: Optional[str]) -> None:
        self.names = {name}

    @property
    def names(self) -> set[str]:
        """The set of names of the breakpoint."""
        name_list = lldb.SBStringList()
        self.lldb_breakpoint.GetNames(name_list)
        return {name_list.GetStringAtIndex(i) for i in range(name_list.GetSize())}

    @names.setter
    def names(self, names: Union[set[str], list[str]]) -> None:
        new_names = set(names)
        if len(new_names) != len(names):
            raise ValueError(f"Duplicate names in {names}")

        current_names = self.names
        names_to_remove = current_names - new_names
        names_to_add = new_names - current_names
        for name in names_to_remove:
            self.lldb_breakpoint.RemoveName(name)
        for name in names_to_add:
            self.lldb_breakpoint.AddName(name)

    @property
    def enabled(self) -> bool:
        """
        Configures whether this breakpoint is enabled or not.
        """
        return self.lldb_breakpoint.IsEnabled()

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.lldb_breakpoint.SetEnabled(value)

    def __repr__(self) -> str:
        enabled_repr = "ENABLED" if self.enabled else "DISABLED"
        guarded_repr = "GUARDED" if self.guarded else "NOT-GUARDED"
        return (
            f"<{self.__class__.__name__} LLDB:{self.lldb_breakpoint} {enabled_repr} {guarded_repr} "
            f"CALLBACK:{self.callback}>"
        )

    def __str__(self) -> str:
        emoji = "🚨" if self.enabled else "🔕"
        enabled_str = "enabled" if self.enabled else "disabled"
        guarded_str = "guarded" if self.guarded else "not-guarded"

        result = f"{emoji} Breakpoint #{self.id} ({enabled_str}, {guarded_str})\n"

        if self.description is not None:
            result += f"\tDescription: {self.description}\n"

        if self.where is not None:
            result += f"\tWhere: {self.where}\n"

        # A single breakpoint may be related to several locations (addresses)
        locations = self.locations
        if len(locations) == 0:
            result += "\tNo locations\n"
        for location in self.locations:
            result += f"\tLocation {location}\n"

        return result.strip("\n")

    def remove(self, remove_guarded: bool = False) -> None:
        """
        Remove the breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument)

        :param bool remove_guarded: Remove the breakpoint even if the breakpoint is guarded
        """
        self._hilda.breakpoints.remove(self, remove_guarded)
```

#### where

```
where: Optional[WhereType]
```

Where the breakpoint was set (when it was created).

#### id

```
id: int
```

A number identifying the breakpoint.

#### callback

```
callback: Optional[Callable]
```

A callback that will be executed when the breakpoint is hit. Note that unless the callback explicitly continues (by calling `cont()`), the program will not continue. The callback will be invoked as `callback(hilda, *args)`, where hilda is the `HildaClient`.

#### condition

```
condition: Optional[str]
```

An LLDB expression to make this a conditional breakpoint.

#### locations

```
locations: list[SBBreakpointLocation]
```

LLDB locations array the breakpoint relates to.

#### name

```
name: Optional[str]
```

A name for the breakpoint. When getting, if the breakpoint has multiple names, raises an exception.

#### names

```
names: set[str]
```

The set of names of the breakpoint.

#### enabled

```
enabled: bool
```

Configures whether this breakpoint is enabled or not.

#### remove

```
remove(remove_guarded: bool = False) -> None
```

Remove the breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument)

Parameters:

| Name             | Type   | Description                                             | Default |
| ---------------- | ------ | ------------------------------------------------------- | ------- |
| `remove_guarded` | `bool` | Remove the breakpoint even if the breakpoint is guarded | `False` |

Source code in `hilda/breakpoints.py`

```
def remove(self, remove_guarded: bool = False) -> None:
    """
    Remove the breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument)

    :param bool remove_guarded: Remove the breakpoint even if the breakpoint is guarded
    """
    self._hilda.breakpoints.remove(self, remove_guarded)
```

### BreakpointList

Manager for `HildaBreakpoint` objects, each one wrapping another native LLDB breakpoint.

Source code in `hilda/breakpoints.py`

```
class BreakpointList:
    """
    Manager for `HildaBreakpoint` objects, each one wrapping another native LLDB breakpoint.
    """

    def __init__(self, hilda) -> None:
        """
        Initialize a breakpoint list.

        :param hilda.hilda_client.HildaClient hilda: Hilda client
        """
        self._hilda = hilda
        self._breakpoints = {}

    def __contains__(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint]):
        return self.get(id_or_name_or_bp) is not None

    def __iter__(self):
        for bp in self._hilda.target.breakpoint_iter():
            yield self[bp.GetID()]

    def __len__(self) -> int:
        return self._hilda.target.GetNumBreakpoints()

    def __getitem__(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint]) -> HildaBreakpoint:
        """
        Get a breakpoint by ID or name (or the breakpoint itself, though it usually makes little sense)

        :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
        """
        bp = self.get(id_or_name_or_bp)
        if bp is None:
            raise KeyError(id_or_name_or_bp)
        return bp

    def __delitem__(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint]) -> None:
        """
        Remove a breakpoint (unless the breakpoint is marked as guarded - see remove())

        :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
        """
        self.remove(id_or_name_or_bp)

    def __repr__(self) -> str:
        return repr(dict(self.items()))

    def __str__(self) -> str:
        return repr(self)

    def get(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint]) -> Optional[HildaBreakpoint]:
        """
        Get a breakpoint by ID or name (or the breakpoint itself, though it usually makes little sense) or null
        if it does not exist.

        :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
        :return: `HildaBreakpoint` if one exists, or `None` otherwise
        """

        if isinstance(id_or_name_or_bp, int):
            bp = self._hilda.target.FindBreakpointByID(id_or_name_or_bp)
        elif isinstance(id_or_name_or_bp, str):
            breakpoints = lldb.SBBreakpointList(self._hilda.target)
            found = self._hilda.target.FindBreakpointsByName(id_or_name_or_bp, breakpoints)
            if not found or breakpoints.GetSize() == 0:
                return None
            if breakpoints.GetSize() != 1:
                # Error out if we found multiple breakpoints with the name
                raise KeyError(id_or_name_or_bp)
            bp = breakpoints.GetBreakpointAtIndex(0)
        elif isinstance(id_or_name_or_bp, HildaBreakpoint):
            bp = id_or_name_or_bp.lldb_breakpoint
        else:
            raise TypeError()

        if not bp.IsValid():
            return None

        bp_id = bp.GetID()
        if bp_id not in self._breakpoints:
            self._hilda.log_debug(f"Found a breakpoint added outside of the Hilda API {bp}")
            self._breakpoints[bp_id] = HildaBreakpoint(self._hilda, bp)

        return self._breakpoints[bp_id]

    def add(
        self,
        where: WhereType,
        callback: Optional[Callable] = None,
        condition: Optional[str] = None,
        guarded: bool = False,
        override: bool = True,
        description: Optional[str] = None,
    ) -> HildaBreakpoint:
        """
        Add a breakpoint.

        :param where: The address of the breakpoint.
            It could be either an address (int), a symbol name (string), a symbol name in a
            specific module (Tuple[str, str], where the first item is the symbol name and the
            second is the module name) or a Hilda symbol object (Symbol, that inherits from int).
        :param callback: A callback that will be executed when the breakpoint is hit.
            Note that unless the callback explicitly continues (by calling cont()), the program will not continue.
            The callback will be invoked as callback(hilda, *args), where hilda is the 'HildaClient'.
        :param condition: An LLDB expression to make this a conditional breakpoint.
        :param guarded: If true, breakpoint will not be removed unless remove_guarded is requested
        :param override: If True and an existing breakpoint with the same `where` is found, remove the old
            breakpoint and replace it with the new breakpoint. Otherwise, prompt the user.
        :return: The new breakpoint
        """
        if where in (bp.where for bp in self) and (
            override
            or inquirer3.confirm(
                "A breakpoint already exist in given location. Would you like to delete the previous one?", True
            )
        ):
            for bp in [bp for bp in self if where == bp.where]:
                del self[bp]

        if isinstance(where, int):
            bp = self._hilda.target.BreakpointCreateByAddress(where)
        elif isinstance(where, str):
            # Note that the name in BreakpointCreateByName is the name of the location,
            # not the name of the breakpoint.
            bp = self._hilda.target.BreakpointCreateByName(where)
        elif isinstance(where, tuple):
            _name, _module = where
            raise NotImplementedError()
        if not bp.IsValid():
            raise HildaException(f"Failed to create breakpoint at {where}")

        bp = HildaBreakpoint(self._hilda, bp, where, description=description)
        bp.callback = callback
        bp.condition = condition
        bp.guarded = guarded

        self._breakpoints[bp.id] = bp

        self._hilda.log_info(f"Breakpoint #{bp.id} has been set")
        return bp

    def add_monitor(
        self,
        where: WhereType,
        condition: Optional[str] = None,
        guarded: bool = False,
        override: bool = True,
        regs: Optional[dict[str, Union[str, Callable]]] = None,
        expr: Optional[dict[str, Union[str, Callable]]] = None,
        retval: Optional[Union[str, Callable]] = None,
        stop: bool = False,
        bt: bool = False,
        cmd: Optional[list[str]] = None,
        force_return: Optional[bool] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> HildaBreakpoint:
        """
        Monitor every time a given address is called.

        Creates a breakpoint whose callback implements the requested features.

        :param where: See add() for details.
        :param condition: See add() for details.
        :param guarded: See add() for details.
        :param override: See add() for details.
        :param regs: Print register values (using the provided format).
            E.g., `regs={'x0': 'x'}` prints x0 in HEX format
            The available formats are:
                'x': hex
                's': string
                'cf': use CFCopyDescription() to get more informative description of the object
                'po': use LLDB po command
                'std::string': for std::string
                Callable: user defined function, will be called like `format_function(hilda_client, value)`.
        :param expr: Print LLDB expression (using the provided format).
            E.g., `expr={'$x0': 'x', '$arg1': 'x'}` (to print the value of x0 and arg1).
            The format behaves like in regs above.
        :param retval: Print the return value of the function (using the provided format).
            The format behaves like in regs above.
        :param stop: If True, stop whenever the breakpoint is hit (otherwise continue debugging).
        :param bt: Print backtrace.
        :param cmd: A list of LLDB commands to run when the breakpoint is hit.
        :param force_return: Return immediately from the function, returning the specified value.
        :param name: Use the provided name instead of the symbol name automatically extracted from the calling frame.
        :param description: Attach a brief description of the breakpoint.
        :return: The new breakpoint
        """

        if regs is None:
            regs = {}
        if expr is None:
            expr = {}
        if cmd is None:
            cmd = []

        def callback(hilda, frame: lldb.SBFrame, bp_loc: lldb.SBBreakpointLocation, *_) -> None:
            """
            Callback function called when a breakpoint is hit.

            :param hilda.hilda_client.HildaClient hilda: Hilda client to operate on
            :param frame: LLDB frame
            :param bp_loc: LLDB breakpoint location
            """
            nonlocal name
            bp = bp_loc.GetBreakpoint()
            symbol = hilda.symbol(hilda.frame.addr.GetLoadAddress(hilda.target))
            thread = hilda.thread
            printed_name = name if name is not None else str(symbol.lldb_address)

            def format_value(fmt: Union[str, Callable], value: Symbol) -> str:
                if callable(fmt):
                    return fmt(hilda, value)
                formatters = {
                    "x": lambda val: f"0x{int(val):x}",
                    "s": lambda val: val.peek_str() if val else None,
                    "cf": lambda val: val.cf_description,
                    "po": lambda val: val.po(),
                    "std::string": hilda._std_string,
                }
                if fmt in formatters:
                    return formatters[fmt](value)
                else:
                    return f"{value:x} (unsupported format)"

            log_message = f"🚨 #{bp.id} 0x{symbol:x} {printed_name} - Thread #{thread.idx}:{hex(thread.id)}"

            if regs != {}:
                log_message += "\nregs:"
                for reg_name, fmt in regs.items():
                    value = hilda.symbol(frame.FindRegister(reg_name).unsigned)
                    log_message += f"\n\t{reg_name} = {format_value(fmt, value)}"

            if expr != {}:
                log_message += "\nexpr:"
                for expr_name, fmt in expr.items():
                    value = hilda.symbol(hilda.evaluate_expression(expr_name))
                    log_message += f"\n\t{expr_name} = {format_value(fmt, value)}"

            if force_return is not None:
                hilda.force_return(force_return)
                log_message += f"\nforced return: {force_return}"

            if bt:
                # bugfix: for callstacks from xpc events
                hilda.finish()
                for frame in hilda.bt():
                    log_message += f"\n\t{frame[0]} {frame[1]}"

            if retval is not None:
                # return from function
                hilda.finish()
                value = hilda.evaluate_expression("$arg1")
                log_message += f"\nreturned: {format_value(retval, value)}"

            hilda.log_info(log_message)

            for command in cmd:
                hilda.lldb_handle_command(command)

            if stop:
                hilda.log_info("Process remains stopped and focused on current thread")
            else:
                hilda.cont()

        return self.add(
            where, callback, condition=condition, guarded=guarded, override=override, description=description
        )

    def remove(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint], remove_guarded: bool = False) -> None:
        """
        Remove a breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument).

        :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
        :param remove_guarded: Remove breakpoint even if the breakpoint is marked as guarded
        """

        bp = self[id_or_name_or_bp]

        if bp.guarded and not remove_guarded:
            self._hilda.log_warning(f"Remove request for breakpoint {bp} is ignored")
            return

        # Removing a breakpoint without using this function would leak the breakpoint in self._breakpoints

        breakpoint_id = bp.id
        self._hilda.target.BreakpointDelete(breakpoint_id)
        self._hilda.log_debug(f"Breakpoint #{breakpoint_id} has been removed")

    def clear(self, remove_guarded: bool = False) -> None:
        """
        Remove all breakpoints (except for breakpoints marked as guarded, see remove_guarded argument).

        :param remove_guarded: Also remove breakpoints marked as guarded
        """
        breakpoints = list(self)
        for bp in breakpoints:
            if not remove_guarded and bp.guarded:
                continue

            self.remove(bp, remove_guarded)

    def show(self) -> None:
        """Show existing breakpoints."""
        if len(self) == 0:
            self._hilda.log_info("No breakpoints")
        for bp in self:
            self._hilda.log_info(bp)

    def items(self):
        """
        Get a breakpoint ID and breakpoint object tuple for every breakpoint
        """
        return ((bp.id, bp) for bp in self)

    def keys(self) -> Generator[int, Any, None]:
        """
        Get the breakpoint ID for every breakpoint
        """
        return (bp.id for bp in self)

    def values(self) -> Generator[HildaBreakpoint, Any, None]:
        """
        Get the breakpoint object for every breakpoint
        """
        return (bp for bp in self)

    def _dispatch_breakpoint_callback(self, frame, bp_loc, *_) -> None:
        """
        Route the breakpoint callback the specific breakpoint callback.

        :param lldb.SBFrame frame: LLDB Frame object.
        :param lldb.SBBreakpointLocation bp_loc: LLDB Breakpoint location object.
        """

        bp_id = bp_loc.GetBreakpoint().GetID()
        self._hilda._bp_frame = frame
        try:
            callback = self[bp_id].callback
            if callback is not None:
                callback(self._hilda, frame, bp_loc, self[bp_id])
        finally:
            self._hilda._bp_frame = None
```

#### get

```
get(id_or_name_or_bp: Union[int, str, HildaBreakpoint]) -> Optional[HildaBreakpoint]
```

Get a breakpoint by ID or name (or the breakpoint itself, though it usually makes little sense) or null if it does not exist.

Parameters:

| Name               | Type                               | Description                                        | Default    |
| ------------------ | ---------------------------------- | -------------------------------------------------- | ---------- |
| `id_or_name_or_bp` | `Union[int, str, HildaBreakpoint]` | Breakpoint's ID or name (or the breakpoint itself) | *required* |

Returns:

| Type                        | Description                                      |
| --------------------------- | ------------------------------------------------ |
| `Optional[HildaBreakpoint]` | HildaBreakpoint if one exists, or None otherwise |

Source code in `hilda/breakpoints.py`

```
def get(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint]) -> Optional[HildaBreakpoint]:
    """
    Get a breakpoint by ID or name (or the breakpoint itself, though it usually makes little sense) or null
    if it does not exist.

    :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
    :return: `HildaBreakpoint` if one exists, or `None` otherwise
    """

    if isinstance(id_or_name_or_bp, int):
        bp = self._hilda.target.FindBreakpointByID(id_or_name_or_bp)
    elif isinstance(id_or_name_or_bp, str):
        breakpoints = lldb.SBBreakpointList(self._hilda.target)
        found = self._hilda.target.FindBreakpointsByName(id_or_name_or_bp, breakpoints)
        if not found or breakpoints.GetSize() == 0:
            return None
        if breakpoints.GetSize() != 1:
            # Error out if we found multiple breakpoints with the name
            raise KeyError(id_or_name_or_bp)
        bp = breakpoints.GetBreakpointAtIndex(0)
    elif isinstance(id_or_name_or_bp, HildaBreakpoint):
        bp = id_or_name_or_bp.lldb_breakpoint
    else:
        raise TypeError()

    if not bp.IsValid():
        return None

    bp_id = bp.GetID()
    if bp_id not in self._breakpoints:
        self._hilda.log_debug(f"Found a breakpoint added outside of the Hilda API {bp}")
        self._breakpoints[bp_id] = HildaBreakpoint(self._hilda, bp)

    return self._breakpoints[bp_id]
```

#### add

```
add(where: WhereType, callback: Optional[Callable] = None, condition: Optional[str] = None, guarded: bool = False, override: bool = True, description: Optional[str] = None) -> HildaBreakpoint
```

Add a breakpoint.

Parameters:

| Name        | Type                 | Description                                                                                                                                                                                                                                                                            | Default    |
| ----------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `where`     | `WhereType`          | The address of the breakpoint. It could be either an address (int), a symbol name (string), a symbol name in a specific module (Tuple[str, str], where the first item is the symbol name and the second is the module name) or a Hilda symbol object (Symbol, that inherits from int). | *required* |
| `callback`  | `Optional[Callable]` | A callback that will be executed when the breakpoint is hit. Note that unless the callback explicitly continues (by calling cont()), the program will not continue. The callback will be invoked as callback(hilda, \*args), where hilda is the 'HildaClient'.                         | `None`     |
| `condition` | `Optional[str]`      | An LLDB expression to make this a conditional breakpoint.                                                                                                                                                                                                                              | `None`     |
| `guarded`   | `bool`               | If true, breakpoint will not be removed unless remove_guarded is requested                                                                                                                                                                                                             | `False`    |
| `override`  | `bool`               | If True and an existing breakpoint with the same where is found, remove the old breakpoint and replace it with the new breakpoint. Otherwise, prompt the user.                                                                                                                         | `True`     |

Returns:

| Type              | Description        |
| ----------------- | ------------------ |
| `HildaBreakpoint` | The new breakpoint |

Source code in `hilda/breakpoints.py`

```
def add(
    self,
    where: WhereType,
    callback: Optional[Callable] = None,
    condition: Optional[str] = None,
    guarded: bool = False,
    override: bool = True,
    description: Optional[str] = None,
) -> HildaBreakpoint:
    """
    Add a breakpoint.

    :param where: The address of the breakpoint.
        It could be either an address (int), a symbol name (string), a symbol name in a
        specific module (Tuple[str, str], where the first item is the symbol name and the
        second is the module name) or a Hilda symbol object (Symbol, that inherits from int).
    :param callback: A callback that will be executed when the breakpoint is hit.
        Note that unless the callback explicitly continues (by calling cont()), the program will not continue.
        The callback will be invoked as callback(hilda, *args), where hilda is the 'HildaClient'.
    :param condition: An LLDB expression to make this a conditional breakpoint.
    :param guarded: If true, breakpoint will not be removed unless remove_guarded is requested
    :param override: If True and an existing breakpoint with the same `where` is found, remove the old
        breakpoint and replace it with the new breakpoint. Otherwise, prompt the user.
    :return: The new breakpoint
    """
    if where in (bp.where for bp in self) and (
        override
        or inquirer3.confirm(
            "A breakpoint already exist in given location. Would you like to delete the previous one?", True
        )
    ):
        for bp in [bp for bp in self if where == bp.where]:
            del self[bp]

    if isinstance(where, int):
        bp = self._hilda.target.BreakpointCreateByAddress(where)
    elif isinstance(where, str):
        # Note that the name in BreakpointCreateByName is the name of the location,
        # not the name of the breakpoint.
        bp = self._hilda.target.BreakpointCreateByName(where)
    elif isinstance(where, tuple):
        _name, _module = where
        raise NotImplementedError()
    if not bp.IsValid():
        raise HildaException(f"Failed to create breakpoint at {where}")

    bp = HildaBreakpoint(self._hilda, bp, where, description=description)
    bp.callback = callback
    bp.condition = condition
    bp.guarded = guarded

    self._breakpoints[bp.id] = bp

    self._hilda.log_info(f"Breakpoint #{bp.id} has been set")
    return bp
```

#### add_monitor

```
add_monitor(where: WhereType, condition: Optional[str] = None, guarded: bool = False, override: bool = True, regs: Optional[dict[str, Union[str, Callable]]] = None, expr: Optional[dict[str, Union[str, Callable]]] = None, retval: Optional[Union[str, Callable]] = None, stop: bool = False, bt: bool = False, cmd: Optional[list[str]] = None, force_return: Optional[bool] = None, name: Optional[str] = None, description: Optional[str] = None) -> HildaBreakpoint
```

Monitor every time a given address is called.

Creates a breakpoint whose callback implements the requested features.

Parameters:

| Name           | Type                                        | Description                                                                                                                                                                                                                                                                                                                                                                           | Default    |
| -------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `where`        | `WhereType`                                 | See add() for details.                                                                                                                                                                                                                                                                                                                                                                | *required* |
| `condition`    | `Optional[str]`                             | See add() for details.                                                                                                                                                                                                                                                                                                                                                                | `None`     |
| `guarded`      | `bool`                                      | See add() for details.                                                                                                                                                                                                                                                                                                                                                                | `False`    |
| `override`     | `bool`                                      | See add() for details.                                                                                                                                                                                                                                                                                                                                                                | `True`     |
| `regs`         | `Optional[dict[str, Union[str, Callable]]]` | Print register values (using the provided format). E.g., regs={'x0': 'x'} prints x0 in HEX format The available formats are: 'x': hex 's': string 'cf': use CFCopyDescription() to get more informative description of the object 'po': use LLDB po command 'std::string': for std::string Callable: user defined function, will be called like format_function(hilda_client, value). | `None`     |
| `expr`         | `Optional[dict[str, Union[str, Callable]]]` | Print LLDB expression (using the provided format). E.g., expr={'$x0': 'x', '$arg1': 'x'} (to print the value of x0 and arg1). The format behaves like in regs above.                                                                                                                                                                                                                  | `None`     |
| `retval`       | `Optional[Union[str, Callable]]`            | Print the return value of the function (using the provided format). The format behaves like in regs above.                                                                                                                                                                                                                                                                            | `None`     |
| `stop`         | `bool`                                      | If True, stop whenever the breakpoint is hit (otherwise continue debugging).                                                                                                                                                                                                                                                                                                          | `False`    |
| `bt`           | `bool`                                      | Print backtrace.                                                                                                                                                                                                                                                                                                                                                                      | `False`    |
| `cmd`          | `Optional[list[str]]`                       | A list of LLDB commands to run when the breakpoint is hit.                                                                                                                                                                                                                                                                                                                            | `None`     |
| `force_return` | `Optional[bool]`                            | Return immediately from the function, returning the specified value.                                                                                                                                                                                                                                                                                                                  | `None`     |
| `name`         | `Optional[str]`                             | Use the provided name instead of the symbol name automatically extracted from the calling frame.                                                                                                                                                                                                                                                                                      | `None`     |
| `description`  | `Optional[str]`                             | Attach a brief description of the breakpoint.                                                                                                                                                                                                                                                                                                                                         | `None`     |

Returns:

| Type              | Description        |
| ----------------- | ------------------ |
| `HildaBreakpoint` | The new breakpoint |

Source code in `hilda/breakpoints.py`

```
def add_monitor(
    self,
    where: WhereType,
    condition: Optional[str] = None,
    guarded: bool = False,
    override: bool = True,
    regs: Optional[dict[str, Union[str, Callable]]] = None,
    expr: Optional[dict[str, Union[str, Callable]]] = None,
    retval: Optional[Union[str, Callable]] = None,
    stop: bool = False,
    bt: bool = False,
    cmd: Optional[list[str]] = None,
    force_return: Optional[bool] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> HildaBreakpoint:
    """
    Monitor every time a given address is called.

    Creates a breakpoint whose callback implements the requested features.

    :param where: See add() for details.
    :param condition: See add() for details.
    :param guarded: See add() for details.
    :param override: See add() for details.
    :param regs: Print register values (using the provided format).
        E.g., `regs={'x0': 'x'}` prints x0 in HEX format
        The available formats are:
            'x': hex
            's': string
            'cf': use CFCopyDescription() to get more informative description of the object
            'po': use LLDB po command
            'std::string': for std::string
            Callable: user defined function, will be called like `format_function(hilda_client, value)`.
    :param expr: Print LLDB expression (using the provided format).
        E.g., `expr={'$x0': 'x', '$arg1': 'x'}` (to print the value of x0 and arg1).
        The format behaves like in regs above.
    :param retval: Print the return value of the function (using the provided format).
        The format behaves like in regs above.
    :param stop: If True, stop whenever the breakpoint is hit (otherwise continue debugging).
    :param bt: Print backtrace.
    :param cmd: A list of LLDB commands to run when the breakpoint is hit.
    :param force_return: Return immediately from the function, returning the specified value.
    :param name: Use the provided name instead of the symbol name automatically extracted from the calling frame.
    :param description: Attach a brief description of the breakpoint.
    :return: The new breakpoint
    """

    if regs is None:
        regs = {}
    if expr is None:
        expr = {}
    if cmd is None:
        cmd = []

    def callback(hilda, frame: lldb.SBFrame, bp_loc: lldb.SBBreakpointLocation, *_) -> None:
        """
        Callback function called when a breakpoint is hit.

        :param hilda.hilda_client.HildaClient hilda: Hilda client to operate on
        :param frame: LLDB frame
        :param bp_loc: LLDB breakpoint location
        """
        nonlocal name
        bp = bp_loc.GetBreakpoint()
        symbol = hilda.symbol(hilda.frame.addr.GetLoadAddress(hilda.target))
        thread = hilda.thread
        printed_name = name if name is not None else str(symbol.lldb_address)

        def format_value(fmt: Union[str, Callable], value: Symbol) -> str:
            if callable(fmt):
                return fmt(hilda, value)
            formatters = {
                "x": lambda val: f"0x{int(val):x}",
                "s": lambda val: val.peek_str() if val else None,
                "cf": lambda val: val.cf_description,
                "po": lambda val: val.po(),
                "std::string": hilda._std_string,
            }
            if fmt in formatters:
                return formatters[fmt](value)
            else:
                return f"{value:x} (unsupported format)"

        log_message = f"🚨 #{bp.id} 0x{symbol:x} {printed_name} - Thread #{thread.idx}:{hex(thread.id)}"

        if regs != {}:
            log_message += "\nregs:"
            for reg_name, fmt in regs.items():
                value = hilda.symbol(frame.FindRegister(reg_name).unsigned)
                log_message += f"\n\t{reg_name} = {format_value(fmt, value)}"

        if expr != {}:
            log_message += "\nexpr:"
            for expr_name, fmt in expr.items():
                value = hilda.symbol(hilda.evaluate_expression(expr_name))
                log_message += f"\n\t{expr_name} = {format_value(fmt, value)}"

        if force_return is not None:
            hilda.force_return(force_return)
            log_message += f"\nforced return: {force_return}"

        if bt:
            # bugfix: for callstacks from xpc events
            hilda.finish()
            for frame in hilda.bt():
                log_message += f"\n\t{frame[0]} {frame[1]}"

        if retval is not None:
            # return from function
            hilda.finish()
            value = hilda.evaluate_expression("$arg1")
            log_message += f"\nreturned: {format_value(retval, value)}"

        hilda.log_info(log_message)

        for command in cmd:
            hilda.lldb_handle_command(command)

        if stop:
            hilda.log_info("Process remains stopped and focused on current thread")
        else:
            hilda.cont()

    return self.add(
        where, callback, condition=condition, guarded=guarded, override=override, description=description
    )
```

#### remove

```
remove(id_or_name_or_bp: Union[int, str, HildaBreakpoint], remove_guarded: bool = False) -> None
```

Remove a breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument).

Parameters:

| Name               | Type                               | Description                                                   | Default    |
| ------------------ | ---------------------------------- | ------------------------------------------------------------- | ---------- |
| `id_or_name_or_bp` | `Union[int, str, HildaBreakpoint]` | Breakpoint's ID or name (or the breakpoint itself)            | *required* |
| `remove_guarded`   | `bool`                             | Remove breakpoint even if the breakpoint is marked as guarded | `False`    |

Source code in `hilda/breakpoints.py`

```
def remove(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint], remove_guarded: bool = False) -> None:
    """
    Remove a breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument).

    :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
    :param remove_guarded: Remove breakpoint even if the breakpoint is marked as guarded
    """

    bp = self[id_or_name_or_bp]

    if bp.guarded and not remove_guarded:
        self._hilda.log_warning(f"Remove request for breakpoint {bp} is ignored")
        return

    # Removing a breakpoint without using this function would leak the breakpoint in self._breakpoints

    breakpoint_id = bp.id
    self._hilda.target.BreakpointDelete(breakpoint_id)
    self._hilda.log_debug(f"Breakpoint #{breakpoint_id} has been removed")
```

#### clear

```
clear(remove_guarded: bool = False) -> None
```

Remove all breakpoints (except for breakpoints marked as guarded, see remove_guarded argument).

Parameters:

| Name             | Type   | Description                               | Default |
| ---------------- | ------ | ----------------------------------------- | ------- |
| `remove_guarded` | `bool` | Also remove breakpoints marked as guarded | `False` |

Source code in `hilda/breakpoints.py`

```
def clear(self, remove_guarded: bool = False) -> None:
    """
    Remove all breakpoints (except for breakpoints marked as guarded, see remove_guarded argument).

    :param remove_guarded: Also remove breakpoints marked as guarded
    """
    breakpoints = list(self)
    for bp in breakpoints:
        if not remove_guarded and bp.guarded:
            continue

        self.remove(bp, remove_guarded)
```

#### show

```
show() -> None
```

Show existing breakpoints.

Source code in `hilda/breakpoints.py`

```
def show(self) -> None:
    """Show existing breakpoints."""
    if len(self) == 0:
        self._hilda.log_info("No breakpoints")
    for bp in self:
        self._hilda.log_info(bp)
```

#### items

```
items()
```

Get a breakpoint ID and breakpoint object tuple for every breakpoint

Source code in `hilda/breakpoints.py`

```
def items(self):
    """
    Get a breakpoint ID and breakpoint object tuple for every breakpoint
    """
    return ((bp.id, bp) for bp in self)
```

#### keys

```
keys() -> Generator[int, Any, None]
```

Get the breakpoint ID for every breakpoint

Source code in `hilda/breakpoints.py`

```
def keys(self) -> Generator[int, Any, None]:
    """
    Get the breakpoint ID for every breakpoint
    """
    return (bp.id for bp in self)
```

#### values

```
values() -> Generator[HildaBreakpoint, Any, None]
```

Get the breakpoint object for every breakpoint

Source code in `hilda/breakpoints.py`

```
def values(self) -> Generator[HildaBreakpoint, Any, None]:
    """
    Get the breakpoint object for every breakpoint
    """
    return (bp for bp in self)
```

## Watchpoints

## hilda.watchpoints

### HildaWatchpoint

Hilda's class representing an LLDB watchpoint, with some optional additional properties

Source code in `hilda/watchpoints.py`

```
class HildaWatchpoint:
    """
    Hilda's class representing an LLDB watchpoint, with some optional additional properties
    """

    def __init__(self, hilda, lldb_watchpoint: lldb.SBWatchpoint, where: Optional[int] = None) -> None:
        """
        Initialize a watchpoint.

        :param hilda.hilda_client.HildaClient hilda: Hilda client
        """
        self._hilda = hilda
        self._where = where
        self._callback = None

        # Actual watchpoint from LLDB API
        self.lldb_watchpoint = lldb_watchpoint

    @property
    def where(self) -> Optional[int]:
        """
        A value identifying where the watchpoint was set (when it was created).

        It could be either an address (int) or a Hilda symbol object (Symbol, that inherits from int).
        Note that self.address is similar, but self.where is where the watchpoint was set when it was
        created (using Hilda API), and self.address is the actual address. They should have the same
        value, although self.where may be a Hilda Symbol.
        """
        return self._where

    @property
    def id(self) -> int:
        """A number identifying the watchpoint."""
        return self.lldb_watchpoint.GetID()

    @property
    def callback(self) -> Optional[Callable]:
        """
        A callback that will be executed when the watchpoint is hit.

        Note that unless the callback explicitly continues (by calling `cont()`), the program will not continue.
        The callback will be invoked as callback(hilda, *args), where hilda is the 'HildaClient'.
        """
        return self._callback

    @callback.setter
    def callback(self, callback: Optional[Callable]) -> None:
        self._callback = callback
        # TODO: Figure out a way to add set this callback programmatically
        self._hilda.lldb_handle_command(
            f"watchpoint command add -F lldb.hilda_client.watchpoints._dispatch_watchpoint_callback {self.id}"
        )

    @property
    def condition(self) -> Optional[str]:
        """
        An LLDB expression to make this a conditional watchpoint.
        """
        return self.lldb_watchpoint.GetCondition()

    @condition.setter
    def condition(self, condition: Optional[str]) -> None:
        self.lldb_watchpoint.SetCondition(condition)

    @property
    def address(self) -> int:
        """
        Get the address this watchpoint watches (also see self.where).
        """
        return self.lldb_watchpoint.GetWatchAddress()

    @property
    def size(self) -> int:
        """
        Get the size this watchpoint watches.
        """
        return self.lldb_watchpoint.GetWatchSize()

    @property
    def enabled(self) -> bool:
        """
        Configures whether this watchpoint is enabled or not.
        """
        return self.lldb_watchpoint.IsEnabled()

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.lldb_watchpoint.SetEnabled(value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} LLDB:{self.lldb_watchpoint} CALLBACK:{self.callback}>"

    def __str__(self) -> str:
        emoji = "🚨" if self.enabled else "🔕"
        enabled_str = "enabled" if self.enabled else "disabled"
        result = f"{emoji} Watchpoint #{self.id} ({enabled_str})\n"

        if self.where is not None:
            result += f"\tWhere: {self.where}\n"

        return result.strip("\n")

    def remove(self) -> None:
        """
        Remove the watchpoint.
        """
        self._hilda.watchpoints.remove(self)
```

#### where

```
where: Optional[int]
```

A value identifying where the watchpoint was set (when it was created).

It could be either an address (int) or a Hilda symbol object (Symbol, that inherits from int). Note that self.address is similar, but self.where is where the watchpoint was set when it was created (using Hilda API), and self.address is the actual address. They should have the same value, although self.where may be a Hilda Symbol.

#### id

```
id: int
```

A number identifying the watchpoint.

#### callback

```
callback: Optional[Callable]
```

A callback that will be executed when the watchpoint is hit.

Note that unless the callback explicitly continues (by calling `cont()`), the program will not continue. The callback will be invoked as callback(hilda, \*args), where hilda is the 'HildaClient'.

#### condition

```
condition: Optional[str]
```

An LLDB expression to make this a conditional watchpoint.

#### address

```
address: int
```

Get the address this watchpoint watches (also see self.where).

#### size

```
size: int
```

Get the size this watchpoint watches.

#### enabled

```
enabled: bool
```

Configures whether this watchpoint is enabled or not.

#### remove

```
remove() -> None
```

Remove the watchpoint.

Source code in `hilda/watchpoints.py`

```
def remove(self) -> None:
    """
    Remove the watchpoint.
    """
    self._hilda.watchpoints.remove(self)
```

### WatchpointList

Manager for `HildaWatchpoint` objects, each one wrapping another native LLDB watchpoint.

Source code in `hilda/watchpoints.py`

```
class WatchpointList:
    """
    Manager for `HildaWatchpoint` objects, each one wrapping another native LLDB watchpoint.
    """

    def __init__(self, hilda) -> None:
        """
        Initialize a watchpoint list.

        :param hilda.hilda_client.HildaClient hilda: Hilda client
        """
        self._hilda = hilda
        self._watchpoints = {}

    def __contains__(self, id_or_wp: Union[int, HildaWatchpoint]) -> bool:
        return self.get(id_or_wp) is not None

    def __iter__(self) -> Generator[HildaWatchpoint, None, None]:
        for wp in self._hilda.target.watchpoint_iter():
            yield self[wp.GetID()]

    def __len__(self) -> int:
        return self._hilda.target.GetNumWatchpoints()

    def __getitem__(self, id_or_wp: Union[int, HildaWatchpoint]) -> HildaWatchpoint:
        """
        Get a watchpoint by ID (or the watchpoint itself, though it usually makes little sense)

        :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
        """
        wp = self.get(id_or_wp)
        if wp is None:
            raise KeyError(id_or_wp)

        return wp

    def __delitem__(self, id_or_wp: Union[int, HildaWatchpoint]):
        """
        Remove a watchpoint.

        :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
        """
        self.remove(id_or_wp)

    def __repr__(self) -> str:
        return repr(dict(self.items()))

    def __str__(self) -> str:
        return repr(self)

    def get(self, id_or_wp: Union[int, HildaWatchpoint]) -> Optional[HildaWatchpoint]:
        """
        Get a watchpoint by ID or the watchpoint itself.

        :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
        :return: `HildaWatchpoint` if one exists, or `None` otherwise
        """

        if isinstance(id_or_wp, int):
            wp = self._hilda.target.FindWatchpointByID(id_or_wp)
        elif isinstance(id_or_wp, HildaWatchpoint):
            wp = id_or_wp.lldb_watchpoint
        else:
            raise KeyError(f'Watchpoint "{id_or_wp}" could not be found')

        if not wp.IsValid():
            return None

        wp_id = wp.GetID()
        if wp_id not in self._watchpoints:
            self._hilda.log_debug(f"Found a watchpoint added outside of the Hilda API {wp}")
            self._watchpoints[wp_id] = HildaWatchpoint(self._hilda, wp)

        return self._watchpoints[wp_id]

    def add(
        self,
        where: int,
        size: int = 8,
        read: bool = True,
        write: bool = True,
        callback: Optional[Callable] = None,
        condition: Optional[str] = None,
    ) -> HildaWatchpoint:
        """
        Add a watchpoint.

        :param where: The address of the watchpoint.
        :param size: The size of the watchpoint (the address span to watch).
        :param read: The watchpoint should monitor reads from memory in the specified address (and size).
        :param write: The watchpoint should monitor writes to memory in the specified address (and size).
        :param callback: A callback that will be executed when the watchpoint is hit.
            Note that unless the callback explicitly continues (by calling cont()), the program will not continue.
            The callback will be invoked as callback(hilda, *args), where hilda is the 'HildaClient'.
        :param condition: An LLDB expression to make this a conditional watchpoint.
        :return: The new watchpoint
        """

        error = lldb.SBError()
        wp = self._hilda.target.WatchAddress(where, size, read, write, error)
        if not wp.IsValid():
            raise HildaException(f"Failed to create watchpoint at {where} ({error})")

        wp = HildaWatchpoint(self._hilda, wp, where)
        wp.callback = callback
        wp.condition = condition

        self._watchpoints[wp.id] = wp

        self._hilda.log_info(f"Watchpoint #{wp.id} has been set")
        return wp

    def remove(self, id_or_wp: Union[int, HildaWatchpoint]) -> None:
        """
        Remove a watchpoint.

        :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
        """
        wp = self[id_or_wp]
        watchpoint_id = wp.id
        self._hilda.target.DeleteWatchpoint(watchpoint_id)
        self._hilda.log_debug(f"Watchpoint #{watchpoint_id} has been removed")

    def clear(self) -> None:
        """
        Remove all watchpoints
        """
        for wp in list(self):
            self.remove(wp)

    def show(self) -> None:
        """Show existing watchpoints."""
        if len(self) == 0:
            self._hilda.log_info("No watchpoints")
        for wp in self:
            self._hilda.log_info(wp)

    def items(self) -> Generator[tuple[int, HildaWatchpoint], None, None]:
        """
        Get a watchpoint ID and watchpoint object tuple for every watchpoint.
        """
        return ((wp.id, wp) for wp in self)

    def keys(self) -> Generator[int, None, None]:
        """
        Get the watchpoint ID for every watchpoint.
        """
        return (wp.id for wp in self)

    def values(self) -> Generator[HildaWatchpoint, None, None]:
        """
        Get the watchpoint object for every watchpoint.
        """
        return (wp for wp in self)

    def _dispatch_watchpoint_callback(self, frame, wp, internal_dict) -> None:
        """
        Route the watchpoint callback the specific watchpoint callback.
        """
        watchpoint_id = wp.GetID()
        self._hilda._bp_frame = frame
        try:
            callback = self[watchpoint_id].callback
            if callback is not None:
                callback(self._hilda, frame, None, self[watchpoint_id])
        finally:
            self._hilda._bp_frame = None
```

#### get

```
get(id_or_wp: Union[int, HildaWatchpoint]) -> Optional[HildaWatchpoint]
```

Get a watchpoint by ID or the watchpoint itself.

Parameters:

| Name       | Type                          | Description                                | Default    |
| ---------- | ----------------------------- | ------------------------------------------ | ---------- |
| `id_or_wp` | `Union[int, HildaWatchpoint]` | Watchpoint's ID (or the watchpoint itself) | *required* |

Returns:

| Type                        | Description                                      |
| --------------------------- | ------------------------------------------------ |
| `Optional[HildaWatchpoint]` | HildaWatchpoint if one exists, or None otherwise |

Source code in `hilda/watchpoints.py`

```
def get(self, id_or_wp: Union[int, HildaWatchpoint]) -> Optional[HildaWatchpoint]:
    """
    Get a watchpoint by ID or the watchpoint itself.

    :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
    :return: `HildaWatchpoint` if one exists, or `None` otherwise
    """

    if isinstance(id_or_wp, int):
        wp = self._hilda.target.FindWatchpointByID(id_or_wp)
    elif isinstance(id_or_wp, HildaWatchpoint):
        wp = id_or_wp.lldb_watchpoint
    else:
        raise KeyError(f'Watchpoint "{id_or_wp}" could not be found')

    if not wp.IsValid():
        return None

    wp_id = wp.GetID()
    if wp_id not in self._watchpoints:
        self._hilda.log_debug(f"Found a watchpoint added outside of the Hilda API {wp}")
        self._watchpoints[wp_id] = HildaWatchpoint(self._hilda, wp)

    return self._watchpoints[wp_id]
```

#### add

```
add(where: int, size: int = 8, read: bool = True, write: bool = True, callback: Optional[Callable] = None, condition: Optional[str] = None) -> HildaWatchpoint
```

Add a watchpoint.

Parameters:

| Name        | Type                 | Description                                                                                                                                                                                                                                                    | Default    |
| ----------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `where`     | `int`                | The address of the watchpoint.                                                                                                                                                                                                                                 | *required* |
| `size`      | `int`                | The size of the watchpoint (the address span to watch).                                                                                                                                                                                                        | `8`        |
| `read`      | `bool`               | The watchpoint should monitor reads from memory in the specified address (and size).                                                                                                                                                                           | `True`     |
| `write`     | `bool`               | The watchpoint should monitor writes to memory in the specified address (and size).                                                                                                                                                                            | `True`     |
| `callback`  | `Optional[Callable]` | A callback that will be executed when the watchpoint is hit. Note that unless the callback explicitly continues (by calling cont()), the program will not continue. The callback will be invoked as callback(hilda, \*args), where hilda is the 'HildaClient'. | `None`     |
| `condition` | `Optional[str]`      | An LLDB expression to make this a conditional watchpoint.                                                                                                                                                                                                      | `None`     |

Returns:

| Type              | Description        |
| ----------------- | ------------------ |
| `HildaWatchpoint` | The new watchpoint |

Source code in `hilda/watchpoints.py`

```
def add(
    self,
    where: int,
    size: int = 8,
    read: bool = True,
    write: bool = True,
    callback: Optional[Callable] = None,
    condition: Optional[str] = None,
) -> HildaWatchpoint:
    """
    Add a watchpoint.

    :param where: The address of the watchpoint.
    :param size: The size of the watchpoint (the address span to watch).
    :param read: The watchpoint should monitor reads from memory in the specified address (and size).
    :param write: The watchpoint should monitor writes to memory in the specified address (and size).
    :param callback: A callback that will be executed when the watchpoint is hit.
        Note that unless the callback explicitly continues (by calling cont()), the program will not continue.
        The callback will be invoked as callback(hilda, *args), where hilda is the 'HildaClient'.
    :param condition: An LLDB expression to make this a conditional watchpoint.
    :return: The new watchpoint
    """

    error = lldb.SBError()
    wp = self._hilda.target.WatchAddress(where, size, read, write, error)
    if not wp.IsValid():
        raise HildaException(f"Failed to create watchpoint at {where} ({error})")

    wp = HildaWatchpoint(self._hilda, wp, where)
    wp.callback = callback
    wp.condition = condition

    self._watchpoints[wp.id] = wp

    self._hilda.log_info(f"Watchpoint #{wp.id} has been set")
    return wp
```

#### remove

```
remove(id_or_wp: Union[int, HildaWatchpoint]) -> None
```

Remove a watchpoint.

Parameters:

| Name       | Type                          | Description                                | Default    |
| ---------- | ----------------------------- | ------------------------------------------ | ---------- |
| `id_or_wp` | `Union[int, HildaWatchpoint]` | Watchpoint's ID (or the watchpoint itself) | *required* |

Source code in `hilda/watchpoints.py`

```
def remove(self, id_or_wp: Union[int, HildaWatchpoint]) -> None:
    """
    Remove a watchpoint.

    :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
    """
    wp = self[id_or_wp]
    watchpoint_id = wp.id
    self._hilda.target.DeleteWatchpoint(watchpoint_id)
    self._hilda.log_debug(f"Watchpoint #{watchpoint_id} has been removed")
```

#### clear

```
clear() -> None
```

Remove all watchpoints

Source code in `hilda/watchpoints.py`

```
def clear(self) -> None:
    """
    Remove all watchpoints
    """
    for wp in list(self):
        self.remove(wp)
```

#### show

```
show() -> None
```

Show existing watchpoints.

Source code in `hilda/watchpoints.py`

```
def show(self) -> None:
    """Show existing watchpoints."""
    if len(self) == 0:
        self._hilda.log_info("No watchpoints")
    for wp in self:
        self._hilda.log_info(wp)
```

#### items

```
items() -> Generator[tuple[int, HildaWatchpoint], None, None]
```

Get a watchpoint ID and watchpoint object tuple for every watchpoint.

Source code in `hilda/watchpoints.py`

```
def items(self) -> Generator[tuple[int, HildaWatchpoint], None, None]:
    """
    Get a watchpoint ID and watchpoint object tuple for every watchpoint.
    """
    return ((wp.id, wp) for wp in self)
```

#### keys

```
keys() -> Generator[int, None, None]
```

Get the watchpoint ID for every watchpoint.

Source code in `hilda/watchpoints.py`

```
def keys(self) -> Generator[int, None, None]:
    """
    Get the watchpoint ID for every watchpoint.
    """
    return (wp.id for wp in self)
```

#### values

```
values() -> Generator[HildaWatchpoint, None, None]
```

Get the watchpoint object for every watchpoint.

Source code in `hilda/watchpoints.py`

```
def values(self) -> Generator[HildaWatchpoint, None, None]:
    """
    Get the watchpoint object for every watchpoint.
    """
    return (wp for wp in self)
```

## Registers

## hilda.registers

### Registers

Wrapper for more convenient access to modify current frame's registers

Source code in `hilda/registers.py`

```
class Registers:
    """
    Wrapper for more convenient access to modify current frame's registers
    """

    def __init__(self, client):
        self.__dict__["_client"] = client

    def __getattr__(self, item):
        return self._client.get_register(item)

    def __getitem__(self, item):
        return self._client.get_register(item)

    def __setattr__(self, key, value):
        return self._client.set_register(key, value)

    def __setitem__(self, key, value):
        return self._client.set_register(key, value)

    def __dir__(self):
        result = []
        for group in self._client.frame.register.regs:
            for register in group:
                result.append(register.name)
        return result

    def show(self):
        """Show current frame's registers"""
        print(self._client.frame.register.regs)
```

#### show

```
show()
```

Show current frame's registers

Source code in `hilda/registers.py`

```
def show(self):
    """Show current frame's registers"""
    print(self._client.frame.register.regs)
```
