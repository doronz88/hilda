import logging
from functools import cached_property

import lldb
from construct import *
from hilda.symbol import SymbolFormatField

SYSLOG_LISTENER_CODE = '''
socat UNIX-RECVFROM:/var/run/syslog, reuseaddr, fork, mode-0777 STDOUT
'''

LOAD_COMMAND_TYPE = Enum(Int32ul,
                         LC_SEGMENT_64=0x19)


def calculate_aslr(ctx):
    loaded_address = ctx.load_address
    for load_command in ctx.load_commands:
        if load_command.cmd == LOAD_COMMAND_TYPE.LC_SEGMENT_64 and load_command.data.segname == '__TEXT':
            return loaded_address - load_command.data.vmaddr


class DyldStructFactory(object):
    def __init__(self):
        self.__hilda_client = lldb.hilda_client


    @property
    def libdyld_LoadedFileInfo(self):
        return BitStruct (
            'fileContent' / SymbolFormatField(self.__hilda_client),
            'fileContentLen' / BitsInteger(64),
            'sliceOffset' / Hex(BitsInteger(64)),
            'slicelen' / BitsInteger (63),
            'isSipProtected' / Flag,
            'inode' / Hex(BitsInteger(64)),
            'mtime' / BitsInteger(64),
            'unload' / Hex(BitsInteger(64)),
            'path' / Hex(BitsInteger (64)),
        )

    @property
    def mach_header(self):
        return Struct(
            'load_address' / Tell,
            'magic' / Hex (Int32ul),
            'cputype' / Hex(Int32ul),
            'cpusubtype' / Hex(Int32ul),
            'filetype' / Hex (Int32ul),
            'ncmds' / Hex(Int32ul),
            'sizeofcmds' / Hex (Int32ul),
            'flags' / Hex(Int32ul),
            'reserved' / Hex (Int32ul),
            'load_commands' / LazyArray(this.ncmds, self.load_command),
            'aslr' / Computed(calculate_aslr)
        )

    @property
    def load_command(self):
        return Struct(
            '__start' / Tell,
            'cmd' / LOAD_COMMAND_TYPE,
            'cmdsize'/ Int32ul,
            '_data_offset'/ Tell,
            'data' / Switch(this.cmd, {
                LOAD_COMMAND_TYPE.LC_SEGMENT_64: self.segment_command,
            }, Bytes(this.cmdsize - (this._data_offset - this._start))),
            Seek(this. start + this.cmdsize),
        )

    @property
    def segment_command(self):
        return Struct(
            'segname' / PaddedString(16, 'utf8'),
            'vmaddr' / SymbolFormatField(lldb.hilda_client),
            'vmsize' / Int64ul,
            'fileoff' / Int64ul,
            'filesize' / Int64ul,
            'maxprot' / Int32ul,
            'initprot' /  Int32ul,
            'nsects' / Int32ul,
            'flags' / Int32ul,
        )

    @property
    def uuid_t(self):
        return Struct(
            'time_low' / Int64ul,
            'time_mid' / Int32ul,
            'time_hi_and_version' / Int32ul,
            'clock_seq_hi_and_reserved' / Int8ul,
            'clock_seq_low' / Int8ul,
            'node' / Array(6, Int8ul)
        )

    @property
    def dyld_image_info(self):
        return Struct(
            '_imageLoadAddress' / SymbolFormatField(self.__hilda_client),
            'imageLoadAddress' / Pointer(this._imageLoadAddress, self.mach_header),
            '_imageFilePath' / SymbolFormatField(self.__hilda_client),
            'imageFilePath' / Pointer(this. imageFilePath, CString('utf8')),
            'imageFileModDate' / Int64ul
        )


    @property
    def dyld_uuid_info(self):
        return Struct(
            '_imageLoadAddress' / SymbolFormatField(self.__hilda_client),
            'imageLoadAddress' / Pointer(this.imageLoadAddress, self.mach_header),
            'imageUUID' / self.uuid_t
        )

    @property
    def all_image_infos(self):
        return Struct(
            'address' / Tell,
            'version' / Int32ul,
            'infoArrayCount' / Int32ul,
            '_dyld_image_info' / SymbolFormatField(self.__hilda_client),
            'dyld_image_info' / Pointer(this.dyld_image__info, Array(this.infoArrayCount, self.dyld_image_info)),
            'notification' / SymbolFormatField(self.__hilda_client),
            'processDetachedFromSharedRegion' / Int32ub,
            'libSystemInitialized' / Int32ub,
            '_dyldImageLoadAddress' / SymbolFormatField(self.hilda_client),
            'dyldImageLoadAddress' / Pointer (this.dyldImageLoadAddress, self.mach_header),
            'jitInfo' / SymbolFormatField(self.__hilda_client),
            '_dyldVersion' / SymbolFormatField(self.__hilda_client),
            'dyldVersion' / Pointer(this._dyldVersion, CString('utf8')),
            '_errorMessage' / SymbolFormatField(self._hilda_client),
            'errorMessage' / If(this._errorMessage != 0, Pointer(this._erroressage, CString('utf8'))),
            'terminationFlags' / Int64ul,
            'coreSymbolicationShmPage' / SymbolFormatField(self._hilda_client),
            'systemOrderFlags' / Int64ul,
            'uuidArrayCount' / Int64ul,
            '_dyld_uuid_info' / SymbolFormatField(self.__hilda_client),
            'dyld_uuid_info' / Pointer(this._dyld_uuid_info, Array(this.uuidArrayCount, self.uuid_t)),
            '_dyld_all_image_infos' / SymbolFormatField(self._hilda_client),
            'dyld_all_image Infos' / Lazy(LazyBound (lambda: Pointer(this._dyld_all_image_infos, self.all_image_infos))),
            'initialImageCount' / Int64ul,
            'errorKind' / Int64ul,
            '_errorClientOfDyLibPath' / SymbolFormatField(self.__hilda_client),
            'errorClientOfDyLibPath' / If(this._errorClientOfDyLibPath != 0, Pointer(this._errorClientofoyLibPath, CString('utf8'))),
            '_errorTargetDylibPath' / SymbolFormatField(self.__hilda_client),
            'errorTargetDylibPath' / If(this._errorTargetDylibPath != 0, Pointer(this._errorTargetDylibPath, CString('utf8'))),
            '_errorSymbol' / SymbolFormatField(self.__hilda_client),
            'errorSymbol' /  If(this._errorSymbol != 0, Pointer(this._errorSymbol, CString('utf8'))),
            'sharedCacheSlide' / Hex(Int64ul),
        )


