"""Export the edited areas of Elosia (sites, blended terrain, roads) as an add-on behaviour pack.

Each region is cut from the edited world into 64 x 64 .mcstructure tiles at absolute coordinates, with
prepare / build / finish functions, so it can be applied to anyone's own copy of the original Elosia world.
"""
import os as _os
BASE = _os.environ.get('ELOSIA_DIR', '/home/user/elosia')
GEN = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'generator')

import json, math, os, shutil, sys, zipfile
import numpy as np
sys.path.insert(0, GEN)
import amulet
from amulet_nbt import ByteTag, IntTag, StringTag, ShortTag
from nbt import Byte, IntList, dumps

EDITED = _os.path.join(BASE, 'work/Elosia')
OUT = _os.path.join(BASE, 'pack')
NS = 'elosia'
VERSION = (1, 21, 60)
BLOCK_VERSION = (VERSION[0] << 24) | (VERSION[1] << 16) | (VERSION[2] << 8)
TILE = 64
hm = np.load(_os.path.join(BASE, 'heightmap.npy')).astype(np.int32) + 63
O = 3072 + 16

# regions: (name, x0, z0, x1, z1) inclusive-exclusive, from the placement (site +/- (half + 16)) and road boxes
SITES = [('lumen_hollow', 4, -108, 96), ('spireholm', -142, -230, 96), ('hive_ring', 282, -218, 96),
         ('sunwheat_plains', 40, -314, 128), ('terrace_rings', -230, -106, 112)]
ROADS = [((0, -3), (4, -61)), ((4, -157), (40, -251)), ((-45, -108), (-175, -106)),
         ((-142, -183), (-110, -107)), ((53, -108), (282, -171))]
REGIONS = []
for name, x, z, s in SITES:
    h = s // 2 + 16
    REGIONS.append((name, x - h, z - h, x + h, z + h))
for k, ((ax, az), (bx, bz)) in enumerate(ROADS):
    REGIONS.append((f'road_{k + 1}', min(ax, bx) - 5, min(az, bz) - 5, max(ax, bx) + 6, max(az, bz) + 6))

W = amulet.load_level(EDITED)
ver = W.translation_manager.get_version('bedrock', VERSION)
_pal = {}


def to_entry(u):
    """Universal block -> (palette entry dict, waterlogged-layer entry or None)."""
    key = u
    if key in _pal:
        return _pal[key]
    out = []
    for blk in [u.base_block] + list(u.extra_blocks):
        b = ver.block.from_universal(blk)[0]
        states = {}
        for k, v in b.properties.items():
            if isinstance(v, ByteTag):
                states[k] = Byte(int(v.py_int))
            elif isinstance(v, (IntTag, ShortTag)):
                states[k] = int(v.py_int)
            else:
                states[k] = str(v.py_str) if hasattr(v, 'py_str') else str(v)
        out.append({'name': b.namespaced_name, 'states': states, 'version': BLOCK_VERSION})
    res = (out[0], out[1] if len(out) > 1 and 'water' in out[1]['name'] else None)
    _pal[key] = res
    return res


