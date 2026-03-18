# Hilda Method Set

Upon starting Hilda, you are welcomed into Hilda's IPython shell.
You can access following set of methods via the variable `p`.

Basic flow control:

- `stop` - Stop process
- `cont` - Continue process
- `finish` - Run current function until return
- `step_into` - Step into current instruction
- `step_over` - Step over current instruction
- `run_for` - Run the process for given interval
- `force_return` - Prematurely return from a stack frame, short-circuiting execution of inner
  frames and optionally yielding a specified value
- `jump` - Jump to given symbol
- `wait_for_module` - Wait for a module to be loaded (`dlopen`) by checking if given expression is contained within its filename
- `detach` - Detach from process (useful for exiting gracefully so the
  process doesn't get killed when you exit)

Breakpoints:

- `bp` or `breakpoints.add` - Add a breakpoint
- `breakpoints.show` - Show existing breakpoints
- `breakpoints.remove` - Remove a single breakpoint
- `breakpoints.clear` - Remove all breakpoints
- `monitor` or `breakpoints.add_monitor` - Create a breakpoint whose callback implements the requested features (print register values, execute commands, mock return value, etc.)

Basic read/write:

- `get_register` - Get register value
- `set_register` - Set register value
- `poke` - Write data at address
- `peek[_str,_std_str]` - Read buffer/C-string/`std::string` at address
- `po` - Print object using LLDB's `po` command, or even run arbitrary native code

  ```python
  p.po('NSMutableString *s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')
  ```
- `disass` - Print disassembly at address
- `show_current_source` - Print current source code (if possible)
- `bt` - Get backtrace
- `lsof` - Get all open FDs
- `hd` - Hexdump a buffer
- `proc_info` - Print information about currently running mapped process
- `print_proc_entitlements` - Get the plist embedded inside the process' `__LINKEDIT` section

Execute code:

- `call` - Call function at given address with given parameters
- `objc_call` - Simulate a call to an Objective-C selector
- `inject` - Inject a single library into currently running process
- `disable_jetsam_memory_checks` -
   Disable jetsam memory checks (to prevent raising
   `error: Execution was interrupted, reason: EXC_RESOURCE RESOURCE_TYPE_MEMORY (limit=15 MB, unused=0x0).`
   when evaluating expressions).

Hilda symbols:

- `symbol` - Get symbol object for a given address
- `objc_symbol` - Get Objective-C symbol wrapper for given address
- `file_symbol` - Calculate symbol address without ASLR
- `globalize_symbols` - Make all symbols in python's global scope

Advanced:

- `lldb_handle_command` - Execute an LLDB command (e.g., `p.lldb_handle_command('register read')`)
- `evaluate_expression` - Use for quick code snippets (wrapper for LLDB's `EvaluateExpression`).

  Take advantage of local variables inside the expression using format string, e.g.,

  ```python
  currentDevice = p.objc_get_class('UIDevice').currentDevice
  p.evaluate_expression(f'[[{currentDevice} systemName] hasPrefix:@"2"]')
  ```
- `import_module` - Import & reload given Python module (intended mainly for external snippets)
- `unwind` - Unwind the stack (useful when `get_evaluation_unwind() == False`)
- `set_selected_thread` - Set the currently selected thread, which is used in other parts of the program, such as displaying disassembly or
  checking registers.
  This ensures the application focuses on the specified thread for these operations.

Objective-C related:

- `objc_get_class` - Get Objective-C class object
- `CFSTR` - Create `CFStringRef` object from given string
- `ns` - Create `NSObject` from given data
- `cf` - Alias of `ns`
- `decode_cf` - Create a Python object from an NS object
