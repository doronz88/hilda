from pprint import pformat

import lldb
from pygments.formatters import TerminalTrueColorFormatter
from pygments import highlight
from pygments.lexers import PythonLexer

from hilda.exceptions import ConvertingFromNSObjectError


def xpc_sniff_send():
    hilda = lldb.hilda_client
    hilda.symbols['xpc_connection_send_message{libxpc.dylib}'].monitor(regs={'x0': 'po', 'x1': 'po'})
    hilda.symbols['xpc_connection_send_message_with_reply{libxpc.dylib}'].monitor(regs={'x0': 'po', 'x1': 'po'})
    hilda.symbols['xpc_connection_send_message_with_reply_sync{libxpc.dylib}'].monitor(regs={'x0': 'po', 'x1': 'po'})


def xpc_sniff_receive():
    lldb.hilda_client.symbols._xpc_connection_call_event_handler.monitor(regs={'x0': 'po', 'x1': 'po'})


def xpc_sniff_incoming_event():
    lldb.hilda_client.symbols.__XPC_CONNECTION_EVENT_HANDLER_CALLOUT__.monitor(regs={'x0': 'po', 'x1': 'po'})


def xpc_sniff_activities():
    lldb.hilda_client.symbols.__XPC_ACTIVITY_CALLING_HANDLER__.monitor(regs={'x0': 'po'})


def xpc_sniff_all():
    xpc_sniff_send()
    xpc_sniff_receive()


def from_xpc_object(address: int):
    """
    Convert XPC object to python object.
    :param address: Address of XPC object.
    """
    return lldb.hilda_client.from_ns(f'_CFXPCCreateCFObjectFromXPCObject({address})')


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