def export_region(name, x0, z0, x1, z1, sdir):
    # vertical range: from below the lowest ground (natural or levelled) to above the highest top
    sub = hm[O + z0:O + z1, O + x0:O + x1]
    y_lo = int(sub.min()) - 8
    y_hi = min(318, int(sub.max()) + 72)
    tiles = []
    for tx in range(x0, x1, TILE):
        for tz in range(z0, z1, TILE):
            w, d = min(TILE, x1 - tx), min(TILE, z1 - tz)
            h = y_hi - y_lo + 1
            arr = np.zeros((w, h, d), dtype=np.int32)
            arr2 = np.full((w, h, d), -1, dtype=np.int32)
            palette, pindex, pal2 = [], {}, {}
            for cx in range(tx >> 4, ((tx + w - 1) >> 4) + 1):
                for cz in range(tz >> 4, ((tz + d - 1) >> 4) + 1):
                    ch = W.get_chunk(cx, cz, 'minecraft:overworld')
                    lut = np.zeros(len(ch.block_palette), np.int32)
                    lut2 = np.full(len(ch.block_palette), -1, np.int32)
                    for i, u in enumerate(ch.block_palette):
                        e, e2 = to_entry(u)
                        k = json.dumps(e, sort_keys=True, default=int)
                        if k not in pindex:
                            pindex[k] = len(palette)
                            palette.append(e)
                        lut[i] = pindex[k]
                        if e2 is not None:
                            k2 = json.dumps(e2, sort_keys=True, default=int)
                            if k2 not in pindex:
                                pindex[k2] = len(palette)
                                palette.append(e2)
                            lut2[i] = pindex[k2]
                    blk = np.asarray(ch.blocks[0:16, y_lo:y_hi + 1, 0:16])
                    gx0, gz0 = cx * 16, cz * 16
                    ax0, az0 = max(gx0, tx), max(gz0, tz)
                    ax1, az1 = min(gx0 + 16, tx + w), min(gz0 + 16, tz + d)
                    part = blk[ax0 - gx0:ax1 - gx0, :, az0 - gz0:az1 - gz0]
                    arr[ax0 - tx:ax1 - tx, :, az0 - tz:az1 - tz] = lut[part]
                    arr2[ax0 - tx:ax1 - tx, :, az0 - tz:az1 - tz] = lut2[part]
                    for be in ch.block_entities:   # keep chests/spawners etc. as they are in the player's world
                        bx, by, bz = be.location if hasattr(be, 'location') else (be.x, be.y, be.z)
                        if tx <= bx < tx + w and tz <= bz < tz + d and y_lo <= by <= y_hi:
                            arr[bx - tx, by - y_lo, bz - tz] = -1
                            arr2[bx - tx, by - y_lo, bz - tz] = -1
            root = {'format_version': 1, 'size': [w, h, d],
                    'structure': {'block_indices': [IntList(arr.reshape(-1)), IntList(arr2.reshape(-1))],
                                  'entities': [], 'palette': {'default': {'block_palette': palette,
                                                                          'block_position_data': {}}}},
                    'structure_world_origin': [tx, y_lo, tz]}
            tname = f'{name}_{(tx - x0) // TILE}_{(tz - z0) // TILE}'
            with open(os.path.join(sdir, tname + '.mcstructure'), 'wb') as fh:
                fh.write(dumps(root))
            tiles.append((tname, tx, y_lo, tz))
    return tiles, y_lo, y_hi


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    sdir = os.path.join(OUT, 'structures', NS)
    os.makedirs(sdir)
    fdir = os.path.join(OUT, 'functions', NS)
    os.makedirs(fdir)
    allf = []
    for name, x0, z0, x1, z1 in REGIONS:
        tiles, y_lo, y_hi = export_region(name, x0, z0, x1, z1, sdir)
        d = os.path.join(fdir, name)
        os.makedirs(d)
        # ticking areas hold at most 100 chunks each: split long regions into pieces
        areas = []
        cx0, cz0, cx1, cz1 = x0 >> 4, z0 >> 4, (x1 - 1) >> 4, (z1 - 1) >> 4
        step = 9
        for ax in range(cx0, cx1 + 1, step):
            for az in range(cz0, cz1 + 1, step):
                areas.append((ax * 16, az * 16, min(cx1, ax + step - 1) * 16 + 15, min(cz1, az + step - 1) * 16 + 15))
        with open(os.path.join(d, 'prepare.mcfunction'), 'w') as fh:
            for i, (a0, b0, a1, b1) in enumerate(areas):
                fh.write(f'tickingarea add {a0} 0 {b0} {a1} 0 {b1} {NS}_{name}_{i} true\n')
            fh.write(f'say Loading {name}... wait ~10 seconds, then run /function {NS}/{name}/build\n')
        with open(os.path.join(d, 'build.mcfunction'), 'w') as fh:
            for tname, tx, ty, tz in tiles:
                fh.write(f'structure load {NS}:{tname} {tx} {ty} {tz}\n')
            fh.write(f'say {name} placed. Run /function {NS}/{name}/finish once it has appeared.\n')
        with open(os.path.join(d, 'finish.mcfunction'), 'w') as fh:
            for i in range(len(areas)):
                fh.write(f'tickingarea remove {NS}_{name}_{i}\n')
            fh.write(f'say {name} done.\n')
        allf.append((name, x0, z0, x1, z1, len(tiles), y_lo, y_hi, len(areas)))
        print(name, (x0, z0, x1, z1), 'tiles', len(tiles), 'y', y_lo, y_hi, 'ticking areas', len(areas), flush=True)
    manifest = {'format_version': 2,
                'header': {'name': 'Elosia: Alien City', 'description': 'Alien villages, farmlands and roads for the Elosia map. '
                           'Stand near each place: /function elosia/<place>/prepare, then build, then finish.',
                           'uuid': '5f0b7c2e-3a1d-4c8e-9b6f-2d4e8a1c7b30', 'version': [1, 0, 0],
                           'min_engine_version': [1, 21, 0]},
                'modules': [{'type': 'data', 'uuid': '8a3e1f9d-6c2b-4f7a-a5d0-3b9c1e7f2a46', 'version': [1, 0, 0]}]}
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=2)
    shutil.copy(_os.path.join(GEN, '..', 'maps', 'lumen_hollow_preview.png'), os.path.join(OUT, 'pack_icon.png'))
    mc = _os.path.join(BASE, 'Elosia_AlienCity_AddOn.mcpack')
    with zipfile.ZipFile(mc, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, OUT))
    json.dump(allf, open(_os.path.join(BASE, 'pack_regions.json'), 'w'))
    print('wrote', mc, round(os.path.getsize(mc) / 1e6, 2), 'MB')


main()
W.close()
