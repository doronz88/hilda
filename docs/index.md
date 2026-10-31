---
template: home.html
hide:
  - navigation
  - toc
---

<div class="hl-feature" markdown>
<div markdown>

### Addresses are Python ints

A [`Symbol`](hilda-symbols.md) is an `int` that knows how to read, write, call and monitor the
memory it points at. ASLR offsets are handled for you.

</div>

```python
s = p.symbols.malloc(16)
s.poke(b'hilda')
print(s.peek(5))

p.symbols.open.monitor(regs={'x0': 'x'}, bt=True)
```

</div>

<div class="hl-feature" markdown>
<div markdown>

### Objective-C, natively

Exported classes are available by name. List their methods, call selectors, and capture live
instances. See [Objective-C support](hilda-objective-c-support.md).

</div>

```python
d = NSDictionary.new()
print(NSDictionary.methods.filter_startswith('init'))

obj = NSDictionary.capture_self(True)
obj.show()
```

</div>

<div class="hl-feature" markdown>
<div markdown>

### Recipes for common jobs

[Snippets](hilda-snippets.md) cover everyday tasks such as sniffing XPC traffic, inspecting
`dyld` and walking Mach-O images.

</div>

```python
from hilda.snippets import xpc

xpc.sniff_all()
```

</div>

<div class="hl-feature" markdown>
<div markdown>

### Scripts, not just sessions

Everything you do in the shell also works from a standalone script.
See [modes of operation](hilda-modes-of-operation.md).

</div>

```python
from hilda.launch_lldb import create_hilda_client_using_attach_by_name

p = create_hilda_client_using_attach_by_name('sysmond')
print(p.symbols.malloc(10))
p.detach()
```

</div>

## See the process state

Hilda shows the stopped process in a [configurable](hilda-configuration.md) UI with four views:
Registers, Disassembly, Stack and Backtrace.

![Hilda UI showing registers, disassembly, stack and backtrace](ui.png)

## Where to go next

- [Installation](installation.md): install with Xcode's Python so LLDB imports correctly.
- [Modes of operation](hilda-modes-of-operation.md): launch, attach, remote and bare LLDB.
- [Shortcuts](hilda-shortcuts.md): key bindings for stepping and continuing.
- [API reference](api/index.md): the generated `HildaClient` reference.
