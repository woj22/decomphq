"""Top-down map of an area coloured by the real top block of each column (after placement)."""
import os as _os
BASE = _os.environ.get('ELOSIA_DIR', '/home/user/elosia')
GEN = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'generator')

import sys, numpy as np, amulet
from PIL import Image, ImageDraw
x0, z0, x1, z1 = -420, -460, 420, 60
W = amulet.load_level(sys.argv[1] if len(sys.argv) > 1 else _os.path.join(BASE, 'work/Elosia'))
hm = np.load(_os.path.join(BASE, 'heightmap.npy')).astype(np.int32) + 63
O = 3072 + 16
COL = {'grass_block': (96, 150, 60), 'dirt': (120, 86, 56), 'coarse_dirt': (110, 80, 52), 'podzol': (90, 64, 34),
       'stone': (125, 125, 125), 'andesite': (130, 130, 130), 'gravel': (130, 124, 120), 'sand': (220, 208, 160),
       'water': (50, 90, 200), 'leaves': (52, 112, 40), 'log': (100, 76, 44), 'snow': (240, 240, 245),
       'snow_block': (240, 240, 245), 'farmland': (96, 64, 38), 'wheat': (214, 186, 92), 'carrots': (230, 140, 40),
       'potatoes': (190, 170, 90), 'beetroots': (160, 50, 60), 'deepslate_tiles': (54, 54, 58), 'calcite': (222, 224, 220),
       'amethyst_block': (140, 100, 200), 'mycelium': (112, 96, 112), 'moss_block': (90, 112, 46),
       'polished_deepslate': (72, 72, 74), 'quartz_block': (236, 230, 222), 'purpur_block': (170, 120, 170),
       'end_stone_bricks': (218, 224, 166), 'end_stone': (220, 222, 160), 'prismarine': (100, 160, 150),
       'honeycomb_block': (230, 160, 40), 'oxidized_copper': (82, 162, 132), 'nether_wart_block': (120, 20, 20),
       'warped_wart_block': (22, 120, 120), 'sea_lantern': (200, 230, 230), 'obsidian': (20, 16, 30),
       'mud_bricks': (140, 106, 80), 'stained_glass': (120, 160, 200), 'concrete': (200, 200, 200),
       'terracotta': (150, 90, 110), 'shroomlight': (240, 150, 70), 'end_rod': (240, 236, 230), 'plant': (90, 150, 60),
       'double_plant': (90, 150, 60), 'hay_block': (200, 170, 40), 'melon': (110, 150, 40), 'pumpkin': (210, 120, 30),
       'sweet_berry_bush': (60, 100, 50), 'cherry_leaves': (240, 170, 200), 'grass': (96, 150, 60)}
w, d = x1 - x0, z1 - z0
img = np.zeros((d, w, 3), np.uint8)
hs = np.zeros((d, w), np.int32)
for cx in range(x0 >> 4, (x1 >> 4) + 1):
    for cz in range(z0 >> 4, (z1 >> 4) + 1):
        try:
            ch = W.get_chunk(cx, cz, 'minecraft:overworld')
        except Exception:
            continue
        names = [b.base_name for b in ch.block_palette]
        cols = [COL.get(n, (255, 0, 255) if n not in ('air', 'cave_air') else None) for n in names]
        top = int(hm[O + cz * 16:O + cz * 16 + 16, O + cx * 16:O + cx * 16 + 16].max()) + 60
        arr = np.asarray(ch.blocks[0:16, -20:min(top, 319), 0:16])
        for lx in range(16):
            for lz in range(16):
                wx, wz = cx * 16 + lx, cz * 16 + lz
                if not (x0 <= wx < x1 and z0 <= wz < z1):
                    continue
                colm = arr[lx, :, lz]
                for k in range(len(colm) - 1, -1, -1):
                    c = cols[colm[k]]
                    if c is not None:
                        img[wz - z0, wx - x0] = c
                        hs[wz - z0, wx - x0] = k
                        break
gy, gx = np.gradient(hs.astype(float))
shade = np.clip(1 - (gx + gy) * 0.06, 0.65, 1.25)
img = (img * shade[..., None]).clip(0, 255).astype(np.uint8)
im = Image.fromarray(img).resize((w * 2, d * 2), Image.NEAREST)
dr = ImageDraw.Draw(im)
px = lambda x, z: ((x - x0) * 2, (z - z0) * 2)
dr.ellipse([*[v - 6 for v in px(0, 0)], *[v + 6 for v in px(0, 0)]], outline=(255, 40, 40), width=3)
dr.text((px(0, 0)[0] + 8, px(0, 0)[1] - 6), 'spawn 0,0', fill=(255, 255, 255))
for name, x, z in [('Lumen Hollow', 4, -108), ('Spireholm', -142, -230), ('Hive Ring', 282, -218),
                   ('Sunwheat Plains', 40, -314), ('Terrace Rings', -230, -106)]:
    p = px(x, z)
    dr.rectangle([p[0] - 60, p[1] - 108, p[0] + 60, p[1] - 92], fill=(0, 0, 0))
    dr.text((p[0] - 56, p[1] - 106), f'{name} ({x},{z})', fill=(255, 255, 255))
im.save(sys.argv[2] if len(sys.argv) > 2 else _os.path.join(BASE, 'city_map.png'))
print('ok', im.size)
