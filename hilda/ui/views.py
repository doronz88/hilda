import shutil
from abc import abstractmethod
from typing import List, Mapping

from click import style
from lldb import SBAddress
from tabulate import tabulate

WORD_SIZE = 8


def dict_diff(d1: Mapping, d2: Mapping) -> List[str]:
    """ Returns a list of keys whose values have changed """
    changed_keys = []
    if d1 is None or d2 is None:
        return changed_keys
    for k, v in d1.items():
        if k in d2 and d2[k] != v:
            changed_keys.append(k)
    return changed_keys


class View:
    """ Base class of view"""

    def __init__(self, hilda_client, title, color_scheme):
        """
        :param hilda_client: hilda.hilda_client.HildaClient
        :param title: str
        :param color_scheme: hilda.ui.ui_manager.ColorScheme
        """
        self.title = title
        self.hilda = hilda_client
        self.active = True
        self.color_scheme = color_scheme

    @abstractmethod
    def __str__(self) -> str:
        return self._format_title()

    def _format_title(self) -> str:
        terminal_size = shutil.get_terminal_size()
        fmt = style(self.title.center(terminal_size.columns, '─'), fg=self.color_scheme.title)
        fmt += '\n'
        return fmt


class StackView(View):
    """ Implements stack view """
    DEFAULT_STACK_DEPTH = 10

    def __init__(self, hilda_client, color_scheme, depth=DEFAULT_STACK_DEPTH):
        """
        :param hilda_client: hilda.hilda_client.HildaClient
        :param depth: int
        :param color_scheme: hilda.ui.ui_manager.ColorScheme

        `prev` saves the last stack stats inorder to perform diff check.
        """
        super().__init__(hilda_client, 'Stack', color_scheme)
        self.depth = depth
        self.prev: Mapping[int, str] = None

    def __str__(self) -> str:
        """ Format stack view for printing """
        stack_mapping = self._create_mapping()
        diff_in_keys = dict_diff(stack_mapping, self.prev)
        self.prev = stack_mapping.copy()
        fmt_parts = []
        offset = 0
        for k, v in stack_mapping.items():
            data_color = self.color_scheme.stack_data if k not in diff_in_keys else self.color_scheme.diff
            fmt = f'{style(hex(k), fg=self.color_scheme.address)}|+' \
                  f'{style(hex(offset), fg=self.color_scheme.stack_offset)}: ' \
                  f'{style(v, fg=data_color)}'
            if offset == 0:
                fmt += f'{"<-- $sp":^50}'
            offset += WORD_SIZE
            fmt_parts.append(fmt)

        return super().__str__() + '\n'.join(fmt_parts)

    def _create_mapping(self) -> Mapping[int, str]:
        """ Generate mapping of stack address:data"""
        base_addr = self.hilda.frame.sp
        stack_mapping = {}
        for i in range(0, self.depth * WORD_SIZE, WORD_SIZE):
            current = base_addr + i
            stack_mapping[current] = '0x' + self.hilda.symbol(current).peek(WORD_SIZE).hex()
        return stack_mapping


