from typing import Callable, Generator, Optional, Union

from hilda.lldb_importer import lldb


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
        """ A number identifying the watchpoint. """
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
        self._hilda.lldb_handle_command(f'watchpoint command add -F '
                                        f'lldb.hilda_client.watchpoints._dispatch_watchpoint_callback {self.id}')

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
        return f'<{self.__class__.__name__} LLDB:{self.lldb_watchpoint} CALLBACK:{self.callback}>'

    def __str__(self) -> str:
        emoji = '🚨' if self.enabled else '🔕'
        enabled_str = 'enabled' if self.enabled else 'disabled'
        result = f'{emoji} Watchpoint #{self.id} ({enabled_str})\n'

        if self.where is not None:
            result += f'\tWhere: {self.where}\n'

        return result.strip('\n')

    def remove(self) -> None:
        """
        Remove the watchpoint.
        """
        self._hilda.watchpoints.remove(self)


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
            self._hilda.log_debug(f'Found a watchpoint added outside of the Hilda API {wp}')
            self._watchpoints[wp_id] = HildaWatchpoint(self._hilda, wp)

        return self._watchpoints[wp_id]

    def add(self, where: int, size: int = 8, read: bool = True, write: bool = True,
            callback: Optional[Callable] = None, condition: str = None) -> HildaWatchpoint:
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
            raise Exception(f'Failed to create watchpoint at {where} ({error})')

        wp = HildaWatchpoint(self._hilda, wp, where)
        wp.callback = callback
        wp.condition = condition

        self._watchpoints[wp.id] = wp

        self._hilda.log_info(f'Watchpoint #{wp.id} has been set')
        return wp

    def remove(self, id_or_wp: Union[int, HildaWatchpoint]) -> None:
        """
        Remove a watchpoint.

        :param id_or_wp: Watchpoint's ID (or the watchpoint itself)
        """
        wp = self[id_or_wp]
        watchpoint_id = wp.id
        self._hilda.target.DeleteWatchpoint(watchpoint_id)
        self._hilda.log_debug(f'Watchpoint #{watchpoint_id} has been removed')

    def clear(self) -> None:
        """
        Remove all watchpoints
        """
        for wp in list(self):
            self.remove(wp)

    def show(self) -> None:
        """ Show existing watchpoints. """
        if len(self) == 0:
            self._hilda.log_info('No watchpoints')
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
