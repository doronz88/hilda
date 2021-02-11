import lldb


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
    cf_object = lldb.hilda_client.symbols._CFXPCCreateCFObjectFromXPCObject(address)
    return lldb.hilda_client.from_cf(cf_object)
