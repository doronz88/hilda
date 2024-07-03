import ast
import builtins

from IPython.terminal.interactiveshell import TerminalInteractiveShell

from hilda.exceptions import EvaluatingExpressionError, SymbolAbsentError
from hilda.hilda_client import HildaClient
from hilda.lldb_importer import lldb
from hilda.symbols_jar import SymbolsJar


class HIEvents:
    def __init__(self, ip: TerminalInteractiveShell):
        self.shell = ip
        self.hilda_client: HildaClient = self.shell.user_ns['p']

    def pre_run_cell(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInfo object
        """
        if info.raw_cell[0] in ['!', '%'] or info.raw_cell.endswith('?'):
            return
        for node in ast.walk(ast.parse(info.raw_cell)):
            if not isinstance(node, ast.Name):
                # we are only interested in names
                continue

            if node.id in locals() or node.id in self.hilda_client.globals or node.id in dir(builtins):
                # That are undefined
                continue

            if not hasattr(SymbolsJar, node.id):
                # ignore SymbolsJar properties
                try:
                    symbol = getattr(self.hilda_client.symbols, node.id)
                except SymbolAbsentError:
                    pass
                else:
                    try:
                        self.hilda_client._add_global(
                            node.id,
                            symbol if symbol.type_ != lldb.eSymbolTypeObjCMetaClass else self.hilda_client.objc_get_class(
                                node.id)
                        )
                    except EvaluatingExpressionError:
                        self.hilda_client.log_warning(
                            f'Process is running. Pause execution in order to resolve "{node.id}"')


def load_ipython_extension(ip: TerminalInteractiveShell):
    hie = HIEvents(ip)
    ip.events.register('pre_run_cell', hie.pre_run_cell)
