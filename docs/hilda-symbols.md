
# Hilda Symbols

In Hilda, the term Symbol is just a nicer way for referring to memory addresses.
Hilda's `Symbol` subclasses `int` (where the value is the memory address), adding support for

 * Reading and writing the memory
 * Jumping to the opcodes in the memory

## Examples

```python
s = p.symbol(0x12345678)

# The Symbol object extends `int`
True == isinstance(s, int)

# Print the un-shifted file address
# (calculating the ASLR shift for you, so you can just view it in IDA)
print(s.file_address)

# Or.. if you know the file address, but don't wanna mess
# with ASLR calculations
s = p.file_symbol(0x12345678)

# Peek(/read) 20 bytes of memory
print(s.peek(20))

# Write into this memory
s.poke('abc')

# Let LLDB print-object (it should guess the type automatically
# based on its memory layout)
print(s.po())

# Or you can help LLDB with telling it its type manually
print(s.po('char *'))

# Jump to `s` as a function, passing (1, "string") as its args
s(1, "string")

# Change the size of each item_size inside `s` for derefs
s.item_size = 1

# *(char *)s = 1
s[0] = 1

# *(((char *)s)+1) = 1
s[1] = 1

# Symbol subclasses int, so all int operations apply
s += 4

# Change s item size back to 8 to store pointers
s.item_size = 8

# *(intptr_t *)s = 1
s[0] = 1

# Store the return value of the function executed at `0x11223344`
# into `*s`
s[0] = p.symbol(0x11223344)()  # Calling symbols also returns symbols

# Attempt to resolve symbol's name
print(p.symbol(0x11223344).lldb_address)

# Monitor each time a symbol is called into console and print its backtrace (`bt` option).
# This will create a scripted breakpoint which prints your desired data and continue.
s.monitor(bt=True)

# You can also:
#   bt -> view the backtrace
#   regs -> view registers upon each call in your desired format
#   retval -> view the return value upon each call in your desired format
#   cmd -> execute a list of LLDB commands on each hit
s.monitor(regs={'x0': 'x'},  # print `x0` in HEX form
          retval='po',  # use LLDB's `po` for printing the returned value
          bt=True,  # view backtrace (will also resolve ASLR addresses for you)
          cmd=['thread list'],  # show thread list
          )

# We can also just `force_return` with a hard-coded value to practically disable
# a specific functionality
s.monitor(force_return=0)  # cause the function to always return `0`

# As for everything, if you need help understanding each such feature,
# simply execute the following to view its help (many such features even contain examples)
s.monitor?

# Create a scripted_breakpoint manually
def scripted_breakpoint(hilda, *args):
    # Like everything in Hilda, registers are also
    # just simple `Symbol` objects, so feel free to
    # use them to your heart's content :)
    if hilda.registers.x0.peek(4) == b'\x11\x22\x33\x44':
        hilda.registers.x0 = hilda.symbols.malloc(200)
        hilda.registers.x0.poke(b'\x22' * 200)

    # Just continue the process
    hilda.cont()


s.bp(scripted_breakpoint)

# Place a breakpoint at a symbol not yet loaded by it's name
p.bp('symbol_name')

# In case you need to specify a specific library it's loaded from
p.bp(('symbol_name', 'ModuleName'))
```

## Named Symbols

Hilda's symbols generalize Exported Symbols (e.g., the `malloc` Exported Symbol). In Hilda, a Symbol that has a name is called a Named Symbol.

Symbols are accessed via `p.symbols`, which is of type `SymbolList`. It acts like a `dict`, and you can either `p.symbols['<symbol-name>']` or just `p.symbols.<symbol-name>`.

For example, the following will invoke the exported
`malloc` function, with `20` as its only argument:

```python
x = p.symbols.malloc(20)
```

### Global Scope Named Symbols

You can also just write their name as if they already were in the global scope. Hilda will check if no name collision
exists, and if so, will perform the following lazily for you:

```python
x = malloc(20)

# Is equivalent to:
malloc = p.symbols.malloc
x = malloc(20)
```

### Filtering Named Symbols

Sometimes you don't really know where to start your research. All you have is just theories of how your desired exported
symbol should be called (if any).

```python
# Find all symbols prefixed as `mem*` AND don't have `cpy`
# in their name
l = p.symbols.filter_startswith('mem') - p.symbols.filter_name_contains('cpy')

# Filter only symbols of type "code" (removing data global for example)
l = l.filter_code_symbols()

# Monitor every time each one is called, print its `x0` in HEX
# form and show the backtrace
l.monitor(regs={'x0': 'x'}, bt=True)
```
