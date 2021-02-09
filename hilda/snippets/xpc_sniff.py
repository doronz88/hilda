def xpc_sniff_send(hilda):
    hilda.symbols['xpc_connection_send_message{libxpc.dylib}'].monitor(regs={'x0': 'po', 'x1': 'po'})
    hilda.symbols['xpc_connection_send_message_with_reply{libxpc.dylib}'].monitor(regs={'x0': 'po', 'x1': 'po'})
    hilda.symbols['xpc_connection_send_message_with_reply_sync{libxpc.dylib}'].monitor(regs={'x0': 'po', 'x1': 'po'})


def xpc_sniff_receive(hilda):
    hilda.symbols._xpc_connection_call_event_handler.monitor(regs={'x0': 'po', 'x1': 'po'})


def xpc_sniff_incoming_event(hilda):
    hilda.symbols.__XPC_CONNECTION_EVENT_HANDLER_CALLOUT__.monitor(regs={'x0': 'po', 'x1': 'po'})


def xpc_sniff_activities(hilda):
    hilda.symbols.__XPC_ACTIVITY_CALLING_HANDLER__.monitor(regs={'x0': 'po'})


def xpc_sniff_all(hilda):
    xpc_sniff_send(hilda)
    xpc_sniff_receive(hilda)
