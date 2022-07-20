import ast
import base64
import builtins
import importlib
import importlib.util
import json
import logging
import os
import pickle
import textwrap
import time
from collections import namedtuple
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Union

import IPython
import docstring_parser
import hexdump
import lldb
from humanfriendly import prompts
from humanfriendly.terminal.html import html_to_ansi
from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import XmlLexer
from tqdm import tqdm
from traitlets.config import Config

from hilda import objective_c_class
from hilda.command import command, CommandsMeta
from hilda.exceptions import *
from hilda.objective_c_symbol import ObjectiveCSymbol
from hilda.registers import Registers
from hilda.snippets.mach import CFRunLoopServiceMachPort_hooks
from hilda.symbol import Symbol
from hilda.symbols_jar import SymbolsJar
from hilda.launch_lldb import disable_logs

IsaMagic = namedtuple('IsaMagic', 'mask value')
ISA_MAGICS = [
    # ARM64
    IsaMagic(mask=0x000003f000000001, value=0x000001a000000001),
    # X86_64
    IsaMagic(mask=0x001f800000000001, value=0x001d800000000001),
]
# Mask for tagged pointer, from objc-internal.h
OBJC_TAG_MASK = (1 << 63)

with open(os.path.join(Path(__file__).resolve().parent, 'hilda_ascii_art.html'), 'r') as f:
    hilda_art = f.read()

GREETING = f"""
{hilda_art}

<b>Hilda has been successfully loaded! 😎
Also, please review the show_commands() function.
Have a nice flight ✈️! Starting an IPython shell...
"""

SerializableSymbol = namedtuple('SerializableSymbol', 'address type_ filename')


