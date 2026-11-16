"""Voxel volume, Bedrock block palette, shape helpers, .mcstructure export and map/preview renders."""
import math
import numpy as np
from nbt import Byte, IntList, dumps

# Block states are written in the Bedrock 1.19.0 format and stamped with that version, so the game's
# block upgrader converts them to current names on load (e.g. wool{color} -> purple_wool, grass -> grass_block).
BLOCK_VERSION = (1 << 24) | (19 << 16)     # 1.19.0.0 = 18022400

B = {
    'air': ('minecraft:air', {}),
    'grass': ('minecraft:grass', {}),
    'dirt': ('minecraft:dirt', {'dirt_type': 'normal'}),
    'coarse': ('minecraft:dirt', {'dirt_type': 'coarse'}),
    'stone': ('minecraft:stone', {'stone_type': 'stone'}),
    'podzol': ('minecraft:podzol', {}),
    'mycelium': ('minecraft:mycelium', {}),
    'moss': ('minecraft:moss_block', {}),
    'farmland': ('minecraft:farmland', {'moisturized_amount': 7}),
    'water': ('minecraft:water', {'liquid_depth': 0}),
    'wheat': ('minecraft:wheat', {'growth': 7}),
    'wheat_young': ('minecraft:wheat', {'growth': 1}),
    'carrots': ('minecraft:carrots', {'growth': 7}),
    'potatoes': ('minecraft:potatoes', {'growth': 7}),
    'beetroot': ('minecraft:beetroot', {'growth': 7}),
    'melon': ('minecraft:melon_block', {}),
    'pumpkin': ('minecraft:pumpkin', {'direction': 0}),
    'berry': ('minecraft:sweet_berry_bush', {'growth': 3}),
    'hay': ('minecraft:hay_block', {'deprecated': 0, 'pillar_axis': 'y'}),
    'calcite': ('minecraft:calcite', {}),
    'tuff': ('minecraft:tuff', {}),
    'amethyst': ('minecraft:amethyst_block', {}),
    'deepslate_tiles': ('minecraft:deepslate_tiles', {}),
    'deepslate_bricks': ('minecraft:deepslate_bricks', {}),
    'pdeepslate': ('minecraft:polished_deepslate', {}),
    'blackstone': ('minecraft:blackstone', {}),
    'pbb': ('minecraft:polished_blackstone_bricks', {}),
    'obsidian': ('minecraft:obsidian', {}),
    'crying': ('minecraft:crying_obsidian', {}),
    'end_stone': ('minecraft:end_stone', {}),
    'end_bricks': ('minecraft:end_bricks', {}),
    'purpur': ('minecraft:purpur_block', {'chisel_type': 'default', 'pillar_axis': 'y'}),
    'purpur_pillar': ('minecraft:purpur_block', {'chisel_type': 'lines', 'pillar_axis': 'y'}),
    'quartz': ('minecraft:quartz_block', {'chisel_type': 'default', 'pillar_axis': 'y'}),
    'quartz_pillar': ('minecraft:quartz_block', {'chisel_type': 'lines', 'pillar_axis': 'y'}),
    'prismarine': ('minecraft:prismarine', {'prismarine_block_type': 'default'}),
    'prismarine_bricks': ('minecraft:prismarine', {'prismarine_block_type': 'bricks'}),
    'dark_prismarine': ('minecraft:prismarine', {'prismarine_block_type': 'dark'}),
    'sea_lantern': ('minecraft:sea_lantern', {}),
    'shroomlight': ('minecraft:shroomlight', {}),
    'glowstone': ('minecraft:glowstone', {}),
    'froglight_p': ('minecraft:pearlescent_froglight', {'pillar_axis': 'y'}),
    'froglight_v': ('minecraft:verdant_froglight', {'pillar_axis': 'y'}),
    'end_rod': ('minecraft:end_rod', {'facing_direction': 1}),
    'lantern': ('minecraft:lantern', {'hanging': Byte(0)}),
    'lightning_rod': ('minecraft:lightning_rod', {'facing_direction': 1}),
    'fence': ('minecraft:fence', {'wood_type': 'dark_oak'}),
    'glass': ('minecraft:glass', {}),
    'warped_stem': ('minecraft:warped_stem', {'pillar_axis': 'y'}),
    'crimson_stem': ('minecraft:crimson_stem', {'pillar_axis': 'y'}),
    'warped_wart': ('minecraft:warped_wart_block', {}),
    'nether_wart': ('minecraft:nether_wart_block', {}),
    'warped_nylium': ('minecraft:warped_nylium', {}),
    'warped_fungus': ('minecraft:warped_fungus', {}),
    'warped_roots': ('minecraft:warped_roots', {}),
    'honeycomb': ('minecraft:honeycomb_block', {}),
    'ox_copper': ('minecraft:oxidized_copper', {}),
    'ox_cut_copper': ('minecraft:oxidized_cut_copper', {}),
    'weathered_copper': ('minecraft:weathered_copper', {}),
    'mud_bricks': ('minecraft:mud_bricks', {}),
    'azalea': ('minecraft:azalea_leaves_flowered', {'persistent_bit': Byte(1), 'update_bit': Byte(0)}),
    'sculk': ('minecraft:sculk', {}),
}
for c in ('white', 'purple', 'magenta', 'cyan', 'light_blue', 'blue', 'black', 'gray', 'lime', 'orange', 'yellow', 'pink'):
    B[f'concrete_{c}'] = ('minecraft:concrete', {'color': c})
    B[f'terracotta_{c}'] = ('minecraft:stained_hardened_clay', {'color': c})
    B[f'glass_{c}'] = ('minecraft:stained_glass', {'color': c})
    B[f'wool_{c}'] = ('minecraft:wool', {'color': c})

