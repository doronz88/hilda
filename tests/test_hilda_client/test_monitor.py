from queue import Queue

import pytest


@pytest.mark.parametrize('fmt, representation', [
    ('po', 'x2 = com.apple.powerlog.state_changed'),
    ('cf', 'x2 = <CFString'),
    ('x', 'x2 = 0x'),
    (lambda client, value: 'Just return this string', 'x2 = Just return this string')
])
def test_monitor_register_formats(hilda_client, fmt: str, representation: str):
    """
    :param hilda.hilda_client.HildaClient hilda_client: Hilda client.
    :param fmt: Register format.
    :param representation: Substring of register's representation.
    """
    if 'executable = aggregated' not in str(hilda_client.process):
        pytest.skip('Unsupported process, please run this test on aggregated')

    logs_queue = Queue()
    bp = hilda_client.symbols._PLStateChanged.monitor(regs={'x2': fmt}, stop=True)
    hilda_client.log_info = logs_queue.put_nowait
    # Trigger a call to _PLStateChanged.
    hilda_client.po('''
        @import ObjectiveC;
        @import Foundation;
        CFNotificationCenterRef center = CFNotificationCenterGetDarwinNotifyCenter();
        CFNotificationCenterPostNotification(center, CFSTR("com.apple.powerlog.state_changed"), NULL, NULL, FALSE);
    ''')
    hilda_client.cont()
    output = logs_queue.get(timeout=10)
    hilda_client.remove_hilda_breakpoint(bp.id)
    assert representation in output