class HildaClient(metaclass=CommandsMeta):
    Breakpoint = namedtuple('Breakpoint', 'address options forced callback')

    RETVAL_BIT_COUNT = 64

    def __init__(self, debugger: lldb.SBDebugger):
        self.logger = logging.getLogger(__name__)
        self.endianness = '<'
        self.debugger = debugger
        self.target = debugger.GetSelectedTarget()
        self.process = self.target.GetProcess()
        self.symbols = SymbolsJar.create(self)
        self.breakpoints = {}
        self.captured_objects = {}
        self.registers = Registers(self)

        # should unwind the stack on errors. change this to False in order to debug self-made calls
        # within hilda
        self._evaluation_unwind_on_error = True

        # should ignore breakpoints while evaluation
        self._evaluation_ignore_breakpoints = True

        self._dynamic_env_loaded = False
        self._symbols_loaded = False

        # the frame called within the context of the hit BP
        self._bp_frame = None

        self._add_global('symbols', self.symbols, [])
        self._add_global('registers', self.registers, [])

        self.log_info(f'Target: {self.target}')
        self.log_info(f'Process: {self.process}')

    @command()
    def hd(self, buf):
        """
        Print an hexdump of given buffer
        :param buf: buffer to print in hexdump form
        """
        print(hexdump.hexdump(buf))

    @command()
    def lsof(self) -> dict:
        """
        Get dictionary of all open FDs
        :return: Mapping between open FDs and their paths
        """
        with open(os.path.join(Path(__file__).resolve().parent, 'lsof.m'), 'r') as f:
            result = json.loads(self.po(f.read()))
        # convert FDs into int
        return {int(k): v for k, v in result.items()}

    @command()
    def bt(self):
        """ Print an improved backtrace. """
        for i, frame in enumerate(self.thread.frames):
            row = ''
            row += html_to_ansi(f'<span style="color: cyan">0x{frame.addr.GetFileAddress():x}</span> ')
            row += str(frame)
            if i == 0:
                # first line
                row += ' 👈'
            print(row)

    @command()
    def disable_jetsam_memory_checks(self):
        """
        Disable jetsam memory checks, prevent raising:
        `error: Execution was interrupted, reason: EXC_RESOURCE RESOURCE_TYPE_MEMORY (limit=15 MB, unused=0x0).`
        when evaluating expression.
        """
        # 6 is for MEMORYSTATUS_CMD_SET_JETSAM_TASK_LIMIT
        result = self.symbols.memorystatus_control(6, self.process.GetProcessID(), 0, 0, 0)
        if result:
            raise DisableJetsamMemoryChecksError()

    @command()
    def symbol(self, address):
        """
        Get symbol object for a given address
        :param address:
        :return: Hilda's symbol object
        """
        return Symbol.create(address, self)

    @command()
    def objc_symbol(self, address) -> ObjectiveCSymbol:
        """
        Get objc symbol wrapper for given address
        :param address:
        :return: Hilda's objc symbol object
        """
        try:
            return ObjectiveCSymbol.create(int(address), self)
        except HildaException as e:
            raise CreatingObjectiveCSymbolError from e

    @command()
    def inject(self, filename):
        """
        Inject a single library into currently running process
        :param filename:
        :return: module object
        """
        module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
        if module.file.basename is not None:
            self.log_warning(f'file {filename} has already been loaded')

        injected = SymbolsJar.create(self)
        handle = self.symbols.dlopen(filename, 10)  # RTLD_GLOBAL|RTLD_NOW

        if handle == 0:
            self.log_critical(f'failed to inject: {filename}')

        module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
        for symbol in module.symbols:
            load_addr = symbol.addr.GetLoadAddress(self.target)
            if load_addr == 0xffffffffffffffff:
                # skip those not having a real address
                continue

            name = symbol.name
            type_ = symbol.GetType()

            if name in ('<redacted>',) or (type_ not in (lldb.eSymbolTypeCode,
                                                         lldb.eSymbolTypeData,
                                                         lldb.eSymbolTypeObjCMetaClass)):
                # ignore unnamed symbols and those which are not: data, code or objc classes
                continue

            injected[name] = self.symbol(load_addr)
        return injected

    @command()
    def rebind_symbols(self, image_range=None, filename_expr=''):
        """
        Reparse all loaded images symbols
        :param image_range: index range for images to load in the form of [start, end]
        :param filename_expr: filter only images containing given expression
        """
        self.log_debug('mapping symbols')
        self._symbols_loaded = False

        for i, module in enumerate(tqdm(self.target.modules)):
            filename = module.file.basename

            if filename_expr not in filename:
                continue

            if image_range is not None and (i < image_range[0] or i > image_range[1]):
                continue

            for symbol in module:
                with suppress(AddingLldbSymbolError):
                    self.add_lldb_symbol(symbol)

        globals()['symbols'] = self.symbols
        self._symbols_loaded = True

    @command()
    def poke(self, address, buf: bytes):
        """
        Write data at given address
        :param address:
        :param buf:
        """
        err = lldb.SBError()
        retval = self.process.WriteMemory(address, buf, err)

        if not err.Success():
            raise AccessingMemoryError()

        return retval

    @command()
    def peek(self, address, size) -> bytes:
        """
        Read data at given address
        :param address:
        :param size:
        :return:
        """
        err = lldb.SBError()
        retval = self.process.ReadMemory(address, int(size), err)

        if not err.Success():
            raise AccessingMemoryError()

        return retval

    @command()
    def peek_str(self, address, encoding=None):
        """
        Peek a buffer till null termination
        :param address:
        :param encoding: character encoding. if None, bytes is returned
        :return:
        """
        if hasattr(self.symbols, 'strlen'):
            # always prefer using native strlen
            buf = self.peek(address, self.symbols.strlen(address))
        else:
            buf = self.peek(address, 1)
            while buf[-1] != 0:
                buf += self.peek(address + len(buf), 1)

            # remove null terminator
            buf = buf[:-1]

        if encoding is not None:
            buf = str(buf, encoding)

        return buf

    @command()
    def stop(self):
        """ Stop process. """
        self.debugger.SetAsync(False)

        is_running = self.process.GetState() == lldb.eStateRunning
        if not is_running:
            self.log_debug('already stopped')
            return

        if not self.process.Stop().Success():
            self.log_critical('failed to stop process')

    @command()
    def cont(self):
        """ Continue process. """
        is_running = self.process.GetState() == lldb.eStateRunning

        if is_running:
            self.log_debug('already running')
            return

        # bugfix:   the debugger may become in sync state, so we make sure
        #           it isn't before trying to continue
        self.debugger.SetAsync(True)

        if not self.process.Continue().Success():
            self.log_critical('failed to continue process')

    @command()
    def detach(self):
        """
        Detach from process.

        Useful in order to exit gracefully so process doesn't get killed
        while you exit
        """
        if not self.process.Detach().Success():
            self.log_critical('failed to detach')

    @command()
    def disass(self, address, buf, should_print=True) -> lldb.SBInstructionList:
        """
        Print disassembly from a given address
        :param address:
        :param buf:
        :param should_print:
        :return:
        """
        inst = self.target.GetInstructions(lldb.SBAddress(address, self.target), buf)
        if should_print:
            print(inst)
        return inst

    @command()
    def file_symbol(self, address) -> Symbol:
        """
        Calculate symbol address without ASLR
        :param address: address as can be seen originally in Mach-O
        """
        return self.symbol(self.target.ResolveFileAddress(address).GetLoadAddress(self.target))

    @command()
    def get_register(self, name) -> Symbol:
        """
        Get value for register by its name
        :param name:
        :return:
        """
        register = self.frame.register[name.lower()]
        if register is None:
            raise AccessingRegisterError()
        return self.symbol(register.unsigned)

    @command()
    def set_register(self, name, value):
        """
        Set value for register by its name
        :param name:
        :param value:
        :return:
        """
        register = self.frame.register[name.lower()]
        if register is None:
            raise AccessingRegisterError()
        register.value = hex(value)

    @command()
    def objc_call(self, obj, selector, *params):
        """
        Simulate a call to an objc selector
        :param obj: obj to pass into `objc_msgSend`
        :param selector: selector to execute
        :param params: any other additional parameters the selector requires
        :return: invocation returned value
        """
        # On object `obj`
        args = self._serialize_call_params([obj])
        # Call selector (by its uid)
        args.append(self._generate_call_expression(self.symbols.sel_getUid, self._serialize_call_params([selector])))
        # With params
        args.extend(self._serialize_call_params(params))
        call_expression = self._generate_call_expression(self.symbols.objc_msgSend, args)
        with self.stopped():
            return self.evaluate_expression(call_expression)

    @command()
    def call(self, address, argv: list = None):
        """
        Call function at given address with given parameters
        :param address:
        :param argv: parameter list
        :return: function's return value
        """
        if argv is None:
            argv = []
        call_expression = self._generate_call_expression(address, self._serialize_call_params(argv))
        with self.stopped():
            return self.evaluate_expression(call_expression)

    @command()
    def monitor(self, address, condition: str = None, **options) -> lldb.SBBreakpoint:
        """
        Monitor every time a given address is called

        The following options are available:
            regs={reg1: format}
                will print register values

                Available formats:
                    x: hex
                    s: string
                    cf: use CFCopyDescription() to get more informative description of the object
                    po: use LLDB po command
                    User defined function, will be called like `format_function(hilda_client, value)`.

                For example:
                    regs={'x0': 'x'} -> x0 will be printed in HEX format
            expr={lldb_expression: format}
                lldb_expression can be for example '$x0' or '$arg1'
                format behaves just like 'regs' option
            retval=format
                Print function's return value. The format is the same as regs format.
            stop=True
                force a stop at every hit
            bt=True
                print backtrace
            cmd=[cmd1, cmd2]
                run several LLDB commands, one by another
            force_return=value
                force a return from function with the specified value
            name=some_value
                use `some_name` instead of the symbol name automatically extracted from the calling frame
            override=True
                override previous break point at same location


        :param address:
        :param condition: set as a conditional breakpoint using an lldb expression
        :param options:
        :return:
        """

        def callback(hilda, frame, bp_loc, options):
            """
            :param HildaClient hilda: Hilda client.
            :param lldb.SBFrame frame: LLDB Frame object.
            :param lldb.SBBreakpointLocation bp_loc: LLDB Breakpoint location object.
            :param dict options: User defined options.
            """
            bp = bp_loc.GetBreakpoint()
            symbol = hilda.breakpoints[bp.id].address  # type: Symbol

            # by default, attempt to resolve the symbol name through lldb
            name = str(symbol.lldb_symbol)
            if options.get('name', False):
                name = options['name']

            log_message = f'🚨 #{bp.id} 0x{symbol:x} {name}'

            if 'regs' in options:
                log_message += '\nregs:'
                for name, fmt in options['regs'].items():
                    value = hilda.symbol(frame.FindRegister(name).unsigned)
                    log_message += f'\n\t{name} = {hilda._monitor_format_value(fmt, value)}'

            if 'expr' in options:
                log_message += '\nexpr:'
                for name, fmt in options['expr'].items():
                    value = hilda.symbol(hilda.evaluate_expression(name))
                    log_message += f'\n\t{name} = {hilda._monitor_format_value(fmt, value)}'

            if options.get('force_return', False):
                hilda.force_return(options['force_return'])
                log_message += f'\nforced return: {options["force_return"]}'

            if options.get('bt', False):
                # bugfix: for callstacks from xpc events
                hilda.finish()
                hilda.bt()

            if options.get('retval', False):
                # return from function
                hilda.finish()
                value = hilda.evaluate_expression('$arg1')
                log_message += f'\nreturned: {hilda._monitor_format_value(options["retval"], value)}'

            hilda.log_info(log_message)

            for cmd in options.get('cmd', []):
                hilda.lldb_handle_command(cmd)

            if not options.get('stop', False):
                hilda.cont()

        return self.bp(address, callback, condition=condition, **options)

    @command()
    def show_current_source(self):
        """ print current source code if possible """
        self.lldb_handle_command('f')

    @command()
    def finish(self):
        """ Run current frame till its end. """
        with self.sync_mode():
            self.thread.StepOutOfFrame(self.frame)
            self._bp_frame = None

    @command()
    def step_into(self):
        """ Step into current instruction. """
        with self.sync_mode():
            self.thread.StepInto()

    @command()
    def step_over(self):
        """ Step over current instruction. """
        with self.sync_mode():
            self.thread.StepOver()

    @command()
    def remove_all_hilda_breakpoints(self, remove_forced=False):
        """
        Remove all breakpoints created by Hilda
        :param remove_forced: include removed of "forced" breakpoints
        """
        breakpoints = list(self.breakpoints.items())
        for bp_id, bp in breakpoints:
            if remove_forced or not bp.forced:
                self.remove_hilda_breakpoint(bp_id)

    @command()
    def remove_hilda_breakpoint(self, bp_id):
        """
        Remove a single breakpoint placed by Hilda
        :param bp_id: Breakpoint's ID
        """
        self.target.BreakpointDelete(bp_id)
        del self.breakpoints[bp_id]
        self.log_info(f'BP #{bp_id} has been removed')

    @command()
    def force_return(self, value=0):
        """
        Prematurely return from a stack frame, short-circuiting exection of newer frames and optionally
        yielding a specified value.
        :param value:
        :return:
        """
        self.finish()
        self.set_register('x0', value)

    @command()
    def proc_info(self):
        """ Print information about currently running mapped process. """
        print(self.process)

    @command()
    def print_proc_entitlements(self):
        """ Get the plist embedded inside the process' __LINKEDIT section. """
        linkedit_section = self.target.modules[0].FindSection('__LINKEDIT')
        linkedit_data = self.symbol(linkedit_section.GetLoadAddress(self.target)).peek(linkedit_section.size)

        # just look for the xml start inside the __LINKEDIT section. should be good enough since wer'e not
        # expecting any other XML there
        entitlements = str(linkedit_data[linkedit_data.find(b'<?xml'):].split(b'\xfa', 1)[0], 'utf8')
        print(highlight(entitlements, XmlLexer(), TerminalTrueColorFormatter()))

    @command()
    def bp(self, address, callback=None, condition: str = None, forced=False, **options) -> lldb.SBBreakpoint:
        """
        Add a breakpoint
        :param address:
        :param condition: set as a conditional breakpoint using lldb expression
        :param callback: callback(hilda, *args) to be called
        :param forced: whether the breakpoint should be protected frm usual removal.
        :param options:
        :return:
        """
        if address in [bp.address for bp in self.breakpoints.values()]:
            override = True if options.get('override', True) else False
            if override or prompts.prompt_for_confirmation('A breakpoint already exist in given location. '
                                                           'Would you like to delete the previous one?', True):
                breakpoints = list(self.breakpoints.items())
                for bp_id, bp in breakpoints:
                    if address == bp.address:
                        self.remove_hilda_breakpoint(bp_id)

        bp = self.target.BreakpointCreateByAddress(address)

        if condition is not None:
            bp.SetCondition(condition)

        # add into Hilda's internal list of breakpoints
        self.breakpoints[bp.id] = HildaClient.Breakpoint(
            address=address, options=options, forced=forced, callback=callback
        )

        if callback is not None:
            bp.SetScriptCallbackFunction('lldb.hilda_client.bp_callback_router')

        self.log_info(f'Breakpoint #{bp.id} has been set')
        return bp

    def bp_callback_router(self, frame, bp_loc, *_):
        """
        Route the breakpoint callback the the specific breakpoint callback.
        :param lldb.SBFrame frame: LLDB Frame object.
        :param lldb.SBBreakpointLocation bp_loc: LLDB Breakpoint location object.
        """
        bp_id = bp_loc.GetBreakpoint().GetID()
        self._bp_frame = frame
        try:
            self.breakpoints[bp_id].callback(self, frame, bp_loc, self.breakpoints[bp_id].options)
        finally:
            self._bp_frame = None

    @command()
    def show_hilda_breakpoints(self):
        """ Show existing breakpoints created by Hilda. """
        for bp_id, bp in self.breakpoints.items():
            print(f'🚨 Breakpoint #{bp_id}: Forced: {bp.forced}')
            print(f'\tAddress: 0x{bp.address:x}')
            print(f'\tOptions: {bp.options}')

    @command()
    def show_commands(self):
        """ Show available commands. """
        for command_name, command_func in self.commands:
            doc = docstring_parser.parse(command_func.__doc__)
            print(f'👾 {command_name} - {doc.short_description}')
            if doc.long_description:
                print(textwrap.indent(doc.long_description, '    '))

    @command()
    def save(self, filename=None):
        """
        Save loaded symbols map (for loading later using the load() command)
        :param filename: optional filename for where to store
        """
        if filename is None:
            filename = self._get_saved_state_filename()

        self.log_info(f'saving current state info: {filename}')
        with open(filename, 'wb') as f:
            symbols_copy = {}
            for k, v in self.symbols.items():
                # converting the symbols into serializable objects
                symbols_copy[k] = SerializableSymbol(address=int(v),
                                                     type_=v.type_,
                                                     filename=v.filename)
            pickle.dump(symbols_copy, f)

    @command()
    def load(self, filename=None):
        """
        Load an existing symbols map (previously saved by the save() command)
        :param filename: filename to load from
        """
        if filename is None:
            filename = self._get_saved_state_filename()

        self.log_info(f'loading current state from: {filename}')
        with open(filename, 'rb') as f:
            symbols_copy = pickle.load(f)

            for k, v in tqdm(symbols_copy.items()):
                self.symbols[k] = self.symbol(v.address)

            # perform sanity test for symbol rand
            if self.symbols.rand() == 0 and self.symbols.rand() == 0:
                # rand returning 0 twice means the loaded file is probably outdated
                raise BrokenLocalSymbolsJarError()

            # assuming the first main image will always change
            self.rebind_symbols(image_range=[0, 0])
            self.init_dynamic_environment()
            self._symbols_loaded = True

    @command()
    def po(self, expression, cast=None):
        """
        Print given object using LLDB's po command

        Can also run big chunks of native code:

        po('NSMutableString *s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')

        :param expression: either a symbol or string the execute
        :param cast: object type
        :raise EvaluatingExpressionError: LLDB failed to evaluate the expression
        :return: LLDB's po output
        """
        casted_expression = ''
        if cast is not None:
            casted_expression += '(%s)' % cast
        casted_expression += f'0x{expression:x}' if isinstance(expression, int) else str(expression)

        res = lldb.SBCommandReturnObject()
        self.debugger.GetCommandInterpreter().HandleCommand(f'expression -i 0 -lobjc -O -- {casted_expression}', res)
        if not res.Succeeded():
            raise EvaluatingExpressionError(res.GetError())
        return res.GetOutput().strip()

    @command()
    def globalize_symbols(self):
        """
        Make all symbols in python's global scope
        """
        reserved_names = list(globals().keys()) + dir(builtins)
        for name, value in tqdm(self.symbols.items()):
            if ':' not in name \
                    and '[' not in name \
                    and '<' not in name \
                    and '(' not in name \
                    and '.' not in name:
                self._add_global(name, value, reserved_names)

    @command()
    def jump(self, symbol: int):
        """ jump to given symbol """
        self.lldb_handle_command(f'j *{symbol}')

    @command()
    def lldb_handle_command(self, cmd):
        """
        Execute an LLDB command

        For example:
            lldb_handle_command('register read')

        :param cmd:
        """
        self.debugger.HandleCommand(cmd)

    @command()
    def objc_get_class(self, name) -> objective_c_class.Class:
        """
        Get ObjC class object
        :param name:
        :return:
        """
        return objective_c_class.Class.from_class_name(self, name)

    @command()
    def CFSTR(self, s):
        """
        Create CFStringRef object from given string
        :param s: given string
        :return:
        """
        return self.ns(s)

    @command()
    def ns(self, data) -> Symbol:
        """
        Create NSObject from given data
        :param data: Data representing the NSObject, must by JSON serializable
        :return: Pointer to a NSObject
        """
        try:
            json_data = json.dumps({'root': data}, default=self._to_ns_json_default)
        except TypeError as e:
            raise ConvertingToNsObjectError from e

        with open(os.path.join(Path(__file__).resolve().parent, 'to_ns_from_json.m'), 'r') as code_f:
            obj_c_code = code_f.read()
        expression = obj_c_code.replace('__json_object_dump__', json_data.replace('"', r'\"'))
        try:
            return self.evaluate_expression(expression)
        except EvaluatingExpressionError as e:
            raise ConvertingToNsObjectError from e

    @command()
    def from_ns(self, address: Union[int, str]):
        """
        Create python object from NS object.
        :param address: NS object.
        :return: Python object.
        """
        with open(os.path.join(Path(__file__).resolve().parent, 'from_ns_to_json.m'), 'r') as f:
            obj_c_code = f.read()
        address = f'0x{address:x}' if isinstance(address, int) else address
        expression = obj_c_code.replace('__ns_object_address__', address)
        try:
            json_dump = self.po(expression)
        except EvaluatingExpressionError as e:
            raise ConvertingFromNSObjectError from e
        return json.loads(json_dump, object_hook=self._from_ns_json_object_hook)['root']

    @command()
    def evaluate_expression(self, expression) -> Symbol:
        """
        Wrapper for LLDB's EvaluateExpression.
        Used for quick code snippets.

        Feel free to use local variables inside the expression using format string.
        For example:
            currentDevice = objc_get_class('UIDevice').currentDevice
            evaluate_expression(f'[[{currentDevice} systemName] hasPrefix:@"2"]')

        :param expression:
        :return: returned symbol
        """
        # prepending a prefix so LLDB knows to return an int type
        if isinstance(expression, int):
            formatted_expression = f'(intptr_t)0x{expression:x}'
        else:
            formatted_expression = str(expression)

        options = lldb.SBExpressionOptions()
        options.SetIgnoreBreakpoints(self._evaluation_ignore_breakpoints)
        options.SetTryAllThreads(True)
        options.SetUnwindOnError(self._evaluation_unwind_on_error)

        e = self.frame.EvaluateExpression(formatted_expression, options)

        if not e.error.Success():
            raise EvaluatingExpressionError(str(e.error))

        return self.symbol(e.unsigned)

    @command()
    def import_module(self, filename, name=None):
        """
        Import & reload given python module (intended mainly for external snippets)
        :param filename: Python filename to import
        :param name: Optional module name, or otherwise use the filename
        :return: Python module
        """
        if name is None:
            name = os.path.splitext(os.path.basename(filename))[0]
        spec = importlib.util.spec_from_file_location(name, filename)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    @command()
    def set_evaluation_unwind(self, value: bool):
        """
        Set whether LLDB will attempt to unwind the stack whenever an expression evaluation error occurs.

        Use unwind() to restore when an error is raised in this case.
        """
        self._evaluation_unwind_on_error = value

    @command()
    def get_evaluation_unwind(self) -> bool:
        """
        Get evaluation unwind state.

        When this value is True, LLDB will attempt unwinding the stack on evaluation errors.
        Otherwise, the stack frame will remain the same on errors to help you investigate the error.
        """
        return self._evaluation_unwind_on_error

    @command()
    def set_evaluation_ignore_breakpoints(self, value: bool):
        """
        Set whether to ignore breakpoints while evaluating expressions
        """
        self._evaluation_ignore_breakpoints = value

    @command()
    def get_evaluation_ignore_breakpoints(self) -> bool:
        """
        Get evaluation "ignore-breakpoints" state.
        """
        return self._evaluation_ignore_breakpoints

    @command()
    def unwind(self) -> bool:
        """ Unwind the stack (useful when get_evaluation_unwind() == False) """
        return self.thread.UnwindInnermostExpression().Success()

    @property
    def thread(self):
        """ Current active thread. """
        if self._bp_frame is not None:
            return self._bp_frame.GetThread()
        return self.process.GetSelectedThread()

    @property
    def frame(self):
        """ Current active frame. """
        if self._bp_frame is not None:
            return self._bp_frame
        return self.thread.GetSelectedFrame()

    @contextmanager
    def stopped(self, interval=0):
        """
        Context-Manager for execution while process is stopped.
        If interval is supplied, then if the device is in running state, it will sleep for the interval
        given before and after execution.
        """
        is_running = self.process.GetState() == lldb.eStateRunning

        if is_running:
            self.stop()
            time.sleep(1)

        try:
            yield
        finally:
            if is_running:
                time.sleep(1)
                self.cont()

    @contextmanager
    def safe_malloc(self, size):
        """
        Context-Manager for allocating a block of memory which is freed afterwards
        :param size:
        :return:
        """
        block = self.symbols.malloc(size)
        if block == 0:
            raise IOError(f'failed to allocate memory of size: {size} bytes')

        try:
            yield block
        finally:
            self.symbols.free(block)

    @contextmanager
    def sync_mode(self):
        """ Context-Manager for execution while LLDB is in sync mode. """
        is_async = self.debugger.GetAsync()
        self.debugger.SetAsync(False)
        try:
            yield
        finally:
            self.debugger.SetAsync(is_async)

    def init_dynamic_environment(self):
        """ Init session-scoped process dynamic dependencies. """
        self.log_debug('init dynamic environment')
        self._dynamic_env_loaded = True

        self.log_debug('disable mach_msg receive errors')
        try:
            CFRunLoopServiceMachPort_hooks.disable_mach_msg_errors()
        except SymbolAbsentError:
            self.log_warning('failed to disable mach_msg errors')

        objc_code = """
        @import ObjectiveC;
        @import Foundation;
        """
        try:
            self.po(objc_code)
        except EvaluatingExpressionError:
            # first time is expected to fail. bug in LLDB?
            pass

    def log_warning(self, message):
        """ Log at warning level """
        self.logger.warning(message)

    def log_debug(self, message):
        """ Log at debug level """
        self.logger.debug(message)

    def log_error(self, message):
        """ Log at error level """
        self.logger.error(message)

    def log_critical(self, message):
        """ Log at critical level """
        self.logger.critical(message)
        raise HildaException(message)

    def log_info(self, message):
        """ Log at info level """
        self.logger.info(message)

    def add_lldb_symbol(self, symbol: lldb.SBSymbol) -> Symbol:
        """
        Convert an LLDB symbol into Hilda's symbol object and insert into `symbols` global
        :param symbol: LLDB symbol
        :return: converted symbol
        :raise AddingLldbSymbolError: Hilda failed to convert the LLDB symbol.
        """
        load_addr = symbol.addr.GetLoadAddress(self.target)
        if load_addr == 0xffffffffffffffff:
            # skip those not having a real address
            raise AddingLldbSymbolError()

        name = symbol.name
        type_ = symbol.GetType()

        if name in ('<redacted>',) or (type_ not in (lldb.eSymbolTypeCode,
                                                     lldb.eSymbolTypeRuntime,
                                                     lldb.eSymbolTypeData,
                                                     lldb.eSymbolTypeObjCMetaClass)):
            # ignore unnamed symbols and those which are not in a really used type
            raise AddingLldbSymbolError()

        value = self.symbol(load_addr)

        # add it into symbols global
        self.symbols[name] = value
        self.symbols[f'{name}{{{value.filename}}}'] = value

        return value

    def interactive(self):
        """ Start an interactive Hilda shell """
        if not self._dynamic_env_loaded:
            self.init_dynamic_environment()
        self._globalize_commands()
        print('\n')
        self.log_info(html_to_ansi(GREETING))

        c = Config()
        c.IPCompleter.use_jedi = False
        c.InteractiveShellApp.exec_lines = [
            '''disable_logs()''',
            '''IPython.get_ipython().events.register('pre_run_cell', self._ipython_run_cell_hook)'''
        ]
        namespace = globals()
        namespace.update(locals())

        IPython.start_ipython(config=c, user_ns=namespace)

    @staticmethod
    def is_objc_type(symbol: Symbol) -> bool:
        """
        Test if a given symbol represents an objc object
        :param symbol:
        :return:
        """
        # Tagged pointers are ObjC objects
        if symbol & OBJC_TAG_MASK == OBJC_TAG_MASK:
            return True

        # Class are not ObjC objects
        for mask, value in ISA_MAGICS:
            if symbol & mask == value:
                return False

        try:
            with symbol.change_item_size(8):
                isa = symbol[0]
        except HildaException:
            return False

        for mask, value in ISA_MAGICS:
            if isa & mask == value:
                return True

        return False

    @staticmethod
    def _add_global(name, value, reserved_names=None):
        if reserved_names is None or name not in reserved_names:
            # don't override existing symbols
            globals()[name] = value

    @staticmethod
    def _get_saved_state_filename():
        return '/tmp/cache.hilda'

    @staticmethod
    def _to_ns_json_default(obj):
        if isinstance(obj, bytes):
            return f'__hilda_magic_key__|NSData|{base64.b64encode(obj).decode()}'
        elif isinstance(obj, datetime):
            return f'__hilda_magic_key__|NSDate|{obj.timestamp()}'
        raise TypeError

    @staticmethod
    def _from_ns_json_object_hook(obj: dict):
        parsed_object = {}
        for key, value in obj.items():
            parsed_object[HildaClient._from_ns_parse_function(key)] = HildaClient._from_ns_parse_function(value)
        return parsed_object

    @staticmethod
    def _from_ns_parse_function(obj):
        if isinstance(obj, list):
            return list(map(HildaClient._from_ns_parse_function, obj))
        if not isinstance(obj, str) or not obj.startswith('__hilda_magic_key__'):
            return obj
        _, type_, data = obj.split('|')
        if type_ == 'NSData':
            return base64.b64decode(data)
        if type_ == 'NSDictionary':
            return tuple(json.loads(data, object_hook=HildaClient._from_ns_json_object_hook).items())
        if type_ == 'NSArray':
            return tuple(json.loads(data, object_hook=HildaClient._from_ns_json_object_hook))
        if type_ == 'NSNumber':
            return eval(data)
        if type_ == 'NSNull':
            return None
        if type_ == 'NSDate':
            return datetime.fromtimestamp(eval(data), timezone.utc)

    def _serialize_call_params(self, argv):
        args_conv = []
        for arg in argv:
            if isinstance(arg, str) or isinstance(arg, bytes):
                if isinstance(arg, str):
                    arg = arg.encode()
                arg = ''.join([f'\\x{b:02x}' for b in arg])
                args_conv.append(f'(intptr_t)"{arg}"')
            elif isinstance(arg, int) or isinstance(arg, Symbol):
                arg = int(arg) & 0xffffffffffffffff
                args_conv.append(f'0x{arg:x}')
            else:
                raise NotImplementedError('cannot serialize argument')
        return args_conv

    @staticmethod
    def _generate_call_expression(address, params):
        args_type = ','.join(['intptr_t'] * len(params))
        args_conv = ','.join(params)
        return f'((intptr_t(*)({args_type}))({address}))({args_conv})'

    def _globalize_commands(self):
        """ Make all command available in global scope. """
        reserved_names = list(globals().keys()) + dir(builtins)

        for command_name, function in self.commands:
            command_func = partial(function, self)
            command_func.__doc__ = function.__doc__

            self._add_global(command_name, command_func, reserved_names)

    def _ipython_run_cell_hook(self, info):
        """
        Enable lazy loading for symbols
        :param info: IPython's CellInfo object
        """
        if info.raw_cell.startswith('!') or info.raw_cell.endswith('?'):
            return

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
                    symbol = getattr(self.symbols, node.id)
                except SymbolAbsentError:
                    pass
                else:
                    self._add_global(
                        node.id,
                        symbol if symbol.type_ != lldb.eSymbolTypeObjCMetaClass else self.objc_get_class(node.id)
                    )

    def _monitor_format_value(self, fmt, value):
        if callable(fmt):
            return fmt(self, value)
        formatters = {
            'x': lambda val: f'0x{int(val):x}',
            's': lambda val: val.peek_str(),
            'cf': lambda val: val.cf_description,
            'po': lambda val: val.po(),
        }
        if fmt in formatters:
            return formatters[fmt](value)
        else:
            return f'{value:x} (unsupported format)'
