import logging
import lldb

SYSLOG_LISTENER_CODE = '''
socat UNIX-RECVFROM:/var/run/syslog,reuseaddr,fork,mode=0777 STDOUT
'''


def enable_syslog():
    client = lldb.hilda_client
    with client.stopped(1):
        # enable sending of log messages via syslogd
        client.symbols._ZZN4dyldL9useSyslogEvE14launchdChecked.item_size = 1
        client.symbols._ZZN4dyldL9useSyslogEvE14launchdChecked[0] = 1

        client.symbols._ZZN4dyldL9useSyslogEvE12launchdOwned.item_size = 1
        client.symbols._ZZN4dyldL9useSyslogEvE12launchdOwned[0] = 1

        client.symbols._ZN4dyldL10sLogSocketE.item_size = 4
        client.symbols._ZN4dyldL10sLogSocketE[0] = 0xffffffff

        options = ('DYLD_PRINT_DOFS', 'DYLD_PRINT_APIS', 'DYLD_PRINT_WARNINGS', 'DYLD_PRINT_BINDINGS')

        # since syslogd isn't really running on iOS we would have to replace its listening server with
        # a valid one beforehand
        logging.info(f'please execute the following code on the device for log listening:\n{SYSLOG_LISTENER_CODE}')
        input('> Hit return to resume')

        with client.safe_malloc(8 * (len(options) + 1)) as envp:
            for i, option in enumerate(options):
                # enable for /usr/lib/dyld via dyld::processDyldEnvironmentVariable(option)
                client.symbols._ZN4dyld30processDyldEnvironmentVariableEPKcS1_S1_(option)
                variable = f'{option}=1'
                logging.info(f'triggering {variable}')
                envp[i] = client.symbols.malloc(len(option) + 10)
                envp[i].poke(variable)
            envp[len(options)] = 0
            # enable for libdyld.dylib via dyld3::setLoggingFromEnvs(envp)
            client.symbols._ZN5dyld318setLoggingFromEnvsEPPKc(envp)
