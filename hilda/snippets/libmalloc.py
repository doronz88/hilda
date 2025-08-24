from construct import Array, BitsInteger, BitStruct, Bytes, Enum, Flag, Hex, Int32ul, Int64ul, Padding, Struct, Tell

from hilda.lldb_importer import lldb
from hilda.symbol import SymbolFormatField

malloc_zone_t = Struct(
    'RESERVED_1_CFALLOCATOR' / Hex(Int64ul),
    'RESERVED_2_CFALLOCATOR' / Hex(Int64ul),
    'size' / SymbolFormatField(lldb.hilda_client),
    'malloc' / SymbolFormatField(lldb.hilda_client),
    'calloc' / SymbolFormatField(lldb.hilda_client),
    'valloc' / SymbolFormatField(lldb.hilda_client),
    'free' / SymbolFormatField(lldb.hilda_client),
    'realloc' / SymbolFormatField(lldb.hilda_client),
    'destroy' / SymbolFormatField(lldb.hilda_client),
    'zone_name' / SymbolFormatField(lldb.hilda_client),
    'batch_malloc' / SymbolFormatField(lldb.hilda_client),
    'batch_free' / SymbolFormatField(lldb.hilda_client),
    'introspect' / SymbolFormatField(lldb.hilda_client),
    'version' / SymbolFormatField(lldb.hilda_client),
    'memalign' / SymbolFormatField(lldb.hilda_client),
    'free_definite_size' / SymbolFormatField(lldb.hilda_client),
    'pressure_relief' / SymbolFormatField(lldb.hilda_client),
    'claimed_address' / SymbolFormatField(lldb.hilda_client),
    'try_free_default' / SymbolFormatField(lldb.hilda_client),
    'malloc_with_options' / SymbolFormatField(lldb.hilda_client),
    'malloc_type_malloc' / SymbolFormatField(lldb.hilda_client),
    'malloc_type_calloc' / SymbolFormatField(lldb.hilda_client),
    'malloc_type_realloc' / SymbolFormatField(lldb.hilda_client),
    'malloc_type_memalign' / SymbolFormatField(lldb.hilda_client),
    'malloc_type_malloc_with_options' / SymbolFormatField(lldb.hilda_client),
)

nanov2_statistics_t = Struct(
    'allocated_regions' / Hex(Int32ul),
    'region_addresses_clhashes' / Hex(Int32ul),
    # 'size_class_statistics' / Array(16, nanov2_size_class_statistics)
)

nanozonev2_s = Struct(
    'address' / Tell,
    'basic_zone' / malloc_zone_t,
    # pad used to mprotect the first page
    Padding(0x4000 - malloc_zone_t.sizeof()+32),
    # metadata of arena blocks
    'current_block' / Hex(Int64ul),
    # current_block_lock omitted
    Padding(0x2fd4),
    'delegate_allocations' / Hex(Int32ul),
    'debug_flags' / Hex(Int64ul),
    'aslr_cookie' / Hex(Int64ul),
    'aslr_cookie_aligned' / Hex(Int64ul),
    'slot_freelist_cookies' / Hex(Int64ul),
    'helper_zone' / Hex(Int64ul),
    'block_lock' / Hex(Int32ul),
    'regions_lock' / Hex(Int32ul),
    'first_region_base_ptr' / Hex(Int64ul),
    'current_region_next_arena' / Hex(Int64ul),
    'madvise_lock' / Hex(Int64ul),
    'nanov2_statistics_t' / nanov2_statistics_t
)

nanov2_size_class_statistics = Struct(
    'total_allocations' / Hex(Int64ul),
    'total_frees' / Hex(Int64ul),
    'madvised_blocks' / Hex(Int64ul),
    'madvise_races' / Hex(Int64ul),
)


class NanoV2Zone:

    def __init__(self, nanov2_base_addr, helper_zone_ptr):
        self.nanov2_base_addr = nanov2_base_addr
        self.nanov2_struct = nanozonev2_s.parse_stream(self.nanov2_base_addr)
        if not self._sanity_check(helper_zone_ptr):
            self.nanov2_struct = None

    def _sanity_check(self, helper_zone_ptr):
        return helper_zone_ptr == int(str(self.nanov2_struct.helper_zone), 16)

    def get_nanov2_struct(self):
        return self.nanov2_struct


