from hilda.breakpoints import WhereType
from hilda.lldb_importer import lldb

p = lldb.hilda_client


def breakpoint(where: WhereType, enable: bool = False):
    """
    A decorator to define a breakpoint, e.g.,

    ```
    @breakpoint('symbol_name')
    def my_breakpoint(hilda, *args):
        print('Hit!')
        hilda.cont()

    my_breakpoint.enabled = True
    ```
    """
    def decorator(callback):
        bp = p.breakpoints.add(where, callback=callback)
        bp.enabled = enable
        return bp

    return decorator


def watchpoint(where: int, enable: bool = False):
    """
    A decorator to define a watchpoint, e.g.,

    ```
    @watchpoint(0x11223344)
    def my_watchpoint(hilda, *args):
        print('Hit!')
        hilda.cont()

    my_watchpoint.enabled = True
    ```
    """
    def decorator(callback):
        wp = p.watchpoints.add(where, callback=callback)
        wp.enabled = enable
        return wp

    return decorator
