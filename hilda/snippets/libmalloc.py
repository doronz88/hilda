from hilda.lldb_importer import lldb
from construct import Array, Hex, Int32ul, Int64ul, Struct, Padding, BitStruct, BitsInteger, Flag, Bytes, Enum

#This a research done by studying libmalloc sources: https://github.com/apple-oss-distributions/libmalloc.
#Special thanks to doronz88 and his amazing work on Hilda. This is for sure a hidden gem (or at least it was for me).
#Hope this code helps someone trying to make sense of libmalloc.

malloc_zone_t = Struct(
    'RESERVED_1_CFALLOCATOR' / Hex(Int64ul),
    'RESERVED_2_CFALLOCATOR' / Hex(Int64ul),
    'size' / Hex(Int64ul),
    'malloc' / Hex(Int64ul),
    'calloc' / Hex(Int64ul),
    'valloc' / Hex(Int64ul),
    'free' / Hex(Int64ul),
    'realloc' / Hex(Int64ul),
    'destroy' / Hex(Int64ul),
    'zone_name' / Hex(Int64ul),
    'batch_malloc' / Hex(Int64ul),
    'batch_free' / Hex(Int64ul),
    'introspect' / Hex(Int64ul),
    'version' / Hex(Int64ul),
    'memalign' / Hex(Int64ul),
    'free_definite_size' / Hex(Int64ul), #from here all these ptrs may exist depending on libmalloc version
    'pressure_relief' / Hex(Int64ul),
    'claimed_address' / Hex(Int64ul),
    'try_free_default' / Hex(Int64ul),
    'malloc_with_options' / Hex(Int64ul),
    'malloc_type_malloc' / Hex(Int64ul),
    'malloc_type_calloc' / Hex(Int64ul),
    'malloc_type_realloc' / Hex(Int64ul),
    'malloc_type_memalign' / Hex(Int64ul),
    'malloc_type_malloc_with_options' / Hex(Int64ul),
)

nanov2_statistics_t = Struct (
    'allocated_regions' / Hex(Int32ul),
    'region_addresses_hashes' / Hex(Int32ul),
    #leaving this commented for easier readiness of output. in case this is interesting just uncomment it :) 
    #'size_class_statistics'  / Array(16, nanov2_size_class_statistics) 
)

