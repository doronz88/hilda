import shlex

from IPython.core.magic import Magics, line_magic, magics_class, needs_local_scope


@magics_class
class HIMagics(Magics):

    @line_magic
    @needs_local_scope
    def objc(self, line, local_ns=None):
        """Load an Objective-C class by name into the IPython session."""
        p = local_ns.get('p')
        class_name = line.strip()
        if not class_name:
            p.log_error("Error: className is required.")
            return
        try:
            local_ns[class_name] = p.objc_get_class(class_name)
            p.log_info(f'{class_name} class loaded successfully')
        except Exception as e:
            p.log_error(f'Error loading class {class_name}: {str(e)}')

    @line_magic
    @needs_local_scope
    def fbp(self, line, local_ns=None):
        """Set a file breakpoint in the debugger."""
        p = local_ns.get('p')
        try:
            module_name, address = shlex.split(line.strip())
            address = int(address, 16)
            p.file_symbol(address, module_name).bp()
        except ValueError as ve:
            p.log_error(f"Error parsing arguments: {str(ve)}")
        except Exception as e:
            p.log_error(f"Error setting breakpoint: {str(e)}")


def load_ipython_extension(ipython):
    ipython.register_magics(HIMagics)
