from cached_property import cached_property

from hilda.lldb_importer import lldb
from hilda.snippets.macho.all_image_infos import AllImageInfos
from hilda.snippets.syslog import open_syslog_socket


def all_image_infos():
    return AllImageInfos()


@cached_property
def version():
    with lldb.hilda_client.stopped(1):
        return \
            lldb.hilda_client.symbols.dyldVersionString.peek_str().decode('utf-8').split("PROJECT", 1)[1].split("\n")[0]


def enable_syslog():
    client = lldb.hilda_client
    with client.stopped(1):
        client.symbols._ZZN4dyldL9useSyslogEvE14launchdChecked.item_size = 1
        client.symbols._ZZN4dyldL9useSyslogEvE14launchdChecked[0] = 1
        client.symbols._ZZN4dyldL9useSyslogEvE12launchdOwned.item_size = 1
        client.symbols._ZZN4dyldL9useSyslogEvE12launchdOwned[0] = 1
        client.symbols._ZN4dyldL10sLogSocketE.item_size = 4
        client.symbols._ZN4dyldL10sLogSocketE[0] = 0xFFFFFFFF
        options = (
            'DYLD_PRINT_APIS',
            'DYLD_PRINT_APIS_APP',
            'DYLD_PRINT_BINDINGS'
            'DYLD_PRINT_DOFS',
            'DYLD_PRINT_INITIALIZERS',
            'DYLD_PRINT_INTERPOSING',
            'DYLD_PRINT_LIBRARIES',
            'DYLD_PRINT_LIBRARIES_POST_LAUNCH',
            'DYLD_PRINT_NOTIFICATIONS',
            'DYLD_PRINT_STATSTICS'
            'DYLD_PRINT_STATSTICS_DETAILS',
            'DYLD_PRINT_SEGMENTS',
            'DYLD_PRINT_WEAK_BINDINGS',
            'DYLD_PRINT_OPTS',
            'DYLD_PRINT_WARNINGS',
        )

        open_syslog_socket()

        with client.safe_malloc(8 * len(options) + 1) as envp:
            for i, option in enumerate(options):
                # enable for /usr/lib/dyld via dyld::processDyldEnvironmentVariable(option)
                client.symbols._ZN4dyld30processDyldEnvironmentVariableEPKcS1_S1_(option)
                variable = f'{option}=1'
                envp[i] = client.symbols.malloc(len(option) + 10)
                envp[i].poke(variable)

            envp[len(options)] = 0

            # enable for libdyld.dylib via dyld::setLoggingFromEnvs(eng)
            client.symbols._ZN5dyld318setLoggingFromEnvsEPPKc(envp)
