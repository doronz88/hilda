import json
from collections import OrderedDict
from pathlib import Path

from hilda.ui.views import BackTraceView, DisassemblyView, RegistersView, StackView


class DotDict(OrderedDict):
    """ Extends `OrderedDict` to access items using dot """
    __slots__ = ["__recursion_lock__"]

    def __getattr__(self, name):
        try:
            if name in self.__slots__:
                return object.__getattribute__(self, name)
            else:
                return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        try:
            if name in self.__slots__:
                return object.__setattr__(self, name, value)
            else:
                self[name] = value
        except KeyError:
            raise AttributeError(name)


class ColorScheme(DotDict):
    def __init__(self, scheme: Path):
        with scheme.open('r') as f:
            data = json.load(f)
        super().__init__(data)


class ViewsManager(DotDict):
    pass


class UiManager:
    """
    Manages Hilda's UI.

    - New views can be added to `ViewManager` (Must be inherent `Views`)
    - Colors can be changed from terminal (Setting `ui_manager.color.title = 'green'` or be modifying `colors.json`)
    - Views can be disabled from terminal (Setting `ui_manager.color.title=False`)
    """

    def __init__(self, hilda_client, scheme_file=Path(__file__).parent / 'colors.json',
                 active: bool = True):
        """
        :param hilda_client: hilda.hilda_client.HildaClient
        :param scheme_file: pathlib.Path
        :param active: bool
        """
        self.colors = ColorScheme(scheme_file)
        self.views = ViewsManager({
            'registers': RegistersView(hilda_client, self.colors),
            'disassembly': DisassemblyView(hilda_client, self.colors),
            'stack': StackView(hilda_client, self.colors),
            'backtrace': BackTraceView(hilda_client, self.colors)
        })
        self.active = active

    def show(self, *args) -> None:
        fmt_parts = []

        for view in self.views.values():
            if view.active is False:
                continue
            fmt_parts.append(str(view))
        print('\n'.join(fmt_parts))
