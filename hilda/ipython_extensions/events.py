import ast
import builtins

import lldb

from hilda.exceptions import SymbolAbsentError
from hilda.symbols_jar import SymbolsJar


class HIEvents:
    def __init__(self, ip):
        self.shell = ip
        self.hilda_client = self.shell.user_ns['p']

    def pre_run_cell(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInfo object
        """
        if info.raw_cell[0] in ['!', '%'] or info.raw_cell.endswith('?'):
            return
        #
        for node in ast.walk(ast.parse(info.raw_cell)):
            if not isinstance(node, ast.Name):
                # we are only interested in names
                continue

            if node.id in locals() or node.id in globals() or node.id in dir(builtins):
                # That are undefined
                continue

            if not hasattr(SymbolsJar, node.id):
                # ignore SymbolsJar properties
                try:
                    symbol = getattr(self.hilda_client.symbols, node.id)
                except SymbolAbsentError:
                    pass
                else:
                    self.hilda_client._add_global(
                        node.id,
                        symbol if symbol.type_ != lldb.eSymbolTypeObjCMetaClass else self.hilda_client.objc_get_class(
                            node.id)
                    )


def load_ipython_extension(ip):
    hie = HIEvents(ip)
    ip.events.register('pre_run_cell', hie.pre_run_cell)
