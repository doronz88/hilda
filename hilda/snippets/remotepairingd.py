from hilda.lldb_importer import lldb

TLV_MAP = {
    0x00: 'METHOD',
    0x01: 'IDENTIFIER',
    0x02: 'SALT',
    0x03: 'PUBLIC_KEY',
    0x04: 'PROOF',
    0x05: 'ENCRYPTED_DATA',
    0x06: 'STATE',
    0x07: 'ERROR',
    0x08: 'RETRY_DELAY',
    0x09: 'CERTIFICATE',
    0x0a: 'SIGNATURE',
    0x0b: 'PERMISSIONS',
    0x0c: 'FRAGMENT_DATA',
    0x0d: 'FRAGMENT_LAST',
    0x0e: 'SESSION_ID',
    0x0f: 'TTL',
    0x10: 'EXTRA_DATA',
    0x11: 'INFO',
    0x12: 'ACL',
    0x13: 'FLAGS',
    0x14: 'VALIDATION_DATA',
    0x15: 'MFI_AUTH_TOKEN',
    0x16: 'MFI_PRODUCT_TYPE',
    0x17: 'SERIAL_NUMBER',
    0x18: 'MFI_AUTH_TOKEN_UUID',
    0x19: 'APP_FLAGS',
    0x1a: 'OWNERSHIP_PROOF',
    0x1b: 'SETUP_CODE_TYPE',
    0x1c: 'PRODUCTION_DATA',
    0x1d: 'APP_INFO',
    0xff: 'SEPARATOR'
}


def _TLV8CopyCoalesced_bp(hilda, *args):
    type_ = hilda.registers.x2
    out_len = hilda.registers.x3
    out_len.item_size = 4
    hilda.finish()

    if hilda.registers.x0 == 0:
        print(f'TLV8CopyCoalesced\n'
              f'    type_: {TLV_MAP[type_]}\n'
              f'    buffer: Null\n'
              f'---\n')
    else:
        print(f'TLV8CopyCoalesced\n'
              f'    type_: {TLV_MAP[type_]}\n'
              f'    buffer: {hilda.registers.x0.peek(out_len[0])}\n'
              f'---\n')
    hilda.cont()


def _TLV8BufferAppend_bp(hilda, *args):
    buffer = hilda.registers.x0
    type_ = hilda.registers.x1
    buffer = hilda.registers.x2
    buffer_len = hilda.registers.x3
    print(f'TLV8BufferAppend\n'
          f'    type_: {TLV_MAP[type_]}\n'
          f'    buffer: {buffer.peek(buffer_len)}\n'
          f'---\n')
    hilda.cont()


def _SRPClientStart_libsrp_bp(hilda, *args):
    username = hilda.registers.x2
    username_len = hilda.registers.x3
    password = hilda.registers.x4
    password_len = hilda.registers.x5
    salt = hilda.registers.x6
    salt_len = hilda.registers.x7
    server_public_key = hilda.registers.sp[0]
    server_public_key_len = hilda.registers.sp[1]
    client_public_key = hilda.registers.sp[2]
    client_public_key_len = hilda.registers.sp[3]
    print(f'SRPClientStart_libsrp\n'
          f'    username: {username.peek(username_len)}\n'
          f'    password: {password.peek(password_len)}\n'
          f'    salt: {salt.peek(salt_len)}\n'
          f'    server_public_key: {server_public_key.peek(server_public_key_len)}\n'
          f'    client_public_key: {client_public_key.peek(client_public_key_len)}\n'
          f'---\n')
    hilda.cont()


def _cced25519_sign_bp(hilda, *args):
    sig = hilda.registers.x1
    len = hilda.registers.x2
    msg = hilda.registers.x3
    msg = msg.peek(len)
    public_key = hilda.registers.x4.peek(32)
    private_key = hilda.registers.x5.peek(32)
    hilda.finish()
    print(f'cced25519_sign\n'
          f'    public_key: {public_key}\n'
          f'    private_key: {private_key}\n'
          f'    msg: {msg}\n'
          f'    sig: {sig.peek(64)}\n'
          f'---\n')
    hilda.cont()


