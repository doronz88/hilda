from hilda.lldb_importer import lldb

_FILENAME = '/tmp/hilda-keylog.txt'


def _ssl_log_secret_bp(hilda, *args):
    label = hilda.registers.x1.peek_str()
    secret = hilda.registers.x2.peek(hilda.registers.x3).hex()
    random = (hilda.registers.x0[6] + 48).peek(32).hex()
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