class NanoV2Arena:
    # You would have to iterate for 64 times to dump everything. But not going to dump 64MB...
    # Found at nanov2_malloc.c
    size_per_slot = [16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256]
    blocks_per_size = [2, 10, 11, 10, 5, 3, 3, 4, 3, 2, 2, 2, 2, 2, 1, 2]
    slots_per_size = [1024, 512, 341, 256, 204, 170, 146, 128, 113, 102, 93, 85, 78, 73, 68, 64]

    def __init__(self, arena_base_addr):
        self.nanov2_arena_struct = Struct(
            # Note that this only parses 1 CPU memblock (1MB). Modify it to be 64.
            *[
                f"blocks_{idx}" / Array(self.blocks_per_size[idx],
                                        Struct('content' /
                                               Array(self.slots_per_size[idx],
                                                     Struct('Q' / Bytes(self.size_per_slot[idx])
                                                            )
                                                     )
                                               ))
                for idx in range(len(self.blocks_per_size))
            ]
        )
        self.arena_struct = self.nanov2_arena_struct.parse_stream(arena_base_addr)

    def get_arena_struct(self):
        return self.arena_struct


class NanoV2ArenaMetadataBlock:
    # This is used by libmalloc to store the metadata of the arena blocks which is used during allocations.
    # It is a matrix because we have a list of block sizes * CPU_NUMBER.

    NEXT_SLOT = Enum(BitsInteger(11),
                     SLOT_NULL=0,
                     SLOT_GUARD=0x7fa,
                     SLOT_BUMP=0x7fb,
                     SLOT_FULL=0x7fc,
                     SLOT_CAN_MADVISE=0x7fd,
                     SLOT_MADVISING=0x7fe,
                     SLOT_MADVISED=0x7ff
                     )

    block_meta_t = BitStruct(
        'in_use' / Flag,
        'gen_count' / Hex(BitsInteger(10)),
        'free_count' / Hex(BitsInteger(10)),
        'next_slot' / NEXT_SLOT,
    )

    def __init__(self, curr_block_addr):
        self.nanov2_arena_metablock_t = Struct(
            # We can't directly parse the block_meta with the CStruct.
            # It has to be Int32ul first because BitStruct does not handle unalignment properly.
            "arena_block_meta" / Array(4096, Hex(Int32ul))
        )
        self.curr_block_addr = curr_block_addr
        self.arena_metadata_block = self.nanov2_arena_metablock_t.parse_stream(curr_block_addr)

    def dump_arena_metadata_block(self):
        block_idx = 0
        for meta_block in self.arena_metadata_block.arena_block_meta:
            hex_meta_contents = str(meta_block)[2:]
            block_meta_struct = self.block_meta_t.parse(bytes.fromhex(hex_meta_contents))
            if block_meta_struct.in_use:
                print(f"Arena block index {block_idx} (CPU {int(block_idx / 64) - 1}): next: {block_meta_struct.next_slot}")
            block_idx = block_idx + 1


RACK_TYPE = Enum(Int32ul,
                 RACK_TYPE_NONE=0,
                 RACK_TYPE_TINY=1,
                 RACK_TYPE_SMALL=2,
                 RACK_TYPE_MEDIUM=3
                 )

region_hash_generation_t = Struct(
    'num_regions_allocated' / Hex(Int64ul),
    'num_regions_allocated_shift' / Hex(Int64ul),
    'hashed_regions_ptr' / Hex(Int64ul),
    'nextgen_ptr' / Hex(Int64ul),
)

rack_s = Struct(
    # Keep in mind this struct is MALLOC_CACHE_ALIGN(128) aligned.
    'address' / Tell,
    'region_lock' / Hex(Int32ul),
    'type' / RACK_TYPE,
    'num_regions' / Hex(Int64ul),
    'num_regions_dealloc' / Hex(Int64ul),
    'region_generation_ptr' / Hex(Int64ul),
    'rg' / Array(2, region_hash_generation_t),
    'initial_regions' / Array(64, Hex(Int64ul)),
    'num_magazines' / Hex(Int32ul),
    'num_magazines_mask' / Hex(Int32ul),
    'num_magazines_mask_shift' / Hex(Int32ul),
    'debug_flags' / Hex(Int32ul),
    'magazines' / Hex(Int64ul),
    'cookie' / Hex(Int64ul),
    'last_madvise' / Hex(Int64ul),
)

