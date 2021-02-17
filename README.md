- [Hilda](#hilda)
  * [Description](#description)
  * [Example](#example)
  * [Installation](#installation)
  * [How to use](#how-to-use)
    + [Starting shell](#starting-shell)
    + [Commands](#commands)
    + [Symbol objects](#symbol-objects)
    + [Globalized symbols](#globalized-symbols)
      - [Searching for the right symbol](#searching-for-the-right-symbol)
    + [Objective-C Classes](#objective-c-classes)
    + [Objective-C Objects](#objective-c-objects)
    + [Using snippets](#using-snippets)

# Hilda

## Description

Hilda is a debugger which combines both the power of LLDB and iPython for easier work.

The name originates from the TV show "Hilda", which is the best friend of
[Frida](https://frida.re/). Both Frida and Hilda are meant for pretty much the same purpose, except Hilda takes the more "
debugger-y" approach (based on LLDB).

Currently, the project is intended for iOS debugging, but in the future we will possibly add support for the following
platforms as well:

* OSX
* Linux
* Android

Since LLDB allows abstraction for both platform and architecture, it should be possible to make the necessary changes without
too many modifications.

Pull requests are more than welcome 😊.

## Example

![](gifs/example.gif)

More examples can be found under the [gifs folder](gifs/).

## Installation

Requirements:

* Jailbroken iOS device
* `iproxy` in PATH (`brew install libimobiledevice`)
* `debugserver` in device's PATH
    * [You can use this tool in order to obtain the binary](https://github.com/doronz88/debugserver-deploy)
    * After re-signing with new entitlements, you can put the binary in the following path: `/usr/bin/debugserver`

In order to install please run:

```shell
xcrun python3 -m pip install --user -U -e .
```

*⚠️ Please note that Hilda is installed on top of XCode's python so LLDB will be able to use its features.*

## How to use

### Starting shell

Simply run:

```shell
hilda PROCESS_NAME SSH_PORT
```

Please note the script assumes the target device is running a ssh server. It will try running the following for you:

```shell
ssh -p SSH_PORT root@localhost "debugserver localhost:1234 --attach=PROCESS_NAME &"&
```

For this to work, make sure the connected device doesn't require a password for the connection (you can use
`ssh-copy-id` to achieve this).

### Commands

In order to view the list of available commands with their documentation, please run the following from within Hilda shell:

```python
show_commands()
```

### Symbol objects

In Hilda, almost everything is wrapped using the `Symbol` Object. Symbol is just a nicer way for referring to addresses
encapsulated with an object allowing to deref the memory inside, or use these addresses as functions.

In order to create a symbol from a given address, please use:

```python
s = symbol(0x12345678)

# peek(/read) 20 bytes of memory
s.peek(20)

# write into this memory
s.poke('abc')

# jump to `s` as a function, passing (1, "string") as its args 
s(1, "string")

# monitor each time a symbol is called into console and print its backtrace (`bt` option)
s.monitor(bt=True)

s.item_size = 1  # change the size of each item_size inside `s` for derefs
s[0] = 1  # will store the value `1` into *s
s[1] = 1  # will store the value `1` into *(s+1)

# symbol inherits from int, so all int operations apply
s += 4

# change s item size back to 8 to store pointers
s.item_size = 8

# storing the return value of the function executed at `0x11223344`
# into `*s`
s[0] = symbol(0x11223344)()
```

### Globalized symbols

Usually you would want/need to use the symbols already mapped into the currently running process. To do so, you can access them
using `symbols.<symbol-name>`. The `symbols` global object is of type `SymbolsJar`, which is a wrapper to `dict` for accessing
all exported symbols. For example, the following will generate a call to the exported
`malloc` function with `20` as its only argument:

```python
x = symbols.malloc(20)
```

You can also just write their name as if they already were in the global scope. Hilda will check if no name collision exists,
and if so, will perform the following lazily for you:

```python
x = malloc(20)

# is equivalent to:
malloc = symbols.malloc
x = malloc(20)
```

#### Searching for the right symbol

Sometimes you don't really know where to start your research. All you have is just theories of how your desired exported symbol
should be called (if any).

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
d = NSDictionary.new()

# which is equivalent to:
NSDictionary = objc_get_class('NSDictionary')
d = NSDictionary.new()
```

This is possible only since `NSDictionary` is exported. In case it is not, you must call `objc_get_class()` explicitly.

As you can see, you can directly access all the class' methods. In order to monitor each time a single one is called, you can:

```python
objc_class.get_method('methodName:').address.monitor()
```

Viewing the class layout can be achieved using:

```python
objc_class.show()
```

You can also monitor all method of a given class to see which is called when using:

```python
objc_class.monitor()
```

### Objective-C Objects

In order to work with ObjC objects, each symbol contains a property called
`objc_symbol`. After calling, you can work better with each object:

```python
d = NSDictionary.new().objc_symbol
d.show()  # print object layout
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
