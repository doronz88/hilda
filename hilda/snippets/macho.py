import lldb
from construct import Enum, Int32ul, Struct, Hex, Pointer, PaddedString, this, Int64ul, Tell, Switch, Bytes, Seek, \
    LazyArray, Computed

from hilda.symbol import SymbolFormatField

LOAD_COMMAND_TYPE = Enum(Int32ul,
                         LC_LOAD_DYLIB=0xc,
                         LC_SEGMENT_64=0x19)


def __calculate_aslr(ctx):
    loaded_address = ctx.load_address
    for load_command in ctx.load_commands:
        if load_command.cmd == LOAD_COMMAND_TYPE.LC_SEGMENT_64 and load_command.data.segname == '__TEXT':
            return loaded_address - load_command.data.vmaddr


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


__dylib = Struct(
    'lc_str' / __lc_str_from_load_command(this),
    'timestamp' / Int64ul,
    'current_version' / Int64ul,
    'compatibility_version' / Int64ul,
)

__dylib_load_command = Struct(
    'dylib' / __dylib,
)

__segment_command = Struct(
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

__load_command = Struct(
    '_start' / Tell,
    'cmd' / LOAD_COMMAND_TYPE,
    'cmdsize' / Int32ul,
    '_data_offset' / Tell,
    'data' / Switch(this.cmd, {
        LOAD_COMMAND_TYPE.LC_SEGMENT_64: __segment_command,
        LOAD_COMMAND_TYPE.LC_LOAD_DYLIB: __dylib_load_command,
    }, Bytes(this.cmdsize - (this._data_offset - this._start))),
    Seek(this._start + this.cmdsize),
)

mach_header = Struct(
    'load_address' / Tell,
    'magic' / Hex(Int32ul),
    'cputype' / Hex(Int32ul),
    'cpusubtype' / Hex(Int32ul),
    'filetype' / Hex(Int32ul),
    'ncmds' / Hex(Int32ul),
    'sizeofcmds' / Hex(Int32ul),
    'flags' / Hex(Int32ul),
    'reserved' / Hex(Int32ul),
    'load_commands' / LazyArray(this.ncmds, __load_command),
    'aslr' / Computed(__calculate_aslr)
)