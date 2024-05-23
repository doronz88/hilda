from pprint import pformat

from pygments import highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexers import PythonLexer

from hilda.exceptions import ConvertingFromNSObjectError
from hilda.lldb_importer import lldb

# module global for storing all active xpc connections
active_xpc_connections = {}


def safe_monitor(symbol_name, **kwargs):
    hilda = lldb.hilda_client
    try:
        hilda.symbols[symbol_name].monitor(**kwargs)
    except KeyError:
        args = []
        for k, v in kwargs.items():
            args.append(f'{k}={v}')
        lldb.hilda_client.log_warning(f'missing symbol: "{symbol_name}". try to locate it manually (in IDA) and place '
                                      f'a breakpoint as follows:\n\tfile_symbol(ADDRESS).monitor({", ".join(args)})')


def sniff_send():
    safe_monitor('xpc_connection_send_message{libxpc.dylib}', regs={'x0': 'po', 'x1': 'po'})
    safe_monitor('xpc_connection_send_message_with_reply{libxpc.dylib}', regs={'x0': 'po', 'x1': 'po'})
    safe_monitor('xpc_connection_send_message_with_reply_sync{libxpc.dylib}', regs={'x0': 'po', 'x1': 'po'})


def sniff_receive():
    safe_monitor('_xpc_connection_call_event_handler', regs={'x0': 'po', 'x1': 'po'})


def sniff_incoming_event():
    safe_monitor('__XPC_CONNECTION_EVENT_HANDLER_CALLOUT__', regs={'x0': 'po', 'x1': 'po'})


def sniff_activities():
    safe_monitor('__XPC_ACTIVITY_CALLING_HANDLER__', regs={'x0': 'po'})


def sniff_all():
    sniff_send()
    sniff_receive()


def from_xpc_object(address: int):
    """
    Convert XPC object to python object.
    :param address: Address of XPC object.
    """
    return lldb.hilda_client.decode_cf(f'_CFXPCCreateCFObjectFromXPCObject({address})')


def disable_transaction_exit() -> None:
    """
    xpc_transaction_exit_clean will kill the process when transaction is done.
    By patching this function the process will stay alive.
    """
    hilda = lldb.hilda_client
    hilda.symbols.xpc_transaction_exit_clean.poke(b'\xc0\x03\x5f\xd6')  # ret


def to_xpc_object(obj: object):
    """
    Convert python object to XPC object.
    :param obj: Native python object
    """
    hilda = lldb.hilda_client
    return hilda.symbols._CFXPCCreateXPCObjectFromCFObject(hilda.ns(obj))


def xpc_to_python_monitor_format(hilda_client, address):
    """
    Format an XPC object as a python object, intended to use as a callback to monitor command.
    It depends on the object compatibility with CF object.
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param hilda.symbol.Symbol address: Symbol to format.
    """
    try:
        formatted = pformat(from_xpc_object(address))
        return highlight(formatted, PythonLexer(), TerminalTrueColorFormatter(style='native'))
    except ConvertingFromNSObjectError:
        return address.po()


def send_message_raw(service_name, message_raw):
    hilda = lldb.hilda_client

    with hilda.stopped():
        if service_name in active_xpc_connections:
            conn = active_xpc_connections[service_name]
        else:
            # 0 is for connecting instead of listening
            conn = hilda.symbols.xpc_connection_create_mach_service(service_name, 0, 0)
            assert conn != 0, 'failed to create xpc connection'
            hilda.po(f'''xpc_connection_set_event_handler({conn}, ^(xpc_object_t obj) {{}})''')
            hilda.symbols.xpc_connection_resume(conn)
            active_xpc_connections[service_name] = conn

        result = hilda.symbols.xpc_connection_send_message_with_reply_sync(conn, message_raw)
        return result


def send_message(service_name, message: object):
    hilda = lldb.hilda_client

    with hilda.stopped():
        message_raw = to_xpc_object(message)
        assert message_raw != 0, 'failed to convert python message object to native xpc object'
        return from_xpc_object(send_message_raw(service_name, message_raw))
