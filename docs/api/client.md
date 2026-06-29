# HildaClient

The main entry point — exposed as the `p` global inside the Hilda shell.

## Creating a client

In standalone scripts (run with `xcrun python3 script.py`), create a client with one of these
factories — see [Hilda as Python Module](../hilda-modes-of-operation.md#hilda-as-python-module) for
runnable examples.

::: hilda.launch_lldb.create_hilda_client_using_attach_by_name

::: hilda.launch_lldb.create_hilda_client_using_attach_by_pid

::: hilda.launch_lldb.create_hilda_client_using_launch

::: hilda.launch_lldb.create_hilda_client_using_remote_attach

## HildaClient

::: hilda.hilda_client.HildaClient
