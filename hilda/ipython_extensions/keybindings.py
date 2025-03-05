from dataclasses import dataclass
from typing import Callable

from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import EmacsInsertMode, HasFocus, HasSelection, ViInsertMode
from prompt_toolkit.keys import Keys


@dataclass
class Keybinding:
    key: str
    description: str
    callback: Callable


def get_keybindings(hilda_client) -> list[Keybinding]:
    """
    Get list of keybindings

    :param hilda.hilda_client.HildaClient hilda_client: Hilda client to bind the keys to operations
    """
    return [
        Keybinding(key=Keys.F1, description='Show this help', callback=hilda_client.show_help),
        Keybinding(key=Keys.F2, description='Show process state UI', callback=hilda_client.ui_manager.show),
        Keybinding(key=Keys.F3, description='Toggle enabling of stdout & stderr',
                   callback=hilda_client.toggle_enable_stdout_stderr),
        Keybinding(key=Keys.F7, description='Step Into', callback=hilda_client.step_into),
        Keybinding(key=Keys.F8, description='Step Over', callback=hilda_client.step_over),
        Keybinding(key=Keys.F9, description='Continue',
                   callback=lambda _: (hilda_client.log_info('Sending continue'), hilda_client.cont())),
        Keybinding(key=Keys.F10, description='Stop',
                   callback=lambda _: (hilda_client.log_info('Sending stop'), hilda_client.stop())),
    ]


def load_ipython_extension(ipython):
    def register_keybindings():
        hilda_client = ipython.user_ns['p']
        insert_mode = ViInsertMode() | EmacsInsertMode()
        registry = ipython.pt_app.key_bindings

        for keybind in get_keybindings(hilda_client):
            registry.add_binding(
                keybind.key, filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode))(keybind.callback)

    register_keybindings()
    ipython.events.register('shell_initialized', register_keybindings)
