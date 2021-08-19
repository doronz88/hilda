import lldb
from construct import *

from hilda.symbol import SymbolFormatField

LOAD_COMMAND_TYPE = Enum(Int32ul,
                         LC_LOAD_DYLIB=0xc,
                         LC_SEGMENT_64=0x19)


class MachOStructFactory(object):
    # for reference for all of the following structs please look at:
    # https://opensource.apple.com/source/xnu/xnu-792/EXTERNAL_HEADERS/mach-o/loader.h

    @staticmethod
    def calculate_aslr(ctx):
        loaded_address = ctx.load_address
        for load_command in ctx.load_commands:
            if load_command.cmd == LOAD_COMMAND_TYPE.LC_SEGMENT_64 and load_command.data.segname == '__TEXT':
                return loaded_address - load_command.data.vmaddr

    @staticmethod
    def mach_header():
        return Struct(
            'load_address' / Tell,
            'magic' / Hex(Int32ul),
            'cputype' / Hex(Int32ul),
            'cpusubtype' / Hex(Int32ul),
            'filetype' / Hex(Int32ul),
            'ncmds' / Hex(Int32ul),
            'sizeofcmds' / Hex(Int32ul),
            'flags' / Hex(Int32ul),
            'reserved' / Hex(Int32ul),
            'load_commands' / LazyArray(this.ncmds, MachOStructFactory.__load_command()),
            'aslr' / Computed(MachOStructFactory.calculate_aslr)
        )

    @staticmethod
    def __load_command():
        return Struct(
            '_start' / Tell,
            'cmd' / LOAD_COMMAND_TYPE,
            'cmdsize' / Int32ul,
            '_data_offset' / Tell,
            'data' / Switch(this.cmd, {
                LOAD_COMMAND_TYPE.LC_SEGMENT_64: MachOStructFactory.__segment_command(),
                LOAD_COMMAND_TYPE.LC_LOAD_DYLIB: MachOStructFactory.__dylib_load_command(),
            }, Bytes(this.cmdsize - (this._data_offset - this._start))),
            Seek(this._start + this.cmdsize),
        )

    @staticmethod
    def __segment_command():
        return Struct(
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

    @staticmethod
    def __dylib_load_command():
        return Struct(
            'dylib' / MachOStructFactory.__dylib(),
        )

    @staticmethod
    def __dylib():
        return Struct(
            'lc_str' / MachOStructFactory.__lc_str(),
            'timestamp' / Int64ul,
            'current_version' / Int64ul,
            'compatibility_version' / Int64ul,
        )

    @staticmethod
    def __lc_str():
        load_command = this._._._
        return Struct(
            # this struct appears as a union in apple's opensource, but is represented in an awful manner, whereas
            # they would treat both the `ptr` and `offset` members as offsets (and never as pointers),
            # so we changed this a bit into the struct that it should have been
            'offset' / Hex(Int32ul),
            '_pad' / Int32ul,
            'name' / Pointer(load_command._start + this.offset, PaddedString(load_command.cmdsize - this.offset, 'utf8')),
        )