# Approximate colours for the maps and previews.
COL = {
    'grass': (98, 140, 62), 'dirt': (122, 88, 58), 'coarse': (110, 80, 54), 'stone': (125, 125, 125),
    'podzol': (92, 64, 34), 'mycelium': (112, 96, 112), 'moss': (90, 112, 46), 'farmland': (90, 60, 36),
    'water': (52, 92, 196), 'wheat': (214, 186, 92), 'wheat_young': (120, 160, 60), 'carrots': (230, 140, 40),
    'potatoes': (190, 170, 90), 'beetroot': (160, 50, 60), 'melon': (110, 150, 40), 'pumpkin': (210, 120, 30),
    'berry': (60, 100, 50), 'hay': (200, 170, 40), 'calcite': (222, 224, 220), 'tuff': (108, 108, 98),
    'amethyst': (140, 100, 200), 'deepslate_tiles': (54, 54, 58), 'deepslate_bricks': (70, 70, 72),
    'pdeepslate': (72, 72, 74), 'blackstone': (42, 36, 42), 'pbb': (50, 44, 52), 'obsidian': (20, 16, 30),
    'crying': (60, 20, 110), 'end_stone': (220, 222, 160), 'end_bricks': (218, 224, 166), 'purpur': (170, 120, 170),
    'purpur_pillar': (176, 128, 176), 'quartz': (236, 230, 222), 'quartz_pillar': (236, 232, 226),
    'prismarine': (100, 160, 150), 'prismarine_bricks': (100, 170, 150), 'dark_prismarine': (52, 92, 76),
    'sea_lantern': (200, 230, 230), 'shroomlight': (240, 150, 70), 'glowstone': (250, 210, 120),
    'froglight_p': (240, 220, 230), 'froglight_v': (220, 240, 200), 'end_rod': (240, 236, 230),
    'lantern': (90, 80, 70), 'lightning_rod': (200, 120, 90), 'fence': (66, 44, 26), 'glass': (200, 220, 230),
    'warped_stem': (58, 96, 100), 'crimson_stem': (110, 50, 70), 'warped_wart': (22, 120, 120),
    'nether_wart': (120, 20, 20), 'warped_nylium': (40, 110, 100), 'warped_fungus': (30, 140, 130),
    'warped_roots': (30, 150, 140), 'honeycomb': (230, 160, 40), 'ox_copper': (82, 162, 132),
    'ox_cut_copper': (80, 154, 128), 'weathered_copper': (108, 150, 110), 'mud_bricks': (140, 106, 80),
    'azalea': (110, 140, 70), 'sculk': (14, 40, 50),
}
_CC = {'white': (230, 230, 230), 'purple': (110, 40, 160), 'magenta': (170, 50, 160), 'cyan': (30, 130, 140),
       'light_blue': (60, 150, 210), 'blue': (50, 60, 160), 'black': (20, 20, 24), 'gray': (60, 64, 68),
       'lime': (100, 180, 30), 'orange': (220, 100, 10), 'yellow': (240, 180, 20), 'pink': (220, 110, 150)}
