"""Top-down map of a Bedrock world: the top block of every column, coloured by block type and hill-shaded."""
import re, struct, sys, time
import numpy as np
import leveldb
from PIL import Image

NAME_RE = re.compile(rb'\x08\x04\x00name(..)', re.S)

def colour(name):
    n = name.replace('minecraft:', '')
    rules = [
        ('water', (52, 92, 170)), ('ice', (150, 180, 230)), ('snow', (240, 244, 248)), ('lava', (220, 90, 20)),
        ('grass_block', (98, 140, 58)), ('grass_path', (150, 125, 70)), ('dirt_path', (150, 125, 70)),
        ('short_grass', (98, 140, 58)), ('tall_grass', (98, 140, 58)), ('fern', (80, 130, 55)), ('grass', (98, 140, 58)),
        ('leaves', (58, 100, 40)), ('azalea', (80, 120, 50)), ('vine', (60, 100, 40)), ('moss', (90, 120, 50)), ('lily', (50, 110, 50)),
        ('kelp', (40, 90, 60)), ('seagrass', (40, 90, 60)), ('podzol', (110, 80, 40)), ('mycelium', (120, 100, 110)),
        ('farmland', (110, 75, 45)), ('wheat', (200, 180, 80)), ('carrots', (90, 150, 40)), ('potatoes', (90, 140, 40)), ('hay', (190, 160, 50)),
        ('red_sand', (190, 105, 40)), ('sandstone', (216, 203, 155)), ('sand', (219, 207, 163)), ('gravel', (130, 125, 120)), ('clay', (160, 166, 178)),
        ('mud', (70, 60, 55)), ('terracotta', (160, 100, 75)), ('hardened_clay', (160, 100, 75)),
        ('red_', (150, 50, 40)), ('brick', (150, 90, 75)), ('nether', (100, 40, 40)), ('copper', (190, 110, 80)),
        ('quartz', (235, 229, 220)), ('calcite', (225, 225, 220)), ('white', (225, 225, 220)), ('diorite', (190, 190, 190)),
        ('deepslate', (80, 80, 85)), ('blackstone', (45, 40, 45)), ('basalt', (80, 80, 85)), ('andesite', (135, 135, 136)),
        ('granite', (150, 105, 85)), ('tuff', (110, 110, 100)), ('cobble', (120, 120, 120)), ('stone', (125, 125, 125)),
        ('spruce', (100, 75, 45)), ('dark_oak', (65, 45, 25)), ('oak', (160, 128, 78)), ('birch', (192, 175, 121)), ('acacia', (170, 92, 52)),
        ('jungle', (160, 115, 81)), ('mangrove', (120, 55, 50)), ('cherry', (225, 170, 170)), ('bamboo', (190, 170, 80)), ('crimson', (120, 50, 70)),
        ('warped', (40, 110, 110)), ('planks', (150, 120, 75)), ('log', (100, 80, 50)), ('wood', (100, 80, 50)),
        ('wool', (210, 210, 210)), ('carpet', (210, 210, 210)), ('concrete', (200, 200, 200)), ('glass', (190, 210, 220)),
        ('gold', (230, 190, 60)), ('iron', (200, 200, 200)), ('flower', (200, 80, 80)), ('rose', (200, 50, 50)), ('tulip', (220, 120, 80)),
        ('dandelion', (230, 210, 60)), ('poppy', (200, 40, 40)), ('pumpkin', (220, 130, 30)), ('melon', (110, 150, 50)), ('cactus', (60, 120, 50)),
        ('sugar_cane', (130, 170, 90)), ('reeds', (130, 170, 90)), ('mushroom', (150, 110, 90)), ('slab', (150, 150, 150)), ('stairs', (150, 150, 150)),
        ('wall', (130, 130, 130)), ('fence', (140, 110, 70)), ('torch', (240, 200, 90)), ('lantern', (240, 190, 90)), ('bedrock', (50, 50, 50)),
    ]
    for k, c in rules:
        if k in n:
            if k in ('wool', 'carpet', 'concrete', 'terracotta', 'stained_glass'):
                pass
            return c
    return (140, 140, 140)

DYE = {'white': (225, 225, 220), 'orange': (220, 120, 40), 'magenta': (180, 70, 170), 'light_blue': (110, 160, 210), 'yellow': (230, 200, 50),
       'lime': (120, 180, 50), 'pink': (220, 140, 160), 'gray': (70, 72, 76), 'light_gray': (150, 150, 145), 'silver': (150, 150, 145), 'cyan': (30, 130, 140),
       'purple': (110, 40, 160), 'blue': (50, 60, 150), 'brown': (110, 75, 45), 'green': (80, 105, 40), 'red': (150, 40, 35), 'black': (30, 30, 34)}

