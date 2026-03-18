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

In addition to using Hilda's CLI, you can also use Hilda directly in Python scripts, using any of the `create_hilda_client_using_*` APIs.

For example:

```python
# ⚠️ Run this script using `xcrun python3` (otherwise importing Hilda, and especially LLDB, will fail)
from hilda.launch_lldb import create_hilda_client_using_attach_by_name

# Attach to `sysmond`
p = create_hilda_client_using_attach_by_name('sysmond')

# Allocate 10 bytes and print their address
print(p.symbols.malloc(10))

# Detach
p.detach()
```
