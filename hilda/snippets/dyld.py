from functools import cached_property

import lldb
from construct import *

from hilda.snippets.syslog import open_syslog_socket
from hilda.snippets.uuid import UUIDStructFactory
from hilda.symbol import SymbolFormatField
from hilda.snippets.macho import MachOStructFactory


class DyldStructFactory(object):

    @staticmethod
    def dyld_image_info():
        return Struct(
            '_imageLoadAddress' / SymbolFormatField(lldb.hilda_client),
            'imageLoadAddress' / Pointer(this._imageLoadAddress, MachOStructFactory.mach_header()),
            '_imageFilePath' / SymbolFormatField(lldb.hilda_client),
            'imageFilePath' / Pointer(this._imageFilePath, CString('utf8')),
            'imageFileModDate' / Int64ul
        )

    @staticmethod
    def dyld_uuid_info():
        return Struct(
            '_imageLoadAddress' / SymbolFormatField(lldb.hilda_client),
            'imageLoadAddress' / If(this._imageLoadAddress != 0, Pointer(this._imageLoadAddress,
                                                                         MachOStructFactory.mach_header())),
            'imageUUID' / UUIDStructFactory.uuid_t()
        )

    @staticmethod
    def all_image_infos():
        return Struct(
            'address' / Tell,
            'version' / Int32ul,
            'infoArrayCount' / Int32ul,
            '_infoArray' / SymbolFormatField(lldb.hilda_client),
            'infoArray' / Pointer(this._infoArray, Array(this.infoArrayCount, DyldStructFactory.dyld_image_info())),
            'notification' / SymbolFormatField(lldb.hilda_client),
            'processDetachedFromSharedRegion' / Int32ub,
            'libSystemInitialized' / Int32ub,
            '_dyldImageLoadAddress' / SymbolFormatField(lldb.hilda_client),
            'dyldImageLoadAddress' / Pointer(this._dyldImageLoadAddress, MachOStructFactory.mach_header()),
            'jitInfo' / SymbolFormatField(lldb.hilda_client),
            '_dyldVersion' / SymbolFormatField(lldb.hilda_client),
            'dyldVersion' / Pointer(this._dyldVersion, CString('utf8')),
            '_errorMessage' / SymbolFormatField(lldb.hilda_client),
            'errorMessage' / If(this._errorMessage != 0, Pointer(this._erroressage, CString('utf8'))),
            'terminationFlags' / Int64ul,
            'coreSymbolicationShmPage' / SymbolFormatField(lldb.hilda_client),
            'systemOrderFlags' / Int64ul,
            'uuidArrayCount' / Int64ul,
            '_uuidArray' / SymbolFormatField(lldb.hilda_client),
            'uuidArray' / If(this._uuidArray != 0,
                             Pointer(this._uuidArray, Array(this.uuidArrayCount, UUIDStructFactory.uuid_t()))),
            '_dyld_all_image_infos' / SymbolFormatField(lldb.hilda_client),
            # 'dyld_all_image_infos' / Lazy(LazyBound(lambda: Pointer(this._dyld_all_image_infos, self.all_image_infos))),
            'initialImageCount' / Int64ul,
            'errorKind' / Int64ul,
            '_errorClientOfDyLibPath' / SymbolFormatField(lldb.hilda_client),
            'errorClientOfDyLibPath' / If(this._errorClientOfDyLibPath != 0, Pointer(this._errorClientofoyLibPath, CString('utf8'))),
            '_errorTargetDylibPath' / SymbolFormatField(lldb.hilda_client),
            'errorTargetDylibPath' / If(this._errorTargetDylibPath != 0, Pointer(this._errorTargetDylibPath, CString('utf8'))),
            '_errorSymbol' / SymbolFormatField(lldb.hilda_client),
            'errorSymbol' / If(this._errorSymbol != 0, Pointer(this._errorSymbol, CString('utf8'))),
            'sharedCacheSlide' / Hex(Int64ul),
        )


def all_image_infos():
    with lldb.hilda_client.stopped(1):
        all_image_infos_symbol = lldb.hilda_client.symbol(lldb.hilda_client.symbols.dyld_all_image_infos)
        return DyldStructFactory.all_image_infos().parse_stream(all_image_infos_symbol)


@cached_property
def version():
    with lldb.hilda_client.stopped(1):
        return lldb.hilda_client.symbols.dyldVersionString.peek_str().decode('utf-8').split("PROJECT", 1)[1].split("\n")[0]


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
                # enable for /usr/lib/dyld via dyld::processtylEnvironmentVariable(option)
                client.symbols._ZN4dyld30processDyldEnvironmentVariableEPKcS1_S1_(option)
                variable = f'{option}=1'
                envp[i] = client.symbols.malloc(len(option) + 10)
                envp[i].poke(variable)

            envp[len(options)] = 0

            #enable for libdyld.dylib via dyld::setLoggingFrosts(eng)
            client.symbols._ZN5dyld318setLoggingFromEnvsEPPKc(envp)


