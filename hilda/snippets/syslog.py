import logging

SYSLOG_LISTENER_CODE = '''
socat UNIX-RECVFROM:/var/run/syslog, reuseaddr, fork, mode-0777 STDOUT
'''


def open_syslog_socket():
    logging.info(f'please execute the following code on the device for log listening:\n{SYSLOG_LISTENER_CODE}')
    input('> Hit return to resume')