nanov2_zone = Struct(
    'basic_zone' / malloc_zone_t,
    Padding(0x4000 - malloc_zone_t.sizeof()+32), #pad used to mprotect the first page.
    'current_block' / Hex(Int64ul), #metadata of arena blocks
    Padding(0x2fd4), #current_block_lock omitted
    #'current_block_lock' / matrix of locks. irrelevant for us to study allocations,
    'delegate_allocations' / Hex(Int32ul),
    'debug_flags' / Hex(Int64ul), #debug_flags is at 0x7004
    'aslr_cookie' / Hex(Int64ul),  #0x7008
    'aslr_cookie_aligned' / Hex(Int64ul), #0x7010
    'slot_freelist_cookies' / Hex(Int64ul), #0x7018 
    'helper_zone' / Hex(Int64ul), #at 0x7020 offset
    'block_lock' / Hex(Int32ul), #at 0x7024 offset
    'regions_lock' / Hex(Int32ul), #at 0x7028 offset
    'first_region_base_ptr' / Hex(Int64ul), #at 0x7030 offset
    'current_region_next_arena' / Hex(Int64ul), #at 0x7038 offset
    'madvise_lock' / Hex(Int64ul), #at 0x7040 offset
    'nanov2_statistics_t' / nanov2_statistics_t #at 0x7048 offset
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
        self.nanov2_struct = nanov2_zone.parse_stream(self.nanov2_base_addr)
        if(not self.sanity_check(helper_zone_ptr)):
            self.nanov2_struct = None

    def sanity_check(self, helper_zone_ptr):
        #func used to check if parsing went ok. malloc_zones[1] contains a helper_zone ptr and we can verify if our struct parsing
        #nanozonev2 parsing went ok if helper_zone ptrs match
        return helper_zone_ptr == int(str(self.nanov2_struct.helper_zone),16)

    def get_nanov2_struct(self):
        return self.nanov2_struct


class NanoV2Arena:
    #Note that this only parses 1 CPU memblock (1MB). You would have to iterate for 64 times to dump everything. But not going to dump 64MB...
    #Found at nanov2_malloc.c
    size_per_slot = [16,32,48,64,80,96,112,128,144,160,176,192,208,224,240,256]
    blocks_per_size = [2,10,11,10,5,3,3,4,3,2,2,2,2,2,1,2]
    slots_per_size = [1024, 512, 341, 256, 204, 170, 146, 128, 113, 102, 93, 85, 78, 73, 68, 64]
    def __init__(self, arena_base_addr):
        self.nanov2_arena_struct = Struct(
            *[f"blocks_{idx}" / Array(self.blocks_per_size[idx], Struct('content' / Array(self.slots_per_size[idx], Struct('Q'/Bytes(self.size_per_slot[idx]))))) for idx in range(len(self.blocks_per_size))]
        )
        self.arena_struct = self.nanov2_arena_struct.parse_stream(arena_base_addr)
        
    def get_arena_struct(self):
        return self.arena_struct

class NanoV2ArenaMetadataBlock:
#This class is used to store the arena metadata block. This is used by libmalloc to store the metadata of the arena blocks which is used during allocations.
#It is a matrix because we have a list of block sizes * CPU_NUMBER so in case there's multithreading locks can be avoided. 
#Note that because we can still access the same block, a lock matrix is also stored in the nanozonev2 but we ignore that for our analysis.

    next_slot_enum = Enum(BitsInteger(11),
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
        'next_slot' / next_slot_enum,
    )

    def __init__(self, curr_block_addr):
        self.current_block_struct = Struct(
            #We can't directly parse the block_meta with the CStruct. It has to be Int32ul first because BitStruct does not handle unalignment properly.
            "arena_metablock" / Array(4096, Hex(Int32ul))
        )
        self.curr_block_addr = curr_block_addr
        self.current_block = self.current_block_struct.parse_stream(curr_block_addr)

    def dump_arena_metadata_block(self):
        curr_block = self.curr_block_addr #we need it to compute block addresses
        block_idx = 0
        for meta_block in self.current_block.arena_metablock:
            hex_meta_contents = str(meta_block)[2:]
            block_meta_struct = self.block_meta_t.parse(bytes.fromhex(hex_meta_contents))
            if(block_meta_struct.in_use):
                print(f"Arena block index {block_idx} (CPU {int(block_idx / 64) - 1}): next slot: {block_meta_struct.next_slot}")
            block_idx = block_idx + 1

    def get_current_block(self):
        return self.current_block


def _get_nanov2_zone():
    hilda = lldb.hilda_client
    default_nanozone_ptr = hilda.symbols.malloc_zones[0][0]
    helper_zone_ptr = hilda.symbols.malloc_zones[0][1]
    return NanoV2Zone(default_nanozone_ptr,helper_zone_ptr)

def dump_nanov2_zone():
    nano_zone_class = _get_nanov2_zone()
    print(nano_zone_class.get_nanov2_struct())

def dump_used_arena():
    #Arena first block is the metadata
    #Afterwards, arena consists of 64 logical blocks (1 per each CPU) that each of them is 1MB. This is used to avoid locking situations and improve performance.
    #Each CPU mem block is -> blocks_per_size = [2,10,11,10,5,3,3,4,3,2,2,2,2,2,1,2] -> 64 blocks
    #Something like this:
    """
    (remember, 1 block is 16k)
        ----------------------------------
        ARENA_METADATA_BLOCK - 16K
        ----------------------------------
                    (it is inline, this arrow is not a ptr)
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

    #Note there can be up to NANOV2_ARENAS_PER_REGION arenas (8). We will only dump 1 of them.
    hilda = lldb.hilda_client
    nano_zone_class = _get_nanov2_zone()
    #arena base addr is always 0x0000600000000000 + aslr_cookie_enabled + 0x4000 (first block is the arena metablock)
    arena_addr = int(str(nano_zone_class.get_nanov2_struct().first_region_base_ptr),16) + int(str(nano_zone_class.get_nanov2_struct().aslr_cookie_aligned),16) + 0x4000
    nanov2_arena_struct = NanoV2Arena(hilda.symbol(arena_addr))
    with open('/tmp/arena_contents.txt', 'w') as arena_dump_file:
        print("Dumping 1MB of arena (CPU_0 mem block) contents into /tmp/arena_contents.txt.")
        arena_dump_file.write(str(nanov2_arena_struct.get_arena_struct()))

def parse_nanov2_block_metadata():
    #The metadata block is the first logical block in the arena. Arena metadata is at arena_addr + aslr_cookie_aligned
    #Note that arena metadata block index would be need to transformed to know which cpu was allocated from and then get the block size within the cpu mem block
    hilda = lldb.hilda_client
    nano_zone_class = _get_nanov2_zone()
    metadata_addr = int(str(nano_zone_class.get_nanov2_struct().first_region_base_ptr),16) + int(str(nano_zone_class.get_nanov2_struct().aslr_cookie_aligned),16)
    print(f"Arena metadata can be found at {metadata_addr:x}")
    current_block_symbol = hilda.symbol(metadata_addr)
    meta_block_class = NanoV2ArenaMetadataBlock(current_block_symbol)
    meta_block_class.dump_arena_metadata_block()