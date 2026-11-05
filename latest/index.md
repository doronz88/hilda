### Addresses are Python ints

A [`Symbol`](https://doronz88.github.io/hilda/latest/hilda-symbols/index.md) is an `int` that knows how to read, write, call and monitor the memory it points at. ASLR offsets are handled for you.

```
s = p.symbols.malloc(16)
s.poke(b'hilda')
print(s.peek(5))

p.symbols.open.monitor(regs={'x0': 'x'}, bt=True)
```

### Objective-C, natively

Exported classes are available by name. List their methods, call selectors, and capture live instances. See [Objective-C support](https://doronz88.github.io/hilda/latest/hilda-objective-c-support/index.md).

```
d = NSDictionary.new()
print(NSDictionary.methods.filter_startswith('init'))

obj = NSDictionary.capture_self(True)
obj.show()
```

### Recipes for common jobs

[Snippets](https://doronz88.github.io/hilda/latest/hilda-snippets/index.md) cover everyday tasks such as sniffing XPC traffic, inspecting `dyld` and walking Mach-O images.

```
from hilda.snippets import xpc

xpc.sniff_all()
```

### Scripts, not just sessions

Everything you do in the shell also works from a standalone script. See [modes of operation](https://doronz88.github.io/hilda/latest/hilda-modes-of-operation/index.md).

```
from hilda.launch_lldb import create_hilda_client_using_attach_by_name

p = create_hilda_client_using_attach_by_name('sysmond')
print(p.symbols.malloc(10))
p.detach()
```

## See the process state

Hilda shows the stopped process in a [configurable](https://doronz88.github.io/hilda/latest/hilda-configuration/index.md) UI with four views: Registers, Disassembly, Stack and Backtrace.

## Where to go next

- [Installation](https://doronz88.github.io/hilda/latest/installation/index.md): install with Xcode's Python so LLDB imports correctly.
- [Modes of operation](https://doronz88.github.io/hilda/latest/hilda-modes-of-operation/index.md): launch, attach, remote and bare LLDB.
- [Shortcuts](https://doronz88.github.io/hilda/latest/hilda-shortcuts/index.md): key bindings for stepping and continuing.
- [API reference](https://doronz88.github.io/hilda/latest/api/index.md): the generated `HildaClient` reference.
