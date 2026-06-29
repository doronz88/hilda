# Hilda

Hilda bridges LLDB and IPython to deliver an improved debugging workflow.

📖 **Full documentation: <https://doronz88.github.io/hilda/>**

Both Hilda and [Frida](https://frida.re/) serve a similar purpose, but Hilda
takes a "debugger" approach (the name actually comes from the TV show "Hilda",
where Hilda is the best friend of Frida).

## Installation

To install, run:

```shell
# ⚠️ Note that the following installs Hilda for the current user using XCode's Python so LLDB will work properly
xcrun python3 -m pip install --user -U hilda
# XCode's Python can be located by running `xcrun --find python3`
# Hilda installation can be located by running `xcrun python3 -m pip show hilda | grep Location`
```

To use Hilda with an iOS device, you will need a Jailbroken iOS device with `debugserver` in the device's `PATH`.
You can use [this tool](https://github.com/doronz88/debugserver-deploy) to get the binary, re-sign it with the appropriate entitlements and put it in `/usr/bin/debugserver`.

## Overview

Start Hilda using (or use another [mode of operation](docs/hilda-modes-of-operation.md)):

```shell
hilda launch /path/to/executable
```

Upon starting Hilda, you are welcomed into Hilda's IPython shell, with the variable `p`, using which you can access [various methods](docs/hilda-method-set.md), including reading and writing memory and adding breakpoints.

Hilda displays the state of the target process using a [configurable](docs/hilda-configuration.md) UI consisting of 4 views (Registers, Disassembly, Stack and Backtrace):

![img.png](docs/ui.png)

Make sure you familiarize yourself with [`Symbol`s](docs/hilda-symbols.md) and [shortcuts](docs/hilda-shortcuts.md).
Hilda also has support for [Objective-C](docs/hilda-objective-c-support.md) and various [builtin snippets](docs/hilda-snippets.md).

## Contributing

Pull requests are more than welcome 😊.
Make sure you run the tests before submission (`xcrun python3 -m pytest`).

If you need help or have an amazing idea you would like to suggest, feel free
to [start a discussion 💬](https://github.com/doronz88/hilda/discussions).

The project is currently focused on iOS/macOS debugging.
Thanks to LLDB's abstraction capabilities for Linux and Android, implementing
support for these should be feasible with minimal changes.