szone_t = Struct(
    'address' / Tell,
    'basic_zone' / malloc_zone_t,
    # it seems like the offset is 0x4068 from the start of the basic_zone to the tiny rack
    Padding(0x4000 - malloc_zone_t.sizeof() + 0x68),
    'cpu_id_key' / Hex(Int64ul),
    'debug_flags' / Hex(Int64ul),
    'log_address' / Hex(Int64ul),
    'tiny_rack' / rack_s,
    Padding(0x78),
    'small_rack' / rack_s,
    Padding(0x78),
    'medium_rack' / rack_s,
    'large_szone_lock' / Hex(Int32ul),
    'num_large_objects_in_use' / Hex(Int32ul),
    'num_large_entries' / Hex(Int32ul),
    'large_entries' / Hex(Int64ul),
    'num_bytes_in_large_objects' / Hex(Int64ul),
    # for macOS, CONFIG_LARGE_CACHE is True. For iOS is False (TODO)
)


class HelperZone:
    def __init__(self, helper_zone_ptr):
        self.szone_struct = szone_t.parse_stream(helper_zone_ptr)

    def get_helper_zone(self):
        return self.szone_struct


def _get_nanov2_zone():
    hilda = lldb.hilda_client
    default_nanozone_ptr = hilda.symbols.malloc_zones[0][0]
    # we need the helper_zone_ptr to perform a sanity check on the parsing.
    helper_zone_ptr = hilda.symbols.malloc_zones[0][1]
    return NanoV2Zone(default_nanozone_ptr, helper_zone_ptr)


def dump_helper_zone():
    hilda = lldb.hilda_client
    helper_zone_ptr = hilda.symbols.malloc_zones[0][1]
    helper_zone = HelperZone(helper_zone_ptr)
    print(helper_zone.get_helper_zone())


def dump_nanov2_zone():
    nano_zone_class = _get_nanov2_zone()
    print(nano_zone_class.get_nanov2_struct())


def dump_used_arena():
    """
    Arena first block is the metadata
    Afterwards, arena consists of 64 logical blocks (1 per each CPU) that each of them is 1MB.
    Each CPU mem block is -> blocks_per_size = [2,10,11,10,5,3,3,4,3,2,2,2,2,2,1,2] -> 64 blocks
    Something like this:

    (remember, 1 block is 16k)
        ----------------------------------
        ARENA_METADATA_BLOCK - 16K
        ----------------------------------
                    (it is inline, this arrow is not a ptr. just drawing purposes.)
        CPU_0_MEM_BLOCK - 1MB -----------> | BLOCK_16 * 2
                                           BLOCK_32 * 10
                                           BLOCK_48 * 11
                                           .... (check blocks_per_size)
        ----------------------------------
        CPU_1_MEM_BLOCK - 1MB
        ----------------------------------
        CPU_X_MEM_BLOCK - 1MB (There are up to 64!)
        ----------------------------------

        Which makes an arena 64CPU mem blocks * 1 mb = 64mb + arena metadata block = 65mb.
        A region consists of 8 arenas which results in 64mb * 8 = 512mb (no metadata accounted)
    """

    # Note there can be up to NANOV2_ARENAS_PER_REGION arenas (8). We will only dump 1 of them.
    hilda = lldb.hilda_client
    nano_zone_class = _get_nanov2_zone()
    # arena base addr is always 0x0000600000000000 + aslr_cookie_enabled + 0x4000 (first block is the arena metablock)
    first_region_base_ptr_int = int(str(nano_zone_class.get_nanov2_struct().first_region_base_ptr), 16)
    aslr_cookie_aligned_int = int(str(nano_zone_class.get_nanov2_struct().aslr_cookie_aligned), 16)
    arena_addr = first_region_base_ptr_int + aslr_cookie_aligned_int + 0x4000
    nanov2_arena_struct = NanoV2Arena(hilda.symbol(arena_addr))
    with open('/tmp/arena_contents.txt', 'w') as arena_dump_file:
        print("Dumping 1MB of arena (CPU_0 mem block) contents into /tmp/arena_contents.txt.")
        arena_dump_file.write(str(nanov2_arena_struct.get_arena_struct()))


def dump_nanov2_block_metadata():
    # The metadata block is the first logical block in the arena. Arena metadata is at arena_addr + aslr_cookie_aligned
    hilda = lldb.hilda_client
    nano_zone_class = _get_nanov2_zone()
    first_region_base_ptr_int = int(str(nano_zone_class.get_nanov2_struct().first_region_base_ptr), 16)
    aslr_cookie_aligned_int = int(str(nano_zone_class.get_nanov2_struct().aslr_cookie_aligned), 16)
    metadata_addr = first_region_base_ptr_int + aslr_cookie_aligned_int
    print(f"Arena metadata can be found at {metadata_addr:x}")
    current_block_symbol = hilda.symbol(metadata_addr)
    meta_block_class = NanoV2ArenaMetadataBlock(current_block_symbol)
    meta_block_class.dump_arena_metadata_block()