def colour2(name):
    n = name.replace('minecraft:', '')
    for d in sorted(DYE, key=len, reverse=True):
        if n.startswith(d + '_') and any(k in n for k in ('wool', 'carpet', 'concrete', 'terracotta', 'glass', 'shulker', 'bed', 'candle')):
            c = DYE[d]
            return tuple(int(v * 0.85) for v in c) if 'terracotta' in n else c
    return colour(name)

def decode(buf):
    """Return (palette names, index array (16,16,16) as [x][z][y]) for storage layer 0 of a v8/v9 sub-chunk."""
    ver = buf[0]
    pos = 3 if ver == 9 else 2 if ver == 8 else 1
    hdr = buf[pos]; pos += 1
    bits = hdr >> 1
    if bits == 0:
        idx = np.zeros(4096, np.int64)
    else:
        per = 32 // bits; nw = -(-4096 // per)
        words = np.frombuffer(buf, dtype='<u4', count=nw, offset=pos); pos += nw * 4
        idx = ((words[:, None] >> (np.arange(per, dtype=np.uint32) * bits)) & ((1 << bits) - 1)).reshape(-1)[:4096].astype(np.int64)
    n = struct.unpack_from('<i', buf, pos)[0]; pos += 4
    names = []
    for m in NAME_RE.finditer(buf, pos):
        L = struct.unpack('<H', m.group(1))[0]
        names.append(buf[m.end():m.end() + L].decode('utf-8', 'replace'))
        if len(names) == n:
            break
    return names, idx.reshape(16, 16, 16)

def main(dbpath, out, x0c, z0c, x1c, z1c):
    t = time.time()
    db = leveldb.LevelDB(dbpath)
    W, H = (x1c - x0c) * 16, (z1c - z0c) * 16
    rgb = np.zeros((H, W, 3), np.uint8)
    hgt = np.zeros((H, W), np.int16)
    water = np.zeros((H, W), bool)
    cache = {}
    n = 0
    for k, v in db.iterate(start=struct.pack('<ii', -10**9, -10**9)) if False else db.iterate():
        if len(k) != 9 or k[8] != 0x2B:
            continue
        cx, cz = struct.unpack_from('<ii', k)
        if not (x0c <= cx < x1c and z0c <= cz < z1c):
            continue
        hm = np.frombuffer(v, dtype='<i2', count=256).reshape(16, 16)    # index [z][x]
        top = hm.astype(np.int32) - 64 - 1
        subs = {}
        for zz in range(16):
            for xx in range(16):
                y = int(top[zz, xx])
                found = None
                for yy in range(y, max(y - 24, -64), -1):
                    sy = yy >> 4
                    if sy not in subs:
                        try:
                            subs[sy] = decode(db.get(struct.pack('<iiBb', cx, cz, 0x2F, sy)))
                        except Exception:
                            subs[sy] = None
                    s = subs[sy]
                    if s is None:
                        continue
                    names, idx = s
                    nm = names[idx[xx, zz, yy & 15]] if idx[xx, zz, yy & 15] < len(names) else 'minecraft:air'
                    if nm.endswith(':air') or 'light_block' in nm or 'structure_void' in nm or 'barrier' in nm:
                        continue
                    found = (nm, yy)
                    break
                px, pz = (cx - x0c) * 16 + xx, (cz - z0c) * 16 + zz
                if found:
                    nm, yy = found
                    if nm not in cache:
                        cache[nm] = colour2(nm)
                    rgb[pz, px] = cache[nm]
                    hgt[pz, px] = yy
                    water[pz, px] = 'water' in nm
        n += 1
        if n % 20000 == 0:
            print(n, 'chunks %.0fs' % (time.time() - t), flush=True)
    # hill shading (light from the north-west) and gentle height tint
    h = hgt.astype(np.float32)
    gx = np.roll(h, 1, 1) - h; gz = np.roll(h, 1, 0) - h
    shade = np.clip(1.0 + (gx + gz) * 0.06, 0.6, 1.35)
    shade[water] = 1.0
    depth = np.clip((h - 62) / 120.0, -0.3, 0.6)
    img = np.clip(rgb.astype(np.float32) * shade[..., None] * (1.0 + depth[..., None] * 0.25), 0, 255).astype(np.uint8)
    Image.fromarray(img).save(out)
    np.savez_compressed(out.replace('.png', '_height.npz'), h=hgt, water=water)
    print('done', n, 'chunks %.0fs' % (time.time() - t), 'block types', len(cache))

if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], int(a[3]), int(a[4]), int(a[5]), int(a[6]))
