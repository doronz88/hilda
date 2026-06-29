# Hilda

Hilda bridges **LLDB and IPython** to deliver an improved debugging workflow.

Both Hilda and [Frida](https://frida.re/) serve a similar purpose, but Hilda takes a "debugger"
approach (the name comes from the TV show *Hilda* — where Hilda is the best friend of Frida).

[Get started :material-arrow-right:](installation.md){ .md-button .md-button--primary }
[Modes of operation](hilda-modes-of-operation.md){ .md-button }

## Overview

Start Hilda (or use another [mode of operation](hilda-modes-of-operation.md)):

```shell
hilda launch /path/to/executable
```

You land in Hilda's IPython shell with the variable `p`, through which you access
[various methods](hilda-method-set.md) — reading/writing memory, adding breakpoints, and more.

Hilda displays the target process state in a [configurable](hilda-configuration.md) UI with four
views (Registers, Disassembly, Stack, Backtrace):

![Hilda UI](ui.png)

## Learn the essentials

<div class="grid cards" markdown>

- :material-download: **[Installation](installation.md)** — install with Xcode's Python so LLDB works.
- :material-cog: **[Modes of operation](hilda-modes-of-operation.md)** — launch, attach, remote, and more.
- :material-tag: **[Symbols](hilda-symbols.md)** — the `Symbol` object and how to use it.
- :material-language-swift: **[Objective-C support](hilda-objective-c-support.md)** — work with ObjC objects/classes.
- :material-keyboard: **[Shortcuts](hilda-shortcuts.md)** and **[snippets](hilda-snippets.md)** — speed up your sessions.
- :material-book-open-variant: **[API reference](api/index.md)** — the generated `HildaClient` reference.

</div>
