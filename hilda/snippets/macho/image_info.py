from construct import CString, If, Int64ul, Pointer, Struct, this

from hilda.lldb_importer import lldb
from hilda.snippets.macho.macho import mach_header_t
from hilda.snippets.macho.macho_load_commands import LoadCommands
from hilda.snippets.uuid import uuid_t
from hilda.symbol import SymbolFormatField

dyld_image_info_t = Struct(
    '_imageLoadAddress' / SymbolFormatField(lldb.hilda_client),
    'imageLoadAddress' / Pointer(this._imageLoadAddress, mach_header_t),
    '_imageFilePath' / SymbolFormatField(lldb.hilda_client),
    'imageFilePath' / Pointer(this._imageFilePath, CString('utf8')),
    'imageFileModDate' / Int64ul
)

dyld_uuid_info_t = Struct(
    '_imageLoadAddress' / SymbolFormatField(lldb.hilda_client),
    'imageLoadAddress' / If(this._imageLoadAddress != 0, Pointer(this._imageLoadAddress,
                                                                 mach_header_t)),
    'imageUUID' / uuid_t
)


class ImageInfo(object):
    def __init__(self, image_info_data):
        self.__image_info_data = image_info_data
        self.__file_path = image_info_data.imageFilePath
        self.__image_mach_header = image_info_data.imageLoadAddress
        self.__load_commands = None

    @property
    def file_path(self):
        return self.__file_path

    @property
    def load_commands(self):
        if self.__load_commands is None:
            self.__load_commands = LoadCommands(self.__image_mach_header.load_commands)

        return self.__load_commands

    def __str__(self):
        return f"<ImageInfo: {self.file_path}>"

    def __repr__(self):
        return self.__str__()
