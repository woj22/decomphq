"""Place the alien villages and farmlands into the Elosia Bedrock world, fitted to its terrain.

Each place is levelled to the median ground height of its footprint (cut and fill), written in, and
blended back into the natural terrain over a 14-block skirt. Roads that follow the terrain link the
places to each other and to spawn.
"""
import math, sys, time
import numpy as np
sys.path.insert(0, '/home/user/decomphq/minecraft_alien/generator')
import amulet
from amulet.api.block import Block
from amulet_nbt import StringTag, IntTag, ByteTag
import vox
from layouts import LAYOUTS

WORLD = sys.argv[1] if len(sys.argv) > 1 else '/home/user/elosia/work/Elosia'
DIM = 'minecraft:overworld'
MARGIN = 14
SITES = [   # key, centre x, centre z  (chosen from the terrain survey: flat, dry, close to spawn)
    ('lumen_hollow', 4, -108),
    ('spireholm', -142, -230),
    ('hive_ring', 282, -218),
    ('sunwheat_plains', 40, -314),
    ('terrace_rings', -230, -106),
]
ROADS = [((0, -3), (4, -61)), ((4, -157), (40, -251)), ((-45, -108), (-175, -106)),
         ((-142, -183), (-110, -107)), ((53, -108), (282, -171))]
VEG = {'leaves', 'log', 'wood', 'plant', 'double_plant', 'vine', 'azalea', 'flowering_azalea', 'leaf_litter',
       'moss_carpet', 'pale_moss_carpet', 'glow_lichen', 'brown_mushroom', 'red_mushroom', 'sapling', 'snow',
       'sweet_berry_bush', 'cocoa', 'bamboo', 'sugar_cane', 'cactus', 'big_dripleaf', 'big_dripleaf_stem',
       'small_dripleaf', 'spore_blossom', 'hanging_roots', 'cave_vines', 'cave_vines_plant', 'bee_nest',
       'mushroom_stem', 'brown_mushroom_block', 'red_mushroom_block', 'pale_hanging_moss', 'firefly_bush',
       'bush', 'short_dry_grass', 'tall_dry_grass', 'wildflowers', 'pink_petals'}

t0 = time.time()
W = amulet.load_level(WORLD)
hm = np.load('/home/user/elosia/heightmap.npy').astype(np.int32) + 63
O = 3072 + 16
ver = W.translation_manager.get_version('bedrock', (1, 19, 0))
_uni = {}


def universal(name):
    if name not in _uni:
        full, states = vox.B[name]
        props = {}
        for k, val in states.items():
            if isinstance(val, vox.Byte):
                props[k] = ByteTag(int(val))
            elif isinstance(val, int):
                props[k] = IntTag(val)
            else:
                props[k] = StringTag(val)
        ns, base = full.split(':')
        u = ver.block.to_universal(Block(ns, base, props))[0]
        _uni[name] = u
    return _uni[name]


chunks = {}


def chunk(cx, cz):
    k = (cx, cz)
    if k not in chunks:
        chunks[k] = W.get_chunk(cx, cz, DIM)
    return chunks[k]


_flags = {}


def flags(ch):
    """Per-palette-index classification: 0 air, 1 vegetation, 2 water, 3 solid ground."""
    key = (id(ch), len(ch.block_palette))
    if key not in _flags:
        f = np.zeros(len(ch.block_palette), dtype=np.int8)
        for i, b in enumerate(ch.block_palette):
            n = b.base_name
            f[i] = 0 if n in ('air', 'cave_air', 'void_air') else 1 if n in VEG else 2 if n == 'water' else 3
        _flags[key] = f
    return _flags[key]


def column(wx, wz, y0, y1):
    ch = chunk(wx >> 4, wz >> 4)
    return ch, np.asarray(ch.blocks[wx & 15, y0:y1, wz & 15]).reshape(-1)


def ground(wx, wz):
    """Highest solid or water block, ignoring trees and plants. Returns (y, highest non-air y)."""
    est = hm[O + wz, O + wx]
    y1 = min(319, max(est + 12, 80))
    ch, col = column(wx, wz, -40, y1)
    f = flags(ch)[col]
    solid = np.nonzero(f >= 2)[0]
    anyb = np.nonzero(f >= 1)[0]
    g = -40 + (solid[-1] if len(solid) else 0)
    top = -40 + (anyb[-1] if len(anyb) else 0)
    return int(g), int(top)


def set_range(wx, wz, y0, y1, name):
    wx, wz, y0, y1 = int(wx), int(wz), int(y0), int(y1)
    if y1 < y0:
        return
    ch = chunk(wx >> 4, wz >> 4)
    idx = ch.block_palette.get_add_block(universal(name))
    ch.blocks[wx & 15, y0:y1 + 1, wz & 15] = idx
    ch.changed = True


def set_block(wx, wy, wz, name):
    set_range(wx, wz, wy, wy, name)


