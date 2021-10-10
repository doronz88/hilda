- [Hilda](#hilda)
    * [Description](#description)
    * [Example](#example)
    * [Installation](#installation)
    * [How to use](#how-to-use)
        + [Starting Hilda shell](#starting-hilda-shell)
        + [Commands](#commands)
        + [Symbol objects](#symbol-objects)
        + [Globalized symbols](#globalized-symbols)
            - [Searching for the right symbol](#searching-for-the-right-symbol)
        + [Objective-C Classes](#objective-c-classes)
        + [Objective-C Objects](#objective-c-objects)
        + [Using snippets](#using-snippets)

# Hilda

## Description

Hilda is a debugger which combines both the power of LLDB and iPython for easier debugging.

The name originates from the TV show "Hilda", which is the best friend of
[Frida](https://frida.re/). Both Frida and Hilda are meant for pretty much the same purpose, except Hilda takes the
more "
debugger-y" approach (based on LLDB).

Currently, the project is intended for iOS/OSX debugging, but in the future we will possibly add support for the
following platforms as well:

* Linux
* Android

Since LLDB allows abstraction for both platform and architecture, it should be possible to make the necessary changes
without too many modifications.

Pull requests are more than welcome 😊.

If you need help or have an amazing idea you would like to suggest, feel free
to [start a discussion 💬](https://github.com/doronz88/hilda/discussions).

## Example

![](gifs/example.gif)

More examples can be found under the [gifs folder](gifs/).

## Installation

Requirements for remote iOS device (not required for debugging a local OSX process):

* Jailbroken iOS device
* `debugserver` in device's PATH
    * [You can use this tool in order to obtain the binary](https://github.com/doronz88/debugserver-deploy)
    * After re-signing with new entitlements, you can put the binary in the following path: `/usr/bin/debugserver`

In order to install please run:

```shell
xcrun python3 -m pip install --user -U -e .
```

*⚠️ Please note that Hilda is installed on top of XCode's python so LLDB will be able to use its features.*

## How to use

### Starting a Hilda shell

#### Bare mode

Use "Bare mode" to get a "bare-bones" lldb shell, whereas hilda plugin is already loaded and ready to start. This mode
is useful when you need to have custom commands for attaching to the target process (for example when debugging OSX
processes).

To start this mode simply use:

```shell
hilda bare
```

Please refer to the following help page if you require help on the command available to you within the lldb shell:

[lldb command map](https://lldb.llvm.org/use/map.html).

As a cheatsheet, connecting to a remote platform like so:

```shell
platform connect connect://ip:port
```

... and attaching to a local process:

```shell
process attach -n proccess_name
process attach -p proccess_pid
```

When you are ready, just execute `hilda` to move to Hilda's iPython shell.

#### Remote mode

This mode will auto-connect to the remote device and attach to your target process assuming you are trying to debug a
remote jailbroken iOS device.

```shell
hilda remote PROCESS_NAME SSH_PORT
```

Please note the script assumes the target device is running a ssh server. It will try running the following for you:

```shell
ssh -p SSH_PORT root@localhost "debugserver localhost:1234 --attach=PROCESS_NAME &"&
```

For this to work, make sure the connected device doesn't require a password for the connection (you can use
`ssh-copy-id` to achieve this).

### Commands

Commands are just global python functions you can access any time. It's really advised to first get a good overview over
them before start using, so you take full advantage of everything Hilda has to offer.

Given below is a list of them:

```
👾 hd - Print an hexdump of given buffer
👾 lsof - Get dictionary of all open FDs
👾 bt - Print an improved backtrace.
👾 disable_jetsam_memory_checks - Disable jetsam memory checks, prevent raising:
    `error: Execution was interrupted, reason: EXC_RESOURCE RESOURCE_TYPE_MEMORY (limit=15 MB, unused=0x0).`
    when evaluating expression.
👾 symbol - Get symbol object for a given address
👾 objc_symbol - Get objc symbol wrapper for given address
👾 inject - Inject a single library into currently running process
👾 rebind_symbols - Reparse all loaded images symbols
👾 poke - Write data at given address
👾 peek - Read data at given address
👾 peek_str - Peek a buffer till null termination
👾 stop - Stop process.
👾 cont - Continue process.
👾 detach - Detach from process.
    Useful in order to exit gracefully so process doesn't get killed
    while you exit
👾 disass - Print disassembly from a given address
👾 file_symbol - Calculate symbol address without ASLR
👾 get_register - Get value for register by its name
👾 set_register - Set value for register by its name
👾 objc_call - Simulate a call to an objc selector
👾 call - Call function at given address with given parameters
👾 monitor - Monitor every time a given address is called
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
👾 finish - Run current frame till its end.
👾 step_into - Step into current instruction.
👾 step_over - Step over current instruction.
👾 remove_all_hilda_breakpoints - Remove all breakpoints created by Hilda
👾 remove_hilda_breakpoint - Remove a single breakpoint placed by Hilda
👾 force_return - Prematurely return from a stack frame, short-circuiting exection of newer frames and optionally
    yielding a specified value.
👾 proc_info - Print information about currently running mapped process.
👾 print_proc_entitlements - Get the plist embedded inside the process' __LINKEDIT section.
👾 bp - Add a breakpoint
👾 show_hilda_breakpoints - Show existing breakpoints created by Hilda.
👾 show_commands - Show available commands.
👾 save - Save loaded symbols map (for loading later using the load() command)
👾 load - Load an existing symbols map (previously saved by the save() command)
👾 po - Print given object using LLDB's po command
    Can also run big chunks of native code:

    po('NSMutableString *s = [NSMutableString string]; [s appendString:@"abc"]; [s description]')
👾 globalize_symbols - Make all symbols in python's global scope
👾 lldb_handle_command - Execute an LLDB command
    For example:
        lldb_handle_command('register read')
👾 objc_get_class - Get ObjC class object
👾 CFSTR - Create CFStringRef object from given string
👾 ns - Create NSObject from given data
👾 from_ns - Create python object from NS object.
👾 evaluate_expression - Wrapper for LLDB's EvaluateExpression.
    Used for quick code snippets.

    Feel free to use local variables inside the expression using format string.
    For example:
        currentDevice = objc_get_class('UIDevice').currentDevice
        evaluate_expression(f'[[{currentDevice} systemName] hasPrefix:@"2"]')
👾 import_module - Import & reload given python module (intended mainly for external snippets)
```

In order to view them within Hilda, please execute:

```python
show_commands()
```

If you just want help for a specific one... Hmm.. for example the `stop` command, you can just use IPython's
capabilities:

```python
# execute the following to print the command's documentation
stop?
```

### Symbol objects

In Hilda, almost everything is wrapped using the `Symbol` Object. Symbol is just a nicer way for referring to addresses
encapsulated with an object allowing to deref the memory inside, or use these addresses as functions.

In order to create a symbol from a given address, please use:

```python
s = symbol(0x12345678)

# the Symbol object extends `int`
True == isinstance(s, int)

# print print the un-shifted file address 
# (calculating the ASLR shift for you, so you can just view it in IDA)
print(s.file_address)

# or.. if you know the file address, but don't wanna mess
# with ASLR calculations
s = file_symbol(0x12345678)

# peek(/read) 20 bytes of memory
print(s.peek(20))

# write into this memory
s.poke('abc')

# let LLDB print-object (it should guess the type automatically
# based on its memory layout)
print(s.po())

# or you can help LLDB with telling it its type manually
print(s.po('char *'))

# jump to `s` as a function, passing (1, "string") as its args 
s(1, "string")

# change the size of each item_size inside `s` for derefs
s.item_size = 1

# *(char *)s = 1
s[0] = 1

# *(((char *)s)+1) = 1
s[1] = 1

# symbol inherits from int, so all int operations apply
s += 4

# change s item size back to 8 to store pointers
s.item_size = 8

# *(intptr_t *)s = 1
s[0] = 1

# storing the return value of the function executed at `0x11223344`
# into `*s`
s[0] = symbol(0x11223344)()  # calling symbols also returns symbols 

# monitor each time a symbol is called into console and print its backtrace (`bt` option)
# this will create a scripted breakpoint which prints your desired data and continue
s.monitor(bt=True)

# you can also:
#   bt -> view the backtrace
#   regs -> view registers upon each call in your desired format
#   retval -> view the return value upon each call in your desired format
#   cmd -> execute a list of LLDB commands on each hit
s.monitor(regs={'x0': 'x'},  # print `x0` in HEX form
          retval='po',  # use LLDB's `po` for printing the returned value
          bt=True,  # view backtrace (will also resolve ASLR addresses for you)
          cmd=['thread list'],  # show thread list 
          )

# we can also just `force_return` with a hard-coded value to practically disable 
# a specific functionality
s.monitor(force_return=0)  # cause the function to always return `0`

# as for everything, if you need help understanding each such feature, 
# simply execute the following to view its help (many such features even contain examples) 
s.monitor?

# create a scripted_breakpoint manually
def scripted_breakpoint(hilda, *args):
    # like everything in hilda, registers are also
    # just simple `Symbol` objects, so feel free to 
    # use them to your heart's content :)
    if hilda.registers.x0.peek(4) == b'\x11\x22\x33\x44':
        hilda.registers.x0 = hilda.symbols.malloc(200)
        hilda.registers.x0.poke(b'\x22' * 200)

    # just continue the process
    hilda.cont()


s.bp(scripted_breakpoint)
```

### Globalized symbols

Usually you would want/need to use the symbols already mapped into the currently running process. To do so, you can
access them using `symbols.<symbol-name>`. The `symbols` global object is of type `SymbolsJar`, which is a wrapper
to `dict` for accessing all exported symbols. For example, the following will generate a call to the exported
`malloc` function with `20` as its only argument:

```python
x = symbols.malloc(20)
```

You can also just write their name as if they already were in the global scope. Hilda will check if no name collision
exists, and if so, will perform the following lazily for you:

```python
x = malloc(20)

# is equivalent to:
malloc = symbols.malloc
x = malloc(20)
```

#### Searching for the right symbol

Sometimes you don't really know where to start your research. All you have is just theories of how your desired exported
symbol should be called (if any).

For that reason alone, we have the `rebind_symbols()`
command - to help you find the symbol you are looking for.

```python
rebind_symbols()  # this might take some time

# find all symbols prefixed as `mem*` AND don't have `cpy`
# in their name
jar = symbols.startswith('mem') - symbols.find('cpy')

# filter only symbols of type "code" (removing data global for example)
jar = jar.code()

# monitor every time each one is called, print its `x0` in HEX
# form and show the backtrace
jar.monitor(regs={'x0': 'x'}, bt=True)
```

### Objective-C Classes

The same as symbols applies to Objective-C classes name resolution. You can either:

```python
d = NSDictionary.new()  # call its `new` selector

# which is equivalent to:
NSDictionary = objc_get_class('NSDictionary')
d = NSDictionary.new()
```

This is possible only since `NSDictionary` is exported. In case it is not, you must call `objc_get_class()` explicitly.

As you can see, you can directly access all the class' methods.

Please look what more stuff you can do as shown below:

```python
# show the class' ivars
print(NSDictionary.ivars)

# show the class' methods
print(NSDictionary.methods)

# show the class' proprties
print(NSDictionary.properties)

# view class' selectors which are prefixed with 'init'
print(NSDictionary.symbols_jar.startswith('-[NSDictionary init'))

# you can of course use any of `SymbolsJar` over them, for example:
# this will `po` (print object) all those selectors returned value
NSDictionary.symbols_jar.startswith('-[NSDictionary init').monitior(retval='po')

# monitor each time any selector in NSDictionary is called
NSDictionary.monitor()

# `force_return` for some specific selector with a hard-coded value (4)
NSDictionary.get_method('valueForKey:').address.monitor(force_return=4)

# capture the `self` object at the first hit of any selector
# `True` for busy-wait for object to be captured
dictionary = NSDictionary.capture_self(True)

# print a colored and formatted version for class layout
dictionary.show()
```

### Objective-C Objects

In order to work with ObjC objects, each symbol contains a property called
`objc_symbol`. After calling, you can work better with each object:

```python
dict = NSDictionary.new().objc_symbol
dict.show()  # print object layout

# just like class, you can access its ivars, method, etc...
print(dict.ivars)

# except now they have values you can view
print(dict._ivarName)

# or edit
dict._ivarName = value

# and of course you can call the object's methods
# hilda will checks if the method returned an ObjC object:
#   - if so, call `objc_symbol` upon it for you
#   - otherwise, leave it as a simple `Symbol` object
arr = dict.objectForKey_('keyContainingNSArray')

# you can also call class-methods
# hilda will call it using either the instance object,
# or the class object respectively of the use
newDict = dict.dictionary()

# print the retrieved object
print(arr.po())
```

Also, working with Objective-C objects like this can be somewhat exhausting, so we created the `ns` and `from_ns`
commands so you are able to use complicated types when parsing values and passing as arguments:

```python
import datetime

# using the `ns` command we can just pass a python-native dictionary
function_requiring_a_specfic_dictionary(ns({
    'key1': 'string',  # will convert to NSString
    'key2': True,  # will convert to NSNumber
    'key3': b'1234',  # will convert to NSData
    'key4': datetime.datetime(2021, 1, 1)  # will convert to NSDate
}))

# and also parse one
normal_python_dict = from_ns(ns({
    'key1': 'string',  # will convert to NSString
    'key2': True,  # will convert to NSNumber
    'key3': b'1234',  # will convert to NSData
    'key4': datetime.datetime(2021, 1, 1)  # will convert to NSDate
}))
```

On last resort, if the object is not serializable for this to work, you can just run pure Objective-C code:

```python
# let LLDB compile and execute the expression
abc_string = evaluate_expression('[NSString stringWithFormat:@"abc"]')

# will print "abc"
print(abc_string.po())
```

### Using snippets

Snippets are extensions for normal functionality used as quick cookbooks for day-to-day tasks of a debugger.

They all use the following concept to use:

```python
from hilda.snippets import snippet_name

snippet_name.do_domething()  
```

For example, XPC sniffing can be done using:

```python
from hilda.snippets import xpc

xpc.xpc_sniff_all()
```

This will monitor all XPC related traffic in the given process.
 
