# HildaClient

The main entry point — exposed as the `p` global inside the Hilda shell.

## Creating a client

In standalone scripts (run with `xcrun python3 script.py`), create a client with one of these factories — see [Hilda as Python Module](https://doronz88.github.io/hilda/latest/hilda-modes-of-operation/#hilda-as-python-module) for runnable examples.

## hilda.launch_lldb.create_hilda_client_using_attach_by_name

```
create_hilda_client_using_attach_by_name(name: Optional[str] = None, wait_for: bool = False) -> HildaClient
```

Source code in `hilda/launch_lldb.py`

```
def create_hilda_client_using_attach_by_name(name: Optional[str] = None, wait_for: bool = False) -> HildaClient:
    lldb_t = LLDBAttachName(name, wait_for)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)
```

## hilda.launch_lldb.create_hilda_client_using_attach_by_pid

```
create_hilda_client_using_attach_by_pid(pid: Optional[int] = None) -> HildaClient
```

Source code in `hilda/launch_lldb.py`

```
def create_hilda_client_using_attach_by_pid(pid: Optional[int] = None) -> HildaClient:
    lldb_t = LLDBAttachPid(pid)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)
```

## hilda.launch_lldb.create_hilda_client_using_launch

```
create_hilda_client_using_launch(exec_path: str, argv: Optional[list] = None, envp: Optional[list] = None, stdin: Optional[str] = None, stdout: Optional[str] = None, stderr: Optional[str] = None, wd: Optional[str] = None, flags: Optional[int] = 0) -> HildaClient
```

Source code in `hilda/launch_lldb.py`

```
def create_hilda_client_using_launch(
    exec_path: str,
    argv: Optional[list] = None,
    envp: Optional[list] = None,
    stdin: Optional[str] = None,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
    wd: Optional[str] = None,
    flags: Optional[int] = 0,
) -> HildaClient:
    lldb_t = LLDBLaunch(exec_path, argv, envp, stdin, stdout, stderr, wd, flags)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)
```

## hilda.launch_lldb.create_hilda_client_using_remote_attach

```
create_hilda_client_using_remote_attach(hostname: str, port: int) -> HildaClient
```

Source code in `hilda/launch_lldb.py`

```
def create_hilda_client_using_remote_attach(hostname: str, port: int) -> HildaClient:
    lldb_t = LLDBRemote(hostname, port)
    lldb_t.start()
    return _get_hilda_client_from_sbdebugger(lldb_t.debugger)
```

## HildaClient

## hilda.hilda_client.HildaClient

Source code in `hilda/hilda_client.py`

```
class HildaClient:
    RETVAL_BIT_COUNT = 64

    def __init__(self, debugger: lldb.SBDebugger) -> None:
        self.logger = logging.getLogger(__name__)
        self.endianness = "<"
        self.debugger = debugger
        self.target = debugger.GetSelectedTarget()
        self.process = self.target.GetProcess()
        self.symbols = SymbolList(self)
        self.breakpoints = BreakpointList(self)
        self.watchpoints = WatchpointList(self)
        self.captured_objects = {}
        self.registers = Registers(self)
        self.arch = self.target.GetTriple().split("-")[0]
        self.ui_manager = UiManager(self)
        self.configs = Configs()
        self._dynamic_env_loaded = False
        self._symbols_loaded = False
        self.globals: typing.MutableMapping[str, Any] = globals()
        self._hilda_root = Path(__file__).parent

        # the frame called within the context of the hit BP
        self._bp_frame = None

        self._add_global("symbols", self.symbols, [])
        self._add_global("registers", self.registers, [])

        self.log_info(f"Target: {self.target}")
        self.log_info(f"Process: {self.process}")

    def hd(self, buf: bytes) -> None:
        """
        Print hexdump representation for given buffer.

        :param buf: buffer to print in hexdump form
        """
        hexdump.hexdump(buf)

    def lsof(self) -> dict[int, Any]:
        """
        Get dictionary of all open FDs
        :return: Mapping between open FDs and their paths
        """
        data = (self._hilda_root / "objective_c" / "lsof.m").read_text()
        result = json.loads(self.po(data))
        # convert FDs into int
        return {int(k): v for k, v in result.items()}

    def bt(self, should_print: bool = False, depth: Optional[int] = None) -> list[Union[str, lldb.SBFrame]]:
        """
        Get backtrace of the current thread.

        :param should_print: Whether to print the backtrace to stdout. Please note this backtrace also resolved user
                             imported symbols.
        :param depth: Maximum depth of the backtrace to return
        :return: List of backtrace frames, each represented as a tuple of (address, frame)
        """
        backtrace = []
        for i, frame in enumerate(self.thread.frames):
            if i == depth:
                break
            row = ""
            row += click.style(f"0x{frame.addr.GetFileAddress():x} ", fg="cyan")
            row += f" frame #{i:02} "
            row += click.style(f"0x{frame.pc:016x} ", fg="yellow")
            row += str(frame.addr)
            if i == 0:
                # first line
                row += " 👈"
            backtrace.append([f"0x{frame.addr.file_addr:016x}", frame])
            if should_print:
                print(row)
        return backtrace

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

    def symbol(self, address: int) -> Symbol:
        """
        Get symbol object for a given address
        :param address:
        :return: Hilda's symbol object
        """
        return self.symbols.add(address)

    def objc_symbol(self, address: int) -> ObjectiveCSymbol:
        """
        Get objc symbol wrapper for given address
        :param address:
        :return: Hilda's objc symbol object
        """
        try:
            return ObjectiveCSymbol.create(int(address), self)
        except HildaException as e:
            raise CreatingObjectiveCSymbolError from e

    def inject(self, filename: str) -> SymbolList:
        """
        Inject a single library into currently running process.

        :param filename: library to inject (dylib)
        :return: SymbolList
        """
        module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
        if module.file.basename is not None:
            self.log_warning(f"file {filename} has already been loaded")

        injected = SymbolList(self)
        handle = self.symbols.dlopen(filename, 10)  # RTLD_GLOBAL|RTLD_NOW

        if handle == 0:
            self.log_critical(f"failed to inject: {filename}")

        module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
        for symbol in module.symbols:
            load_addr = symbol.addr.GetLoadAddress(self.target)
            if load_addr == 0xFFFFFFFFFFFFFFFF:
                # skip those not having a real address
                continue

            name = symbol.name
            type_ = symbol.GetType()

            if name in ("<redacted>",) or (
                type_ not in (lldb.eSymbolTypeCode, lldb.eSymbolTypeData, lldb.eSymbolTypeObjCMetaClass)
            ):
                # ignore unnamed symbols and those which are not: data, code or objc classes
                continue

            injected.add(self.symbol(load_addr), name)
        return injected

    @stop_is_needed
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

    @stop_is_needed
    def poke_text(self, address: int, code: str) -> int:
        """
        Write instructions to address.
        :param address:
        :param code:
        """
        if not lldb.KEYSTONE_SUPPORT:
            raise NotImplementedError("Not supported without keystone")
        bytecode, _count = self._ks.asm(code, as_bytes=True)
        return self.poke(address, bytecode)

    @stop_is_needed
    def peek(self, address, size: int) -> bytes:
        """
        Read data at given address
        :param address:
        :param size:
        :return:
        """
        if size == 0:
            return b""

        err = lldb.SBError()
        retval = self.process.ReadMemory(address, int(size), err)

        if not err.Success():
            raise AccessingMemoryError()

        return retval

    @stop_is_needed
    def peek_str(self, address: Symbol) -> str:
        """
        Peek a buffer till null termination
        :param address:
        :return:
        """
        size = 0x100
        while True:
            err = lldb.SBError()
            result = self.process.ReadCStringFromMemory(address, size, err)
            if not err.Success():
                raise AccessingMemoryError()
            # a shorter result means the null terminator was found within the buffer
            if len(result) < size - 1:
                return result
            size *= 2

    @stop_is_needed
    def peek_std_str(self, address: Symbol) -> str:
        """
        Peek a std::string
        :param address: Address to read the std::string from
        :return: Python string
        """
        return self._std_string(address)

    def stop(self, *args) -> None:
        """Stop process."""
        self.debugger.SetAsync(False)

        is_running = self.process.GetState() == lldb.eStateRunning
        if not is_running:
            self.log_debug("already stopped")
            return

        if not self.process.Stop().Success():
            self.log_critical("failed to stop process")

    def run_for(self, seconds: float) -> None:
        """
        Run the process for a given time
        :return:
        """
        self.cont()
        self.logger.info(f"Running for {seconds} seconds")
        time.sleep(seconds)
        self.stop()

    def cont(self, *args) -> None:
        """Continue process."""
        is_running = self.process.GetState() == lldb.eStateRunning

        if is_running:
            self.log_debug("already running")
            return

        # bugfix:   the debugger may become in sync state, so we make sure
        #           it isn't before trying to continue
        self.debugger.SetAsync(True)

        if not self.process.Continue().Success():
            self.log_critical("failed to continue process")

    def detach(self) -> None:
        """
        Detach from process.

        Useful in order to exit gracefully so process doesn't get killed
        while you exit
        """
        if not self.process.is_alive:
            return
        if not self.process.Detach().Success():
            self.log_critical("failed to detach")
            return
        self.log_info("Process Detached")

    @stop_is_needed
    def disass(
        self, address: int, buf: bytes, flavor: str = "intel", should_print: bool = False
    ) -> lldb.SBInstructionList:
        """
        Print disassembly from a given address
        :param flavor:
        :param address:
        :param buf:
        :param should_print:
        :return:
        """
        inst = self.target.GetInstructionsWithFlavor(lldb.SBAddress(address, self.target), flavor, buf)
        if should_print:
            print(inst)
        return inst

    def file_symbol(self, address: int, module_name: Optional[str] = None) -> Symbol:
        """
        Calculate symbol address without ASLR
        :param address: address as can be seen originally in Mach-O
        :param module_name: Module name to resolve the symbol from
        """
        module = self.target if module_name is None else self.target.FindModule(lldb.SBFileSpec(module_name))

        return self.symbol(module.ResolveFileAddress(address).GetLoadAddress(self.target))

    def get_register(self, name: str) -> Union[float, Symbol]:
        """
        Get value for register by its name. Value can either be an Symbol (int) or a float.

        :param name: Register name
        :return: Register value
        """
        register_value = self.frame.register[name.lower()]
        if register_value is None:
            raise AccessingRegisterError()
        return self._get_symbol_or_float_from_sbvalue(register_value)

    def set_register(self, name: str, value: Union[float, int]) -> None:
        """
        Set value for register by its name.

        :param name: Register name
        :param value: Register value
        """
        register = self.frame.register[name.lower()]
        if register is None:
            raise AccessingRegisterError()
        if isinstance(value, int):
            register.value = hex(value)
        else:
            register.value = str(value)

    def objc_call(self, obj: int, selector: str, *params):
        """
        Simulate a call to an objc selector.

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

    def call(self, address, argv: Optional[list] = None):
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

    def monitor(self, address, condition: Optional[str] = None, **options) -> HildaBreakpoint:
        """
        Monitor every time a given address is called

        Alias of self.breakpoints.add_monitor()
        """
        return self.breakpoints.add_monitor(address, condition, **options)

    def show_current_source(self) -> None:
        """print current source code if possible"""
        self.lldb_handle_command("f")

    def finish(self):
        """Run current frame till its end."""
        with self.sync_mode():
            self.thread.StepOutOfFrame(self.frame)
            self._bp_frame = None

    @stop_is_needed
    def step_into(self, *args):
        """Step into current instruction."""
        with self.sync_mode():
            self.thread.StepInto()
        if self.ui_manager.active:
            self.ui_manager.show()

    @stop_is_needed
    def step_over(self, *args):
        """Step over current instruction."""
        with self.sync_mode():
            self.thread.StepOver()
        if self.ui_manager.active:
            self.ui_manager.show()

    def force_return(self, value: int = 0) -> None:
        """
        Prematurely return from a stack frame, short-circuiting exection of newer frames and optionally
        yielding a specified value.
        :param value:
        :return:
        """
        self.finish()
        self.set_register("x0", value)

    def proc_info(self) -> None:
        """Print information about currently running mapped process."""
        print(self.process)

    def print_proc_entitlements(self) -> None:
        """Get the plist embedded inside the process' __LINKEDIT section."""
        linkedit_section = self.target.modules[0].FindSection("__LINKEDIT")
        linkedit_data = self.symbol(linkedit_section.GetLoadAddress(self.target)).peek(linkedit_section.size)

        # just look for the xml start inside the __LINKEDIT section. should be good enough since wer'e not
        # expecting any other XML there
        entitlements = str(linkedit_data[linkedit_data.find(b"<?xml") :].split(b"\xfa", 1)[0], "utf8")
        print(highlight(entitlements, XmlLexer(), TerminalTrueColorFormatter()))

    def bp(
        self,
        address_or_name: WhereType,
        callback: Optional[Callable] = None,
        condition: Optional[str] = None,
        guarded: bool = False,
        description: Optional[str] = None,
        **options,
    ) -> HildaBreakpoint:
        """
        Add a breakpoint

        Alias of self.breakpoints.add()

        :param address_or_name: Where to place the breakpoint
        :param condition: set as a conditional breakpoint using lldb expression
        :param callback: callback(hilda, *args) to be called
        :param guarded: whether the breakpoint should be protected frm usual removal.
        :param description: Attach a breakpoint description
        :param options: can contain an `override` keyword to specify if to override an existing BP
        :return: native LLDB breakpoint
        """
        return self.breakpoints.add(address_or_name, callback, condition, guarded, description=description, **options)

    def po(self, expression: str, cast: Optional[str] = None) -> str:
        """
        Print given object using LLDB's po command

        Can also run big chunks of native code:

        po('NSMutableString *s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')

        :param expression: either a symbol or string the execute
        :param cast: object type
        :raise EvaluatingExpressionError: LLDB failed to evaluate the expression
        :return: LLDB's po output
        """
        casted_expression = ""
        if cast is not None:
            casted_expression += f"({cast})"
        casted_expression += f"0x{expression:x}" if isinstance(expression, int) else str(expression)

        res = lldb.SBCommandReturnObject()
        self.debugger.GetCommandInterpreter().HandleCommand(f"expression -i 0 -lobjc -O -- {casted_expression}", res)
        if not res.Succeeded():
            raise EvaluatingExpressionError(res.GetError())
        return res.GetOutput().strip()

    def globalize_symbols(self) -> None:
        """
        Make all symbols in python's global scope
        """
        reserved_names = list(globals().keys()) + dir(builtins)
        for name, value in tqdm(self.symbols.items()):
            if ":" not in name and "[" not in name and "<" not in name and "(" not in name and "." not in name:
                self._add_global(name, value, reserved_names)

    def jump(self, symbol: int) -> None:
        """jump to given symbol"""
        self.lldb_handle_command(f"j *{symbol}")

    def lldb_handle_command(self, cmd: str, capture_output: bool = False) -> Optional[str]:
        """
        Execute an LLDB command

        For example:
            lldb_handle_command('register read')

        :param cmd: LLDB command
        :param capture_output: True if capturing the command output
        :return: The output if capture was requested, None if not or the command failed
        """
        if capture_output:
            result = lldb.SBCommandReturnObject()
            self.debugger.GetCommandInterpreter().HandleCommand(cmd, result)
            return result.GetOutput() if result.Succeeded() else None
        else:
            self.debugger.HandleCommand(cmd)

    def objc_get_class(self, name: str, module_name: Optional[str] = None) -> objective_c_class.Class:
        """
        Get ObjC class object
        :param module_name:
        :param name:
        :return:
        """
        if module_name is not None:
            ret = self.symbol(self._get_module_class_list(module_name)[name]).objc_class
        else:
            ret = objective_c_class.Class.from_class_name(self, name)
        return ret

    def CFSTR(self, symbol: int) -> Symbol:
        """Create CFStringRef object from given string"""
        return self.cf(symbol)

    def cf(self, data: CfSerializable) -> Symbol:
        """
        Create NSObject from given data (same as ns())
        :param data: Data representing the NSObject, must by JSON serializable
        :return: Pointer to a NSObject
        """
        return self.ns(data)

    def ns(self, data: CfSerializable) -> Symbol:
        """
        Create NSObject from given data (same as cf())
        :param data: Data representing the NSObject, must by JSON serializable
        :return: Pointer to a NSObject
        """
        try:
            json_data = json.dumps({"root": data}, default=self._to_ns_json_default)
        except TypeError as e:
            raise ConvertingToNsObjectError from e
        obj_c_code = (self._hilda_root / "objective_c" / "to_ns_from_json.m").read_text()
        expression = obj_c_code.replace("__json_object_dump__", json_data.replace('"', r"\""))
        try:
            return self.evaluate_expression(expression)
        except EvaluatingExpressionError as e:
            raise ConvertingToNsObjectError from e

    def decode_cf(self, address: Union[int, str]) -> CfSerializable:
        """
        Create python object from NS object.
        :param address: NS object.
        :return: Python object.
        """
        obj_c_code = (self._hilda_root / "objective_c" / "from_ns_to_json.m").read_text()
        address = f"0x{address:x}" if isinstance(address, int) else address
        expression = obj_c_code.replace("__ns_object_address__", address)
        try:
            json_dump = self.po(expression)
        except EvaluatingExpressionError as e:
            raise ConvertingFromNSObjectError from e
        return json.loads(json_dump, object_hook=self._from_ns_json_object_hook)["root"]

    def evaluate_expression(self, expression: str) -> Union[float, Symbol]:
        """
        Wrapper for LLDB's EvaluateExpression.
        Used for quick code snippets.

        Feel free to use local variables inside the expression using format string.
        For example:
            currentDevice = objc_get_class('UIDevice').currentDevice
            evaluate_expression(f'[[{currentDevice} systemName] hasPrefix:@"2"]')

        :param expression: Expression to evaluate
        :return: Returned value (either float or a Symbol)
        """
        # prepending a prefix so LLDB knows to return an int type
        formatted_expression = f"(intptr_t)0x{expression:x}" if isinstance(expression, int) else str(expression)

        options = lldb.SBExpressionOptions()
        options.SetIgnoreBreakpoints(self.configs.evaluation_ignore_breakpoints)
        options.SetTryAllThreads(True)
        options.SetUnwindOnError(self.configs.evaluation_unwind_on_error)

        sbvalue = self.frame.EvaluateExpression(formatted_expression, options)

        if not sbvalue.error.Success():
            raise EvaluatingExpressionError(str(sbvalue.error))

        return self._get_symbol_or_float_from_sbvalue(sbvalue)

    def import_module(self, filename: str, name: Optional[str] = None) -> Any:
        """
        Import & reload given python module (intended mainly for external snippets)
        :param filename: Python filename to import
        :param name: Optional module name, or otherwise use the filename
        :return: Python module
        """
        filename = os.path.expanduser(filename)
        if name is None:
            name = os.path.splitext(os.path.basename(filename))[0]
        spec = importlib.util.spec_from_file_location(name, filename)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def set_selected_thread(self, idx: Optional[int] = None) -> None:
        if idx is None:
            thread = selection_prompt(self.process.threads)
        else:
            try:
                thread = next(t for t in self.process.threads if t.idx == idx)
            except IndexError as e:
                raise InvalidThreadIndexError() from e
        self.process.SetSelectedThread(thread)

    def unwind(self) -> bool:
        """Unwind the stack (useful when get_evaluation_unwind() == False)"""
        return self.thread.UnwindInnermostExpression().Success()

    @cached_property
    def pid(self) -> int:
        return self.process.GetProcessID()

    @property
    def thread(self):
        """Current active thread."""
        if self._bp_frame is not None:
            return self._bp_frame.GetThread()
        return self.process.GetSelectedThread()

    @property
    def frame(self):
        """Current active frame."""
        if self._bp_frame is not None:
            return self._bp_frame
        return self.thread.GetSelectedFrame()

    @contextmanager
    def stopped(self, interval: int = 0):
        """
        Context-Manager for execution while process is stopped.
        If interval is supplied, then if the device is in running state, it will sleep for the interval
        given before and after execution.
        """
        is_running = self.process.GetState() == lldb.eStateRunning

        if is_running:
            self.stop()
            time.sleep(interval)

        try:
            yield
        finally:
            if is_running:
                time.sleep(interval)
                self.cont()

    @contextmanager
    def safe_malloc(self, size: int):
        """
        Context-Manager for allocating a block of memory which is freed afterwards
        :param size:
        :return:
        """
        block = self.symbols.malloc(size)
        if block == 0:
            raise OSError(f"failed to allocate memory of size: {size} bytes")

        try:
            yield block
        finally:
            self.symbols.free(block)

    @contextmanager
    def sync_mode(self):
        """Context-Manager for execution while LLDB is in sync mode."""
        is_async = self.debugger.GetAsync()
        self.debugger.SetAsync(False)
        try:
            yield
        finally:
            self.debugger.SetAsync(is_async)

    def init_dynamic_environment(self):
        """Init session-scoped process dynamic dependencies."""
        self.log_debug("init dynamic environment")
        self._dynamic_env_loaded = True

        self.log_debug("disable mach_msg receive errors")
        try:
            CFRunLoopServiceMachPort_hooks.disable_mach_msg_errors()
        except SymbolAbsentError:
            self.log_warning("failed to disable mach_msg errors")

        objc_code = """
        @import ObjectiveC;
        @import Foundation;
        """
        with suppress(EvaluatingExpressionError):
            # First time is expected to fail - bug in LLDB?
            self.po(objc_code)

    def log_warning(self, message):
        """Log at warning level"""
        self.logger.warning(message)

    def log_debug(self, message):
        """Log at debug level"""
        self.logger.debug(message)

    def log_error(self, message):
        """Log at error level"""
        self.logger.error(message)

    def log_critical(self, message):
        """Log at critical level"""
        self.logger.critical(message)
        raise HildaException(message)

    def log_info(self, message):
        """Log at info level"""
        self.logger.info(message)

    def wait_for_module(self, expression: str) -> None:
        """Wait for a module to be loaded using `dlopen` by matching given expression"""
        self.log_info(f'Waiting for module name containing "{expression}" to be loaded')

        def bp(client: HildaClient, frame, bp_loc, options) -> None:
            loading_module_name = client.evaluate_expression("$arg1").peek_str()
            client.log_info(f"Loading module: {loading_module_name}")
            if expression not in loading_module_name:
                client.cont()
                return
            client.finish()
            client.log_info(f"Desired module has been loaded: {expression}. Process remains stopped")
            bp_id = bp_loc.GetBreakpoint().GetID()
            client.breakpoints.remove(bp_id)

        self.bp("dlopen", bp)
        self.cont()

    def show_help(self, *_) -> None:
        """
        Show banner help message
        """
        help_snippets = [HelpSnippet(key="p", description="Global to access all features")]
        for keybinding in get_keybindings(self):
            help_snippets.append(HelpSnippet(key=keybinding.key.upper(), description=keybinding.description))

        for help_snippet in help_snippets:
            click.echo(help_snippet)

    def interact(
        self, additional_namespace: Optional[typing.Mapping] = None, startup_files: Optional[list[str]] = None
    ) -> None:
        """Start an interactive Hilda shell"""
        if not self._dynamic_env_loaded:
            self.init_dynamic_environment()

        # Show greeting
        click.secho("Hilda has been successfully loaded! 😎", bold=True)
        click.secho("Usage:", bold=True)
        self.show_help()
        click.echo(click.style("Have a nice flight ✈️! Starting an IPython shell...", bold=True))

        # Configure and start IPython shell
        ipython_config = Config()
        ipython_config.IPCompleter.use_jedi = False
        ipython_config.BaseIPythonApplication.profile = "hilda"
        ipython_config.InteractiveShellApp.extensions = [
            "hilda.ipython_extensions.magics",
            "hilda.ipython_extensions.events",
            "hilda.ipython_extensions.keybindings",
        ]
        ipython_config.InteractiveShellApp.exec_lines = ["disable_logs()"]
        if startup_files is not None:
            ipython_config.InteractiveShellApp.exec_files = startup_files
            self.log_debug(f"Startup files - {startup_files}")

        namespace = self.globals
        namespace["p"] = self
        namespace["ui"] = self.ui_manager
        namespace["cfg"] = self.configs
        if additional_namespace is not None:
            namespace.update(additional_namespace)
        sys.argv = ["a"]
        IPython.start_ipython(config=ipython_config, user_ns=namespace)

    def toggle_enable_stdout_stderr(self, *args) -> None:
        self.configs.enable_stdout_stderr = not self.configs.enable_stdout_stderr
        self.logger.info(f"Changed stdout and stderr status to: {self.configs.enable_stdout_stderr}")

    def __enter__(self) -> "HildaClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.detach()

    def _add_global(self, name: str, value: Any, reserved_names=None) -> None:
        if reserved_names is None or name not in reserved_names:
            # don't override existing symbols
            self.globals[name] = value

    @staticmethod
    def _get_saved_state_filename():
        return "/tmp/cache.hilda"

    @staticmethod
    def _to_ns_json_default(obj):
        if isinstance(obj, bytes):
            return f"__hilda_magic_key__|NSData|{base64.b64encode(obj).decode()}"
        elif isinstance(obj, datetime):
            return f"__hilda_magic_key__|NSDate|{obj.timestamp()}"
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
        if not isinstance(obj, str) or not obj.startswith("__hilda_magic_key__"):
            return obj
        _, type_, data = obj.split("|")
        if type_ == "NSData":
            return base64.b64decode(data)
        if type_ == "NSDictionary":
            return tuple(json.loads(data, object_hook=HildaClient._from_ns_json_object_hook).items())
        if type_ == "NSArray":
            return tuple(json.loads(data, object_hook=HildaClient._from_ns_json_object_hook))
        if type_ == "NSNumber":
            return eval(data)
        if type_ == "NSNull":
            return None
        if type_ == "NSDate":
            return datetime.fromtimestamp(eval(data), timezone.utc)

    def _serialize_call_params(self, argv):
        args_conv = []
        for arg in argv:
            if isinstance(arg, (str, bytes)):
                if isinstance(arg, str):
                    arg = arg.encode()
                arg = "".join([f"\\x{b:02x}" for b in arg])
                args_conv.append(f'(intptr_t)"{arg}"')
            elif isinstance(arg, (int, Symbol)):
                arg = int(arg) & 0xFFFFFFFFFFFFFFFF
                args_conv.append(f"0x{arg:x}")
            else:
                raise NotImplementedError(f"cannot serialize argument of type: {type(arg)}")
        return args_conv

    def _generate_call_expression(self, address, params):
        args_type = ",".join(["intptr_t"] * len(params))
        args_conv = ",".join(params)

        if self.arch == "arm64e":
            address = f"ptrauth_sign_unauthenticated((void *){address}, ptrauth_key_asia, 0)"

        return f"((intptr_t(*)({args_type}))({address}))({args_conv})"

    @staticmethod
    def _std_string(value: Symbol) -> str:
        if struct.unpack("b", (value + 23).peek(1))[0] >= 0:
            return value.peek_str()
        else:
            return value[0].peek_str()

    @cached_property
    def _object_identifier(self) -> Symbol:
        return (
            self.symbols
            .objc_getClass("VMUObjectIdentifier")
            .objc_call("alloc")
            .objc_call("initWithTask:", self.symbols.mach_task_self())
        )

    @cached_property
    def _ks(self) -> Optional["Ks"]:
        if not lldb.KEYSTONE_SUPPORT:
            return False
        platforms = {
            "arm64": Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN),
            "arm64e": Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN),
            "x86_64h": Ks(KS_ARCH_X86, KS_MODE_64),
        }
        return platforms.get(self.arch)

    def _get_module_class_list(self, module_name: str):
        for m in self.target.module_iter():
            if module_name != m.file.basename:
                continue
            objc_classlist = m.FindSection("__DATA").FindSubSection("__objc_classlist")
            objc_classlist_addr = self.symbol(objc_classlist.GetLoadAddress(self.target))
            obj_c_code = (self._hilda_root / "objective_c" / "get_objectivec_class_by_module.m").read_text()
            obj_c_code = obj_c_code.replace("__count_objc_class", f"{objc_classlist.size // 8}").replace(
                "__objc_class_list", f"{objc_classlist_addr}"
            )
            return json.loads(self.po(obj_c_code))

    def _get_symbol_or_float_from_sbvalue(self, value: lldb.SBValue) -> Union[float, Symbol]:
        # The `value` attribute of an SBValue stores a string representation of the actual value
        # in a python-compatible format, so we can eval it to get the native python value
        value = eval(value.value)
        if isinstance(value, float):
            return value
        return self.symbol(value)
```

### thread

```
thread
```

Current active thread.

### frame

```
frame
```

Current active frame.

### hd

```
hd(buf: bytes) -> None
```

Print hexdump representation for given buffer.

Parameters:

| Name  | Type    | Description                     | Default    |
| ----- | ------- | ------------------------------- | ---------- |
| `buf` | `bytes` | buffer to print in hexdump form | *required* |

Source code in `hilda/hilda_client.py`

```
def hd(self, buf: bytes) -> None:
    """
    Print hexdump representation for given buffer.

    :param buf: buffer to print in hexdump form
    """
    hexdump.hexdump(buf)
```

### lsof

```
lsof() -> dict[int, Any]
```

Get dictionary of all open FDs

Returns:

| Type             | Description                              |
| ---------------- | ---------------------------------------- |
| `dict[int, Any]` | Mapping between open FDs and their paths |

Source code in `hilda/hilda_client.py`

```
def lsof(self) -> dict[int, Any]:
    """
    Get dictionary of all open FDs
    :return: Mapping between open FDs and their paths
    """
    data = (self._hilda_root / "objective_c" / "lsof.m").read_text()
    result = json.loads(self.po(data))
    # convert FDs into int
    return {int(k): v for k, v in result.items()}
```

### bt

```
bt(should_print: bool = False, depth: Optional[int] = None) -> list[Union[str, lldb.SBFrame]]
```

Get backtrace of the current thread.

Parameters:

| Name           | Type            | Description                                                                                               | Default |
| -------------- | --------------- | --------------------------------------------------------------------------------------------------------- | ------- |
| `should_print` | `bool`          | Whether to print the backtrace to stdout. Please note this backtrace also resolved user imported symbols. | `False` |
| `depth`        | `Optional[int]` | Maximum depth of the backtrace to return                                                                  | `None`  |

Returns:

| Type                        | Description                                                               |
| --------------------------- | ------------------------------------------------------------------------- |
| `list[Union[str, SBFrame]]` | List of backtrace frames, each represented as a tuple of (address, frame) |

Source code in `hilda/hilda_client.py`

```
def bt(self, should_print: bool = False, depth: Optional[int] = None) -> list[Union[str, lldb.SBFrame]]:
    """
    Get backtrace of the current thread.

    :param should_print: Whether to print the backtrace to stdout. Please note this backtrace also resolved user
                         imported symbols.
    :param depth: Maximum depth of the backtrace to return
    :return: List of backtrace frames, each represented as a tuple of (address, frame)
    """
    backtrace = []
    for i, frame in enumerate(self.thread.frames):
        if i == depth:
            break
        row = ""
        row += click.style(f"0x{frame.addr.GetFileAddress():x} ", fg="cyan")
        row += f" frame #{i:02} "
        row += click.style(f"0x{frame.pc:016x} ", fg="yellow")
        row += str(frame.addr)
        if i == 0:
            # first line
            row += " 👈"
        backtrace.append([f"0x{frame.addr.file_addr:016x}", frame])
        if should_print:
            print(row)
    return backtrace
```

### disable_jetsam_memory_checks

```
disable_jetsam_memory_checks()
```

Disable jetsam memory checks, prevent raising: `error: Execution was interrupted, reason: EXC_RESOURCE RESOURCE_TYPE_MEMORY (limit=15 MB, unused=0x0).` when evaluating expression.

Source code in `hilda/hilda_client.py`

```
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
```

### symbol

```
symbol(address: int) -> Symbol
```

Get symbol object for a given address

Parameters:

| Name      | Type  | Description | Default    |
| --------- | ----- | ----------- | ---------- |
| `address` | `int` |             | *required* |

Returns:

| Type     | Description           |
| -------- | --------------------- |
| `Symbol` | Hilda's symbol object |

Source code in `hilda/hilda_client.py`

```
def symbol(self, address: int) -> Symbol:
    """
    Get symbol object for a given address
    :param address:
    :return: Hilda's symbol object
    """
    return self.symbols.add(address)
```

### objc_symbol

```
objc_symbol(address: int) -> ObjectiveCSymbol
```

Get objc symbol wrapper for given address

Parameters:

| Name      | Type  | Description | Default    |
| --------- | ----- | ----------- | ---------- |
| `address` | `int` |             | *required* |

Returns:

| Type               | Description                |
| ------------------ | -------------------------- |
| `ObjectiveCSymbol` | Hilda's objc symbol object |

Source code in `hilda/hilda_client.py`

```
def objc_symbol(self, address: int) -> ObjectiveCSymbol:
    """
    Get objc symbol wrapper for given address
    :param address:
    :return: Hilda's objc symbol object
    """
    try:
        return ObjectiveCSymbol.create(int(address), self)
    except HildaException as e:
        raise CreatingObjectiveCSymbolError from e
```

### inject

```
inject(filename: str) -> SymbolList
```

Inject a single library into currently running process.

Parameters:

| Name       | Type  | Description               | Default    |
| ---------- | ----- | ------------------------- | ---------- |
| `filename` | `str` | library to inject (dylib) | *required* |

Returns:

| Type         | Description |
| ------------ | ----------- |
| `SymbolList` | SymbolList  |

Source code in `hilda/hilda_client.py`

```
def inject(self, filename: str) -> SymbolList:
    """
    Inject a single library into currently running process.

    :param filename: library to inject (dylib)
    :return: SymbolList
    """
    module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
    if module.file.basename is not None:
        self.log_warning(f"file {filename} has already been loaded")

    injected = SymbolList(self)
    handle = self.symbols.dlopen(filename, 10)  # RTLD_GLOBAL|RTLD_NOW

    if handle == 0:
        self.log_critical(f"failed to inject: {filename}")

    module = self.target.FindModule(lldb.SBFileSpec(os.path.basename(filename), False))
    for symbol in module.symbols:
        load_addr = symbol.addr.GetLoadAddress(self.target)
        if load_addr == 0xFFFFFFFFFFFFFFFF:
            # skip those not having a real address
            continue

        name = symbol.name
        type_ = symbol.GetType()

        if name in ("<redacted>",) or (
            type_ not in (lldb.eSymbolTypeCode, lldb.eSymbolTypeData, lldb.eSymbolTypeObjCMetaClass)
        ):
            # ignore unnamed symbols and those which are not: data, code or objc classes
            continue

        injected.add(self.symbol(load_addr), name)
    return injected
```

### poke

```
poke(address, buf: bytes)
```

Write data at given address

Parameters:

| Name      | Type    | Description | Default    |
| --------- | ------- | ----------- | ---------- |
| `address` |         |             | *required* |
| `buf`     | `bytes` |             | *required* |

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
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
```

### poke_text

```
poke_text(address: int, code: str) -> int
```

Write instructions to address.

Parameters:

| Name      | Type  | Description | Default    |
| --------- | ----- | ----------- | ---------- |
| `address` | `int` |             | *required* |
| `code`    | `str` |             | *required* |

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def poke_text(self, address: int, code: str) -> int:
    """
    Write instructions to address.
    :param address:
    :param code:
    """
    if not lldb.KEYSTONE_SUPPORT:
        raise NotImplementedError("Not supported without keystone")
    bytecode, _count = self._ks.asm(code, as_bytes=True)
    return self.poke(address, bytecode)
```

### peek

```
peek(address, size: int) -> bytes
```

Read data at given address

Parameters:

| Name      | Type  | Description | Default    |
| --------- | ----- | ----------- | ---------- |
| `address` |       |             | *required* |
| `size`    | `int` |             | *required* |

Returns:

| Type    | Description |
| ------- | ----------- |
| `bytes` |             |

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def peek(self, address, size: int) -> bytes:
    """
    Read data at given address
    :param address:
    :param size:
    :return:
    """
    if size == 0:
        return b""

    err = lldb.SBError()
    retval = self.process.ReadMemory(address, int(size), err)

    if not err.Success():
        raise AccessingMemoryError()

    return retval
```

### peek_str

```
peek_str(address: Symbol) -> str
```

Peek a buffer till null termination

Parameters:

| Name      | Type     | Description | Default    |
| --------- | -------- | ----------- | ---------- |
| `address` | `Symbol` |             | *required* |

Returns:

| Type  | Description |
| ----- | ----------- |
| `str` |             |

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def peek_str(self, address: Symbol) -> str:
    """
    Peek a buffer till null termination
    :param address:
    :return:
    """
    size = 0x100
    while True:
        err = lldb.SBError()
        result = self.process.ReadCStringFromMemory(address, size, err)
        if not err.Success():
            raise AccessingMemoryError()
        # a shorter result means the null terminator was found within the buffer
        if len(result) < size - 1:
            return result
        size *= 2
```

### peek_std_str

```
peek_std_str(address: Symbol) -> str
```

Peek a std::string

Parameters:

| Name      | Type     | Description                          | Default    |
| --------- | -------- | ------------------------------------ | ---------- |
| `address` | `Symbol` | Address to read the std::string from | *required* |

Returns:

| Type  | Description   |
| ----- | ------------- |
| `str` | Python string |

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def peek_std_str(self, address: Symbol) -> str:
    """
    Peek a std::string
    :param address: Address to read the std::string from
    :return: Python string
    """
    return self._std_string(address)
```

### stop

```
stop(*args) -> None
```

Stop process.

Source code in `hilda/hilda_client.py`

```
def stop(self, *args) -> None:
    """Stop process."""
    self.debugger.SetAsync(False)

    is_running = self.process.GetState() == lldb.eStateRunning
    if not is_running:
        self.log_debug("already stopped")
        return

    if not self.process.Stop().Success():
        self.log_critical("failed to stop process")
```

### run_for

```
run_for(seconds: float) -> None
```

Run the process for a given time

Returns:

| Type   | Description |
| ------ | ----------- |
| `None` |             |

Source code in `hilda/hilda_client.py`

```
def run_for(self, seconds: float) -> None:
    """
    Run the process for a given time
    :return:
    """
    self.cont()
    self.logger.info(f"Running for {seconds} seconds")
    time.sleep(seconds)
    self.stop()
```

### cont

```
cont(*args) -> None
```

Continue process.

Source code in `hilda/hilda_client.py`

```
def cont(self, *args) -> None:
    """Continue process."""
    is_running = self.process.GetState() == lldb.eStateRunning

    if is_running:
        self.log_debug("already running")
        return

    # bugfix:   the debugger may become in sync state, so we make sure
    #           it isn't before trying to continue
    self.debugger.SetAsync(True)

    if not self.process.Continue().Success():
        self.log_critical("failed to continue process")
```

### detach

```
detach() -> None
```

Detach from process.

Useful in order to exit gracefully so process doesn't get killed while you exit

Source code in `hilda/hilda_client.py`

```
def detach(self) -> None:
    """
    Detach from process.

    Useful in order to exit gracefully so process doesn't get killed
    while you exit
    """
    if not self.process.is_alive:
        return
    if not self.process.Detach().Success():
        self.log_critical("failed to detach")
        return
    self.log_info("Process Detached")
```

### disass

```
disass(address: int, buf: bytes, flavor: str = 'intel', should_print: bool = False) -> lldb.SBInstructionList
```

Print disassembly from a given address

Parameters:

| Name           | Type    | Description | Default    |
| -------------- | ------- | ----------- | ---------- |
| `flavor`       | `str`   |             | `'intel'`  |
| `address`      | `int`   |             | *required* |
| `buf`          | `bytes` |             | *required* |
| `should_print` | `bool`  |             | `False`    |

Returns:

| Type                | Description |
| ------------------- | ----------- |
| `SBInstructionList` |             |

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def disass(
    self, address: int, buf: bytes, flavor: str = "intel", should_print: bool = False
) -> lldb.SBInstructionList:
    """
    Print disassembly from a given address
    :param flavor:
    :param address:
    :param buf:
    :param should_print:
    :return:
    """
    inst = self.target.GetInstructionsWithFlavor(lldb.SBAddress(address, self.target), flavor, buf)
    if should_print:
        print(inst)
    return inst
```

### file_symbol

```
file_symbol(address: int, module_name: Optional[str] = None) -> Symbol
```

Calculate symbol address without ASLR

Parameters:

| Name          | Type            | Description                                 | Default    |
| ------------- | --------------- | ------------------------------------------- | ---------- |
| `address`     | `int`           | address as can be seen originally in Mach-O | *required* |
| `module_name` | `Optional[str]` | Module name to resolve the symbol from      | `None`     |

Source code in `hilda/hilda_client.py`

```
def file_symbol(self, address: int, module_name: Optional[str] = None) -> Symbol:
    """
    Calculate symbol address without ASLR
    :param address: address as can be seen originally in Mach-O
    :param module_name: Module name to resolve the symbol from
    """
    module = self.target if module_name is None else self.target.FindModule(lldb.SBFileSpec(module_name))

    return self.symbol(module.ResolveFileAddress(address).GetLoadAddress(self.target))
```

### get_register

```
get_register(name: str) -> Union[float, Symbol]
```

Get value for register by its name. Value can either be an Symbol (int) or a float.

Parameters:

| Name   | Type  | Description   | Default    |
| ------ | ----- | ------------- | ---------- |
| `name` | `str` | Register name | *required* |

Returns:

| Type                   | Description    |
| ---------------------- | -------------- |
| `Union[float, Symbol]` | Register value |

Source code in `hilda/hilda_client.py`

```
def get_register(self, name: str) -> Union[float, Symbol]:
    """
    Get value for register by its name. Value can either be an Symbol (int) or a float.

    :param name: Register name
    :return: Register value
    """
    register_value = self.frame.register[name.lower()]
    if register_value is None:
        raise AccessingRegisterError()
    return self._get_symbol_or_float_from_sbvalue(register_value)
```

### set_register

```
set_register(name: str, value: Union[float, int]) -> None
```

Set value for register by its name.

Parameters:

| Name    | Type                | Description    | Default    |
| ------- | ------------------- | -------------- | ---------- |
| `name`  | `str`               | Register name  | *required* |
| `value` | `Union[float, int]` | Register value | *required* |

Source code in `hilda/hilda_client.py`

```
def set_register(self, name: str, value: Union[float, int]) -> None:
    """
    Set value for register by its name.

    :param name: Register name
    :param value: Register value
    """
    register = self.frame.register[name.lower()]
    if register is None:
        raise AccessingRegisterError()
    if isinstance(value, int):
        register.value = hex(value)
    else:
        register.value = str(value)
```

### objc_call

```
objc_call(obj: int, selector: str, *params)
```

Simulate a call to an objc selector.

Parameters:

| Name       | Type  | Description                                           | Default    |
| ---------- | ----- | ----------------------------------------------------- | ---------- |
| `obj`      | `int` | obj to pass into objc_msgSend                         | *required* |
| `selector` | `str` | selector to execute                                   | *required* |
| `params`   |       | any other additional parameters the selector requires | `()`       |

Returns:

| Type | Description               |
| ---- | ------------------------- |
|      | invocation returned value |

Source code in `hilda/hilda_client.py`

```
def objc_call(self, obj: int, selector: str, *params):
    """
    Simulate a call to an objc selector.

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
```

### call

```
call(address, argv: Optional[list] = None)
```

Call function at given address with given parameters

Parameters:

| Name      | Type             | Description    | Default    |
| --------- | ---------------- | -------------- | ---------- |
| `address` |                  |                | *required* |
| `argv`    | `Optional[list]` | parameter list | `None`     |

Returns:

| Type | Description             |
| ---- | ----------------------- |
|      | function's return value |

Source code in `hilda/hilda_client.py`

```
def call(self, address, argv: Optional[list] = None):
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
```

### monitor

```
monitor(address, condition: Optional[str] = None, **options) -> HildaBreakpoint
```

Monitor every time a given address is called

Alias of self.breakpoints.add_monitor()

Source code in `hilda/hilda_client.py`

```
def monitor(self, address, condition: Optional[str] = None, **options) -> HildaBreakpoint:
    """
    Monitor every time a given address is called

    Alias of self.breakpoints.add_monitor()
    """
    return self.breakpoints.add_monitor(address, condition, **options)
```

### show_current_source

```
show_current_source() -> None
```

print current source code if possible

Source code in `hilda/hilda_client.py`

```
def show_current_source(self) -> None:
    """print current source code if possible"""
    self.lldb_handle_command("f")
```

### finish

```
finish()
```

Run current frame till its end.

Source code in `hilda/hilda_client.py`

```
def finish(self):
    """Run current frame till its end."""
    with self.sync_mode():
        self.thread.StepOutOfFrame(self.frame)
        self._bp_frame = None
```

### step_into

```
step_into(*args)
```

Step into current instruction.

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def step_into(self, *args):
    """Step into current instruction."""
    with self.sync_mode():
        self.thread.StepInto()
    if self.ui_manager.active:
        self.ui_manager.show()
```

### step_over

```
step_over(*args)
```

Step over current instruction.

Source code in `hilda/hilda_client.py`

```
@stop_is_needed
def step_over(self, *args):
    """Step over current instruction."""
    with self.sync_mode():
        self.thread.StepOver()
    if self.ui_manager.active:
        self.ui_manager.show()
```

### force_return

```
force_return(value: int = 0) -> None
```

Prematurely return from a stack frame, short-circuiting exection of newer frames and optionally yielding a specified value.

Parameters:

| Name    | Type  | Description | Default |
| ------- | ----- | ----------- | ------- |
| `value` | `int` |             | `0`     |

Returns:

| Type   | Description |
| ------ | ----------- |
| `None` |             |

Source code in `hilda/hilda_client.py`

```
def force_return(self, value: int = 0) -> None:
    """
    Prematurely return from a stack frame, short-circuiting exection of newer frames and optionally
    yielding a specified value.
    :param value:
    :return:
    """
    self.finish()
    self.set_register("x0", value)
```

### proc_info

```
proc_info() -> None
```

Print information about currently running mapped process.

Source code in `hilda/hilda_client.py`

```
def proc_info(self) -> None:
    """Print information about currently running mapped process."""
    print(self.process)
```

### print_proc_entitlements

```
print_proc_entitlements() -> None
```

Get the plist embedded inside the process' \_\_LINKEDIT section.

Source code in `hilda/hilda_client.py`

```
def print_proc_entitlements(self) -> None:
    """Get the plist embedded inside the process' __LINKEDIT section."""
    linkedit_section = self.target.modules[0].FindSection("__LINKEDIT")
    linkedit_data = self.symbol(linkedit_section.GetLoadAddress(self.target)).peek(linkedit_section.size)

    # just look for the xml start inside the __LINKEDIT section. should be good enough since wer'e not
    # expecting any other XML there
    entitlements = str(linkedit_data[linkedit_data.find(b"<?xml") :].split(b"\xfa", 1)[0], "utf8")
    print(highlight(entitlements, XmlLexer(), TerminalTrueColorFormatter()))
```

### bp

```
bp(address_or_name: WhereType, callback: Optional[Callable] = None, condition: Optional[str] = None, guarded: bool = False, description: Optional[str] = None, **options) -> HildaBreakpoint
```

Add a breakpoint

Alias of self.breakpoints.add()

Parameters:

| Name              | Type                 | Description                                                              | Default    |
| ----------------- | -------------------- | ------------------------------------------------------------------------ | ---------- |
| `address_or_name` | `WhereType`          | Where to place the breakpoint                                            | *required* |
| `condition`       | `Optional[str]`      | set as a conditional breakpoint using lldb expression                    | `None`     |
| `callback`        | `Optional[Callable]` | callback(hilda, \*args) to be called                                     | `None`     |
| `guarded`         | `bool`               | whether the breakpoint should be protected frm usual removal.            | `False`    |
| `description`     | `Optional[str]`      | Attach a breakpoint description                                          | `None`     |
| `options`         |                      | can contain an override keyword to specify if to override an existing BP | `{}`       |

Returns:

| Type              | Description            |
| ----------------- | ---------------------- |
| `HildaBreakpoint` | native LLDB breakpoint |

Source code in `hilda/hilda_client.py`

```
def bp(
    self,
    address_or_name: WhereType,
    callback: Optional[Callable] = None,
    condition: Optional[str] = None,
    guarded: bool = False,
    description: Optional[str] = None,
    **options,
) -> HildaBreakpoint:
    """
    Add a breakpoint

    Alias of self.breakpoints.add()

    :param address_or_name: Where to place the breakpoint
    :param condition: set as a conditional breakpoint using lldb expression
    :param callback: callback(hilda, *args) to be called
    :param guarded: whether the breakpoint should be protected frm usual removal.
    :param description: Attach a breakpoint description
    :param options: can contain an `override` keyword to specify if to override an existing BP
    :return: native LLDB breakpoint
    """
    return self.breakpoints.add(address_or_name, callback, condition, guarded, description=description, **options)
```

### po

```
po(expression: str, cast: Optional[str] = None) -> str
```

Print given object using LLDB's po command

Can also run big chunks of native code:

po('NSMutableString \*s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')

Parameters:

| Name         | Type            | Description                           | Default    |
| ------------ | --------------- | ------------------------------------- | ---------- |
| `expression` | `str`           | either a symbol or string the execute | *required* |
| `cast`       | `Optional[str]` | object type                           | `None`     |

Returns:

| Type  | Description      |
| ----- | ---------------- |
| `str` | LLDB's po output |

Raises:

| Type                        | Description                            |
| --------------------------- | -------------------------------------- |
| `EvaluatingExpressionError` | LLDB failed to evaluate the expression |

Source code in `hilda/hilda_client.py`

```
def po(self, expression: str, cast: Optional[str] = None) -> str:
    """
    Print given object using LLDB's po command

    Can also run big chunks of native code:

    po('NSMutableString *s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')

    :param expression: either a symbol or string the execute
    :param cast: object type
    :raise EvaluatingExpressionError: LLDB failed to evaluate the expression
    :return: LLDB's po output
    """
    casted_expression = ""
    if cast is not None:
        casted_expression += f"({cast})"
    casted_expression += f"0x{expression:x}" if isinstance(expression, int) else str(expression)

    res = lldb.SBCommandReturnObject()
    self.debugger.GetCommandInterpreter().HandleCommand(f"expression -i 0 -lobjc -O -- {casted_expression}", res)
    if not res.Succeeded():
        raise EvaluatingExpressionError(res.GetError())
    return res.GetOutput().strip()
```

### globalize_symbols

```
globalize_symbols() -> None
```

Make all symbols in python's global scope

Source code in `hilda/hilda_client.py`

```
def globalize_symbols(self) -> None:
    """
    Make all symbols in python's global scope
    """
    reserved_names = list(globals().keys()) + dir(builtins)
    for name, value in tqdm(self.symbols.items()):
        if ":" not in name and "[" not in name and "<" not in name and "(" not in name and "." not in name:
            self._add_global(name, value, reserved_names)
```

### jump

```
jump(symbol: int) -> None
```

jump to given symbol

Source code in `hilda/hilda_client.py`

```
def jump(self, symbol: int) -> None:
    """jump to given symbol"""
    self.lldb_handle_command(f"j *{symbol}")
```

### lldb_handle_command

```
lldb_handle_command(cmd: str, capture_output: bool = False) -> Optional[str]
```

Execute an LLDB command

For example: lldb_handle_command('register read')

Parameters:

| Name             | Type   | Description                          | Default    |
| ---------------- | ------ | ------------------------------------ | ---------- |
| `cmd`            | `str`  | LLDB command                         | *required* |
| `capture_output` | `bool` | True if capturing the command output | `False`    |

Returns:

| Type            | Description                                                            |
| --------------- | ---------------------------------------------------------------------- |
| `Optional[str]` | The output if capture was requested, None if not or the command failed |

Source code in `hilda/hilda_client.py`

```
def lldb_handle_command(self, cmd: str, capture_output: bool = False) -> Optional[str]:
    """
    Execute an LLDB command

    For example:
        lldb_handle_command('register read')

    :param cmd: LLDB command
    :param capture_output: True if capturing the command output
    :return: The output if capture was requested, None if not or the command failed
    """
    if capture_output:
        result = lldb.SBCommandReturnObject()
        self.debugger.GetCommandInterpreter().HandleCommand(cmd, result)
        return result.GetOutput() if result.Succeeded() else None
    else:
        self.debugger.HandleCommand(cmd)
```

### objc_get_class

```
objc_get_class(name: str, module_name: Optional[str] = None) -> objective_c_class.Class
```

Get ObjC class object

Parameters:

| Name          | Type            | Description | Default    |
| ------------- | --------------- | ----------- | ---------- |
| `module_name` | `Optional[str]` |             | `None`     |
| `name`        | `str`           |             | *required* |

Returns:

| Type    | Description |
| ------- | ----------- |
| `Class` |             |

Source code in `hilda/hilda_client.py`

```
def objc_get_class(self, name: str, module_name: Optional[str] = None) -> objective_c_class.Class:
    """
    Get ObjC class object
    :param module_name:
    :param name:
    :return:
    """
    if module_name is not None:
        ret = self.symbol(self._get_module_class_list(module_name)[name]).objc_class
    else:
        ret = objective_c_class.Class.from_class_name(self, name)
    return ret
```

### CFSTR

```
CFSTR(symbol: int) -> Symbol
```

Create CFStringRef object from given string

Source code in `hilda/hilda_client.py`

```
def CFSTR(self, symbol: int) -> Symbol:
    """Create CFStringRef object from given string"""
    return self.cf(symbol)
```

### cf

```
cf(data: CfSerializable) -> Symbol
```

Create NSObject from given data (same as ns())

Parameters:

| Name   | Type             | Description                                               | Default    |
| ------ | ---------------- | --------------------------------------------------------- | ---------- |
| `data` | `CfSerializable` | Data representing the NSObject, must by JSON serializable | *required* |

Returns:

| Type     | Description           |
| -------- | --------------------- |
| `Symbol` | Pointer to a NSObject |

Source code in `hilda/hilda_client.py`

```
def cf(self, data: CfSerializable) -> Symbol:
    """
    Create NSObject from given data (same as ns())
    :param data: Data representing the NSObject, must by JSON serializable
    :return: Pointer to a NSObject
    """
    return self.ns(data)
```

### ns

```
ns(data: CfSerializable) -> Symbol
```

Create NSObject from given data (same as cf())

Parameters:

| Name   | Type             | Description                                               | Default    |
| ------ | ---------------- | --------------------------------------------------------- | ---------- |
| `data` | `CfSerializable` | Data representing the NSObject, must by JSON serializable | *required* |

Returns:

| Type     | Description           |
| -------- | --------------------- |
| `Symbol` | Pointer to a NSObject |

Source code in `hilda/hilda_client.py`

```
def ns(self, data: CfSerializable) -> Symbol:
    """
    Create NSObject from given data (same as cf())
    :param data: Data representing the NSObject, must by JSON serializable
    :return: Pointer to a NSObject
    """
    try:
        json_data = json.dumps({"root": data}, default=self._to_ns_json_default)
    except TypeError as e:
        raise ConvertingToNsObjectError from e
    obj_c_code = (self._hilda_root / "objective_c" / "to_ns_from_json.m").read_text()
    expression = obj_c_code.replace("__json_object_dump__", json_data.replace('"', r"\""))
    try:
        return self.evaluate_expression(expression)
    except EvaluatingExpressionError as e:
        raise ConvertingToNsObjectError from e
```

### decode_cf

```
decode_cf(address: Union[int, str]) -> CfSerializable
```

Create python object from NS object.

Parameters:

| Name      | Type              | Description | Default    |
| --------- | ----------------- | ----------- | ---------- |
| `address` | `Union[int, str]` | NS object.  | *required* |

Returns:

| Type             | Description    |
| ---------------- | -------------- |
| `CfSerializable` | Python object. |

Source code in `hilda/hilda_client.py`

```
def decode_cf(self, address: Union[int, str]) -> CfSerializable:
    """
    Create python object from NS object.
    :param address: NS object.
    :return: Python object.
    """
    obj_c_code = (self._hilda_root / "objective_c" / "from_ns_to_json.m").read_text()
    address = f"0x{address:x}" if isinstance(address, int) else address
    expression = obj_c_code.replace("__ns_object_address__", address)
    try:
        json_dump = self.po(expression)
    except EvaluatingExpressionError as e:
        raise ConvertingFromNSObjectError from e
    return json.loads(json_dump, object_hook=self._from_ns_json_object_hook)["root"]
```

### evaluate_expression

```
evaluate_expression(expression: str) -> Union[float, Symbol]
```

Wrapper for LLDB's EvaluateExpression. Used for quick code snippets.

Feel free to use local variables inside the expression using format string. For example: currentDevice = objc_get_class('UIDevice').currentDevice evaluate_expression(f'\[[{currentDevice} systemName] hasPrefix:@"2"\]')

Parameters:

| Name         | Type  | Description            | Default    |
| ------------ | ----- | ---------------------- | ---------- |
| `expression` | `str` | Expression to evaluate | *required* |

Returns:

| Type                   | Description                               |
| ---------------------- | ----------------------------------------- |
| `Union[float, Symbol]` | Returned value (either float or a Symbol) |

Source code in `hilda/hilda_client.py`

```
def evaluate_expression(self, expression: str) -> Union[float, Symbol]:
    """
    Wrapper for LLDB's EvaluateExpression.
    Used for quick code snippets.

    Feel free to use local variables inside the expression using format string.
    For example:
        currentDevice = objc_get_class('UIDevice').currentDevice
        evaluate_expression(f'[[{currentDevice} systemName] hasPrefix:@"2"]')

    :param expression: Expression to evaluate
    :return: Returned value (either float or a Symbol)
    """
    # prepending a prefix so LLDB knows to return an int type
    formatted_expression = f"(intptr_t)0x{expression:x}" if isinstance(expression, int) else str(expression)

    options = lldb.SBExpressionOptions()
    options.SetIgnoreBreakpoints(self.configs.evaluation_ignore_breakpoints)
    options.SetTryAllThreads(True)
    options.SetUnwindOnError(self.configs.evaluation_unwind_on_error)

    sbvalue = self.frame.EvaluateExpression(formatted_expression, options)

    if not sbvalue.error.Success():
        raise EvaluatingExpressionError(str(sbvalue.error))

    return self._get_symbol_or_float_from_sbvalue(sbvalue)
```

### import_module

```
import_module(filename: str, name: Optional[str] = None) -> Any
```

Import & reload given python module (intended mainly for external snippets)

Parameters:

| Name       | Type            | Description                                         | Default    |
| ---------- | --------------- | --------------------------------------------------- | ---------- |
| `filename` | `str`           | Python filename to import                           | *required* |
| `name`     | `Optional[str]` | Optional module name, or otherwise use the filename | `None`     |

Returns:

| Type  | Description   |
| ----- | ------------- |
| `Any` | Python module |

Source code in `hilda/hilda_client.py`

```
def import_module(self, filename: str, name: Optional[str] = None) -> Any:
    """
    Import & reload given python module (intended mainly for external snippets)
    :param filename: Python filename to import
    :param name: Optional module name, or otherwise use the filename
    :return: Python module
    """
    filename = os.path.expanduser(filename)
    if name is None:
        name = os.path.splitext(os.path.basename(filename))[0]
    spec = importlib.util.spec_from_file_location(name, filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
```

### unwind

```
unwind() -> bool
```

Unwind the stack (useful when get_evaluation_unwind() == False)

Source code in `hilda/hilda_client.py`

```
def unwind(self) -> bool:
    """Unwind the stack (useful when get_evaluation_unwind() == False)"""
    return self.thread.UnwindInnermostExpression().Success()
```

### stopped

```
stopped(interval: int = 0)
```

Context-Manager for execution while process is stopped. If interval is supplied, then if the device is in running state, it will sleep for the interval given before and after execution.

Source code in `hilda/hilda_client.py`

```
@contextmanager
def stopped(self, interval: int = 0):
    """
    Context-Manager for execution while process is stopped.
    If interval is supplied, then if the device is in running state, it will sleep for the interval
    given before and after execution.
    """
    is_running = self.process.GetState() == lldb.eStateRunning

    if is_running:
        self.stop()
        time.sleep(interval)

    try:
        yield
    finally:
        if is_running:
            time.sleep(interval)
            self.cont()
```

### safe_malloc

```
safe_malloc(size: int)
```

Context-Manager for allocating a block of memory which is freed afterwards

Parameters:

| Name   | Type  | Description | Default    |
| ------ | ----- | ----------- | ---------- |
| `size` | `int` |             | *required* |

Returns:

| Type | Description |
| ---- | ----------- |
|      |             |

Source code in `hilda/hilda_client.py`

```
@contextmanager
def safe_malloc(self, size: int):
    """
    Context-Manager for allocating a block of memory which is freed afterwards
    :param size:
    :return:
    """
    block = self.symbols.malloc(size)
    if block == 0:
        raise OSError(f"failed to allocate memory of size: {size} bytes")

    try:
        yield block
    finally:
        self.symbols.free(block)
```

### sync_mode

```
sync_mode()
```

Context-Manager for execution while LLDB is in sync mode.

Source code in `hilda/hilda_client.py`

```
@contextmanager
def sync_mode(self):
    """Context-Manager for execution while LLDB is in sync mode."""
    is_async = self.debugger.GetAsync()
    self.debugger.SetAsync(False)
    try:
        yield
    finally:
        self.debugger.SetAsync(is_async)
```

### init_dynamic_environment

```
init_dynamic_environment()
```

Init session-scoped process dynamic dependencies.

Source code in `hilda/hilda_client.py`

```
def init_dynamic_environment(self):
    """Init session-scoped process dynamic dependencies."""
    self.log_debug("init dynamic environment")
    self._dynamic_env_loaded = True

    self.log_debug("disable mach_msg receive errors")
    try:
        CFRunLoopServiceMachPort_hooks.disable_mach_msg_errors()
    except SymbolAbsentError:
        self.log_warning("failed to disable mach_msg errors")

    objc_code = """
    @import ObjectiveC;
    @import Foundation;
    """
    with suppress(EvaluatingExpressionError):
        # First time is expected to fail - bug in LLDB?
        self.po(objc_code)
```

### log_warning

```
log_warning(message)
```

Log at warning level

Source code in `hilda/hilda_client.py`

```
def log_warning(self, message):
    """Log at warning level"""
    self.logger.warning(message)
```

### log_debug

```
log_debug(message)
```

Log at debug level

Source code in `hilda/hilda_client.py`

```
def log_debug(self, message):
    """Log at debug level"""
    self.logger.debug(message)
```

### log_error

```
log_error(message)
```

Log at error level

Source code in `hilda/hilda_client.py`

```
def log_error(self, message):
    """Log at error level"""
    self.logger.error(message)
```

### log_critical

```
log_critical(message)
```

Log at critical level

Source code in `hilda/hilda_client.py`

```
def log_critical(self, message):
    """Log at critical level"""
    self.logger.critical(message)
    raise HildaException(message)
```

### log_info

```
log_info(message)
```

Log at info level

Source code in `hilda/hilda_client.py`

```
def log_info(self, message):
    """Log at info level"""
    self.logger.info(message)
```

### wait_for_module

```
wait_for_module(expression: str) -> None
```

Wait for a module to be loaded using `dlopen` by matching given expression

Source code in `hilda/hilda_client.py`

```
def wait_for_module(self, expression: str) -> None:
    """Wait for a module to be loaded using `dlopen` by matching given expression"""
    self.log_info(f'Waiting for module name containing "{expression}" to be loaded')

    def bp(client: HildaClient, frame, bp_loc, options) -> None:
        loading_module_name = client.evaluate_expression("$arg1").peek_str()
        client.log_info(f"Loading module: {loading_module_name}")
        if expression not in loading_module_name:
            client.cont()
            return
        client.finish()
        client.log_info(f"Desired module has been loaded: {expression}. Process remains stopped")
        bp_id = bp_loc.GetBreakpoint().GetID()
        client.breakpoints.remove(bp_id)

    self.bp("dlopen", bp)
    self.cont()
```

### show_help

```
show_help(*_) -> None
```

Show banner help message

Source code in `hilda/hilda_client.py`

```
def show_help(self, *_) -> None:
    """
    Show banner help message
    """
    help_snippets = [HelpSnippet(key="p", description="Global to access all features")]
    for keybinding in get_keybindings(self):
        help_snippets.append(HelpSnippet(key=keybinding.key.upper(), description=keybinding.description))

    for help_snippet in help_snippets:
        click.echo(help_snippet)
```

### interact

```
interact(additional_namespace: Optional[Mapping] = None, startup_files: Optional[list[str]] = None) -> None
```

Start an interactive Hilda shell

Source code in `hilda/hilda_client.py`

```
def interact(
    self, additional_namespace: Optional[typing.Mapping] = None, startup_files: Optional[list[str]] = None
) -> None:
    """Start an interactive Hilda shell"""
    if not self._dynamic_env_loaded:
        self.init_dynamic_environment()

    # Show greeting
    click.secho("Hilda has been successfully loaded! 😎", bold=True)
    click.secho("Usage:", bold=True)
    self.show_help()
    click.echo(click.style("Have a nice flight ✈️! Starting an IPython shell...", bold=True))

    # Configure and start IPython shell
    ipython_config = Config()
    ipython_config.IPCompleter.use_jedi = False
    ipython_config.BaseIPythonApplication.profile = "hilda"
    ipython_config.InteractiveShellApp.extensions = [
        "hilda.ipython_extensions.magics",
        "hilda.ipython_extensions.events",
        "hilda.ipython_extensions.keybindings",
    ]
    ipython_config.InteractiveShellApp.exec_lines = ["disable_logs()"]
    if startup_files is not None:
        ipython_config.InteractiveShellApp.exec_files = startup_files
        self.log_debug(f"Startup files - {startup_files}")

    namespace = self.globals
    namespace["p"] = self
    namespace["ui"] = self.ui_manager
    namespace["cfg"] = self.configs
    if additional_namespace is not None:
        namespace.update(additional_namespace)
    sys.argv = ["a"]
    IPython.start_ipython(config=ipython_config, user_ns=namespace)
```