def place(key, cx, cz):
    v = LAYOUTS[key][0]()
    x0, z0 = cx - v.w // 2, cz - v.d // 2
    gnd = np.zeros((v.w, v.d), np.int32)
    tops = np.zeros((v.w, v.d), np.int32)
    for i in range(v.w):
        for j in range(v.d):
            gnd[i, j], tops[i, j] = ground(x0 + i, z0 + j)
    T = int(np.median(gnd))
    G = v.G
    base_y = int(T - G)
    lo = G - 4
    luts = {}
    keep_under = {v.ids.get('stone', -1), v.ids.get('dirt', -1)}
    for i in range(v.w):
        for j in range(v.d):
            wx, wz = x0 + i, z0 + j
            ch = chunk(wx >> 4, wz >> 4)
            if id(ch) not in luts:
                luts[id(ch)] = np.array([ch.block_palette.get_add_block(universal(n)) for n in v.names], dtype=np.uint32)
            lut = luts[id(ch)]
            g0 = int(gnd[i, j])
            if g0 < T - 4:   # fill up to the layout's foundation
                set_range(wx, wz, g0 + 1, T - 5, 'dirt')
            clear_top = max(tops[i, j], base_y + v.h - 1)
            if clear_top > base_y + v.h - 1:
                set_range(wx, wz, base_y + v.h, clear_top, 'air')
            col = v.a[i, lo:, j]
            existing = np.asarray(ch.blocks[wx & 15, base_y + lo:base_y + v.h, wz & 15]).reshape(-1)
            new = lut[col]
            under = (np.arange(lo, v.h) < G) & np.isin(col, list(keep_under))
            if g0 >= T:   # natural stone/dirt already there: keep it under the surface
                new = np.where(under, existing, new)
            ch.blocks[wx & 15, base_y + lo:base_y + v.h, wz & 15] = new.reshape(1, -1, 1)
            ch.changed = True
    # blend skirt back to the natural terrain
    for i in range(-MARGIN, v.w + MARGIN):
        for j in range(-MARGIN, v.d + MARGIN):
            if 0 <= i < v.w and 0 <= j < v.d:
                continue
            dx = max(-i, 0, i - (v.w - 1))
            dz = max(-j, 0, j - (v.d - 1))
            d = math.hypot(dx, dz)
            if d > MARGIN:
                continue
            wx, wz = x0 + i, z0 + j
            g0, top = ground(wx, wz)
            t = d / MARGIN
            w = t * t * (3 - 2 * t)
            gn = int(round(T * (1 - w) + g0 * w))
            if gn == g0:
                continue
            if gn < g0:
                set_range(wx, wz, gn + 1, max(top, g0), 'air')
                set_block(wx, gn, wz, 'grass')
            else:
                set_range(wx, wz, g0 + 1, max(top, gn), 'air')
                set_range(wx, wz, g0 + 1, gn - 1, 'dirt')
                set_block(wx, gn, wz, 'grass')
    return T


def road(a, b, width=3):
    ax, az = a
    bx, bz = b
    n = int(math.hypot(bx - ax, bz - az))
    pts = [(ax + (bx - ax) * k / n, az + (bz - az) * k / n) for k in range(n + 1)]
    hs = np.array([ground(round(x), round(z))[0] for x, z in pts], dtype=float)
    k = 9   # smooth the climb so steps stay walkable
    pad = np.pad(hs, k, mode='edge')
    sm = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    dx, dz = (bx - ax) / n, (bz - az) / n
    px, pz = -dz, dx
    for s, ((x, z), h) in enumerate(zip(pts, sm)):
        h = int(round(h))
        for o in range(-(width // 2), width // 2 + 1):
            wx, wz = round(x + px * o), round(z + pz * o)
            g0, top = ground(wx, wz)
            if g0 > h:
                set_range(wx, wz, h + 1, max(top, g0), 'air')
            else:
                set_range(wx, wz, h + 1, max(top, h + 3), 'air')
                set_range(wx, wz, g0 + 1, h - 1, 'dirt')
            set_block(wx, h, wz, 'deepslate_tiles')
            set_range(wx, wz, h + 1, h + 3, 'air')
        if s % 24 == 12:   # glow pylon beside the road
            wx, wz = round(x + px * (width // 2 + 2)), round(z + pz * (width // 2 + 2))
            g0, _ = ground(wx, wz)
            set_range(wx, wz, g0 + 1, g0 + 4, 'purpur_pillar')
            set_block(wx, g0 + 5, wz, 'sea_lantern')
            set_block(wx, g0 + 6, wz, 'end_rod')


levels = {}
for key, x, z in SITES:
    levels[key] = place(key, x, z)
    print(f'{key:16s} at ({x}, {z}) level y={levels[key]}  chunks loaded {len(chunks)}  {time.time() - t0:.0f}s', flush=True)
for a, b in ROADS:
    road(a, b)
print('roads done', round(time.time() - t0), 's; saving', sum(1 for c in chunks.values() if c.changed), 'chunks', flush=True)
W.save()
W.close()
print('saved', round(time.time() - t0), 's', levels)
