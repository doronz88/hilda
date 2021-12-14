import logging

import lldb
from construct import Struct, Tell, Int32ul, Pointer, this, Array, Int32ub, CString, If, Int64ul, Hex
from humanfriendly import prompts

from hilda.snippets.macho.image_info import dyld_image_info_t, ImageInfo
from hilda.snippets.macho.macho import mach_header_t
from hilda.snippets.uuid import uuid_t
from hilda.symbol import SymbolFormatField

all_image_infos_t = Struct(
    'address' / Tell,
    'version' / Int32ul,
    'infoArrayCount' / Int32ul,
    '_infoArray' / SymbolFormatField(lldb.hilda_client),
    'infoArray' / Pointer(this._infoArray, Array(this.infoArrayCount, dyld_image_info_t)),
    'notification' / SymbolFormatField(lldb.hilda_client),
    'processDetachedFromSharedRegion' / Int32ub,
    'libSystemInitialized' / Int32ub,
    '_dyldImageLoadAddress' / SymbolFormatField(lldb.hilda_client),
    'dyldImageLoadAddress' / Pointer(this._dyldImageLoadAddress, mach_header_t),
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
                     Pointer(this._uuidArray, Array(this.uuidArrayCount, uuid_t))),
    '_dyld_all_image_infos' / SymbolFormatField(lldb.hilda_client),
    # 'dyld_all_image_infos' / Lazy(LazyBound(lambda: Pointer(this._dyld_all_image_infos, self.all_image_infos))),
    'initialImageCount' / Int64ul,
    'errorKind' / Int64ul,
    '_errorClientOfDyLibPath' / SymbolFormatField(lldb.hilda_client),
    'errorClientOfDyLibPath' / If(this._errorClientOfDyLibPath != 0,
                                  Pointer(this._errorClientofoyLibPath, CString('utf8'))),
    '_errorTargetDylibPath' / SymbolFormatField(lldb.hilda_client),
    'errorTargetDylibPath' / If(this._errorTargetDylibPath != 0, Pointer(this._errorTargetDylibPath, CString('utf8'))),
    '_errorSymbol' / SymbolFormatField(lldb.hilda_client),
    'errorSymbol' / If(this._errorSymbol != 0, Pointer(this._errorSymbol, CString('utf8'))),
    'sharedCacheSlide' / Hex(Int64ul),
)


class AllImageInfos(object):
    def reload(self):
        with lldb.hilda_client.stopped(1):
            all_image_infos_symbol = lldb.hilda_client.symbol(lldb.hilda_client.symbols.dyld_all_image_infos)
            self.__all_image_infos = all_image_infos_t.parse_stream(all_image_infos_symbol)
            self.__image_infos = []

            for image_info_data in self.__all_image_infos.infoArray:
                image_info = ImageInfo(image_info_data)
                self.__image_infos.append(image_info)

    def __init__(self):
        self.__all_image_infos = None
        self.__image_infos = None

        self.reload()

    @property
    def images(self):
        return self.__image_infos

    def find_images(self, name):
        return [image for image in self.images if name in image.file_path]

    def image_dependencies(self, image_name):
        images = [image for image in self.find_images(image_name)]

        if len(images) == 0:
            # This is a time consuming action. We only do it in
            # because a library could be dynamically opened
            self.reload()
            images = [image for image in self.find_images(image_name)]

            if len(images) == 0:
                print(f"Image {image_name} is not loaded")
                return

        return AllImageInfos.__image_dependencies(images)

    @staticmethod
    def __image_dependencies(images):
        unique_images = []

        for image in images:
            if image.file_path not in [unique_image.file_path for unique_image in unique_images]:
                unique_images.append(image)

        image = unique_images[0]
        if len(unique_images) > 1:
            image = AllImageInfos.__select_specific_image(unique_images)

        dependencies = set([image_name.path for image_name in image.load_commands.dylib_commands])

        return dependencies

    @staticmethod
    def __select_specific_image(images):
        logging.info('Multiple images were found with that prefix.\nPlease select one')
        print([f"{image.file_path}" for image in images])
        selected_image_path = prompts.prompt_for_choice([f"{image.file_path}" for image in images])
        for image in images:
            if image.file_path == selected_image_path:
                return image
