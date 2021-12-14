from construct import Int32ul, Struct, Hex, this, Tell, LazyArray, Computed
from hilda.snippets.macho.macho_load_commands import LOAD_COMMAND_TYPE, load_command_t


def __calculate_aslr(ctx):
    loaded_address = ctx.load_address
    for load_command in ctx.load_commands:
        if load_command.cmd == LOAD_COMMAND_TYPE.LC_SEGMENT_64 and load_command.data.segname == '__TEXT':
            return loaded_address - load_command.data.vmaddr


mach_header_t = Struct(
    'load_address' / Tell,
    'magic' / Hex(Int32ul),
    'cputype' / Hex(Int32ul),
    'cpusubtype' / Hex(Int32ul),
    'filetype' / Hex(Int32ul),
    'ncmds' / Hex(Int32ul),
    'sizeofcmds' / Hex(Int32ul),
    'flags' / Hex(Int32ul),
    'reserved' / Hex(Int32ul),
    'load_commands' / LazyArray(this.ncmds, load_command_t),
    'aslr' / Computed(__calculate_aslr)
)
