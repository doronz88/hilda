# Hilda Modes of Operation

Hilda supports the following CLI options:

- `hilda launch /path/to/executable` -
  Run and debug the executable (on current host)
- `hilda attach [-p pid] [-n process-name]` -
  Attach to an already running process (on current host), specified by either `pid` or `process-name`
- `hilda remote HOSTNAME PORT` -
  Attach to an already running process (on a target host, specified by `HOSTNAME` and `PORT`)
- `hilda bare` -
  Start a regular LLDB shell, with the regular [LLDB commands](https://lldb.llvm.org/use/map.html), but also load Hilda as a plugin. A common use-case is

  ```shell
  # Connect to a remote platform
  platform connect connect://ip:port

  # Attach to a local process
  process attach -n process_name  # or
  process attach -p process_pid

  # When ready, switch to Hilda's IPython shell
  hilda
  ```

## Hilda as Python Module

In addition to using Hilda's CLI, you can write your own standalone scripts that use Hilda directly, via any of the `create_hilda_client_using_*` APIs. Each returns a ready-to-use [`HildaClient`](api/client.md).

Save your script and run it with **Xcode's Python**:

```shell
xcrun python3 script.py
```

!!! warning
    Standalone scripts must be run with `xcrun python3` (Xcode's Python) — otherwise importing Hilda, and especially LLDB, will fail. See [Installation](installation.md) for why.

### Attach by process name

`create_hilda_client_using_attach_by_name(name, wait_for=False)` attaches to a running process by
name:

```python
from hilda.launch_lldb import create_hilda_client_using_attach_by_name

# Attach to the running `sysmond`
p = create_hilda_client_using_attach_by_name('sysmond')

# Allocate 10 bytes and print their address
print(p.symbols.malloc(10))

# Detach when done
p.detach()
```

Pass `wait_for=True` to block until a process with that name launches, then attach to it — useful
for catching short-lived or relaunching processes:

```python
from hilda.launch_lldb import create_hilda_client_using_attach_by_name

# Wait for the next `MobileSafari` launch, then attach
p = create_hilda_client_using_attach_by_name('MobileSafari', wait_for=True)
```

### Attach by PID

`create_hilda_client_using_attach_by_pid(pid)` attaches to a specific process id:

```python
from hilda.launch_lldb import create_hilda_client_using_attach_by_pid

# Attach to PID 1337
p = create_hilda_client_using_attach_by_pid(1337)

print(p.symbols.getpid()())  # call a native function

p.detach()
```
