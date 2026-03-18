# Hilda Configuration

## `cfg`

In Hilda's IPython shell, the variable `cfg` is available.
It holds the various settings for evaluation and monitoring, including

- `evaluation_unwind_on_error` - When `True`, unwind on error during evaluation (Default: `False`).
- `evaluation_ignore_breakpoints` - When `True`, ignore breakpoints during evaluation (Default: `False`).
- `nsobject_exclusion` - When `True`, exclude `NSObject` during evaluation, reducing IPython autocomplete results (
  Default: `False`).
- `objc_verbose_monitor` - When `True`, using `monitor()` will automatically print Objective-C method arguments (
  Default: `False`).

## `ui`

In Hilda's IPython shell, the variable `ui` is available.

You can use it to display Hilda's UI:

```python
ui.show()
```

By default `step_into` and `step_over` will show this UI automatically.
You may disable this behavior by executing:

```python
ui.active = False
```

Attentively, if you want to display UI after hitting a breakpoint, you can register `ui.show` as callback:

```python
p.symbol(0x7ff7b97c21b0).bp(ui.show)
```

Try playing with the UI settings by yourself:

```python
# Disable stack view
ui.views.stack.active = False

# View words from the stack
ui.views.stack.depth = 10

# View last 10 frames
ui.views.backtrace.depth = 10

# Disassemble 5 instructions
ui.views.disassembly.instruction_count = 5

# Change disassembly syntax to AT&T
ui.views.disassembly.flavor = 'att'

# View floating point registers
ui.views.registers.rtype = 'float'

# Change addresses print color
ui.colors.address = 'red'

# Change titles color
ui.colors.title = 'green'
```
