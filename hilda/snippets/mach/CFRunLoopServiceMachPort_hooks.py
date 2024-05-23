from hilda.exceptions import SymbolAbsentError
from hilda.lldb_importer import lldb


def _CFRunLoopServiceMachPort_hook(hilda, *args):
    """
    :param hilda.hilda_client.HildaClient hilda:
     """
    hilda.jump(hilda.CFRunLoopServiceMachPort_while_ea)
    hilda.cont()


def _disable_internal_error_handling() -> None:
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

    if hilda.arch == 'x86_64h':
        return

    # on iOS 16.x, will need to also patch this one
    try:
        handle_error = hilda.symbols['__CFRunLoopServiceMachPort.cold.1']
    except SymbolAbsentError:
        return

    for instruction in handle_error.disass(2000, should_print=False):
        if instruction.GetMnemonic(hilda.target) in ('brk', 'ud2'):
            # mov x0, x0
            hilda.symbol(instruction.addr.GetLoadAddress(hilda.target)).poke(b'\xe0\x03\x00\xaa')


def _disable_mach_msg_timeout() -> None:
    """
    Remove the timeout validation from __CFRunLoopServiceMachPort. This is done by patching the mach_msg_timeout_t
    parameter (4rd one) to MACH_MSG_TIMEOUT_NONE. On arm the parameter passes on `x3` register.

        __int64 __fastcall __CFRunLoopServiceMachPort(
            mach_port_name_t a1,
            mach_msg_header_t **a2,
            mach_port_t *a3,
            mach_msg_timeout_t a4,
            voucher_mach_msg_state_t *a5,
            id *a6)

        CoreFoundation:__text:0000000186E5012C ___CFRunLoopServiceMachPort
        CoreFoundation:__text:0000000186E5012C                 SUB             SP, SP, #0x70
        CoreFoundation:__text:0000000186E50130                 STP             X28, X27, [SP,#0x60+var_50]
        CoreFoundation:__text:0000000186E50134                 STP             X26, X25, [SP,#0x60+var_40]
        CoreFoundation:__text:0000000186E50138                 STP             X24, X23, [SP,#0x60+var_30]
        CoreFoundation:__text:0000000186E5013C                 STP             X22, X21, [SP,#0x60+var_20]
        CoreFoundation:__text:0000000186E50140                 STP             X20, X19, [SP,#0x60+var_10]
        CoreFoundation:__text:0000000186E50144                 STP             X29, X30, [SP,#0x60+var_s0]
        CoreFoundation:__text:0000000186E50148                 ADD             X29, SP, #0x60
        CoreFoundation:__text:0000000186E5014C                 MOV             X21, X5
        CoreFoundation:__text:0000000186E50150                 MOV             X22, X4
        CoreFoundation:__text:0000000186E50154                 MOV             X23, X3       <-------- Timeout parameter
    """
    if not lldb.KEYSTONE_SUPPORT:
        return

    hilda = lldb.hilda_client
    if hilda.arch == 'x86_64h':
        return

    with hilda.stopped():
        for inst in hilda.symbols.__CFRunLoopServiceMachPort.disass(200, should_print=False):
            mnemonic = inst.GetMnemonic(hilda.target)
            operands = inst.GetOperands(hilda.target)
            if mnemonic != 'mov' or not operands.endswith('x3'):
                continue
            addr = inst.GetAddress()
            file_addr = addr.GetFileAddress()
            new_inst = f'{mnemonic} {operands.replace("x3", "0")}'
            hilda.file_symbol(file_addr).poke_text(new_inst)
            break


def disable_mach_msg_errors() -> None:
    _disable_mach_msg_timeout()
    _disable_internal_error_handling()
