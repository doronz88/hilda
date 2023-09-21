import lldb

_FILENAME = '/tmp/hilda-keylog.txt'


def _extract_params_arm(hilda):
    label = hilda.registers.x1.peek_str()
    secret = hilda.registers.x2.peek(hilda.registers.x3).hex()
    random = (hilda.registers.x0[6] + 48).peek(32).hex()
    return label, secret, random


def _extract_params_intel(hilda):
    label = hilda.registers.rsi.peek_str()
    secret = hilda.registers.rdx.peek(hilda.registers.rcx).hex()
    random = (hilda.registers.rdi[6] + 48).peek(32).hex()
    return label, secret, random


def _ssl_log_secret_bp(hilda, *args):
    label, secret, random = _extract_params_intel(hilda) if hilda.arch == 'x86_64h' else _extract_params_arm(hilda)
    print(f'ssl_log_secret\n'
          f'    label: {label}\n'
          f'    secret: {secret}\n'
          f'    random: {random}\n'
          f'---\n')
    with open(_FILENAME, 'a') as f:
        f.write(f'{label} {random} {secret}\n')
    hilda.cont()


def start_keylog(filename: str = None) -> None:
    global _FILENAME

    if filename is not None:
        _FILENAME = filename
    hilda_client = lldb.hilda_client
    hilda_client.symbols._ZN4bssl14ssl_log_secretEPK6ssl_stPKcNS_4SpanIKhEE.bp(_ssl_log_secret_bp)
