"""Alien villages and farmlands for Minecraft Bedrock. Each layout returns a Volume (ground surface at y = G)."""
import math
import random
from vox import Volume

# ================================================================================================ components


def glow_pylon(v, x, z, h=4, body='purpur_pillar', top='sea_lantern'):
    """Lamp post: a slim pillar, a glowing block and an end-rod spike (lights paths at night)."""
    g = v.G
    v.column(x, z, g + 1, g + h, body)
    v.set(x, g + h + 1, z, top)
    v.set(x, g + h + 2, z, 'end_rod')


def path(v, x0, z0, x1, z1, w=3, block='deepslate_tiles', edge='moss', lamps=0, lamp_kw=None):
    """Straight path of `w` blocks with mossy edges; optional lamps every `lamps` blocks."""
    g = v.G
    n = int(max(abs(x1 - x0), abs(z1 - z0)))
    dx, dz = (x1 - x0) / max(n, 1), (z1 - z0) / max(n, 1)
    px, pz = -dz, dx
    for i in range(n + 1):
        cx, cz = x0 + dx * i, z0 + dz * i
        for k in range(-(w // 2), w // 2 + 1):
            v.set(cx + px * k, g, cz + pz * k, block)
        for k in (-(w // 2) - 1, w // 2 + 1):
            if v.get(round(cx + px * k), g, round(cz + pz * k)) in ('grass', 'mycelium', 'podzol'):
                v.set(cx + px * k, g, cz + pz * k, edge)
        if lamps and i % lamps == lamps // 2:
            glow_pylon(v, round(cx + px * (w // 2 + 2)), round(cz + pz * (w // 2 + 2)), **(lamp_kw or {}))


def plaza(v, cx, cz, r, block='pdeepslate', ring_block='amethyst'):
    v.disc(cx, cz, v.G, r, block)
    v.disc(cx, cz, v.G, r, ring_block, ring=1)


def ring_monument(v, cx, cz, r=6, facing='x', body='obsidian', inner='crying', light='sea_lantern'):
    """A great standing ring (the planet's ancient symbol) on a stepped dais, with a floating crystal core."""
    g = v.G
    v.disc(cx, cz, g + 1, r + 2, 'pbb')
    v.disc(cx, cz, g + 2, r, 'pdeepslate')
    base = g + 3 + r
    for a in range(0, 360, 2):
        t = math.radians(a)
        for dr in (0.0, 0.7):
            off = (r + dr) * math.cos(t)
            y = base + (r + dr) * math.sin(t)
            for w in (0, 1):
                if facing == 'x':
                    v.set(cx + off, y, cz + w, body if dr > 0 else inner)
                else:
                    v.set(cx + w, y, cz + off, body if dr > 0 else inner)
        if a % 30 == 0:
            off = (r - 0.8) * math.cos(t)
            y = base + (r - 0.8) * math.sin(t)
            if facing == 'x':
                v.set(cx + off, y, cz, light)
            else:
                v.set(cx, y, cz + off, light)
    v.ellipsoid(cx + 0.5 if facing == 'x' else cx, base, cz + 0.5 if facing != 'x' else cz, 1.2, 2.2, 1.2, 'amethyst')
    v.set(cx, base, cz, 'sea_lantern')


def mushroom_tree(v, x, z, h, cap_r, stem='warped_stem', cap='warped_wart', light='shroomlight', thick=2):
    """Giant alien fungus: thick stem, a broad domed cap, glowing bulbs hanging underneath."""
    g = v.G
    for dx in range(thick):
        for dz in range(thick):
            v.column(x + dx, z + dz, g + 1, g + h, stem)
    c = thick / 2 - 0.5
    v.ellipsoid(x + c, g + h, z + c, cap_r, cap_r * 0.45, cap_r, cap, shell=1.2, ymin=g + h - 1)
    rnd = random.Random(x * 31 + z)
    for _ in range(int(cap_r * 1.6)):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(1.5, cap_r - 1.0)
        px, pz = x + c + math.cos(a) * d, z + c + math.sin(a) * d
        hang = rnd.randint(1, 2)
        for k in range(hang):
            v.set(px, g + h - 1 - k, pz, light if k == hang - 1 else cap)


def crystal_spire(v, x, z, h, r=1.6, body='amethyst', tip='end_rod'):
    g = v.G
    for y in range(h):
        rr = r * (1 - y / h) + 0.4
        v.disc(x, z, g + 1 + y, rr, body)
    v.set(x, g + h + 1, z, 'sea_lantern')
    v.column(x, z, g + h + 2, g + h + 3, tip)
    for a in range(0, 360, 90):   # small side crystals
        t = math.radians(a + 45)
        for k in range(3):
            v.set(x + math.cos(t) * (r + 1 + k * 0.6), g + 1 + k, z + math.sin(t) * (r + 1 + k * 0.6), body)


def dome_house(v, cx, cz, r, wall='calcite', band='terracotta_purple', glass='glass_cyan', door_dir=(0, 1),
               light='shroomlight', floor='pdeepslate'):
    """Rounded alien home: a hollow dome with a coloured band, a ring of windows, a door and a glowing core."""
    g = v.G
    v.disc(cx, cz, g, r, floor)
    v.ellipsoid(cx, g, cz, r, r * 0.95, r, wall, shell=1.1, ymin=g + 1)
    v.ellipsoid(cx, g, cz, r - 1.1, r * 0.95 - 1.1, r - 1.1, 'air', ymin=g + 1)
    for x in range(int(cx - r - 1), int(cx + r + 2)):     # coloured band
        for z in range(int(cz - r - 1), int(cz + r + 2)):
            for y in (g + 2,):
                if v.get(x, y, z) == wall:
                    v.set(x, y, z, band)
    for a in range(0, 360, 45):   # windows
        t = math.radians(a + 22)
        wx, wz = cx + math.cos(t) * (r - 0.5), cz + math.sin(t) * (r - 0.5)
        for y in (g + 3, g + 4):
            if v.get(round(wx), y, round(wz)) in (wall, band):
                v.set(wx, y, wz, glass)
    v.set(cx, g + int(r * 0.95) - 1, cz, light)   # ceiling light
    v.ellipsoid(cx, g + r * 0.95, cz, 1.0, 0.8, 1.0, glass)   # skylight
    dx, dz = door_dir
    for k in range(int(r) - 2, int(r) + 2):
        for y in (g + 1, g + 2, g + 3):
            for w in (-1, 0, 1):
                if w != 0 and y == g + 3:
                    continue
                v.set(cx + dx * k + (w if dz else 0), y, cz + dz * k + (w if dx else 0), 'air')
    for k in range(int(r) + 1, int(r) + 3):   # doorstep
        v.set(cx + dx * k, g, cz + dz * k, floor)


def needle_tower(v, cx, cz, h, r=3, wall='quartz', trim='prismarine_bricks', roof='purpur', glass='glass_light_blue',
                 door_dir=(0, 1), base=None):
    """Slender Avari tower: banded round shaft, window rings, a flared balcony and a tall cone roof."""
    g = v.G if base is None else base
    v.cyl(cx, cz, g, g, r + 1, 'pdeepslate')
    v.cyl(cx, cz, g + 1, g + h, r, wall, hollow=True)
    for y in range(g + 1, g + h + 1, 5):
        v.disc(cx, cz, y, r, trim, ring=1.2)
    for y in range(g + 4, g + h - 2, 5):
        for a in range(0, 360, 60):
            t = math.radians(a)
            v.set(cx + math.cos(t) * r, y, cz + math.sin(t) * r, glass)
            v.set(cx + math.cos(t) * r, y + 1, cz + math.sin(t) * r, glass)
    for y in range(g + 6, g + h, 6):   # floors with a light
        v.disc(cx, cz, y, r - 0.8, 'pdeepslate')
        v.set(cx, y, cz, 'sea_lantern')
    v.disc(cx, cz, g + h + 1, r + 2, trim)    # balcony
    v.disc(cx, cz, g + h + 2, r + 2, 'fence', ring=1)
    for y in range(0, r * 4):    # cone roof
        rr = (r + 1.5) * (1 - y / (r * 4))
        v.disc(cx, cz, g + h + 2 + y, max(rr, 0.4), roof, ring=1.3 if rr > 1.5 else None)
    v.set(cx, g + h + 2 + r * 4, cz, 'sea_lantern')
    v.column(cx, cz, g + h + 3 + r * 4, g + h + 5 + r * 4, 'end_rod')
    dx, dz = door_dir
    for y in (g + 1, g + 2):
        v.set(cx + dx * r, y, cz + dz * r, 'air')
    v.set(cx + dx * (r + 1), g, cz + dz * (r + 1), 'pdeepslate')


def pod_house(v, cx, cz, r=4, wall='honeycomb', roof='ox_copper', glass='glass_orange', door_dir=(1, 0)):
    """Vorn hive-pod: an octagonal honeycomb drum, copper cone roof, slit windows and an antenna."""
    g = v.G
    v.cyl(cx, cz, g, g, r, 'mud_bricks')
    v.cyl(cx, cz, g + 1, g + 4, r, wall, hollow=True)
    for a in range(0, 360, 45):
        t = math.radians(a)
        v.set(cx + math.cos(t) * r, g + 3, cz + math.sin(t) * r, glass)
    for y in range(0, r + 1):
        v.disc(cx, cz, g + 5 + y, max(r + 0.8 - y, 0.5), roof, ring=1.3 if r - y > 1 else None)
    v.set(cx, g + 6 + r, cz, 'lightning_rod')
    v.set(cx, g + 4, cz, 'froglight_p')
    dx, dz = door_dir
    for y in (g + 1, g + 2):
        v.set(cx + dx * r, y, cz + dz * r, 'air')


def farm_plot(v, x0, z0, w, d, crop='wheat', border='mud_bricks', water_every=9):
    """Hydrated farmland: water lines every 9 blocks (keeps every block within 4 of water), crops on top."""
    g = v.G
    v.box(x0 - 1, g, z0 - 1, x0 + w, g, z0 + d, border)
    for x in range(x0, x0 + w):
        is_water = (x - x0) % water_every == water_every // 2
        for z in range(z0, z0 + d):
            if is_water:
                v.set(x, g, z, 'water')
                v.set(x, g - 1, z, 'mud_bricks')
            else:
                if crop in ('melon', 'pumpkin'):
                    v.set(x, g, z, 'farmland' if (x - x0) % 3 == 1 else 'dirt')
                    if (x - x0) % 3 != 1 and (z - z0) % 2 == 0:
                        v.set(x, g + 1, z, crop)
                elif crop == 'berry':
                    v.set(x, g, z, 'grass')
                    if (x + z) % 2 == 0:
                        v.set(x, g + 1, z, 'berry')
                else:
                    v.set(x, g, z, 'farmland')
                    v.set(x, g + 1, z, crop)


def hay_barn(v, cx, cz, w=13, d=19, wall='concrete_white', band='terracotta_purple', roof='glass_purple'):
    """Long barn with a vaulted glass roof, hay stacked inside."""
    g = v.G
    x0, x1, z0, z1 = cx - w // 2, cx + w // 2, cz - d // 2, cz + d // 2
    v.box(x0, g, z0, x1, g, z1, 'pdeepslate')
    v.box(x0, g + 1, z0, x1, g + 5, z1, wall, hollow=True)
    v.box(x0, g + 3, z0, x1, g + 3, z1, band, hollow=True)
    v.box(x0 + 1, g + 1, z0 + 1, x1 - 1, g + 5, z1 - 1, 'air')
    half = w / 2
    for x in range(x0, x1 + 1):   # vaulted roof
        k = (x - cx) / half
        y = g + 6 + int(round(math.sqrt(max(0.0, 1 - k * k)) * half * 0.7))
        for z in range(z0, z1 + 1):
            v.set(x, y, z, roof if (z - z0) % 4 else 'purpur')
        for z in (z0, z1):
            v.box(x, g + 6, z, x, y, z, wall)
    for z in range(z0 + 2, z1 - 1, 3):   # hay stacks
        for x in range(x0 + 1, x0 + 4):
            v.column(x, z, g + 1, g + 3, 'hay')
            v.column(x1 - (x - x0), z, g + 1, g + 2, 'hay')
    for y in (g + 1, g + 2, g + 3, g + 4):   # big doors
        for x in range(cx - 2, cx + 3):
            v.set(x, y, z1, 'air')
            v.set(x, y, z0, 'air')
    v.set(cx, g + 5, cz, 'glowstone')


def silo(v, cx, cz, h=14, r=3, wall='calcite', band='terracotta_cyan', cap='amethyst'):
    g = v.G
    v.cyl(cx, cz, g + 1, g + h, r, wall, hollow=True)
    for y in range(g + 3, g + h, 4):
        v.disc(cx, cz, y, r, band, ring=1.2)
    v.ellipsoid(cx, g + h, cz, r + 0.5, r * 0.8, r + 0.5, cap, shell=1.2, ymin=g + h)
    v.set(cx, g + h + int(r * 0.8) + 1, cz, 'end_rod')


def irrigation_pylon(v, x, z, h=6):
    """Prismarine water-tower pylon: glowing collar, end-rod cap."""
    g = v.G
    v.column(x, z, g + 1, g + h, 'prismarine_bricks')
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        v.set(x + dx, g + h - 1, z + dz, 'dark_prismarine')
    v.set(x, g + h + 1, z, 'sea_lantern')
    v.set(x, g + h + 2, z, 'end_rod')


def wind_spire(v, x, z, h=16):
    """Alien wind spire: tall purpur mast with three rotor fins and a glowing crown."""
    g = v.G
    v.column(x, z, g + 1, g + h, 'purpur_pillar')
    for k, (dx, dz) in enumerate(((1, 0), (-1, 1), (-1, -1))):
        for i in range(1, 5):
            v.set(x + dx * i, g + h - 3 - i // 2 + k, z + dz * i, 'end_rod' if i == 4 else 'quartz')
    v.set(x, g + h + 1, z, 'froglight_v')
    v.set(x, g + h + 2, z, 'lightning_rod')


def fence_line(v, x0, z0, x1, z1, gap=None):
    g = v.G
    n = int(max(abs(x1 - x0), abs(z1 - z0)))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / max(n, 1)
        z = z0 + (z1 - z0) * i / max(n, 1)
        if gap and abs(x - gap[0]) + abs(z - gap[1]) < 2:
            continue
        v.set(x, g + 1, z, 'fence')
        if i % 8 == 0:
            v.set(x, g + 2, z, 'lantern')


def scatter_ground(v, seed, choices):
    """Paint the open ground with soft patches of alien turf."""
    g = v.G
    for x in range(v.w):
        for z in range(v.d):
            if v.get(x, g, z) == 'grass':
                n = math.sin(x * 0.21 + seed) * math.cos(z * 0.17 - seed) + math.sin((x + z) * 0.07)
                if n > 0.6:
                    v.set(x, g, z, choices[0])
                elif n < -0.9:
                    v.set(x, g, z, choices[1])


# ================================================================================================ layouts


def lumen_hollow():
    """Village 1: domed homes around a ring monument, giant glowing fungus trees, crystal spires."""
    v = Volume(96, 44, 96, ground='grass')
    c = 48
    scatter_ground(v, 3, ('mycelium', 'moss'))
    plaza(v, c, c, 11)
    ring_monument(v, c, c, 6, 'x')
    for a, (dx, dz) in zip(range(0, 360, 90), ((1, 0), (0, 1), (-1, 0), (0, -1))):
        path(v, c + dx * 12, c + dz * 12, c + dx * 46, c + dz * 46, 3, lamps=10)
    homes = []
    for k in range(9):
        a = math.radians(k * 40 + 20)
        rr = 28 if k % 2 else 33
        hx, hz = c + math.cos(a) * rr, c + math.sin(a) * rr
        r = 5 if k % 3 else 6
        door = (-round(math.cos(a)), 0) if abs(math.cos(a)) > abs(math.sin(a)) else (0, -round(math.sin(a)))
        bands = ['terracotta_purple', 'terracotta_cyan', 'terracotta_magenta']
        dome_house(v, round(hx), round(hz), r, band=bands[k % 3],
                   glass=['glass_cyan', 'glass_magenta', 'glass_light_blue'][k % 3], door_dir=door)
        homes.append((hx, hz))
        path(v, hx - math.cos(a) * (r + 2), hz - math.sin(a) * (r + 2), c + math.cos(a) * 12, c + math.sin(a) * 12, 1,
             block='pdeepslate', lamps=0)
    for k, (tx, tz, h, cr, stem, cap) in enumerate([
            (14, 18, 14, 7, 'warped_stem', 'warped_wart'), (80, 16, 17, 8, 'crimson_stem', 'nether_wart'),
            (82, 78, 13, 6, 'warped_stem', 'warped_wart'), (16, 80, 16, 7, 'crimson_stem', 'nether_wart'),
            (30, 62, 10, 5, 'warped_stem', 'warped_wart'), (64, 30, 11, 5, 'crimson_stem', 'nether_wart'),
            (8, 48, 12, 5, 'warped_stem', 'warped_wart'), (88, 50, 12, 5, 'crimson_stem', 'nether_wart')]):
        mushroom_tree(v, tx, tz, h, cr, stem, cap, thick=2 if cr >= 6 else 1)
    for (sx, sz, h) in [(64, 64, 13), (32, 34, 10), (70, 88, 9), (24, 6, 8)]:
        crystal_spire(v, sx, sz, h)
    farm_plot(v, 60, 4, 17, 9, 'carrots')
    farm_plot(v, 4, 60, 9, 17, 'wheat')
    return v


def spireholm():
    """Village 2: needle towers on a two-level end-stone terrace, sky bridges, a ring gate and a pool."""
    v = Volume(96, 72, 96, ground='grass')
    g = v.G
    c = 48
    scatter_ground(v, 7, ('moss', 'podzol'))
    v.disc(c, c, g, 30, 'end_bricks')        # lower terrace
    v.cyl(c, c, g + 1, g + 2, 26, 'end_bricks')
    v.disc(c, c, g + 2, 26, 'end_stone')
    v.disc(c, c, g + 2, 26, 'purpur', ring=1)
    v.cyl(c, c, g + 3, g + 3, 14, 'quartz')    # upper plaza
    v.disc(c, c, g + 3, 14, 'prismarine_bricks', ring=1)
    for k in range(4):   # ramps up the terrace
        a = math.radians(k * 90)
        for i in range(8):
            rr = 34 - i
            for w in (-2, -1, 0, 1, 2):
                x = c + math.cos(a) * rr - math.sin(a) * w
                z = c + math.sin(a) * rr + math.cos(a) * w
                v.box(round(x), g + 1, round(z), round(x), g + min(2, i // 3), round(z), 'end_bricks')
    v.disc(c, c, g + 3, 4, 'water')    # reflecting pool with a central spire
    v.disc(c, c, g + 2, 5, 'dark_prismarine')
    towers = []
    for k in range(6):
        a = math.radians(k * 60 + 30)
        tx, tz = round(c + math.cos(a) * 20), round(c + math.sin(a) * 20)
        h = 18 + (k % 3) * 6
        needle_tower(v, tx, tz, h, 3, roof='purpur' if k % 2 else 'dark_prismarine',
                     door_dir=(-round(math.cos(a)), 0) if abs(math.cos(a)) > 0.7 else (0, -round(math.sin(a))), base=g + 2)
        towers.append((tx, tz, h))
    # central great spire rising from the pool
    v.cyl(c, c, g + 3, g + 40, 2, 'quartz_pillar')
    for y in range(g + 6, g + 40, 6):
        v.disc(c, c, y, 2.5, 'sea_lantern', ring=0.8)
    for y in range(0, 14):
        v.disc(c, c, g + 41 + y, max(3.5 * (1 - y / 14), 0.4), 'amethyst')
    v.column(c, c, g + 55, g + 57, 'end_rod')
    # sky bridges between neighbouring towers (at balcony height of the lower one)
    for k in range(6):
        ax, az, ah = towers[k]
        bx, bz, bh = towers[(k + 1) % 6]
        y = g + 2 + min(ah, bh) + 1
        v.line((ax, y, az), (bx, y, bz), 'deepslate_tiles', r=1)
        v.line((ax, y + 1, az), (bx, y + 1, bz), 'air', r=0)
    # ring gate on the southern approach
    for x in range(c - 8, c + 9):
        for y in range(0, 17):
            d = math.hypot(x - c, y - 0)
            if 6.5 <= d <= 8.2:
                v.set(x, g + 1 + y, 88, 'obsidian' if d > 7.5 else 'crying')
    v.set(c, g + 9, 88, 'sea_lantern')
    path(v, c, 94, c, 80, 5, block='quartz', edge='moss', lamps=6)
    for (px, pz) in [(10, 10), (86, 10), (10, 86), (86, 86), (12, 48), (84, 48)]:
        crystal_spire(v, px, pz, 7, 1.2, body='prismarine', tip='end_rod')
    farm_plot(v, 66, 64, 18, 9, 'beetroot', border='end_bricks')
    farm_plot(v, 12, 64, 18, 9, 'potatoes', border='end_bricks')
    return v


def hive_ring():
    """Village 3 (Vorn): honeycomb pod houses ringed around a sunken hive hall with a glass crown."""
    v = Volume(96, 40, 96, ground='grass')
    g = v.G
    c = 48
    scatter_ground(v, 11, ('podzol', 'coarse'))
    # sunken hall
    v.box(c - 13, g - 3, c - 13, c + 13, g, c + 13, 'air')
    v.disc(c, c, g - 3, 13, 'ox_cut_copper')
    v.ellipsoid(c, g - 3, c, 13, 12, 13, 'honeycomb', shell=1.3, ymin=g - 3)
    v.ellipsoid(c, g - 3, c, 11.7, 10.7, 11.7, 'air', ymin=g - 2)
    for y in range(g - 2, g + 9):
        for a in range(0, 360, 8):
            t = math.radians(a)
            if (a // 8) % 6 == 0:
                rr = 13 * math.sqrt(max(0.0, 1 - ((y - g + 3) / 12) ** 2)) - 0.6
                v.set(c + math.cos(t) * rr, y, c + math.sin(t) * rr, 'ox_copper')
    v.ellipsoid(c, g + 8, c, 5, 2.5, 5, 'glass_orange', ymin=g + 7)
    for k in range(6):
        a = math.radians(k * 60)
        v.set(c + math.cos(a) * 6, g + 6, c + math.sin(a) * 6, 'froglight_p')
    for i in range(4):   # stairs down into the hall
        v.box(c - 1, g - i, c + 13 + 3 - i, c + 1, g - i, c + 13 + 3 - i, 'ox_cut_copper')
        v.box(c - 1, g - i + 1, c + 13 + 3 - i, c + 1, g + 2, c + 13 + 3 - i, 'air')
    v.box(c - 1, g - 2, c + 11, c + 1, g + 1, c + 13, 'air')
    # pod houses in two rings
    for k in range(12):
        a = math.radians(k * 30 + (15 if k % 2 else 0))
        rr = 26 if k % 2 else 33
        px, pz = round(c + math.cos(a) * rr), round(c + math.sin(a) * rr)
        door = (-round(math.cos(a)), 0) if abs(math.cos(a)) > abs(math.sin(a)) else (0, -round(math.sin(a)))
        pod_house(v, px, pz, 4 if k % 3 else 5, roof='ox_copper' if k % 2 else 'weathered_copper', door_dir=door)
    # antenna masts and gardens
    for k in range(6):
        a = math.radians(k * 60 + 30)
        x, z = round(c + math.cos(a) * 18), round(c + math.sin(a) * 18)
        v.column(x, z, g + 1, g + 9, 'ox_cut_copper')
        v.set(x, g + 10, z, 'froglight_v')
        v.set(x, g + 11, z, 'lightning_rod')
    farm_plot(v, 4, 4, 14, 14, 'berry')
    farm_plot(v, 78, 4, 14, 14, 'melon')
    farm_plot(v, 78, 78, 14, 14, 'carrots', border='ox_cut_copper')
    path(v, c, 63, c, 95, 3, block='ox_cut_copper', edge='podzol', lamps=8,
         lamp_kw=dict(body='ox_cut_copper', top='froglight_p'))
    return v


def sunwheat_plains():
    """Farmland 1: a 128 x 128 grid of hydrated fields, a pivot circle, an alien crop circle, barns and silos."""
    v = Volume(128, 36, 128, ground='grass')
    g = v.G
    crops = ['wheat', 'carrots', 'wheat', 'potatoes', 'wheat', 'beetroot', 'pumpkin', 'wheat', 'carrots', 'wheat',
             'melon', 'potatoes', 'wheat', 'beetroot', 'wheat', 'carrots']
    k = 0
    plot = 25
    for i in range(4):
        for j in range(4):
            x0, z0 = 3 + i * (plot + 6), 3 + j * (plot + 6)
            if (i, j) in ((1, 1), (2, 1), (1, 2), (2, 2)):
                continue   # centre: the pivot field and the yard
            farm_plot(v, x0, z0, plot, plot, crops[k % len(crops)])
            k += 1
    for i in range(5):   # paths between fields, lit by irrigation pylons
        p = i * (plot + 6) + 0.5
        path(v, p, 0, p, 127, 3, block='deepslate_tiles', edge='moss')
        path(v, 0, p, 127, p, 3, block='deepslate_tiles', edge='moss')
        for j in range(5):
            irrigation_pylon(v, round(p) + 2, round(j * (plot + 6)) + 2)
    # centre: circular pivot field (wheat) around a water tower, with an alien crop circle in it
    cx, cz, R = 64, 64, 26
    for x in range(cx - R, cx + R + 1):
        for z in range(cz - R, cz + R + 1):
            d = math.hypot(x - cx, z - cz)
            if d > R:
                continue
            ring = int(d) % 9 == 4
            if d < 3:
                continue
            if ring:
                v.set(x, g, z, 'water')
                v.set(x, g - 1, z, 'mud_bricks')
            else:
                v.set(x, g, z, 'farmland')
                # crop circle: concentric bands and spokes of young (short) wheat
                ang = math.degrees(math.atan2(z - cz, x - cx)) % 360
                pattern = (14 <= d <= 15.5) or (20 <= d <= 21) or (d < 8 and int(ang / 45) % 2 == 0)
                v.set(x, g + 1, z, 'wheat_young' if pattern else 'wheat')
    v.disc(cx, cz, g, R + 1, 'mud_bricks', ring=1)
    v.cyl(cx, cz, g + 1, g + 12, 2, 'prismarine_bricks')
    v.ellipsoid(cx, g + 14, cz, 4, 3, 4, 'glass_cyan', shell=1)
    v.ellipsoid(cx, g + 14, cz, 3, 2, 3, 'water')
    v.set(cx, g + 18, cz, 'sea_lantern')
    for i in range(3, R):
        v.set(cx + i, g + 6, cz, 'quartz' if i % 4 else 'sea_lantern')
        if i % 8 == 0:
            v.column(cx + i, cz, g + 1, g + 5, 'end_bricks')
    # farmyard on the four central corners: barn, silos, wind spires
    hay_barn(v, 36, 36, 13, 19)
    silo(v, 92, 34, 16, 3)
    silo(v, 99, 40, 12, 2)
    silo(v, 34, 92, 14, 3, band='terracotta_purple')
    dome_house(v, 92, 92, 6, band='terracotta_cyan', door_dir=(-1, 0))
    dome_house(v, 101, 84, 4, band='terracotta_magenta', door_dir=(0, -1))
    for (x, z) in [(28, 60), (60, 28), (100, 66), (66, 100)]:
        wind_spire(v, x, z, 18)
    for x0, z0, x1, z1 in [(1, 1, 126, 1), (126, 1, 126, 126), (126, 126, 1, 126), (1, 126, 1, 1)]:
        fence_line(v, x0, z0, x1, z1, gap=((x0 + x1) // 2, (z0 + z1) // 2))
    return v


def terrace_rings():
    """Farmland 2: a hill shaped into stepped circular terraces (rings of crops edged with water channels),
    waterfalls down the sides and an observatory dome on top."""
    v = Volume(112, 48, 112, ground='grass')
    g = v.G
    c = 56
    levels = 7
    step = 3
    for L in range(levels):
        r = 52 - L * 7
        top = g + L * step
        v.cyl(c, c, g + 1, top, r, 'dirt')
        v.disc(c, c, top, r, 'grass')
        if L < levels - 1:
            inner = r - 7
            crop = ['wheat', 'carrots', 'potatoes', 'wheat', 'beetroot', 'wheat'][L]
            for x in range(c - r, c + r + 1):
                for z in range(c - r, c + r + 1):
                    d = math.hypot(x - c, z - c)
                    if inner + 0.5 < d <= r:
                        if d > r - 1.2:
                            v.set(x, top, z, 'mud_bricks')     # retaining edge
                        elif d > r - 2.2:
                            v.set(x, top, z, 'water')
                            v.set(x, top - 1, z, 'mud_bricks')
                        else:
                            v.set(x, top, z, 'farmland')
                            v.set(x, top + 1, z, crop)
    # stairs climbing the terraces on four sides
    for k in range(4):
        dx, dz = [(1, 0), (0, 1), (-1, 0), (0, -1)][k]
        for L in range(levels):
            r = 52 - L * 7
            for i in range(7):
                rr = r - i
                y = g + L * step + min(step, (i * step) // 6)
                for w in (-1, 0, 1):
                    x, z = c + dx * rr + (w if dz else 0), c + dz * rr + (w if dx else 0)
                    v.box(x, g + 1, z, x, y, z, 'deepslate_bricks')
                    v.box(x, y + 1, z, x, y + 3, z, 'air')
    # waterfalls tumbling down the diagonals
    for a in (45, 135, 225, 315):
        t = math.radians(a)
        for L in range(levels):
            r = 52 - L * 7
            for i in range(7):
                rr = r - i - 0.5
                x, z = c + math.cos(t) * rr, c + math.sin(t) * rr
                v.set(x, g + L * step, z, 'water')
    # observatory dome on the summit
    top = g + (levels - 1) * step
    v.ellipsoid(c, top, c, 7, 6.6, 7, 'quartz', shell=1.1, ymin=top + 1)
    v.ellipsoid(c, top, c, 5.9, 5.5, 5.9, 'air', ymin=top + 1)
    v.disc(c, c, top, 7, 'pdeepslate')
    v.ellipsoid(c, top + 6.6, c, 2.5, 1.5, 2.5, 'glass_purple')
    v.set(c, top + 4, c, 'sea_lantern')
    for y in (top + 1, top + 2, top + 3):
        for w in (-1, 0, 1):
            v.box(c + w, y, c + 5, c + w, y, c + 8, 'air')
    for a in range(0, 360, 60):
        t = math.radians(a)
        irrigation_pylon(v, round(c + math.cos(t) * 54), round(c + math.sin(t) * 54), 7)
    # storage silos and a barn at the foot
    silo(v, 8, 8, 13, 3)
    silo(v, 104, 104, 13, 3, band='terracotta_purple')
    hay_barn(v, 100, 12, 11, 15)
    return v


LAYOUTS = {
    'lumen_hollow': (lumen_hollow, 'Lumen Hollow (village)', 'Domed homes around a ring monument, giant glowing fungus trees, crystal spires.'),
    'spireholm': (spireholm, 'Spireholm (village)', 'Needle towers on terraces, sky bridges, a great spire over a pool, a ring gate.'),
    'hive_ring': (hive_ring, 'Hive Ring (village)', 'Vorn honeycomb pod houses around a sunken copper hive hall.'),
    'sunwheat_plains': (sunwheat_plains, 'Sunwheat Plains (farmland)', '12 hydrated fields, a pivot field with a crop circle, barn, silos, wind spires.'),
    'terrace_rings': (terrace_rings, 'Terrace Rings (farmland)', 'A hill of circular crop terraces with water channels, waterfalls and a summit observatory.'),
}
