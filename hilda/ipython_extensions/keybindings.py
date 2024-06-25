from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import EmacsInsertMode, HasFocus, HasSelection, ViInsertMode
from prompt_toolkit.keys import Keys


def load_ipython_extension(ipython):
    def register_keybindings():
        hilda = ipython.user_ns['p']
        keys_mapping = {Keys.F1: hilda.ui_manager.show,
                        Keys.F7: hilda.step_into,
                        Keys.F8: hilda.step_over,
                        Keys.F9: lambda _: (hilda.log_info('Sending continue'), hilda.cont()),
                        Keys.F10: lambda _: (hilda.log_info('Sending stop'), hilda.stop())}

        insert_mode = ViInsertMode() | EmacsInsertMode()
        registry = ipython.pt_app.key_bindings

        for key, callback in keys_mapping.items():
            registry.add_binding(key, filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode))(
                callback)

    register_keybindings()
    ipython.events.register('shell_initialized', register_keybindings)
