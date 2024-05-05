from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import EmacsInsertMode, HasFocus, HasSelection, ViInsertMode
from prompt_toolkit.keys import Keys


def load_ipython_extension(ipython):
    def register_keybindings():
        hilda = ipython.user_ns.get('p')
        if not hilda:
            print("Hilda instance not found in IPython namespace.")
            return

        insert_mode = ViInsertMode() | EmacsInsertMode()

        if hasattr(ipython, 'pt_app'):
            registry = ipython.pt_app.key_bindings

            registry.add_binding(Keys.F7, filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode))(
                hilda.step_into)
            registry.add_binding(Keys.F8, filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode))(
                hilda.step_over)
            registry.add_binding(Keys.F9, filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode))(
                hilda.cont)
            registry.add_binding(Keys.F10, filter=(HasFocus(DEFAULT_BUFFER) & ~HasSelection() & insert_mode))(
                hilda.stop)

    register_keybindings()
    ipython.events.register('shell_initialized', register_keybindings)
