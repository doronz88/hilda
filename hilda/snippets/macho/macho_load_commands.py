from typing import List

from construct import Array, Bytes, Enum, Hex, Int8ul, Int32ul, Int64ul, PaddedString, Pointer, Seek, Struct, Switch, \
    Tell, this

from hilda.lldb_importer import lldb
from hilda.snippets.macho.apple_version import version_t
from hilda.symbol import SymbolFormatField

# See: https://opensource.apple.com/source/xnu/xnu-7195.81.3/EXTERNAL_HEADERS/mach-o/loader.h
LC_REQ_DYLD = 0x80000000

LOAD_COMMAND_TYPE = Enum(Int32ul,
                         LC_SEGMENT=0x1,
                         LC_SYMTAB=0x2,
                         LC_SYMSEG=0x3,
                         LC_THREAD=0x4,
                         LC_UNIXTHREAD=0x5,
                         LC_LOADFVMLIB=0x6,
                         LC_IDFVMLIB=0x7,
                         LC_IDENT=0x8,
                         LC_FVMFILE=0x9,
                         LC_PREPAGE=0xa,
                         LC_DYSYMTAB=0xb,
                         LC_LOAD_DYLIB=0xc,
                         LC_ID_DYLIB=0xd,
                         LC_LOAD_DYLINKER=0xe,
                         LC_ID_DYLINKER=0xf,
                         LC_PREBOUND_DYLIB=0x10,
                         LC_ROUTINES=0x11,
                         LC_SUB_FRAMEWORK=0x12,
                         LC_SUB_UMBRELLA=0x13,
                         LC_SUB_CLIENT=0x14,
                         LC_SUB_LIBRARY=0x15,
                         LC_TWOLEVEL_HINTS=0x16,
                         LC_PREBIND_CKSUM=0x17,
                         LC_LOAD_WEAK_DYLIB=(0x18 | LC_REQ_DYLD),
                         LC_SEGMENT_64=0x19,
                         LC_ROUTINES_64=0x1a,
                         LC_UUID=0x1b,
                         LC_RPATH=(0x1c | LC_REQ_DYLD),
                         LC_CODE_SIGNATURE=0x1d,
                         LC_SEGMENT_SPLIT_INFO=0x1e,
                         LC_REEXPORT_DYLIB=0x1f | LC_REQ_DYLD,
                         LC_LAZY_LOAD_DYLIB=0x20,
                         LC_ENCRYPTION_INFO=0x21,
                         LC_DYLD_INFO=0x22,
                         LC_DYLD_INFO_ONLY=(0x22 | LC_REQ_DYLD),
                         LC_LOAD_UPWARD_DYLIB=(0x23 | LC_REQ_DYLD),
                         LC_VERSION_MIN_MACOSX=0x24,
                         LC_VERSION_MIN_IPHONEOS=0x25,
                         LC_FUNCTION_STARTS=0x26,
                         LC_DYLD_ENVIRONMENT=0x27,
                         LC_MAIN=(0x28 | LC_REQ_DYLD),
                         LC_DATA_IN_CODE=0x29,
                         LC_SOURCE_VERSION=0x2A,
                         LC_DYLIB_CODE_SIGN_DRS=0x2B,
                         LC_ENCRYPTION_INFO_64=0x2C,
                         LC_LINKER_OPTION=0x2D,
                         LC_LINKER_OPTIMIZATION_HINT=0x2E,
                         LC_VERSION_MIN_TVOS=0x2F,
                         LC_VERSION_MIN_WATCHOS=0x30,
                         LC_NOTE=0x31,
                         LC_BUILD_VERSION=0x32,
                         LC_DYLD_EXPORTS_TRIE=(0x33 | LC_REQ_DYLD),
                         LC_DYLD_CHAINED_FIXUPS=(0x34 | LC_REQ_DYLD),
                         LC_FILESET_ENTRY=(0x35 | LC_REQ_DYLD)
                         )


