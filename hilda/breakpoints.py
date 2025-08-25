from typing import Any, Callable, Generator, Optional, Union

import inquirer3

from hilda.lldb_importer import lldb
from hilda.symbol import Symbol

"""
A value identifying where the breakpoint was set (when it was created)

It could be either an address (int), a symbol name (string), a symbol name in a
specific module (Tuple[str, str], where the first item is the symbol name and the
second is the module name) or a Hilda symbol object (Symbol, that inherits from int).
"""
WhereType = Union[int, str, tuple[str, str], Symbol]


class HildaBreakpoint:
    """
    Hilda's class representing an LLDB breakpoint, with some optional additional properties
    """

    def __init__(self, hilda, lldb_breakpoint: lldb.SBBreakpoint,
                 where: Optional[WhereType] = None, description: Optional[str] = None) -> None:
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
        """ Where the breakpoint was set (when it was created). """
        return self._where

    @property
    def id(self) -> int:
        """ A number identifying the breakpoint. """
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
                'lldb.hilda_client.breakpoints._dispatch_breakpoint_callback')

    @property
    def condition(self) -> Optional[str]:
        """ An LLDB expression to make this a conditional breakpoint. """
        return self.lldb_breakpoint.GetCondition()

    @condition.setter
    def condition(self, condition: Optional[str]) -> None:
        self.lldb_breakpoint.SetCondition(condition)

    @property
    def locations(self) -> list[lldb.SBBreakpointLocation]:
        """ LLDB locations array the breakpoint relates to. """
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
            raise ValueError(f'Breakpoint {self.id} has multiple names {names}')

        name, = names
        return name

    @name.setter
    def name(self, name: Optional[str]) -> None:
        self.names = {name}

    @property
    def names(self) -> set[str]:
        """ The set of names of the breakpoint. """
        name_list = lldb.SBStringList()
        self.lldb_breakpoint.GetNames(name_list)
        return set(name_list.GetStringAtIndex(i) for i in range(name_list.GetSize()))

    @names.setter
    def names(self, names: Union[set[str], list[str]]) -> None:
        new_names = set(names)
        if len(new_names) != len(names):
            raise ValueError(f'Duplicate names in {names}')

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
        enabled_repr = 'ENABLED' if self.enabled else 'DISABLED'
        guarded_repr = 'GUARDED' if self.guarded else 'NOT-GUARDED'
        return (f'<{self.__class__.__name__} LLDB:{self.lldb_breakpoint} {enabled_repr} {guarded_repr} '
                f'CALLBACK:{self.callback}>')

    def __str__(self) -> str:
        emoji = '🚨' if self.enabled else '🔕'
        enabled_str = 'enabled' if self.enabled else 'disabled'
        guarded_str = 'guarded' if self.guarded else 'not-guarded'

        result = f'{emoji} Breakpoint #{self.id} ({enabled_str}, {guarded_str})\n'

        if self.description is not None:
            result += f'\tDescription: {self.description}\n'

        if self.where is not None:
            result += f'\tWhere: {self.where}\n'

        # A single breakpoint may be related to several locations (addresses)
        locations = self.locations
        if len(locations) == 0:
            result += '\tNo locations\n'
        for location in self.locations:
            result += f'\tLocation {location}\n'

        return result.strip('\n')

    def remove(self, remove_guarded: bool = False) -> None:
        """
        Remove the breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument)

        :param bool remove_guarded: Remove the breakpoint even if the breakpoint is guarded
        """
        self._hilda.breakpoints.remove(self, remove_guarded)


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
            self._hilda.log_debug(f'Found a breakpoint added outside of the Hilda API {bp}')
            self._breakpoints[bp_id] = HildaBreakpoint(self._hilda, bp)

        return self._breakpoints[bp_id]

    def add(self, where: WhereType, callback: Optional[Callable] = None, condition: str = None, guarded: bool = False,
            override: bool = True, description: Optional[str] = None) -> HildaBreakpoint:
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
        if where in (bp.where for bp in self):
            if override or inquirer3.confirm('A breakpoint already exist in given location. '
                                             'Would you like to delete the previous one?', True):
                for bp in list(bp for bp in self if where == bp.where):
                    del self[bp]

        if isinstance(where, int):
            bp = self._hilda.target.BreakpointCreateByAddress(where)
        elif isinstance(where, str):
            # Note that the name in BreakpointCreateByName is the name of the location,
            # not the name of the breakpoint.
            bp = self._hilda.target.BreakpointCreateByName(where)
        elif isinstance(where, tuple):
            name, module = where
            raise NotImplementedError()
        if not bp.IsValid():
            raise Exception(f'Failed to create breakpoint at {where}')

        bp = HildaBreakpoint(self._hilda, bp, where, description=description)
        bp.callback = callback
        bp.condition = condition
        bp.guarded = guarded

        self._breakpoints[bp.id] = bp

        self._hilda.log_info(f'Breakpoint #{bp.id} has been set')
        return bp

    def add_monitor(self, where: WhereType,
                    condition: str = None,
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
                    'x': lambda val: f'0x{int(val):x}',
                    's': lambda val: val.peek_str() if val else None,
                    'cf': lambda val: val.cf_description,
                    'po': lambda val: val.po(),
                    'std::string': hilda._std_string
                }
                if fmt in formatters:
                    return formatters[fmt](value)
                else:
                    return f'{value:x} (unsupported format)'

            log_message = f'🚨 #{bp.id} 0x{symbol:x} {printed_name} - Thread #{thread.idx}:{hex(thread.id)}'

            if regs != {}:
                log_message += '\nregs:'
                for name, fmt in regs.items():
                    value = hilda.symbol(frame.FindRegister(name).unsigned)
                    log_message += f'\n\t{name} = {format_value(fmt, value)}'

            if expr != {}:
                log_message += '\nexpr:'
                for name, fmt in expr.items():
                    value = hilda.symbol(hilda.evaluate_expression(name))
                    log_message += f'\n\t{name} = {format_value(fmt, value)}'

            if force_return is not None:
                hilda.force_return(force_return)
                log_message += f'\nforced return: {force_return}'

            if bt:
                # bugfix: for callstacks from xpc events
                hilda.finish()
                for frame in hilda.bt():
                    log_message += f'\n\t{frame[0]} {frame[1]}'

            if retval is not None:
                # return from function
                hilda.finish()
                value = hilda.evaluate_expression('$arg1')
                log_message += f'\nreturned: {format_value(retval, value)}'

            hilda.log_info(log_message)

            for command in cmd:
                hilda.lldb_handle_command(command)

            if stop:
                hilda.log_info('Process remains stopped and focused on current thread')
            else:
                hilda.cont()

        return self.add(where, callback, condition=condition, guarded=guarded, override=override,
                        description=description)

    def remove(self, id_or_name_or_bp: Union[int, str, HildaBreakpoint], remove_guarded: bool = False) -> None:
        """
        Remove a breakpoint (unless the breakpoint is marked as guarded, see remove_guarded argument).

        :param id_or_name_or_bp: Breakpoint's ID or name (or the breakpoint itself)
        :param remove_guarded: Remove breakpoint even if the breakpoint is marked as guarded
        """

        bp = self[id_or_name_or_bp]

        if bp.guarded and not remove_guarded:
            self._hilda.log_warning(f'Remove request for breakpoint {bp} is ignored')
            return

        # Removing a breakpoint without using this function would leak the breakpoint in self._breakpoints

        breakpoint_id = bp.id
        self._hilda.target.BreakpointDelete(breakpoint_id)
        self._hilda.log_debug(f'Breakpoint #{breakpoint_id} has been removed')

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
        """ Show existing breakpoints. """
        if len(self) == 0:
            self._hilda.log_info('No breakpoints')
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