for c, rgb in _CC.items():
    COL[f'concrete_{c}'] = rgb
    COL[f'terracotta_{c}'] = tuple(int(v * 0.75 + 30) for v in rgb)
    COL[f'glass_{c}'] = tuple(int(v * 0.6 + 90) for v in rgb)
    COL[f'wool_{c}'] = tuple(min(255, int(v * 1.05)) for v in rgb)

AIR = 0


class Volume:
    """X (east), Y (up), Z (south). Ground surface at y = G. Everything above is air (clears terrain on load)."""

    def __init__(self, w, h, d, ground='grass', G=5, sub='dirt'):
        self.w, self.h, self.d, self.G = w, h, d, G
        self.names = ['air']
        self.ids = {'air': 0}
        self.a = np.zeros((w, h, d), dtype=np.int16)
        self.box(0, 0, 0, w - 1, G - 3, d - 1, 'stone')
        self.box(0, G - 2, 0, w - 1, G - 1, d - 1, sub)
        self.box(0, G, 0, w - 1, G, d - 1, ground)

    def bid(self, name):
        if name not in self.ids:
            if name not in B:
                raise KeyError(name)
            self.ids[name] = len(self.names)
            self.names.append(name)
        return self.ids[name]

    def inside(self, x, y, z):
        return 0 <= x < self.w and 0 <= y < self.h and 0 <= z < self.d

    def set(self, x, y, z, name):
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if self.inside(x, y, z):
            self.a[x, y, z] = self.bid(name)

    def get(self, x, y, z):
        if self.inside(x, y, z):
            return self.names[self.a[x, y, z]]
        return 'air'

    def box(self, x0, y0, z0, x1, y1, z1, name, hollow=False):
        x0, x1 = sorted((int(x0), int(x1)))
        y0, y1 = sorted((int(y0), int(y1)))
        z0, z1 = sorted((int(z0), int(z1)))
        x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
        x1, y1, z1 = min(x1, self.w - 1), min(y1, self.h - 1), min(z1, self.d - 1)
        if x1 < x0 or y1 < y0 or z1 < z0:
            return
        i = self.bid(name)
        if hollow:
            self.a[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1][[0, -1], :, :] = i
            self.a[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1][:, :, [0, -1]] = i
        else:
            self.a[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = i

    def column(self, x, z, y0, y1, name):
        self.box(x, y0, z, x, y1, z, name)

    def disc(self, cx, cz, y, r, name, ring=None):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for z in range(int(cz - r - 1), int(cz + r + 2)):
                d = math.hypot(x - cx, z - cz)
                if d <= r + 0.3 and (ring is None or d >= r - ring + 0.3):
                    self.set(x, y, z, name)

    def cyl(self, cx, cz, y0, y1, r, name, hollow=False):
        for y in range(int(y0), int(y1) + 1):
            self.disc(cx, cz, y, r, name, ring=1.2 if hollow else None)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, name, shell=None, ymin=None, ymax=None):
        for x in range(int(cx - rx - 1), int(cx + rx + 2)):
            for y in range(int(cy - ry - 1), int(cy + ry + 2)):
                if (ymin is not None and y < ymin) or (ymax is not None and y > ymax):
                    continue
                for z in range(int(cz - rz - 1), int(cz + rz + 2)):
                    q = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2
                    if q <= 1.0:
                        if shell is None:
                            self.set(x, y, z, name)
                        else:
                            qi = ((x - cx) / max(rx - shell, 0.5)) ** 2 + ((y - cy) / max(ry - shell, 0.5)) ** 2 + \
                                 ((z - cz) / max(rz - shell, 0.5)) ** 2
                            if qi > 1.0:
                                self.set(x, y, z, name)

    def line(self, p0, p1, name, r=0):
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        n = int(max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)) * 1.5) + 1
        for i in range(n + 1):
            t = i / n
            x, y, z = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t
            if r <= 0:
                self.set(x, y, z, name)
            else:
                for dx in range(-r, r + 1):
                    for dz in range(-r, r + 1):
                        if dx * dx + dz * dz <= r * r:
                            self.set(x + dx, y, z + dz, name)

    def replace_where(self, mask, name):
        self.a[mask] = self.bid(name)

    # ------------------------------------------------------------------ export
    def to_mcstructure(self, x0=0, z0=0, w=None, d=None):
        w = w or self.w
        d = d or self.d
        sub = self.a[x0:x0 + w, :, z0:z0 + d]
        sx, sy, sz = sub.shape
        used = np.unique(sub)
        remap = np.full(len(self.names), -1, dtype=np.int32)
        remap[used] = np.arange(len(used))
        idx = remap[sub].reshape(-1)    # C order over (x, y, z): z fastest, then y, then x
        palette = []
        for u in used:
            name, states = B[self.names[u]]
            palette.append({'name': name, 'states': dict(states), 'version': BLOCK_VERSION})
        root = {
            'format_version': 1,
            'size': [sx, sy, sz],
            'structure': {
                'block_indices': [IntList(idx), IntList(np.full(idx.shape, -1, dtype=np.int32))],
                'entities': [],
                'palette': {'default': {'block_palette': palette, 'block_position_data': {}}},
            },
            'structure_world_origin': [0, 0, 0],
        }
        return dumps(root)

    # ------------------------------------------------------------------ renders
    def heightmap(self):
        solid = self.a != 0
        ys = np.where(solid.any(axis=1), self.h - 1 - np.argmax(solid[:, ::-1, :], axis=1), 0)
        return ys

    def map_png(self, path, scale=4, title=None):
        from PIL import Image, ImageDraw
        hm = self.heightmap()
        img = Image.new('RGB', (self.w * scale, self.d * scale))
        px = img.load()
        for x in range(self.w):
            for z in range(self.d):
                y = hm[x, z]
                name = self.names[self.a[x, y, z]]
                c = COL.get(name, (255, 0, 255))
                shade = 1.0 + 0.012 * (y - self.G)
                if x > 0 and hm[x - 1, z] > y:
                    shade *= 0.8
                if z > 0 and hm[x, z - 1] > y:
                    shade *= 0.85
                c = tuple(max(0, min(255, int(v * shade))) for v in c)
                for i in range(scale):
                    for j in range(scale):
                        px[x * scale + i, z * scale + j] = c
        dr = ImageDraw.Draw(img)
        for k in range(0, max(self.w, self.d) + 1, 16):   # chunk grid
            dr.line([(k * scale, 0), (k * scale, self.d * scale)], fill=(0, 0, 0), width=1)
            dr.line([(0, k * scale), (self.w * scale, k * scale)], fill=(0, 0, 0), width=1)
        if title:
            dr.rectangle([0, 0, len(title) * 7 + 10, 16], fill=(0, 0, 0))
            dr.text((5, 2), title, fill=(255, 255, 255))
        img.save(path)

    def iso_png(self, path, s=4):
        """Isometric preview (looking from the south-west), painter's algorithm over exposed blocks."""
        from PIL import Image, ImageDraw
        W = (self.w + self.d) * s * 2 + 40
        H = (self.w + self.d) * s + self.h * s * 2 + 40
        img = Image.new('RGB', (W, H), (24, 26, 34))
        dr = ImageDraw.Draw(img)
        ox, oy = self.d * s * 2 + 20, self.h * s * 2 + 20
        a = self.a
        solid = a != 0
        for ssum in range(self.w + self.d - 1):
            for x in range(max(0, ssum - self.d + 1), min(self.w, ssum + 1)):
                z = ssum - x
                col = solid[x, :, z]
                if not col.any():
                    continue
                for y in np.nonzero(col)[0]:
                    top = y + 1 >= self.h or not solid[x, y + 1, z]
                    east = x + 1 >= self.w or not solid[x + 1, y, z]
                    south = z + 1 >= self.d or not solid[x, y, z + 1]
                    if not (top or east or south):
                        continue
                    c = COL.get(self.names[a[x, y, z]], (255, 0, 255))
                    sx = ox + (x - z) * s * 2
                    sy = oy + (x + z) * s - y * s * 2
                    if top:
                        dr.polygon([(sx, sy - s), (sx + 2 * s, sy), (sx, sy + s), (sx - 2 * s, sy)], fill=c)
                    if south:
                        cc = tuple(int(v * 0.72) for v in c)
                        dr.polygon([(sx - 2 * s, sy), (sx, sy + s), (sx, sy + 3 * s), (sx - 2 * s, sy + 2 * s)], fill=cc)
                    if east:
                        cc = tuple(int(v * 0.86) for v in c)
                        dr.polygon([(sx, sy + s), (sx + 2 * s, sy), (sx + 2 * s, sy + 2 * s), (sx, sy + 3 * s)], fill=cc)
        bbox = img.getbbox()
        img.crop(bbox).save(path)
