from contextlib import suppress

from hilda.exceptions import AddingLldbSymbolError, SymbolAbsentError
from hilda.lldb_importer import lldb


class SymbolsJar:
    def __init__(self, hilda):
        """
        Initialize a symbol list.

        :param hilda.hilda_client.HildaClient hilda: Hilda client
        """
        self._hilda = hilda
        self._symbols = {}

    def __len__(self):
        return len(self._symbols)

    def __contains__(self, key: str):
        return key in self._symbols

    def __getitem__(self, item: str):
        def get_lazy(name: str):
            client = self._hilda
            if '{' in name:
                # remove module name from symbol
                name = name.split('{', 1)[0]
            for s in client.target.FindSymbols(name):
                with suppress(AddingLldbSymbolError):
                    return client.add_lldb_symbol(s.symbol)
            return None

        if item not in self._symbols:
            symbol = get_lazy(item)
            if symbol:
                return symbol
        return self._symbols[item]

    def __getattr__(self, name):
        symbol = self.get(name)
        if symbol is None:
            raise SymbolAbsentError(f'no such symbol: {name}')

        return symbol

    def get(self, name):
        if name in self._symbols:
            return self._symbols.get(name)

        client = self._hilda
        for s in client.target.FindSymbols(name):
            with suppress(AddingLldbSymbolError):
                return client.add_lldb_symbol(s.symbol)
        return None

    def add(self, key, value):
        self._symbols[key] = value

    def items(self):
        return self._symbols.items()

    def __sub__(self, other):
        retval = SymbolsJar(self._hilda)
        for k1, v1 in self.items():
            if k1 not in other:
                retval.add(k1, v1)
        return retval

    def __add__(self, other):
        retval = SymbolsJar(self._hilda)
        for k, v in other.items():
            retval.add(k, v)
        for k, v in self.items():
            retval.add(k, v)
        return retval

    def bp(self, callback=None, **args):
        """
        Place a breakpoint on all symbols in current jar.
        Look for the bp command for more details.
        :param callback:  callback function to be executed upon an hit
        :param args: optional args for the bp command
        """
        for k, v in self.items():
            v.bp(callback, **args)

    def by_module(self):
        """
        Filter to only names containing their module names
        :return: reduced symbol jar
        """
        retval = SymbolsJar(self._hilda)
        for k, v in self.items():
            if '{' not in k or '}' not in k:
                continue
            retval.add(k, v)
        return retval

    def by_type(self, lldb_type):
        """
        Filter by LLDB symbol types (for example: lldb.eSymbolTypeCode,
        lldb.eSymbolTypeData, ...)
        :param lldb_type: symbol type from LLDB consts
        :return: symbols matching the type filter
        """
        retval = SymbolsJar(self._hilda)
        for k, v in self.items():
            if v.type_ == lldb_type:
                retval.add(k, v)
        return retval

    def code(self):
        """
        Filter only code symbols
        :return: symbols with type lldb.eSymbolTypeCode
        """
        return self.by_type(lldb.eSymbolTypeCode)

    def data(self):
        """
        Filter only data symbols
        :return: symbols with type lldb.eSymbolTypeCode
        """
        return self.by_type(lldb.eSymbolTypeData)

    def objc_class(self):
        """
        Filter only objc meta classes
        :return: symbols with type lldb.eSymbolTypeObjCMetaClass
        """
        return self.clean().by_type(lldb.eSymbolTypeObjCMetaClass)

    def clean(self):
        """
        Filter only symbols without module suffix
        :return: reduced symbol jar
        """
        retval = SymbolsJar(self._hilda)
        for k, v in self.items():
            if '{' in k:
                continue
            retval.add(k, v)
        return retval

    def monitor(self, **args):
        """
        Perform monitor for all symbols in current jar.
        See monitor command for more details.
        :param args: given arguments for monitor command
        """
        for name, address in self.items():
            options = args.copy()
            if name == '_client':
                continue
            if self._hilda.configs.objc_verbose_monitor:
                arg_count = name.count(':')
                if arg_count > 0:
                    arg_count = min(6, arg_count)
                    options['expr'] = {f'$arg{i + 3}': 'po' for i in range(arg_count)}
            name = options.get('name', name)
            address.monitor(name=name, **options)

    def startswith(self, exp, case_sensitive=True):
        """
        Filter only symbols with given prefix
        :param exp: prefix
        :param case_sensitive: is case sensitive
        :return: reduced symbol jar
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = SymbolsJar(self._hilda)
        for k, v in self.items():
            orig_k = k
            if not case_sensitive:
                k = k.lower()
            if k.startswith(exp):
                retval.add(orig_k, v)
        return retval

    def endswith(self, exp, case_sensitive=True):
        """
        Filter only symbols with given prefix
        :param exp: prefix
        :param case_sensitive: is case sensitive
        :return: reduced symbol jar
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = SymbolsJar(self._hilda)
        for k, v in self.items():
            orig_k = k
            if not case_sensitive:
                k = k.lower()
            if k.endswith(exp):
                retval.add(orig_k, v)
        return retval

    def find(self, exp, case_sensitive=True):
        """
        Filter symbols containing a given expression
        :param exp: given expression
        :param case_sensitive: is case sensitive
        :return: reduced symbol jar
        """
        if not case_sensitive:
            exp = exp.lower()

        retval = SymbolsJar(self._hilda)
        for k, v in self.items():
            orig_k = k
            if not case_sensitive:
                k = k.lower()
            if exp in k:
                retval.add(orig_k, v)
        return retval