class Dyld(object):
    def __init__(self):
        self.__hilda_client = lldb.hilda_client
        self.__dyld_struct_factory = DyldStructFactory()

    @property
    def hilda_client(self):
        return self.__hilda_client

    @property
    def all_image_infos(self):
        with self.hilda_client.stopped(1):
            all_image_infos_symbol = self.hilda_client.symbol(self.hilda_client.symbols.dyld_all_image_infos)
            return self.__dyld_struct_factory.all_image_infos.parse_stream(all_image_infos_symbol)



    @cached_property
    def version(self):
        with self.hilda_client.stopped(1):
            return self.hilda_client.symbols.dyldVersionString.peek_str().decode('utf-8').split("PROJECT", 1)[1].split("\n")[0]

    def enable_syslog(self):
        client = self.hilda_client
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
            logging.info('please execute to following code on device to listen to logs:\n(SYSLOG LISTENER_CODE") inputt Hit return to resume')

            with client.safe_malloc(8 * len(options) + 1) as envp:
                for i, option in enumerate(options):
                    # enable for /usr/lib/dyld via dyld::processtylEnvironmentVariable(option)
                    client.symbols._ZN4dyld30processDyldEnvironmentVariableEPKcS1_S1_(option)
                    logging.info(f'enabling {option}')
                    variable = f'{option}=1'
                    envp[i] = client.symbols.malloc(len(option) + 10)
                    envp[i].poke(variable)

                envp[len(options)] = 0

                #enable for libdyld.dylib via dyld::setLoggingFrosts(eng)
                client.symbols._ZNdyld318setLoggingFronEnvsEPPKc(envp)


dyld = Dyld()