def __lc_str_from_load_command(this):
    load_command = this._._._
    return Struct(
        # this struct appears as a union in apple's opensource, but is represented in an awful manner, whereas
        # they would treat both the `ptr` and `offset` members as offsets (and never as pointers),
        # so we changed this a bit into the struct that it should have been
        'offset' / Hex(Int32ul),
        '_pad' / Int32ul,
        'name' / Pointer(load_command._start + this.offset, PaddedString(load_command.cmdsize - this.offset, 'utf8')),
    )


__dylib_t = Struct(
    'lc_str' / __lc_str_from_load_command(this),
    'timestamp' / Int64ul,
    'current_version' / Int64ul,
    'compatibility_version' / Int64ul,
)

# Load commands:
# reference - https://opensource.apple.com/source/xnu/xnu-2050.18.24/EXTERNAL_HEADERS/mach-o/loader.h
__dylib_command_t = Struct(
    'dylib' / __dylib_t,
)

__segment_command_t = Struct(
    'segname' / PaddedString(16, 'utf8'),
    'vmaddr' / SymbolFormatField(lldb.hilda_client),
    'vmsize' / Int64ul,
    'fileoff' / Int64ul,
    'filesize' / Int64ul,
    'maxprot' / Int32ul,
    'initprot' / Int32ul,
    'nsects' / Int32ul,
    'flags' / Int32ul,
)

__uuid_command_t = Struct(
    'uuid' / Array(16, Int8ul)
)

__build_tool_version = Struct(
    'tool' / Int32ul,
    'version' / Int32ul
)

__build_version_command_t = Struct(
    'platform' / Int32ul,
    'minos' / version_t,
    'sdk' / version_t,
    'ntools' / Int32ul,
    # '_build_tools' / SymbolFormatField(this),
    # 'build_tools' / If(this._build_tools != 0, Array(this.ntools, Pointer(this._build_tools, __build_tool_version)))
)

load_command_t = Struct(
    '_start' / Tell,
    'cmd' / LOAD_COMMAND_TYPE,
    'cmdsize' / Int32ul,
    '_data_offset' / Tell,
    'data' / Switch(this.cmd, {
        LOAD_COMMAND_TYPE.LC_BUILD_VERSION: __build_version_command_t,
        LOAD_COMMAND_TYPE.LC_UUID: __uuid_command_t,
        LOAD_COMMAND_TYPE.LC_SEGMENT_64: __segment_command_t,
        LOAD_COMMAND_TYPE.LC_LOAD_DYLIB: __dylib_command_t,
        LOAD_COMMAND_TYPE.LC_LOAD_WEAK_DYLIB: __dylib_command_t,
        LOAD_COMMAND_TYPE.LC_ID_DYLIB: __dylib_command_t,
        LOAD_COMMAND_TYPE.LC_REEXPORT_DYLIB: __dylib_command_t,
        LOAD_COMMAND_TYPE.LC_LAZY_LOAD_DYLIB: __dylib_command_t,
    }, Bytes(this.cmdsize - (this._data_offset - this._start))),
    Seek(this._start + this.cmdsize),
)


class LoadCommand(object):
    def __init__(self, load_command_data):
        self.__load_command_data = load_command_data
        self.__cmd = load_command_data.cmd
        self.__cmd_size = load_command_data.cmdsize
        self.__data_offset = load_command_data._data_offset

    @property
    def cmd(self):
        return self.__cmd

    @property
    def cmd_size(self):
        return self.__cmd_size


class DylibCommand(LoadCommand):
    def __init__(self, load_command_data):
        super(DylibCommand, self).__init__(load_command_data)
        dylib_data = load_command_data.data.dylib

        self.__path = dylib_data.lc_str.name
        self.__timestamp = dylib_data.timestamp
        self.__current_version = dylib_data.current_version
        self.__compatibility_version = dylib_data.compatibility_version

    def __str__(self):
        return f'<DylibCommand: path = {self.path}>'

    def __repr__(self):
        return self.__str__()

    @property
    def path(self):
        return self.__path


