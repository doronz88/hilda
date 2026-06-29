# Installation

Install Hilda using **Xcode's Python**, so LLDB works properly:

```shell
# Installs Hilda for the current user using Xcode's Python
xcrun python3 -m pip install --user -U hilda
```

- Locate Xcode's Python: `xcrun --find python3`
- Locate the Hilda install: `xcrun python3 -m pip show hilda | grep Location`

## Debugging an iOS device

To use Hilda with an iOS device you need a **jailbroken** device with `debugserver` in the
device's `PATH`. Use [debugserver-deploy](https://github.com/doronz88/debugserver-deploy) to fetch
the binary, re-sign it with the appropriate entitlements, and place it at `/usr/bin/debugserver`.

Next: pick a [mode of operation](hilda-modes-of-operation.md) to start a session.