class RegistersView(View):
    """ Implements registers view """
    DEFAULT_REGISTERS_TYPE = 'general'

    def __init__(self, hilda_client, color_scheme, rtype=DEFAULT_REGISTERS_TYPE):
        """
        :param hilda_client: hilda.hilda_client.HildaClient
        :param rtype: str
        :param color_scheme: hilda.ui.ui_manager.ColorScheme

        `prev` saves the last registers stats inorder to perform diff check.
        """
        super().__init__(hilda_client, 'Registers', color_scheme)
        self.prev: Mapping[str, str] = None
        self.rtype = rtype

    def __str__(self) -> str:
        """ Format registers view for printing"""
        regs_mapping = self._create_mapping()
        diff_in_keys = dict_diff(regs_mapping, self.prev)
        self.prev = regs_mapping.copy()
        list_of_lists = []
        names = []
        values = []
        i = 0

        # Divide the registers into columns of 16
        for k, v in regs_mapping.items():
            if i % 16 == 0 and i != 0:
                list_of_lists.append(names.copy())
                list_of_lists.append(values.copy())
                names = []
                values = []

            names.append(style(k, fg=self.color_scheme.regs_name))
            if k in diff_in_keys:
                values.append(style(v, fg=self.color_scheme.diff))
            else:
                values.append(style(v, fg=self.color_scheme.regs_value))
            i += 1

        return super().__str__() + tabulate(list(zip(*list_of_lists)), tablefmt='plain', numalign='left')

    def _create_mapping(self) -> Mapping[str, str]:
        """ Generate mapping of registers name:data"""
        regs = self._get_registers()
        regs_mapping = {}
        for reg in regs:
            regs_mapping[reg.GetName()] = reg.GetValue()
        return regs_mapping

    def _get_registers(self):
        """
        Returns list of registers grouped by type.
        Available types: [general,floating]
        :return:  lldb.SBValueList
        """
        registers_set = self.hilda.frame.GetRegisters()
        for value in registers_set:
            if self.rtype.lower() in value.GetName().lower():
                return value
        return None


class DisassemblyView(View):
    """ Implements disassembly view """
    DEFAULT_INSTRUCTION_COUNT = 5
    DEFAULT_DISASSEMBLY_FLAVOR = 'intel'

    def __init__(self, hilda_client, color_scheme, instruction_count=DEFAULT_INSTRUCTION_COUNT,
                 flavor=DEFAULT_DISASSEMBLY_FLAVOR):
        """
        :param hilda_client: hilda.hilda_client.HildaClient
        :param instruction_count: int
        :param color_scheme: hilda.ui.ui_manager.ColorScheme
        """
        super().__init__(hilda_client, 'Disassembly', color_scheme)
        self.instruction_count = instruction_count
        self.flavor = flavor

    def __str__(self) -> str:
        """ Format disassembly view for printing """
        pc = self.hilda.frame.pc
        target = self.hilda.target

        disass = target.ReadInstructions(SBAddress(pc, target), self.instruction_count, self.flavor)
        fmt_parts = []
        for inst in disass:
            load_addr = inst.addr.GetLoadAddress(self.hilda.target)
            file_addr = inst.addr.GetFileAddress()
            base_name = style(inst.addr.module.file.basename, self.color_scheme.basename)
            load_addr = style(hex(load_addr), fg=self.color_scheme.address)
            file_addr = style(hex(file_addr), fg=self.color_scheme.address)
            mnemonic = style(inst.GetMnemonic(self.hilda.target), fg=self.color_scheme.mnemonic)
            operands = style(inst.GetOperands(self.hilda.target), fg=self.color_scheme.operands)
            fmt = f'{base_name}[{load_addr}][{file_addr}]: {mnemonic} {operands}'
            if load_addr == self.hilda.frame.pc:
                fmt += f'{"<-- $pc":^50}'
            fmt_parts.append(fmt)
        return super().__str__() + '\n'.join(fmt_parts)


class BackTraceView(View):
    """ Implements backtrace view """
    DEFAULT_BACKTRACE_DEPTH = 5

    def __init__(self, hilda_client, color_scheme, depth=DEFAULT_BACKTRACE_DEPTH):
        """
        :param hilda_client: hilda.hilda_client.HildaClient
        :param depth: int
        :param color_scheme: hilda.ui.ui_manager.ColorScheme
        """
        super().__init__(hilda_client, 'BackTrace', color_scheme)
        self.depth = depth

    def __str__(self) -> str:
        """ Format backtrace view for printing"""
        bt = self.hilda.bt(should_print=False, depth=self.depth)
        bt_colored = []
        for pair in bt:
            bt_colored.append(
                [
                    style(pair[0], fg=self.color_scheme.address),
                    pair[1]
                ]
            )
        return super().__str__() + tabulate(bt_colored, tablefmt='plain', numalign='left')