class Segment64Command(LoadCommand):
    def __init__(self, load_command_data):
        super(Segment64Command, self).__init__(load_command_data)

        self.__segname = load_command_data.data.segname
        self.__vmaddr = load_command_data.data.vmaddr
        self.__vmsize = load_command_data.data.vmsize
        self.__fileoff = load_command_data.data.fileoff
        self.__filesize = load_command_data.data.filesize
        self.__maxprot = load_command_data.data.maxprot
        self.__initprot = load_command_data.data.initprot
        self.__nsects = load_command_data.data.nsects
        self.__flags = load_command_data.data.flags

    @property
    def vmaddr(self):
        return self.__vmaddr

    @property
    def segname(self):
        return self.__segname

    def __str__(self):
        return f'<Segment64Command: segname={self.segname}, vmaddr={self.vmaddr}, vmsize={self.__vmsize}>'

    def __repr__(self):
        return self.__str__()


class UUIDCommand(LoadCommand):
    def __init__(self, load_command_data):
        super(UUIDCommand, self).__init__(load_command_data)

        self.__uuid = load_command_data.data.uuid

    def __str__(self):
        return '<UUIDCommand>'

    def __repr__(self):
        return self.__str__()


class BuildVersionCommand(LoadCommand):
    def __init__(self, load_command_data):
        super(BuildVersionCommand, self).__init__(load_command_data)

        self.__platform = load_command_data.data.platform
        self.__minos = load_command_data.data.platform
        self.__sdk = load_command_data.data.platform
        self.__ntools = load_command_data.data.platform
        self.__build_tools = load_command_data.data.build_tools

    def __str__(self):
        return f'<BuildVersionCommand platform={self.platform}>'

    def __repr__(self):
        return self.__str__()

    @property
    def platform(self):
        return self.__platform

    @property
    def minos(self):
        return self.__minos

    @property
    def sdk(self):
        return self.__sdk


class UnimplementedCommand(LoadCommand):
    def __init__(self, load_command_data):
        super(UnimplementedCommand, self).__init__(load_command_data)

        self.__bytes = load_command_data.data

    def __str__(self):
        return f'<cmd={self.cmd} is not implemented((Feel free to add!!). bytes={self.__bytes}>'

    def __repr__(self):
        return self.__str__()


class LoadCommands:
    def __init__(self, load_commands_data):
        self.__load_commands = []
        for load_command_data in load_commands_data:
            if load_command_data.cmd == 'LC_SEGMENT_64':
                load_command = Segment64Command(load_command_data)
            elif load_command_data.cmd == 'LC_LOAD_DYLIB' or \
                    load_command_data.cmd == 'LC_ID_DYLIB' or \
                    load_command_data.cmd == 'LC_LOAD_WEAK_DYLIB' or \
                    load_command_data.cmd == 'LC_REEXPORT_DYLIB' or \
                    load_command_data.cmd == 'LC_LAZY_LOAD_DYLIB':
                load_command = DylibCommand(load_command_data)
            elif load_command_data.cmd == 'LC_UUID':
                load_command = UUIDCommand(load_command_data)
            else:
                load_command = UnimplementedCommand(load_command_data)

            self.__load_commands.append(load_command)

    @property
    def all(self):
        return self.__load_commands

    @property
    def segment_commands(self) -> List[Segment64Command]:
        return [segment_command for segment_command in self.__load_commands if
                isinstance(segment_command, Segment64Command)]

    @property
    def dylib_commands(self) -> List[DylibCommand]:
        return [dylib_command for dylib_command in self.__load_commands if isinstance(dylib_command, DylibCommand)]

    def find(self, predicate=None) -> List[LoadCommand]:
        if predicate is None:
            return self.__load_commands

        matching_load_commands = []
        for load_command in self.__load_commands:
            if predicate(load_command):
                matching_load_commands.append(load_command)

        return matching_load_commands