def _cced25519_verify_bp(hilda, *args):
    sig = hilda.registers.x3
    len = hilda.registers.x1
    msg = hilda.registers.x2
    msg = msg.peek(len)
    public_key = hilda.registers.x4.peek(32)
    hilda.finish()
    print(f'cced25519_verify\n'
          f'    public_key: {public_key}\n'
          f'    msg: {msg}\n'
          f'    sig: {sig.peek(64)}\n'
          f'---\n')
    hilda.cont()


def _CryptoHKDF_bp(hilda, *args):
    descriptor = hilda.registers.x0
    key = hilda.registers.x1.peek(hilda.registers.x2)
    salt = hilda.registers.x3
    salt_len = hilda.registers.x4
    info = hilda.registers.x5
    info_len = hilda.registers.x6
    out_key = hilda.registers.sp[0]
    hilda.finish()
    print(f'CryptoHKDF\n'
          f'    descriptor: {descriptor}\n'
          f'    key: {key}\n'
          f'    salt: {salt.peek(salt_len)}\n'
          f'    info: {info.peek(info_len)}\n'
          f'    outKey: {out_key.peek(32)}\n'
          f'---\n')
    hilda.cont()


def _chacha20_poly1305_encrypt_all_bp(hilda, *args):
    key = hilda.registers.x0.peek(32)
    nonce = hilda.registers.x1.peek(hilda.registers.x2)
    plaintext = hilda.registers.x5
    plaintext_len = hilda.registers.x6
    print(f'_chacha20_poly1305_encrypt_all\n'
          f'    key: {key}\n'
          f'    nonce: {nonce}\n'
          f'    plaintext: {plaintext.peek(plaintext_len)}\n'
          f'---\n')
    hilda.cont()


def _chacha20_poly1305_decrypt_all_bp(hilda, *args):
    key = hilda.registers.x0.peek(32)
    nonce = hilda.registers.x1.peek(hilda.registers.x2)
    encrypted = hilda.registers.x5
    encrypted_len = hilda.registers.x6
    plaintext = hilda.registers.x7
    encrypted_buf = encrypted.peek(encrypted_len)
    hilda.finish()
    print(f'_chacha20_poly1305_decrypt_all\n'
          f'    key: {key}\n'
          f'    nonce: {nonce}\n'
          f'    encrypted: {encrypted_buf}\n'
          f'    plaintext: {plaintext.peek(encrypted_len)}\n'
          f'---\n')
    hilda.cont()


def monitor_crypto_functions() -> None:
    hilda_client = lldb.hilda_client

    hilda_client.symbols.TLV8CopyCoalesced.bp(_TLV8CopyCoalesced_bp)
    hilda_client.symbols.TLV8BufferAppend.bp(_TLV8BufferAppend_bp)
    hilda_client.symbols.SRPClientStart_libsrp.bp(_SRPClientStart_libsrp_bp)
    hilda_client.symbols.SRPClientVerify_libsrp.monitor()
    hilda_client.symbols.SRPServerStart_libsrp.monitor()
    hilda_client.symbols.SRPServerVerify_libsrp.monitor()
    hilda_client.symbols.cced25519_sign.bp(_cced25519_sign_bp)
    hilda_client.symbols.cced25519_verify.bp(_cced25519_verify_bp)
    hilda_client.symbols.CryptoHKDF.bp(_CryptoHKDF_bp)
    hilda_client.symbols._chacha20_poly1305_encrypt_all.bp(_chacha20_poly1305_encrypt_all_bp)
    hilda_client.symbols._chacha20_poly1305_decrypt_all.bp(_chacha20_poly1305_decrypt_all_bp)
