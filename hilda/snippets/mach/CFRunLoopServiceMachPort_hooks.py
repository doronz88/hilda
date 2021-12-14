import lldb


def _CFRunLoopServiceMachPort_hook(hilda, *args):
    """
    :param hilda.hilda_client.HildaClient hilda:
    """
    hilda.jump(hilda.CFRunLoopServiceMachPort_while_ea)
    hilda.cont()


def disable_mach_msg_errors():
    """
    Disable the error check inside the CFRunLoopServiceMachPort from the mach_msg syscall.
    This is used to debug slow handling of mach messages.
    """
    hilda = lldb.hilda_client
    with hilda.stopped():
        instructions = hilda.symbols.__CFRunLoopServiceMachPort.disass(2000, should_print=False)
        while_ea = None
        for instruction in instructions:
            if (while_ea is None) and instruction.DoesBranch():
                # Beginning of the `while(true) { ... }`
                while_ea = instruction.GetOperands(hilda.target)
                hilda.CFRunLoopServiceMachPort_while_ea = int(hilda.file_symbol(eval(while_ea)))
            elif instruction.GetMnemonic(hilda.target) in ('brk', 'ud2'):
                symbol = hilda.symbol(instruction.addr.GetLoadAddress(hilda.target))
                symbol.bp(
                    _CFRunLoopServiceMachPort_hook,
                    forced=True,
                    name=f'__CFRunLoopServiceMachPort-brk-{int(symbol - hilda.symbols.__CFRunLoopServiceMachPort)}'
                )
