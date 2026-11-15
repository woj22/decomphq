"""Generate the imperial capital as a Minecraft Bedrock world (.mcworld) from the overhead map.

  python gen_city.py [--out PATH] [--preview]

Scale: 1.25 blocks per map pixel (the walled city is ~1,750 x 1,050 blocks). Ground level is y = 0.
Land use comes from imperium/web/data/citymap.json (made by tools/map_extract.py from reference/city_map.png):
R roofs -> building lots, S streets, W water, T trees, F fields, V villas. Landmarks are placed at their map positions.
Every building is enterable: furnished floors, partitions, ladders between storeys, lamps, chests.
"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blocks import *  # noqa
import blocks as BL
import bedrock as BR

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAP = json.load(open(os.path.join(ROOT, "web", "data", "citymap.json")))
S = 1.25
MARGIN = 64
NX, NZ = 2048, 1408
Y0, NY = -16, 176                        # stored y range: -16 .. 159
V = np.zeros((NX, NY, NZ), dtype=np.uint16)
H = np.zeros((NX, NZ), dtype=np.int16)   # top of the ground
OCC = np.zeros((NX, NZ), dtype=bool)      # reserved footprints
AVENUE = np.zeros((NX, NZ), dtype=bool)   # main streets
BE = []                                   # block entities
rng = random.Random(7)


def px2b(px, py):
    return int(round(px * S)) + MARGIN, int(round(py * S)) + MARGIN


# ------------------------------------------------------------------------------------------------ map grid at block resolution
grid = np.array([list(r) for r in MAP["rows"]])                 # (256, 384) of class chars
bx = np.arange(NX)
bz = np.arange(NZ)
gi = np.clip(((bx - MARGIN) / S / 4).astype(int), 0, MAP["w"] - 1)
gj = np.clip(((bz - MARGIN) / S / 4).astype(int), 0, MAP["h"] - 1)
CLS = grid[gj[None, :], gi[:, None]]                              # (NX, NZ)
outside_map = ((bx[:, None] - MARGIN) < 0) | ((bx[:, None] - MARGIN) >= 1536 * S) | ((bz[None, :] - MARGIN) < 0) | ((bz[None, :] - MARGIN) >= 1024 * S)
CLS = np.where(outside_map, "F", CLS)

WALL = [px2b(*p) for p in MAP["wall"]]
GATES = [px2b(*p) for p in [[65, 505], [430, 772], [745, 835], [1100, 137], [1262, 248], [1395, 405], [1425, 505], [1450, 770]]]


def inside_poly(poly):
    from matplotlib.path import Path
    xs, zs = np.meshgrid(bx, bz, indexing="ij")
    return Path(poly).contains_points(np.c_[xs.ravel(), zs.ravel()]).reshape(NX, NZ)


try:
    INSIDE = inside_poly(WALL)
except ImportError:
    from PIL import Image, ImageDraw
    im = Image.new("L", (NX, NZ), 0)
    ImageDraw.Draw(im).polygon(WALL, fill=1)
    INSIDE = np.asarray(im).T.astype(bool)


# ------------------------------------------------------------------------------------------------ primitives
def put(x, y, z, b):
    if 0 <= x < NX and 0 <= z < NZ and Y0 <= y < Y0 + NY:
        V[x, y - Y0, z] = b


def get(x, y, z):
    if 0 <= x < NX and 0 <= z < NZ and Y0 <= y < Y0 + NY:
        return V[x, y - Y0, z]
    return AIR


def box(x0, y0, z0, x1, y1, z1, b):
    """Fill the inclusive box (coordinates in any order) with block b."""
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    x0, z0, y0 = max(x0, 0), max(z0, 0), max(y0, Y0)
    x1, z1, y1 = min(x1, NX - 1), min(z1, NZ - 1), min(y1, Y0 + NY - 1)
    if x0 > x1 or z0 > z1 or y0 > y1:
        return
    V[x0:x1 + 1, y0 - Y0:y1 - Y0 + 1, z0:z1 + 1] = b


def ring(x0, y0, z0, x1, y1, z1, b):
    box(x0, y0, z0, x1, y1, z0, b); box(x0, y0, z1, x1, y1, z1, b)
    box(x0, y0, z0, x0, y1, z1, b); box(x1, y0, z0, x1, y1, z1, b)


def block_entity(x, y, z, data):
    x, y, z = int(x), int(y), int(z)
    data.update({"x": x, "y": y, "z": z})
    BE.append((x, y, z, data))


def chest(x, y, z, f, items=()):
    put(x, y, z, CHEST(f))
    it = BR.List(BR.TAG_COMPOUND, [{"Name": "minecraft:" + n, "Count": BR.Byte(c), "Damage": BR.Short(0), "Slot": BR.Byte(i), "WasPickedUp": BR.Byte(0)}
                                   for i, (n, c) in enumerate(items)])
    block_entity(x, y, z, {"id": "Chest", "x": x, "y": y, "z": z, "Items": it, "isMovable": BR.Byte(1), "Findable": BR.Byte(0)})


def banner(x, y, z, facing, wall=True, laurel=True):
    """Imperial banner: crimson with a gold border and a gold wreath-like flower."""
    put(x, y, z, WALL_BANNER(facing) if wall else STANDING_BANNER(facing))
    pats = BR.List(BR.TAG_COMPOUND, [{"Color": 11, "Pattern": "cbo"}] + ([{"Color": 11, "Pattern": "flo"}] if laurel else []))
    block_entity(x, y, z, {"id": "Banner", "x": x, "y": y, "z": z, "Base": 1, "Type": 0, "Patterns": pats, "isMovable": BR.Byte(1)})


def bed(x, z, y, d):
    """Bed with its foot at (x, z), head one step in direction d (0 S, 1 W, 2 N, 3 E)."""
    dx, dz = [(0, 1), (-1, 0), (0, -1), (1, 0)][d]
    put(x, y, z, BED(d, False)); put(x + dx, y, z + dz, BED(d, True))
    col = rng.choice([14, 14, 11, 4, 0, 10])
    for (a, b2) in ((x, z), (x + dx, z + dz)):
        block_entity(a, y, b2, {"id": "Bed", "x": a, "y": y, "z": b2, "color": BR.Byte(col), "isMovable": BR.Byte(1)})


def pot(x, y, z, plant=None):
    put(x, y, z, FLOWER_POT)
    plant = plant or rng.choice([("red_flower", {"flower_type": "poppy"}), ("red_flower", {"flower_type": "allium"}), ("yellow_flower", {}),
                                 ("sapling", {"sapling_type": "oak", "age_bit": 0}), ("red_flower", {"flower_type": "oxeye"})])
    st = {k: (BR.Byte(v) if k in BR.BYTE_STATES or k == "age_bit" else v) for k, v in plant[1].items()}
    block_entity(x, y, z, {"id": "FlowerPot", "x": x, "y": y, "z": z, "PlantBlock": {"name": "minecraft:" + plant[0], "states": st, "version": BL.VERSION},
                           "isMovable": BR.Byte(1)})


def ground_y(x0, z0, x1, z1):
    return int(H[max(x0, 0):x1 + 1, max(z0, 0):z1 + 1].max())


def foundation(x0, z0, x1, z1, y, b=STONEBRICK):
    """Fill from the lowest ground under the footprint up to y."""
    lo = int(H[max(x0, 0):x1 + 1, max(z0, 0):z1 + 1].min())
    if lo < y:
        box(x0, lo, z0, x1, y, z1, b)


# ------------------------------------------------------------------------------------------------ terrain
def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


PAL = px2b(465, 165)
PAL_Y = 40
xs, zs = np.meshgrid(bx, bz, indexing="ij")
rp = np.hypot(xs - PAL[0], zs - PAL[1])
# the Palatine: a plateau stepped down in terraces with retaining walls
hill = np.select([rp < 84, rp < 98, rp < 112, rp < 126, rp < 140], [PAL_Y, 32, 24, 16, 8], 0)
# countryside: rolling ground beyond the walls, flat near the river
dist_in = np.zeros((NX, NZ))
try:
    from scipy import ndimage
    dist_in = ndimage.distance_transform_edt(~INSIDE)
except ImportError:
    dist_in = np.where(INSIDE, 0, 40)
roll = (5 * np.sin(xs / 61.0) * np.cos(zs / 47.0) + 4 * np.sin((xs + 2 * zs) / 97.0) + 3 * np.cos((xs - zs) / 41.0) + 6)
roll = np.clip(roll, 0, 16) * smooth((dist_in - 6) / 50)
water = CLS == "W"
H[:] = np.maximum(hill, np.where(INSIDE, 0, roll)).astype(np.int16)
H[water] = -5
# keep the river banks low
if "ndimage" in dir():
    near_w = ndimage.distance_transform_edt(~water)
    H[:] = np.where(~water, np.minimum(H, (near_w * 0.6).astype(np.int16)), H)

CAP_PLAT = (px2b(668, 312), px2b(850, 440))


def build_terrain():
    t0 = time.time()
    ys = np.arange(NY)[None, :, None] + Y0
    Hb = H[:, None, :]
    V[:] = np.where(ys <= Hb - 4, STONE, np.where(ys <= Hb - 1, DIRT, np.where(ys == Hb, GRASS, AIR))).astype(np.uint16)
    # river: water to y = -1 over a sand and gravel bed
    wx, wz = np.nonzero(water)
    V[wx, -5 - Y0, wz] = SAND
    for y in range(-4, 0):
        V[wx, y - Y0, wz] = WATER
    # sandy banks
    if "ndimage" in globals() or True:
        try:
            from scipy import ndimage as nd
            bank = (nd.distance_transform_edt(~water) <= 2) & ~water
            bx2, bz2 = np.nonzero(bank & (H <= 1))
            V[bx2, H[bx2, bz2] - Y0, bz2] = SAND
        except ImportError:
            pass
    # retaining walls on the palace hill terraces: stone brick faces where the ground steps down
    step = np.zeros_like(H)
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        step = np.maximum(step, H - np.roll(np.roll(H, dx, 0), dz, 1))
    wx, wz = np.nonzero((step >= 6) & (rp < 150))
    for x, z in zip(wx, wz):
        h = H[x, z]
        V[x, h - 8 - Y0:h + 1 - Y0, z] = STONEBRICK
        V[x, h + 1 - Y0, z] = SLAB("stone_brick")
    print("terrain %.1fs" % (time.time() - t0))


# ------------------------------------------------------------------------------------------------ streets
def pave(x, z, y, kind="street"):
    r = rng.random()
    if kind == "street":
        b = SANDSTONE if r < 0.42 else SANDSTONE_SMOOTH if r < 0.64 else P_ANDESITE if r < 0.8 else SMOOTH_STONE if r < 0.9 else COARSE
    elif kind == "plaza":
        b = SANDSTONE_SMOOTH if (x // 3 + z // 3) % 2 else QUARTZ_SMOOTH
    elif kind == "road":
        b = PATH if r < 0.7 else GRAVEL if r < 0.85 else COARSE
    else:
        b = kind
    V[x, y - Y0, z] = b


def build_streets():
    t0 = time.time()
    sx, sz = np.nonzero(INSIDE & ~OCC & ~water)
    for x, z in zip(sx, sz):
        if rp[x, z] < 140:
            continue
        if AVENUE[x, z]:
            pave(x, z, int(H[x, z]), STONEBRICK if (x + z) % 5 else P_ANDESITE)
        else:
            pave(x, z, int(H[x, z]))
    ax, az = np.nonzero(AVENUE & ~OCC)
    for x, z in zip(ax, az):
        if (x * 31 + z * 17) % 97 == 0 and rp[x, z] > 140:
            y = int(H[x, z])
            box(x, y + 1, z, x, y + 3, z, FENCE["dark_oak"]); put(x, y + 4, z, LANTERN)
    # street lanterns on posts, along street cells next to building blocks
    st = INSIDE & (CLS == "S") & (rp > 140)
    cand = np.argwhere(st[::11, ::11]) * 11
    for x, z in cand:
        if rng.random() < 0.55 and not OCC[x, z]:
            y = int(H[x, z])
            box(x, y + 1, z, x, y + 2, z, FENCE["dark_oak"]); put(x, y + 3, z, LANTERN)
    print("streets %.1fs" % (time.time() - t0))


# ------------------------------------------------------------------------------------------------ furniture and rooms
FOOD = [("bread", 6), ("wheat", 12), ("apple", 5), ("carrot", 8), ("potato", 8), ("cooked_cod", 4), ("honey_bottle", 2)]
GOODS = [("paper", 16), ("book", 3), ("iron_ingot", 4), ("gold_nugget", 9), ("string", 8), ("leather", 5), ("bowl", 4), ("glass_bottle", 6)]


def room_cells(rx0, rz0, rx1, rz1, avoid):
    """Cells along the walls of a room (inside it), clockwise, skipping doorway fronts and the ladder."""
    cells = []
    for x in range(rx0, rx1 + 1):
        cells.append((x, rz0, 3)); cells.append((x, rz1, 2))      # facing away from the wall: 3 = south, 2 = north
    for z in range(rz0 + 1, rz1):
        cells.append((rx0, z, 5)); cells.append((rx1, z, 4))
    return [c for c in cells if (c[0], c[1]) not in avoid]


def furnish(rx0, rz0, rx1, rz1, y, kind, avoid):
    """Furnish a room whose floor is at y (furniture at y + 1)."""
    if rx1 - rx0 < 1 or rz1 - rz0 < 1:
        return
    cells = room_cells(rx0, rz0, rx1, rz1, avoid)
    rng.shuffle(cells)
    used = set()
    f = y + 1

    def take(n=1, along=None):
        for c in cells:
            if (c[0], c[1]) in used:
                continue
            used.add((c[0], c[1]))
            return c
        return None

    cxm, czm = (rx0 + rx1) // 2, (rz0 + rz1) // 2
    if kind == "bedroom":
        for _ in range(1 + ((rx1 - rx0) * (rz1 - rz0) > 20)):
            c = take()
            if not c:
                break
            x, z, fd = c
            # head against the wall the cell is on
            d = {3: 2, 2: 0, 5: 1, 4: 3}[fd]
            dx, dz = [(0, 1), (-1, 0), (0, -1), (1, 0)][d]
            fx, fz = x - dx, z - dz
            if rx0 <= fx <= rx1 and rz0 <= fz <= rz1 and (fx, fz) not in avoid and get(fx, f, fz) == AIR:
                bed(fx, fz, f, d); used.add((fx, fz))
        c = take()
        if c:
            chest(c[0], f, c[1], c[2], rng.sample(GOODS, 2))
        c = take()
        if c:
            put(c[0], f, c[1], PLANKS["spruce"]); pot(c[0], f + 1, c[1])
        put(cxm, f, czm, rng.choice([RED_CARPET, BLUE_CARPET, BROWN_CARPET, PURPLE_CARPET]))
    elif kind == "kitchen":
        for b in (FURNACE, None, CRAFTING, CAULDRON, BARREL, None):
            c = take()
            if not c:
                break
            if b is FURNACE:
                put(c[0], f, c[1], FURNACE(c[2]))
            elif b is BARREL:
                put(c[0], f, c[1], BARREL(1))
            elif b is None:
                chest(c[0], f, c[1], c[2], rng.sample(FOOD, 3))
            else:
                put(c[0], f, c[1], b)
        put(cxm, f, czm, FENCE["oak"]); put(cxm, f + 1, czm, PRESSURE_PLATE())
    elif kind == "living":
        put(cxm, f, czm, FENCE["dark_oak"]); put(cxm, f + 1, czm, PRESSURE_PLATE())
        for (dx, dz, d) in ((1, 0, 0), (-1, 0, 1), (0, 1, 2), (0, -1, 3)):
            if rx0 <= cxm + dx <= rx1 and rz0 <= czm + dz <= rz1 and (cxm + dx, czm + dz) not in avoid:
                put(cxm + dx, f, czm + dz, STAIRS("oak_stairs", d)); used.add((cxm + dx, czm + dz))
        for b in (BOOKSHELF, BOOKSHELF, "pot", "chest"):
            c = take()
            if not c:
                break
            if b == "pot":
                put(c[0], f, c[1], BARREL(1)); pot(c[0], f + 1, c[1])
            elif b == "chest":
                chest(c[0], f, c[1], c[2], rng.sample(GOODS, 2))
            else:
                box(c[0], f, c[1], c[0], f + 1, c[1], b)
    elif kind == "dining":
        L = max(1, min(rx1 - rx0, rz1 - rz0) - 2)
        horiz = (rx1 - rx0) >= (rz1 - rz0)
        for k in range(-(L // 2), L - L // 2):
            tx, tz = (cxm + k, czm) if horiz else (cxm, czm + k)
            if not (rx0 < tx < rx1 and rz0 < tz < rz1):
                continue
            put(tx, f, tz, FENCE["dark_oak"]); put(tx, f + 1, tz, WHITE_CARPET)
            for s, d in ((1, 2 if horiz else 0), (-1, 3 if horiz else 1)):
                cx2, cz2 = (tx, tz + s) if horiz else (tx + s, tz)
                if rx0 <= cx2 <= rx1 and rz0 <= cz2 <= rz1 and (cx2, cz2) not in avoid:
                    put(cx2, f, cz2, STAIRS("spruce_stairs", d))
        c = take()
        if c:
            put(c[0], f, c[1], BARREL(1))
    elif kind.startswith("shop"):
        trade = kind.split(":")[1] if ":" in kind else rng.choice(["grain", "wine", "smith", "cloth", "books", "pottery", "general"])
        stock = {"grain": [HAY, HAY, BARREL(1), COMPOSTER], "wine": [BARREL(1), BARREL(1), BARREL(4), BARREL(5)], "smith": [ANVIL, SMITHING, FURNACE(2), CAULDRON],
                 "cloth": [LOOM, WOOL("red", (161, 39, 34)), WOOL("white", (233, 236, 236)), WOOL("yellow", (249, 198, 39))],
                 "books": [BOOKSHELF, BOOKSHELF, LECTERN(0), CARTO], "pottery": [TERRACOTTA, ORANGE_TC, FLOWER_POT, CAULDRON],
                 "general": [BARREL(1), CRAFTING, FLETCH, BARREL(1)]}[trade]
        for b in stock + stock[:2]:
            c = take()
            if not c:
                break
            put(c[0], f, c[1], b)
            if b == HAY and rng.random() < 0.5:
                put(c[0], f + 1, c[1], HAY)
        c = take()
        if c:
            chest(c[0], f, c[1], c[2], rng.sample(GOODS + FOOD, 3))
        # the counter across the room
        horiz = (rx1 - rx0) >= (rz1 - rz0)
        if horiz:
            for x in range(rx0 + 1, rx1):
                if (x, czm) not in avoid and get(x, f, czm) == AIR and x != cxm:
                    put(x, f, czm, SLAB("smooth_stone", True))
        else:
            for z in range(rz0 + 1, rz1):
                if (cxm, z) not in avoid and get(cxm, f, z) == AIR and z != czm:
                    put(cxm, f, z, SLAB("smooth_stone", True))
    elif kind == "storage":
        for _ in range(6):
            c = take()
            if not c:
                break
            r = rng.random()
            if r < 0.4:
                put(c[0], f, c[1], BARREL(1)); put(c[0], f + 1, c[1], BARREL(1)) if rng.random() < 0.5 else None
            elif r < 0.7:
                chest(c[0], f, c[1], c[2], rng.sample(FOOD + GOODS, 3))
            else:
                put(c[0], f, c[1], HAY)
    elif kind == "tavern":
        for k in range(2):
            tx, tz = cxm + (k * 3 - 1), czm
            if rx0 < tx < rx1:
                put(tx, f, tz, FENCE["spruce"]); put(tx, f + 1, tz, PRESSURE_PLATE())
                for (dx, d) in ((1, 0), (-1, 1)):
                    if rx0 <= tx + dx <= rx1 and get(tx + dx, f, tz) == AIR and (tx + dx, tz) not in avoid:
                        put(tx + dx, f, tz, STAIRS("spruce_stairs", d))
        for b in (BARREL(4), BARREL(5), BARREL(1), CAMPFIRE):
            c = take()
            if c:
                put(c[0], f, c[1], b)
    # a lamp hanging from the ceiling in the middle of every room
    if get(cxm, y + 3, czm) == AIR and (cxm, czm) not in avoid:
        put(cxm, y + 3, czm, LANTERN_HANG)


# ------------------------------------------------------------------------------------------------ roofs
def tile_roof(x0, z0, x1, z1, y, kind="hip", mat="brick", over=1):
    """Low Roman roof from half-slabs: every ring steps in one block and rises half a block."""
    X0, Z0, X1, Z1 = x0 - over, z0 - over, x1 + over, z1 + over
    k = 0
    while True:
        a0, b0, a1, b1 = (X0 + k, Z0 + k, X1 - k, Z1 - k) if kind == "hip" else ((X0, Z0 + k, X1, Z1 - k) if (x1 - x0) >= (z1 - z0) else (X0 + k, Z0, X1 - k, Z1))
        if a0 > a1 or b0 > b1:
            break
        yy = y + k // 2
        sl = SLAB(mat, top=(k % 2 == 1))
        if a1 - a0 <= 1 or b1 - b0 <= 1:
            box(a0, yy, b0, a1, yy, b1, sl if k % 2 == 0 else BRICKS if mat == "brick" else QUARTZ)
            break
        ring(a0, yy, b0, a1, yy, b1, sl) if kind == "hip" else None
        if kind != "hip":
            if (x1 - x0) >= (z1 - z0):
                box(a0, yy, b0, a1, yy, b0, sl); box(a0, yy, b1, a1, yy, b1, sl)
                # gable end walls
                if k > 0:
                    for xx in (x0, x1):
                        box(xx, y, b0 + 1, xx, yy, b1 - 1, WHITE_TC if mat == "brick" else QUARTZ)
            else:
                box(a0, yy, b0, a0, yy, b1, sl); box(a1, yy, b0, a1, yy, b1, sl)
                if k > 0:
                    for zz in (z0, z1):
                        box(a0 + 1, y, zz, a1 - 1, yy, zz, WHITE_TC if mat == "brick" else QUARTZ)
        k += 1


def roof_terrace(x0, z0, x1, z1, y):
    box(x0, y, z0, x1, y, z1, SLAB("smooth_stone"))
    ring(x0, y + 1, z0, x1, y + 1, z1, SLAB("quartz"))
    if rng.random() < 0.7:
        # pergola with vines of leaves and potted plants
        px0, pz0, px1, pz1 = x0 + 2, z0 + 2, min(x1 - 2, x0 + 6), min(z1 - 2, z0 + 6)
        for (a, b2) in ((px0, pz0), (px1, pz0), (px0, pz1), (px1, pz1)):
            box(a, y + 1, b2, a, y + 3, b2, FENCE["spruce"])
        box(px0, y + 4, pz0, px1, y + 4, pz1, LEAVES_OAK)
        put((px0 + px1) // 2, y + 1, (pz0 + pz1) // 2, BARREL(1))
    for _ in range(3):
        a, b2 = rng.randint(x0 + 1, x1 - 1), rng.randint(z0 + 1, z1 - 1)
        if get(a, y + 1, b2) == AIR:
            pot(a, y + 1, b2)


# ------------------------------------------------------------------------------------------------ houses with interiors
WALL_STYLES = [
    {"wall": SANDSTONE_SMOOTH, "trim": QUARTZ_SMOOTH, "wood": "spruce"},
    {"wall": WHITE_TC, "trim": SANDSTONE_SMOOTH, "wood": "oak"},
    {"wall": QUARTZ_SMOOTH, "trim": SANDSTONE_CUT, "wood": "dark_oak"},
    {"wall": SANDSTONE_CUT, "trim": QUARTZ_SMOOTH, "wood": "spruce"},
    {"wall": WHITE_TC, "trim": QUARTZ_SMOOTH, "wood": "spruce"},
    {"wall": YELLOW_TC, "trim": SANDSTONE_SMOOTH, "wood": "oak"},
]


def street_side(x0, z0, x1, z1):
    """0 = -z (north), 1 = +x (east), 2 = +z (south), 3 = -x (west): the side facing the most street."""
    def score(cells):
        return sum(1 for (x, z) in cells if 0 <= x < NX and 0 <= z < NZ and CLS[x, z] in "SP" and not OCC[x, z])
    sides = [[(x, z0 - 2) for x in range(x0, x1 + 1)], [(x1 + 2, z) for z in range(z0, z1 + 1)],
             [(x, z1 + 2) for x in range(x0, x1 + 1)], [(x0 - 2, z) for z in range(z0, z1 + 1)]]
    sc = [score(s) for s in sides]
    best = int(np.argmax(sc))
    return best if sc[best] > 0 else rng.randrange(4)


def door_at(x, y, z, side, kind="spruce_door"):
    d = {0: 3, 1: 0, 2: 1, 3: 2}[side]           # door faces outward
    kind = "wooden_door" if kind == "oak_door" else kind
    put(x, y, z, DOOR(kind, d, False)); put(x, y + 1, z, DOOR(kind, d, True))
    ox, oz = [(0, -1), (1, 0), (0, 1), (-1, 0)][side]
    if get(x + ox, y - 1, z + oz) == AIR or get(x + ox, y, z + oz) == AIR:
        pass
    # a doorstep and a lamp beside the door
    put(x + ox, y + 2, z + oz, AIR)


def house(x0, z0, x1, z1, floors, style=None, shops=False, roof=None, door_side=None, rich=False):
    st = style or rng.choice(WALL_STYLES)
    wall, trim, wood = st["wall"], st["trim"], st["wood"]
    y0 = ground_y(x0, z0, x1, z1)
    foundation(x0, z0, x1, z1, y0)
    FH = 4
    top = y0 + floors * FH
    box(x0, y0, z0, x1, top, z1, wall)
    box(x0 + 1, y0 + 1, z0 + 1, x1 - 1, top - 1, z1 - 1, AIR)
    ring(x0, y0, z0, x1, y0, z1, STONEBRICK)
    for (a, b2) in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
        box(a, y0, b2, a, top, b2, QUARTZ_PILLAR if rich else trim)
    ring(x0, top, z0, x1, top, z1, trim)
    side = street_side(x0, z0, x1, z1) if door_side is None else door_side
    w, d = x1 - x0, z1 - z0
    ladder = (x0 + 1, z0 + 1) if side != 0 else (x1 - 1, z1 - 1)
    lad_face = 3 if ladder[1] == z0 + 1 else 2
    # partitions: split the long axis, and the short one too for big floors
    splits_x = [x0 + w // 2] if w >= 9 else []
    splits_z = [z0 + d // 2] if d >= 9 and (w >= 12 or not splits_x) else []
    for f in range(floors):
        yf = y0 + f * FH
        box(x0 + 1, yf, z0 + 1, x1 - 1, yf, z1 - 1, PLANKS[wood])
        if f > 0:
            ring(x0, yf, z0, x1, yf, z1, trim)
        doors = set()
        for sx in splits_x:
            box(sx, yf + 1, z0 + 1, sx, yf + 3, z1 - 1, PLANKS[wood] if f else wall)
            for dz_ in ([z0 + 2, z1 - 2] if splits_z else [rng.randint(z0 + 2, z1 - 2)]):
                box(sx, yf + 1, dz_, sx, yf + 2, dz_, AIR); doors |= {(sx - 1, dz_), (sx + 1, dz_), (sx, dz_)}
        for sz in splits_z:
            box(x0 + 1, yf + 1, sz, x1 - 1, yf + 3, sz, PLANKS[wood] if f else wall)
            for dx_ in ([x0 + 2, x1 - 2] if splits_x else [rng.randint(x0 + 2, x1 - 2)]):
                box(dx_, yf + 1, sz, dx_, yf + 2, sz, AIR); doors |= {(dx_, sz - 1), (dx_, sz + 1), (dx_, sz)}
        # windows on every side (the shop front and the door bay stay clear on the ground floor)
        dcx = (x0 + x1) // 2 if side in (0, 2) else (z0 + z1) // 2
        for s_ in range(4):
            if s_ % 2 == 0:
                zz = z0 if s_ == 0 else z1
                spots = [(x, zz) for x in range(x0 + 2, x1 - 1, 3)]
            else:
                xx = x1 if s_ == 1 else x0
                spots = [(xx, z) for z in range(z0 + 2, z1 - 1, 3)]
            for (a_, b2) in spots:
                along = a_ if s_ % 2 == 0 else b2
                if f == 0 and s_ == side and (shops or abs(along - dcx) <= 1):
                    continue
                box(a_, yf + 2, b2, a_, yf + 2 + (f > 0), b2, PANE)
        # ladder up through the floors
        lx, lz = ladder
        box(lx, yf + 1, lz, lx, yf + FH, lz, LADDER(lad_face) if f < floors - 1 else AIR)
        avoid = doors | {ladder, (ladder[0], ladder[1] + (1 if lad_face == 3 else -1))}
        if f == 0:
            cxm_, czm_ = (x0 + x1) // 2, (z0 + z1) // 2
            avoid |= {[(cxm_, z0 + 1), (x1 - 1, czm_), (cxm_, z1 - 1), (x0 + 1, czm_)][side]}
        # rooms
        xs_ = [x0] + splits_x + [x1]
        zs_ = [z0] + splits_z + [z1]
        rooms = [(xs_[i] + 1, zs_[j] + 1, xs_[i + 1] - 1, zs_[j + 1] - 1) for i in range(len(xs_) - 1) for j in range(len(zs_) - 1)]
        if f == 0:
            kinds = ["shop", "kitchen", "storage", "tavern"] if shops else ["living", "kitchen", "dining", "storage"]
        else:
            kinds = ["bedroom", "living", "bedroom", "dining", "bedroom", "storage"]
        rng.shuffle(kinds)
        for i, r in enumerate(rooms):
            furnish(*r, yf, kinds[i % len(kinds)], avoid)
    # ground-floor door and shop fronts
    cxm, czm = (x0 + x1) // 2, (z0 + z1) // 2
    if side in (0, 2):
        zz = z0 if side == 0 else z1
        door_at(cxm, y0 + 1, zz, side)
        if shops:
            oz = -1 if side == 0 else 1
            for a in range(x0 + 2, x1 - 1, 3):
                if abs(a - cxm) > 1:
                    box(a, y0 + 1, zz, min(a + 1, x1 - 1), y0 + 2, zz, AIR)
                    box(a, y0 + 4, zz + oz, min(a + 1, x1 - 1), y0 + 4, zz + oz, AWNING_COLORS[(a // 3) % len(AWNING_COLORS)])
    else:
        xx = x1 if side == 1 else x0
        door_at(xx, y0 + 1, czm, side)
        if shops:
            ox = 1 if side == 1 else -1
            for b2 in range(z0 + 2, z1 - 1, 3):
                if abs(b2 - czm) > 1:
                    box(xx, y0 + 1, b2, xx, y0 + 2, min(b2 + 1, z1 - 1), AIR)
                    box(xx + ox, y0 + 4, b2, xx + ox, y0 + 4, min(b2 + 1, z1 - 1), AWNING_COLORS[(b2 // 3) % len(AWNING_COLORS)])
    # clear what used to be in front of the ladder at the ground-floor doorway
    rk = roof or rng.choice(["hip", "hip", "hip", "gable", "terrace"])
    if rk == "terrace":
        roof_terrace(x0, z0, x1, z1, top)
        lx, lz = ladder
        box(lx, top - FH + 1, lz, lx, top + 1, lz, LADDER(lad_face))
        put(lx, top, lz, LADDER(lad_face))
    else:
        tile_roof(x0, z0, x1, z1, top + 1, rk, "brick")
    OCC[x0:x1 + 1, z0:z1 + 1] = True
    return top


def domus(x0, z0, x1, z1):
    """A single-storey town house around an atrium with a rain pool, a peristyle garden behind."""
    st = rng.choice(WALL_STYLES)
    y0 = ground_y(x0, z0, x1, z1)
    foundation(x0, z0, x1, z1, y0)
    top = y0 + 5
    box(x0, y0, z0, x1, top, z1, st["wall"])
    box(x0 + 1, y0 + 1, z0 + 1, x1 - 1, top - 1, z1 - 1, AIR)
    box(x0 + 1, y0, z0 + 1, x1 - 1, y0, z1 - 1, PLANKS[st["wood"]])
    side = street_side(x0, z0, x1, z1)
    horiz = side in (0, 2)
    # atrium in the front half, peristyle garden in the back half
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if horiz:
        fz = (z0 + cz) // 2 if side == 0 else (cz + z1) // 2
        bz0, bz1 = (cz + 1, z1 - 1) if side == 0 else (z0 + 1, cz - 1)
        ax0, az0, ax1, az1 = cx - 2, fz - 2, cx + 2, fz + 2
        gx0, gz0, gx1, gz1 = x0 + 3, bz0 + 1, x1 - 3, bz1 - 1
    else:
        fx = (x0 + cx) // 2 if side == 3 else (cx + x1) // 2
        bx0, bx1 = (cx + 1, x1 - 1) if side == 3 else (x0 + 1, cx - 1)
        ax0, az0, ax1, az1 = fx - 2, cz - 2, fx + 2, cz + 2
        gx0, gz0, gx1, gz1 = bx0 + 1, z0 + 3, bx1 - 1, z1 - 3
    # atrium: the roof opens over a sunken pool
    box(ax0, y0, az0, ax1, y0, az1, QUARTZ_SMOOTH)
    box(ax0 + 1, y0, az0 + 1, ax1 - 1, y0, az1 - 1, WATER)
    box(ax0 + 1, y0 - 1, az0 + 1, ax1 - 1, y0 - 1, az1 - 1, QUARTZ_SMOOTH)
    for (a, b2) in ((ax0, az0), (ax1, az0), (ax0, az1), (ax1, az1)):
        box(a, y0 + 1, b2, a, top - 1, b2, QUARTZ_PILLAR)
    # peristyle garden: open to the sky, ringed by columns
    if gx1 - gx0 >= 3 and gz1 - gz0 >= 3:
        box(gx0, y0, gz0, gx1, y0, gz1, GRASS)
        box(gx0, y0 + 1, gz0, gx1, top + 3, gz1, AIR)
        for a in range(gx0, gx1 + 1, 2):
            for b2 in (gz0, gz1):
                box(a, y0 + 1, b2, a, top - 1, b2, QUARTZ_PILLAR); put(a, y0, b2, QUARTZ_SMOOTH)
        for b2 in range(gz0, gz1 + 1, 2):
            for a in (gx0, gx1):
                box(a, y0 + 1, b2, a, top - 1, b2, QUARTZ_PILLAR); put(a, y0, b2, QUARTZ_SMOOTH)
        gcx, gcz = (gx0 + gx1) // 2, (gz0 + gz1) // 2
        put(gcx, y0, gcz, WATER); put(gcx, y0 + 1, gcz, AIR)
        for (a, b2) in ((gcx - 1, gcz), (gcx + 1, gcz), (gcx, gcz - 1), (gcx, gcz + 1)):
            put(a, y0 + 1, b2, SLAB("quartz"))
        for _ in range((gx1 - gx0) * (gz1 - gz0) // 6):
            a, b2 = rng.randint(gx0 + 1, gx1 - 1), rng.randint(gz0 + 1, gz1 - 1)
            if get(a, y0 + 1, b2) == AIR:
                put(a, y0 + 1, b2, rng.choice([POPPY, DANDELION, ALLIUM, TALLGRASS, TALLGRASS]))
        put(gx0 + 1, y0 + 1, gz0 + 1, AIR); cypress(gx0 + 1, y0, gz0 + 1, rng.randint(5, 7))
    # rooms around: partitions every ~5 blocks along the walls
    avoid = set()
    if horiz:
        for xx in range(x0 + 5, x1 - 2, 5):
            box(xx, y0 + 1, z0 + 1, xx, top - 1, z0 + 4, st["wall"]); box(xx, y0 + 1, z1 - 4, xx, top - 1, z1 - 1, st["wall"])
        for xx in range(x0 + 1, x1 - 1, 5):
            furnish(xx, z0 + 1, min(xx + 3, x1 - 1), z0 + 3, y0, rng.choice(["bedroom", "living", "dining", "kitchen"]), avoid)
            furnish(xx, z1 - 3, min(xx + 3, x1 - 1), z1 - 1, y0, rng.choice(["bedroom", "storage", "dining"]), avoid)
    else:
        for zz in range(z0 + 5, z1 - 2, 5):
            box(x0 + 1, y0 + 1, zz, x0 + 4, top - 1, zz, st["wall"]); box(x1 - 4, y0 + 1, zz, x1 - 1, top - 1, zz, st["wall"])
        for zz in range(z0 + 1, z1 - 1, 5):
            furnish(x0 + 1, zz, x0 + 3, min(zz + 3, z1 - 1), y0, rng.choice(["bedroom", "living", "dining", "kitchen"]), avoid)
            furnish(x1 - 3, zz, x1 - 1, min(zz + 3, z1 - 1), y0, rng.choice(["bedroom", "storage", "dining"]), avoid)
    # doorways through the room partitions toward the middle
    if horiz:
        box(x0 + 2, y0 + 1, z0 + 4, x1 - 2, y0 + 2, z0 + 4, AIR) if False else None
    if horiz:
        door_at(cx, y0 + 1, z0 if side == 0 else z1, side)
    else:
        door_at(x1 if side == 1 else x0, y0 + 1, cz, side)
    # roof with openings over the atrium and garden
    tile_roof(x0, z0, x1, z1, top + 1, "hip")
    box(ax0 + 1, top, az0 + 1, ax1 - 1, top + 12, az1 - 1, AIR)
    if gx1 - gx0 >= 3 and gz1 - gz0 >= 3:
        box(gx0 + 1, top, gz0 + 1, gx1 - 1, top + 12, gz1 - 1, AIR)
    OCC[x0:x1 + 1, z0:z1 + 1] = True


# ------------------------------------------------------------------------------------------------ trees
def cypress(x, y, z, h):
    box(x, y + 1, z, x, y + 2, z, LOG_SPRUCE)
    for k in range(2, h + 1):
        r = 1 if 3 <= k <= h - 3 else 0
        if r:
            box(x - 1, y + k, z, x + 1, y + k, z, LEAVES_SPRUCE); box(x, y + k, z - 1, x, y + k, z + 1, LEAVES_SPRUCE)
        put(x, y + k, z, LEAVES_SPRUCE)
    put(x, y + h + 1, z, LEAVES_SPRUCE)


def pine(x, y, z, h):
    box(x, y + 1, z, x, y + h, z, LOG_DARK)
    for dy, r in ((h - 1, 2), (h, 3), (h + 1, 2)):
        for a in range(-r, r + 1):
            for b2 in range(-r, r + 1):
                if a * a + b2 * b2 <= r * r + 1 and get(x + a, y + dy, z + b2) == AIR:
                    put(x + a, y + dy, z + b2, LEAVES_DARK)


def olive(x, y, z):
    box(x, y + 1, z, x, y + 2, z, LOG_OAK)
    for a in range(-2, 3):
        for b2 in range(-2, 3):
            for dy in (3, 4):
                if abs(a) + abs(b2) <= (3 if dy == 3 else 2) and get(x + a, y + dy, z + b2) == AIR:
                    put(x + a, y + dy, z + b2, LEAVES_ACACIA if rng.random() < 0.5 else LEAVES_OAK)


def tree(x, z):
    y = int(H[x, z])
    if get(x, y + 1, z) != AIR or CLS[x, z] == "W":
        return
    r = rng.random()
    if r < 0.55:
        cypress(x, y, z, rng.randint(7, 11))
    elif r < 0.85:
        pine(x, y, z, rng.randint(6, 9))
    else:
        olive(x, y, z)


# ------------------------------------------------------------------------------------------------ architecture kit
def column(x, y, z, h, base=QUARTZ_SMOOTH, shaft=QUARTZ_PILLAR, cap=QUARTZ_CHISELED):
    put(x, y, z, base)
    box(x, y + 1, z, x, y + h - 2, z, shaft)
    put(x, y + h - 1, z, cap)


def statue(x, y, z, facing=2, mat=QUARTZ_SMOOTH, spear=True):
    """A standing figure about 9 blocks tall on its own pedestal (facing: 0 N, 1 E, 2 S, 3 W)."""
    box(x - 1, y + 1, z - 1, x + 1, y + 2, z + 1, QUARTZ_CHISELED)
    box(x - 1, y + 3, z - 1, x + 1, y + 3, z + 1, SLAB("quartz"))
    yb = y + 3
    box(x - 1, yb + 1, z, x + 1, yb + 3, z, mat)              # legs and robe
    box(x - 1, yb + 4, z, x + 1, yb + 6, z, mat)              # torso
    across = (1, 0) if facing in (0, 2) else (0, 1)
    for s in (-1, 1):
        put(x + s * (2 if across[0] else 0), yb + 5, z + s * (2 if across[1] else 0), mat)     # shoulders/arms
    put(x, yb + 7, z, mat)
    put(x, yb + 8, z, SANDSTONE_SMOOTH if mat == QUARTZ_SMOOTH else mat)                  # head
    if spear:
        sx, sz = (x + 2, z) if across[0] else (x, z + 2)
        box(sx, yb + 1, sz, sx, yb + 9, sz, FENCE["birch"])
        put(sx, yb + 10, sz, GOLD)


def brazier(x, y, z):
    put(x, y + 1, z, QUARTZ_CHISELED)
    put(x, y + 2, z, CAULDRON if False else SLAB("quartz", True))
    put(x, y + 3, z, CAMPFIRE)


def temple(x0, z0, w, d, facing=2, colh=8, gold=False, statue_in=True):
    """A peripteral temple on a podium. facing: 2 = front toward +z (south), 0 = toward -z."""
    x1, z1 = x0 + w - 1, z0 + d - 1
    y = ground_y(x0, z0, x1, z1)
    foundation(x0, z0, x1, z1, y)
    pod = 3
    box(x0, y + 1, z0, x1, y + pod, z1, STONEBRICK)
    ring(x0, y + pod, z0, x1, y + pod, z1, QUARTZ_SMOOTH)
    box(x0 + 1, y + pod, z0 + 1, x1 - 1, y + pod, z1 - 1, QUARTZ_SMOOTH)
    # front steps the full width
    for k in range(pod):
        if facing == 2:
            box(x0 + 1, y + 1 + k, z1 + pod - k, x1 - 1, y + 1 + k, z1 + pod - k, STAIRS("quartz_stairs", 3))
            box(x0 + 1, y + 1, z1 + pod - k, x1 - 1, y + k, z1 + pod - k, QUARTZ_SMOOTH)
        else:
            box(x0 + 1, y + 1 + k, z0 - pod + k, x1 - 1, y + 1 + k, z0 - pod + k, STAIRS("quartz_stairs", 2))
            box(x0 + 1, y + 1, z0 - pod + k, x1 - 1, y + k, z0 - pod + k, QUARTZ_SMOOTH)
    yb = y + pod
    # columns all round, every other block
    for x in range(x0 + 1, x1, 2):
        column(x, yb + 1, z0 + 1, colh); column(x, yb + 1, z1 - 1, colh)
    for z in range(z0 + 1, z1, 2):
        column(x0 + 1, yb + 1, z, colh); column(x1 - 1, yb + 1, z, colh)
    # cella with a great door toward the front
    cx0, cz0, cx1, cz1 = x0 + 4, z0 + (5 if facing == 0 else 4), x1 - 4, z1 - (5 if facing == 2 else 4)
    box(cx0, yb + 1, cz0, cx1, yb + colh, cz1, QUARTZ_BRICKS)
    box(cx0 + 1, yb + 1, cz0 + 1, cx1 - 1, yb + colh - 1, cz1 - 1, AIR)
    box(cx0 + 1, yb, cz0 + 1, cx1 - 1, yb, cz1 - 1, P_DIORITE)
    dz_ = cz1 if facing == 2 else cz0
    mx = (x0 + x1) // 2
    box(mx - 1, yb + 1, dz_, mx + 1, yb + 4, dz_, AIR)
    # inside: the god's statue at the back, an altar, braziers, banners
    bz_ = cz0 + 2 if facing == 2 else cz1 - 2
    if statue_in and cz1 - cz0 > 8:
        statue(mx, yb, bz_, facing, GOLD if gold else QUARTZ_SMOOTH, spear=True)
        for s in (-1, 1):
            brazier(mx + s * 3, yb, bz_ + (3 if facing == 2 else -3))
        put(mx, yb + 1, (cz0 + cz1) // 2, QUARTZ_CHISELED); put(mx, yb + 2, (cz0 + cz1) // 2, SLAB("quartz"))
        for z in range(cz0 + 2, cz1 - 1, 2):
            if z != (cz0 + cz1) // 2:
                put(mx, yb, z, RED_WOOL)
        for z in range(cz0 + 2, cz1 - 1, 4):
            banner(cx0 + 1, yb + colh - 2, z, 5); banner(cx1 - 1, yb + colh - 2, z, 4)
            put(cx0 + 1, yb + 1, z, LANTERN); put(cx1 - 1, yb + 1, z, LANTERN)
    # entablature: architrave, a crimson frieze with gold dentils, cornice
    ye = yb + colh + 1
    box(x0, ye, z0, x1, ye, z1, QUARTZ_SMOOTH)
    ring(x0, ye + 1, z0, x1, ye + 1, z1, RED_TC)
    for x in range(x0, x1 + 1, 2):
        put(x, ye + 1, z0, GOLD); put(x, ye + 1, z1, GOLD)
    box(x0 + 1, ye + 1, z0 + 1, x1 - 1, ye + 1, z1 - 1, QUARTZ_SMOOTH)
    box(x0, ye + 2, z0, x1, ye + 2, z1, QUARTZ_SMOOTH)
    # pitched roof along the length with pediments at both ends
    k = 0
    while x0 + k <= x1 - k:
        yy = ye + 3 + k // 2
        sl = SLAB("brick" if not gold else "smooth_sandstone", top=(k % 2 == 1))
        box(x0 + k, yy, z0, x0 + k, yy, z1, sl); box(x1 - k, yy, z0, x1 - k, yy, z1, sl)
        for zz in (z0, z1):
            box(x0 + k + 1, ye + 3, zz, x1 - k - 1, yy, zz, QUARTZ_SMOOTH)
        k += 1
    for zz in (z0 - 1, z1 + 1) if False else ():
        pass
    # pediment ornament: a gold acroterion
    put((x0 + x1) // 2, ye + 4 + (w // 2) // 2, z1 if facing == 2 else z0, GOLD)
    OCC[x0:x1 + 1, z0 - pod - 1:z1 + pod + 2] = True
    return yb


def rotunda(cx, cz, r=10, h=10):
    y = ground_y(cx - r, cz - r, cx + r, cz + r)
    foundation(cx - r - 1, cz - r - 1, cx + r + 1, cz + r + 1, y)
    for x in range(cx - r - 1, cx + r + 2):
        for z in range(cz - r - 1, cz + r + 2):
            d = math.hypot(x - cx, z - cz)
            if d <= r + 0.5:
                put(x, y, z, P_DIORITE if (x + z) % 2 else QUARTZ_SMOOTH)
                if d > r - 0.7:
                    box(x, y + 1, z, x, y + h, z, QUARTZ_BRICKS)
                # dome: hemisphere shell
            for yy in range(0, r + 1):
                rr = math.sqrt(max(0, r * r - yy * yy))
                if rr - 1.0 < d <= rr + 0.3 and d > 1.6:
                    put(x, y + h + 1 + yy, z, SANDSTONE_SMOOTH if yy < r - 2 else GOLD)
    # interior: statue under the oculus, lanterns, a ring of banners
    statue(cx, y, cz, 2, QUARTZ_SMOOTH)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        px, pz = cx + int(round(math.cos(a) * (r - 1))), cz + int(round(math.sin(a) * (r - 1)))
        put(px, y + 1, pz, LANTERN)
    # portico on the south
    for x in range(cx - 4, cx + 5, 2):
        for z in (cz + r + 2, cz + r + 4):
            column(x, y + 1, z, h)
        put(x, y, cz + r + 3, QUARTZ_SMOOTH)
    box(cx - 5, y + h + 1, cz + r, cx + 5, y + h + 1, cz + r + 5, QUARTZ_SMOOTH)
    box(cx - 5, y, cz + r, cx + 5, y, cz + r + 5, QUARTZ_SMOOTH)
    box(cx - 1, y + 1, cz + r - 1, cx + 1, y + 4, cz + r, AIR)
    OCC[cx - r - 2:cx + r + 3, cz - r - 2:cz + r + 7] = True


def fountain(cx, cz, r=4, y=None):
    y = int(H[cx, cz]) if y is None else y
    for x in range(cx - r, cx + r + 1):
        for z in range(cz - r, cz + r + 1):
            d = math.hypot(x - cx, z - cz)
            if d <= r + 0.4:
                put(x, y, z, QUARTZ_SMOOTH)
                if d > r - 0.6:
                    put(x, y + 1, z, SLAB("quartz"))
                else:
                    put(x, y, z, WATER); put(x, y - 1, z, QUARTZ_SMOOTH)
    box(cx, y, cz, cx, y + 3, cz, QUARTZ_PILLAR)
    put(cx, y + 4, cz, WATER)
    OCC[cx - r:cx + r + 1, cz - r:cz + r + 1] = True


# ------------------------------------------------------------------------------------------------ landmarks
def build_capitol():
    (x0, z0), (x1, z1) = CAP_PLAT
    yp = 6
    box(x0, 0, z0, x1, yp, z1, STONEBRICK)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            put(x, yp, z, P_DIORITE if (x // 4 + z // 4) % 2 else QUARTZ_SMOOTH)
    H[x0:x1 + 1, z0:z1 + 1] = yp
    OCC[x0:x1 + 1, z0:z1 + 1] = True
    mx = (x0 + x1) // 2
    # the grand south stair
    for k in range(yp):
        box(mx - 14, k + 1, z1 + yp - k, mx + 14, k + 1, z1 + yp - k, STAIRS("quartz_stairs", 3))
        box(mx - 14, 0, z1 + yp - k, mx + 14, k, z1 + yp - k, STONEBRICK)
    for k in range(0, yp * 2):
        put(mx, 0, z1 + yp, P_DIORITE)
    for s in (-1, 1):
        box(mx + s * 15, 1, z1, mx + s * 15, yp + 1, z1 + yp, QUARTZ_SMOOTH)
    # colonnaded stoas on three sides, with offices and shops inside
    for (a0, b0, a1, b1, side) in ((x0 + 2, z0 + 2, x1 - 2, z0 + 12, 2), (x0 + 2, z0 + 14, x0 + 12, z1 - 4, 1), (x1 - 12, z0 + 14, x1 - 2, z1 - 4, 3)):
        stoa(a0, b0, a1, b1, yp, side)
    # the great temple, two lesser temples, gardens and an altar
    tw, td = 39, 59
    ty = temple(mx - tw // 2, z0 + 26, tw, td, 2, 12, gold=True)
    for s, ox in ((-1, x0 + 22), (1, x1 - 40)):
        temple(ox, z0 + 60, 19, 27, 2, 8)
    for (gx, gz) in ((x0 + 25, z1 - 35), (x1 - 45, z1 - 35)):
        box(gx, yp, gz, gx + 20, yp, gz + 22, GRASS)
        for k in range(10):
            a, b2 = rng.randint(gx + 1, gx + 19), rng.randint(gz + 1, gz + 21)
            if get(a, yp + 1, b2) == AIR:
                cypress(a, yp, b2, rng.randint(7, 10))
        fountain(gx + 10, gz + 11, 3, yp)
    # the processional way: statues and braziers in pairs, cypress rows along the stoas
    for z in range(z0 + 26 + td + 14, z1 - 4, 10):
        for sgn in (-1, 1):
            statue(mx + sgn * 9, yp, z, 1 if sgn < 0 else 3)
            brazier(mx + sgn * 5, yp, z + 5)
    for z in range(z0 + 16, z1 - 8, 5):
        for xx in (x0 + 16, x1 - 16):
            if get(xx, yp + 1, z) == AIR:
                put(xx, yp, z, GRASS); cypress(xx, yp, z, 8)
    for z in range(z0 + 26 + td + 10, z1):
        for xx in range(mx - 2, mx + 3):
            put(xx, yp, z, RED_WOOL if abs(xx - mx) < 2 else GOLD if z % 3 == 0 else QUARTZ_SMOOTH)
    ax, az = mx, z0 + 26 + td + 7
    box(ax - 2, yp + 1, az - 1, ax + 2, yp + 1, az + 1, QUARTZ_CHISELED); put(ax, yp + 2, az, CAMPFIRE)
    for s in (-1, 1):
        statue(mx + s * 8, yp, az + 6, 2, QUARTZ_SMOOTH)
    print("capitol at", mx, z0)


def stoa(x0, z0, x1, z1, y, open_side):
    """A long colonnade: columns along the open side, a roofed hall of rooms behind."""
    colh = 7
    w, d = x1 - x0, z1 - z0
    box(x0, y, z0, x1, y + colh, z1, QUARTZ_BRICKS)
    box(x0 + 1, y + 1, z0 + 1, x1 - 1, y + colh - 1, z1 - 1, AIR)
    box(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, PLANKS["spruce"])
    # open the colonnade side: columns every 3 blocks, a walkway behind
    if open_side in (0, 2):
        zz = z1 if open_side == 2 else z0
        inner = zz - 3 if open_side == 2 else zz + 3
        box(x0 + 1, y + 1, zz, x1 - 1, y + colh - 1, zz, AIR)
        for x in range(x0 + 1, x1, 3):
            column(x, y, zz, colh)
        box(x0 + 1, y + 1, inner, x1 - 1, y + colh - 1, inner, QUARTZ_BRICKS)
        box(x0 + 1, y, min(zz, inner) + 1, x1 - 1, y, max(zz, inner) - 1, P_DIORITE)
        for x in range(x0 + 4, x1 - 2, 7):
            box(x, y + 1, inner, x, y + 2, inner, AIR)
            r0, r1 = (z0 + 1, inner - 1) if open_side == 2 else (inner + 1, z1 - 1)
            box(x + 3, y + 1, r0, x + 3, y + colh - 1, r1, QUARTZ_BRICKS)
            furnish(x - 2, r0, x + 2, r1, y, rng.choice(["shop", "living", "storage", "shop:books"]), set())
            banner(x, y + colh - 2, inner + (1 if open_side == 2 else -1), 3 if open_side == 2 else 2)
    else:
        xx = x1 if open_side == 1 else x0
        inner = xx - 3 if open_side == 1 else xx + 3
        box(xx, y + 1, z0 + 1, xx, y + colh - 1, z1 - 1, AIR)
        for z in range(z0 + 1, z1, 3):
            column(xx, y, z, colh)
        box(inner, y + 1, z0 + 1, inner, y + colh - 1, z1 - 1, QUARTZ_BRICKS)
        box(min(xx, inner) + 1, y, z0 + 1, max(xx, inner) - 1, y, z1 - 1, P_DIORITE)
        for z in range(z0 + 4, z1 - 2, 7):
            box(inner, y + 1, z, inner, y + 2, z, AIR)
            r0, r1 = (x0 + 1, inner - 1) if open_side == 1 else (inner + 1, x1 - 1)
            box(r0, y + 1, z + 3, r1, y + colh - 1, z + 3, QUARTZ_BRICKS)
            furnish(r0, z - 2, r1, z + 2, y, rng.choice(["shop", "living", "storage", "shop:books"]), set())
            banner(inner + (1 if open_side == 1 else -1), y + colh - 2, z, 5 if open_side == 1 else 4)
    tile_roof(x0, z0, x1, z1, y + colh + 1, "hip")
    OCC[x0:x1 + 1, z0:z1 + 1] = True


def build_forum():
    (x0, z0), (x1, z1) = px2b(700, 470), px2b(820, 665)
    mx = (x0 + x1) // 2
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            put(x, 0, z, SANDSTONE_SMOOTH if (x // 3 + z // 3) % 2 else QUARTZ_SMOOTH)
    H[x0:x1 + 1, z0:z1 + 1] = 0
    OCC[x0 - 1:x1 + 2, z0 - 1:z1 + 2] = True
    # the temple of the deified emperor at the north end, facing the square
    temple(mx - 13, z0 + 2, 27, 37, 2, 10)
    # porticoes with shops (tabernae) down both long sides
    stoa(x0, z0 + 46, x0 + 13, z1 - 4, 0, 1)
    stoa(x1 - 13, z0 + 46, x1, z1 - 4, 0, 3)
    for fz in (px2b(760, 610)[1], px2b(760, 645)[1]):
        fountain(mx, fz, 5, 0)
    for z in range(z0 + 48, z1 - 6, 14):
        for s in (-1, 1):
            statue(mx + s * 22, 0, z, 1 if s < 0 else 3)
    # market stalls
    for k in range(10):
        sx, sz = rng.randint(x0 + 18, x1 - 22), rng.randint(z0 + 50, z1 - 10)
        if OCC[sx - 1:sx + 4, sz - 1:sz + 3].any() and not abs(sx - mx) > 30:
            pass
        if abs(sx - mx) < 7:
            continue
        for (a, b2) in ((sx, sz), (sx + 3, sz), (sx, sz + 2), (sx + 3, sz + 2)):
            box(a, 1, b2, a, 3, b2, FENCE["spruce"])
        box(sx, 4, sz, sx + 3, 4, sz + 2, AWNING_COLORS[k % len(AWNING_COLORS)])
        put(sx + 1, 1, sz + 1, BARREL(1)); put(sx + 2, 1, sz + 1, rng.choice([HAY, BARREL(1), CAULDRON, PUMPKIN_DUMMY]))
    print("forum")


PUMPKIN_DUMMY = B("pumpkin", {"direction": 0}, (220, 130, 30))


def build_colosseum():
    cx, cz = px2b(1085, 350)
    a, b = 82, 69
    top = 34
    yb = 0
    for x in range(cx - a - 1, cx + a + 2):
        for z in range(cz - b - 1, cz + b + 2):
            r = math.hypot((x - cx) / a, (z - cz) / b)
            if r > 1.0:
                continue
            ang = math.atan2((z - cz) / b, (x - cx) / a)
            put(x, yb, z, SANDSTONE)
            if r >= 0.965:
                # outer wall: four arcaded tiers, the top one with small windows
                box(x, 1, z, x, top, z, SANDSTONE_SMOOTH if r > 0.985 else SANDSTONE_CUT)
                bay = int((ang + math.pi) / (2 * math.pi) * 80)
                frac = (ang + math.pi) / (2 * math.pi) * 80 - bay
                for t in range(3):
                    y0 = 1 + t * 8
                    if 0.3 < frac < 0.85 and r > 0.97:
                        box(x, y0 + 1, z, x, y0 + 5, z, AIR)
                        if frac < 0.42 or frac > 0.73:
                            put(x, y0 + 5, z, SANDSTONE_SMOOTH)
                    put(x, y0 + 7, z, SANDSTONE_CHISELED if r > 0.985 else SANDSTONE_CUT)
                if 0.45 < frac < 0.6 and r > 0.97:
                    put(x, 28, z, AIR)
                put(x, top + 1, z, SLAB("smooth_sandstone"))
            elif r >= 0.6:
                # seating rakes up from the arena wall to the outer wall, hollow underneath for the corridors
                t = (r - 0.6) / 0.365
                hs = int(5 + t * 27)
                box(x, hs - 1, z, x, hs, z, SANDSTONE_SMOOTH)
                if rng.random() < 0.08:
                    put(x, hs + 1, z, rng.choice([WHITE_CARPET, RED_CARPET]))
                # radial walls every few bays and ring corridors at two radii hold it up
                rb = int((ang + math.pi) / (2 * math.pi) * 48)
                fr = (ang + math.pi) / (2 * math.pi) * 48 - rb
                if fr < 0.12:
                    box(x, 1, z, x, hs - 2, z, SANDSTONE_CUT)
                    if 0.7 < r < 0.95:
                        box(x, 1, z, x, 4, z, AIR)
                if abs(r - 0.78) < 0.012 or abs(r - 0.9) < 0.012:
                    box(x, 1, z, x, hs - 2, z, SANDSTONE_CUT)
                    if fr > 0.4 and fr < 0.6:
                        box(x, 1, z, x, 4, z, AIR)
                if 0.24 < fr < 0.26 and 0.7 < r < 0.9:
                    put(x, 3, z, LANTERN_HANG if get(x, 4, z) != AIR else LANTERN)
            elif r >= 0.585:
                box(x, 1, z, x, 4, z, QUARTZ_SMOOTH)
                put(x, 5, z, FENCE["dark_oak"])
            else:
                put(x, yb, z, SAND)
    # entrances on the four axes cut through the seating to the arena
    for (dx, dz, L) in ((1, 0, a), (-1, 0, a), (0, 1, b), (0, -1, b)):
        for k in range(int(L * 0.55), L + 2):
            x, z = cx + dx * k, cz + dz * k
            box(x - abs(dz) * 2, 1, z - abs(dx) * 2, x + abs(dz) * 2, 6, z + abs(dx) * 2, AIR)
        banner(cx + dx * (L + 1) + (2 if dz else 0) * 0, 9, cz + dz * (L + 1), {(1, 0): 5, (-1, 0): 4, (0, 1): 3, (0, -1): 2}[(dx, dz)])
    # the emperor's box and masts for the awning on top
    box(cx - 6, 8, cz + int(b * 0.6) + 1, cx + 6, 8, cz + int(b * 0.6) + 4, QUARTZ_SMOOTH)
    box(cx - 6, 9, cz + int(b * 0.6) + 1, cx + 6, 9, cz + int(b * 0.6) + 1, SLAB("quartz"))
    for x in range(cx - 5, cx + 6, 2):
        banner(x, 7, cz + int(b * 0.6), 2)
    for k in range(40):
        ang = k / 40 * 2 * math.pi
        x, z = cx + int(round(math.cos(ang) * a * 0.975)), cz + int(round(math.sin(ang) * b * 0.975))
        box(x, top + 1, z, x, top + 5, z, FENCE["spruce"])
    # a paved plaza around the amphitheatre
    for x in range(cx - a - 8, cx + a + 9):
        for z in range(cz - b - 8, cz + b + 9):
            if math.hypot((x - cx) / a, (z - cz) / b) > 1.0 and not OCC[x, z]:
                put(x, 0, z, SANDSTONE_SMOOTH if (x // 4 + z // 4) % 2 else SANDSTONE)
                OCC[x, z] = True
    OCC[cx - a - 2:cx + a + 3, cz - b - 2:cz + b + 3] = True
    print("colosseum")


def build_circus():
    cx, cz = px2b(230, 570)
    L, W = 250, 86
    ang = math.atan2(80, 160)
    c, s = math.cos(ang), math.sin(ang)
    R = W / 2
    for x in range(cx - 140, cx + 141):
        for z in range(cz - 110, cz + 111):
            u = (x - cx) * c + (z - cz) * s
            v = -(x - cx) * s + (z - cz) * c
            # stadium shape: a rectangle with one rounded end
            uu = max(0.0, u - (L / 2 - R))
            dist = math.hypot(uu, v) if u > L / 2 - R else abs(v)
            if u < -L / 2 or dist > R:
                continue
            if not INSIDE[x, z] and CLS[x, z] != "F":
                pass
            ground = 0
            put(x, ground, z, SAND)
            box(x, ground + 1, z, x, ground + 30, z, AIR)
            edge = R - dist
            if u < -L / 2 + 8:                       # starting gates
                box(x, 1, z, x, 9, z, QUARTZ_BRICKS)
                if int(v) % 4 in (0, 1) and u > -L / 2 + 2:
                    box(x, 1, z, x, 4, z, AIR)
                put(x, 10, z, SLAB("quartz"))
            elif edge < 14:                          # stands
                hs = int(2 + (14 - edge) * 1.2)
                box(x, 1, z, x, hs, z, SANDSTONE_SMOOTH)
                if edge < 1.2:
                    box(x, hs + 1, z, x, hs + 3, z, SANDSTONE_CUT)
                    if int(u) % 6 == 0:
                        put(x, hs + 4, z, LANTERN)
            elif edge < 15:
                box(x, 1, z, x, 2, z, QUARTZ_SMOOTH)
            elif abs(v) < 2.5 and abs(u) < L * 0.33:   # the spina
                box(x, 1, z, x, 2, z, QUARTZ_SMOOTH)
                if abs(v) < 1:
                    put(x, 2, z, WATER)
            OCC[x, z] = True
            H[x, z] = 0
    # obelisk and turning posts on the spina
    box(cx, 3, cz, cx, 22, cz, SANDSTONE_CHISELED); put(cx, 23, cz, GOLD)
    for k in (-1, 1):
        px, pz = int(cx + c * k * L * 0.33), int(cz + s * k * L * 0.33)
        for d in range(3):
            box(px + d - 1, 3, pz, px + d - 1, 6, pz, GOLD)
        statue(int(cx + c * k * L * 0.16), 2, int(cz + s * k * L * 0.16), 0)
    print("circus")


def build_baths(cx, cz, w=56, d=40):
    x0, z0, x1, z1 = cx - w // 2, cz - d // 2, cx + w // 2, cz + d // 2
    y = ground_y(x0, z0, x1, z1)
    foundation(x0, z0, x1, z1, y)
    hgt = 12
    box(x0, y, z0, x1, y + hgt, z1, WHITE_TC)
    box(x0 + 1, y + 1, z0 + 1, x1 - 1, y + hgt - 1, z1 - 1, AIR)
    box(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, P_DIORITE)
    # three halls: cold, warm, hot - each with a pool
    third = (x1 - x0) // 3
    for i in range(3):
        a0 = x0 + i * third
        if i:
            box(a0, y + 1, z0 + 1, a0, y + hgt - 1, z1 - 1, WHITE_TC); box(a0, y + 1, cz - 1, a0, y + 4, cz + 1, AIR)
        px0, px1 = a0 + 4, a0 + third - 4
        box(px0, y, z0 + 6, px1, y, z1 - 6, WATER); box(px0, y - 1, z0 + 6, px1, y - 1, z1 - 6, QUARTZ_SMOOTH)
        ring(px0 - 1, y, z0 + 5, px1 + 1, y, z1 - 5, QUARTZ_SMOOTH)
        for z in range(z0 + 3, z1 - 2, 4):
            put(a0 + 2, y + 1, z, CAMPFIRE if i == 2 else LANTERN)
            put(a0 + third - 2, y + 1, z, LANTERN)
        mx = a0 + third // 2
        for yy in range(0, 7):
            rr = math.sqrt(max(0, 49 - yy * yy))
            for x in range(mx - 8, mx + 9):
                for z in range(cz - 8, cz + 9):
                    dd = math.hypot(x - mx, z - cz)
                    if rr - 1 < dd <= rr + 0.3 and dd > 1.2:
                        put(x, y + hgt + yy, z, SANDSTONE_SMOOTH)
        box(mx - 1, y + hgt, cz - 1, mx + 1, y + hgt, cz + 1, AIR)
    # entrance, benches, windows high up
    box(cx - 1, y + 1, z1, cx + 1, y + 3, z1, AIR)
    for x in range(x0 + 2, x1 - 1, 3):
        put(x, y + hgt - 3, z0, PANE); put(x, y + hgt - 3, z1, PANE)
    for x in range(x0 + 2, x1 - 1, 2):
        put(x, y + 1, z0 + 1, STAIRS("quartz_stairs", 3)); put(x, y + 1, z1 - 1, STAIRS("quartz_stairs", 2))
    tile_roof(x0, z0, x1, z1, y + hgt + 1, "gable") if False else None
    box(x0, y + hgt, z0, x1, y + hgt, z1, SLAB("smooth_stone"))
    for i in range(3):
        mx = x0 + i * third + third // 2
        box(mx - 8, y + hgt, cz - 8, mx + 8, y + hgt, cz + 8, AIR)
        for yy in range(0, 7):
            rr = math.sqrt(max(0, 49 - yy * yy))
            for x in range(mx - 8, mx + 9):
                for z in range(cz - 8, cz + 9):
                    dd = math.hypot(x - mx, z - cz)
                    if rr - 1 < dd <= rr + 0.3 and dd > 1.2:
                        put(x, y + hgt + yy, z, SANDSTONE_SMOOTH)
    OCC[x0:x1 + 1, z0:z1 + 1] = True


def build_walls():
    t0 = time.time()
    hgt = 12
    from math import hypot
    poly = WALL
    cxp = sum(p[0] for p in poly) / len(poly)
    czp = sum(p[1] for p in poly) / len(poly)
    gate_near = lambda x, z, r: any(hypot(x - gx, z - gz) < r for gx, gz in GATES)
    for i in range(len(poly)):
        (ax, az), (bx_, bz_) = poly[i], poly[(i + 1) % len(poly)]
        L = hypot(bx_ - ax, bz_ - az)
        n = int(L * 2) + 1
        nx_, nz_ = -(bz_ - az) / L, (bx_ - ax) / L
        if (ax + bx_) / 2 + nx_ * 10 - cxp != 0 and hypot((ax + bx_) / 2 + nx_ * 10 - cxp, (az + bz_) / 2 + nz_ * 10 - czp) < hypot((ax + bx_) / 2 - cxp, (az + bz_) / 2 - czp):
            nx_, nz_ = -nx_, -nz_                    # make the normal point outward
        for k in range(n):
            t = k / max(1, n - 1)
            x, z = ax + (bx_ - ax) * t, az + (bz_ - az) * t
            if gate_near(x, z, 7):
                continue
            for o in np.linspace(-2.5, 2.5, 11):
                X, Z = int(round(x + nx_ * o)), int(round(z + nz_ * o))
                if not (0 <= X < NX and 0 <= Z < NZ):
                    continue
                g = int(H[X, Z])
                box(X, min(g, 0) - 2, Z, X, hgt, Z, SANDSTONE_CUT if o > -2 else SANDSTONE)
                put(X, hgt, Z, SLAB("smooth_sandstone") if abs(o) < 1.8 else SANDSTONE_CUT)
                if o > 2.0 and k % 4 < 2:
                    box(X, hgt + 1, Z, X, hgt + 2, Z, SANDSTONE_CUT)
                OCC[X, Z] = True
        # towers along the run
        for k in range(0, int(L), 64):
            x, z = int(ax + (bx_ - ax) * k / L), int(az + (bz_ - az) * k / L)
            if gate_near(x, z, 16):
                continue
            tower(x, z, hgt + 7)
    for (gx, gz) in GATES:
        gatehouse(gx, gz, hgt)
    print("walls %.1fs" % (time.time() - t0))


def tower(x, z, h, r=4):
    g = int(H[max(0, min(NX - 1, x)), max(0, min(NZ - 1, z))])
    box(x - r, min(g, 0) - 2, z - r, x + r, h, z + r, SANDSTONE_CUT)
    box(x - r + 1, 1, z - r + 1, x + r - 1, h - 1, z + r - 1, AIR)
    for yy in range(1, h - 1, 5):
        box(x - r + 1, yy - 1 if yy > 1 else 0, z - r + 1, x + r - 1, yy - 1 if yy > 1 else 0, z + r - 1, PLANKS["spruce"])
        put(x - r + 1, yy, z - r + 1, BARREL(1)); put(x + r - 1, yy, z + r - 1, LANTERN)
        for (a, b2) in ((x, z - r), (x, z + r), (x - r, z), (x + r, z)):
            put(a, yy + 2, b2, IRON_BARS)
    box(x, 1, z - r + 1, x, h, z - r + 1, LADDER(3))
    box(x - r, h, z - r, x + r, h, z + r, SANDSTONE_CUT)
    put(x, h, z - r + 1, AIR)
    box(x - r + 1, 0, z, x - r + 1, 1, z, AIR) if False else None
    box(x, 1, z + r, x, 2, z + r, AIR); put(x, 1, z + r, DOOR("spruce_door", 1, False)); put(x, 2, z + r, DOOR("spruce_door", 1, True))
    for a in range(x - r, x + r + 1, 2):
        put(a, h + 1, z - r, SANDSTONE_CUT); put(a, h + 1, z + r, SANDSTONE_CUT)
    for b2 in range(z - r, z + r + 1, 2):
        put(x - r, h + 1, b2, SANDSTONE_CUT); put(x + r, h + 1, b2, SANDSTONE_CUT)
    banner(x, h - 1, z + r + 1, 3)
    OCC[x - r:x + r + 1, z - r:z + r + 1] = True


def gatehouse(gx, gz, hgt):
    for (ox, oz) in ((-9, -9), (9, -9), (-9, 9), (9, 9)):
        pass
    # two towers either side of an arched passage, on whichever axis the wall runs
    for s in (-1, 1):
        tower(gx + s * 9, gz, hgt + 9, 4) if True else None
    box(gx - 5, hgt - 3, gz - 4, gx + 5, hgt + 2, gz + 4, SANDSTONE_CUT)
    box(gx - 4, 1, gz - 6, gx + 4, hgt - 4, gz + 6, AIR)
    box(gx - 3, hgt - 4, gz - 6, gx + 3, hgt - 4, gz + 6, AIR)
    put(gx, hgt + 1, gz + 5, GOLD); put(gx, hgt + 1, gz - 5, GOLD)
    banner(gx - 2, hgt - 4, gz + 5, 3); banner(gx + 2, hgt - 4, gz + 5, 3)
    for x in range(gx - 4, gx + 5):
        for z in range(gz - 12, gz + 13):
            if 0 <= x < NX and 0 <= z < NZ and CLS[x, z] != "W":
                pave(x, z, max(0, int(H[x, z])), "street")


def build_bridges():
    for (a, b2) in [((1148, 122), (1215, 80)), ((1290, 255), (1395, 255)), ((1372, 410), (1492, 410)), ((1440, 505), (1530, 505)), ((1445, 795), (1530, 795))]:
        (x0, z0), (x1, z1) = px2b(*a), px2b(*b2)
        L = math.hypot(x1 - x0, z1 - z0)
        ux, uz = (x1 - x0) / L, (z1 - z0) / L
        nx_, nz_ = -uz, ux
        deck = 5
        for k in range(int(L) + 16):
            t = k - 8
            x, z = x0 + ux * t, z0 + uz * t
            ramp = min(deck, max(0, int(min(t + 8, L + 8 - t) * 0.6)))
            for o in np.linspace(-3.5, 3.5, 15):
                X, Z = int(round(x + nx_ * o)), int(round(z + nz_ * o))
                if not (0 <= X < NX and 0 <= Z < NZ):
                    continue
                pier = (k % 14) < 3 and CLS[X, Z] == "W"
                lo = -5 if pier else ramp - 1
                arch = 0 if pier else int(3 * math.sin(math.pi * ((k % 14) - 3) / 11)) if CLS[X, Z] == "W" else 0
                box(X, max(lo, ramp - 1 - arch) if not pier else -5, Z, X, ramp, Z, STONEBRICK)
                put(X, ramp, Z, P_ANDESITE)
                if abs(o) > 3.2:
                    put(X, ramp + 1, Z, SLAB("stone_brick"))
                box(X, ramp + 1 if abs(o) <= 3.2 else ramp + 2, Z, X, ramp + 6, Z, AIR)
                OCC[X, Z] = True
            if k % 14 == 7 and 4 < t < L - 4:
                for s in (-1, 1):
                    X, Z = int(round(x + nx_ * 3.5 * s)), int(round(z + nz_ * 3.5 * s))
                    put(X, deck + 2, Z, LANTERN)


def build_aqueduct():
    pts = [px2b(270, 148), px2b(560, 42), px2b(700, -120)]
    for i in range(len(pts) - 1):
        (ax, az), (bx_, bz_) = pts[i], pts[i + 1]
        L = math.hypot(bx_ - ax, bz_ - az)
        ux, uz = (bx_ - ax) / L, (bz_ - az) / L
        nx_, nz_ = -uz, ux
        top = 30
        for k in range(int(L)):
            x, z = ax + ux * k, az + uz * k
            ph = k % 10
            for o in np.linspace(-2, 2, 9):
                X, Z = int(round(x + nx_ * o)), int(round(z + nz_ * o))
                if not (0 <= X < NX and 0 <= Z < NZ) or rp[X, Z] < 86:
                    continue
                g = int(H[X, Z])
                if g >= top - 3:
                    continue
                if ph < 3:      # piers
                    box(X, g, Z, X, top - 1, Z, STONEBRICK)
                else:           # two tiers of arches
                    mid = (top + g) // 2
                    a1 = int(4 * math.sin(math.pi * (ph - 2.5) / 7.5))
                    box(X, mid - 1 - max(0, a1) // 2 + 2, Z, X, mid + 1, Z, STONEBRICK)
                    box(X, top - 3 - max(0, a1) // 2, Z, X, top - 1, Z, STONEBRICK)
                put(X, top, Z, STONEBRICK)
                if abs(o) > 1.6:
                    put(X, top + 1, Z, STONEBRICK)
                elif abs(o) < 1.2:
                    put(X, top + 1, Z, WATER)
                OCC[X, Z] = True


def ship(x, z, horiz=True):
    """A merchant ship moored in the harbour: hull, deck, cabin, mast and sail."""
    L, W = 18, 5
    for i in range(L):
        half = W // 2 - (1 if i < 2 or i > L - 3 else 0) - (1 if i == 0 or i == L - 1 else 0)
        for j in range(-half - 1, half + 2):
            X, Z = (x + i, z + j) if horiz else (x + j, z + i)
            edge = abs(j) == half + 1
            box(X, -2, Z, X, -1, Z, PLANKS["dark_oak"])
            put(X, 0, Z, PLANKS["dark_oak"] if edge else PLANKS["spruce"])
            if edge:
                put(X, 1, Z, FENCE["dark_oak"])
            else:
                put(X, 1, Z, AIR)
    mx, mz = (x + L // 2, z) if horiz else (x, z + L // 2)
    for yy in range(1, 13):
        put(mx, yy, mz, LOG_SPRUCE)
    for yy in range(5, 12):
        for j in range(-3, 4):
            X, Z = (mx + 1, mz + j) if horiz else (mx + j, mz + 1)
            put(X, yy, Z, WOOL("white", (233, 236, 236)) if (yy + j) % 5 else WOOL("red", (161, 39, 34)))
    cx_, cz_ = (x + L - 5, z) if horiz else (x, z + L - 5)
    box(cx_ - 1, 1, cz_ - 1, cx_ + 1, 3, cz_ + 1, PLANKS["spruce"])
    box(cx_, 1, cz_, cx_, 2, cz_, AIR)
    put(cx_, 1, cz_, BARREL(1))
    chest(cx_ + (0 if horiz else 1), 1, cz_ + (1 if horiz else 0), 2, [("wheat", 32), ("bread", 8)])


def build_harbour():
    (x0, z0), (x1, z1) = px2b(1150, 560), px2b(1440, 830)
    sub = water[x0:x1, z0:z1]
    edge = np.zeros_like(sub)
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        edge |= ~np.roll(np.roll(sub, dx, 0), dz, 1)
    ex, ez = np.nonzero(sub & edge)
    for a, b2 in zip(ex + x0, ez + z0):
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            X, Z = a + dx, b2 + dz
            if not water[X, Z] and INSIDE[X, Z]:
                box(X, -5, Z, X, 0, Z, STONEBRICK); put(X, 0, Z, SMOOTH_STONE)
                if (X + Z) % 9 == 0:
                    put(X, 1, Z, FENCE["spruce"]); put(X, 2, Z, LANTERN)
    # piers and ships
    placed = 0
    for _ in range(400):
        if placed >= 9:
            break
        x, z = rng.randint(x0, x1 - 30), rng.randint(z0, z1 - 10)
        if water[x:x + 22, z - 4:z + 5].all():
            ship(x + 2, z, True); placed += 1
            water[x:x + 22, z - 4:z + 5] = False
    print("harbour ships", placed)


# ------------------------------------------------------------------------------------------------ the imperial palace
def build_palace():
    cx, cz = PAL
    y = PAL_Y
    # plateau paving and gardens
    for x in range(cx - 84, cx + 85):
        for z in range(cz - 84, cz + 85):
            if rp[x, z] < 84:
                put(x, y, z, GRASS)
    OCC[cx - 140:cx + 141, cz - 140:cz + 141] |= rp[cx - 140:cx + 141, cz - 140:cz + 141] < 140
    # ---- the great terrace over the city (south), marble paving and a crimson carpet
    tz0 = cz - 4
    for x in range(cx - 70, cx + 71):
        for z in range(tz0, cz + 84):
            if rp[x, z] < 80:
                put(x, y, z, QUARTZ_SMOOTH if (x + z) % 2 == 0 else P_DIORITE)
                if (x % 8 == 0 or z % 8 == 0):
                    put(x, y, z, SANDSTONE_SMOOTH)
            elif rp[x, z] < 82 and z > tz0:
                # balustrade along the edge: balusters under a marble rail
                put(x, y, z, QUARTZ_SMOOTH)
                put(x, y + 1, z, FENCE["birch"] if (x + z) % 2 else QUARTZ_PILLAR)
                put(x, y + 2, z, SLAB("quartz"))
    for x in range(cx - 4, cx + 5):
        for z in range(tz0 + 1, cz + 78):
            if rp[x, z] < 79:
                put(x, y + 1, z, RED_CARPET if abs(x - cx) < 4 else YELLOW_CARPET)
    # statues, braziers, cypress planters and banner poles along the carpet and balustrade
    for z in range(tz0 + 10, cz + 72, 14):
        for s in (-1, 1):
            statue(cx + s * 10, y, z, 1 if s < 0 else 3)
            brazier(cx + s * 6, y, z + 7)
            px_, pz_ = cx + s * 18, z + 3
            box(px_ - 1, y + 1, pz_ - 1, px_ + 1, y + 1, pz_ + 1, ORANGE_TC); cypress(px_, y + 1, pz_, 7)
    for k in range(0, 360, 12):
        a = math.radians(k)
        x, z = cx + int(round(math.cos(a) * 78)), cz + int(round(math.sin(a) * 78))
        if z > cz + 10:
            box(x, y + 1, z, x, y + 7, z, FENCE["dark_oak"]); put(x, y + 8, z, GOLD)
            if k % 24 == 0:
                brazier(x, y, z) if False else put(x, y + 3, z, LANTERN)
    # ---- the palace hall: podium, a grand stair with carpet, a colonnade and banners
    hx0, hx1, hz0, hz1 = cx - 36, cx + 36, cz - 62, cz - 10
    pod = 6
    box(hx0, y + 1, hz0, hx1, y + pod, hz1, QUARTZ_BRICKS)
    hy = y + pod
    box(hx0, hy, hz0, hx1, hy, hz1, QUARTZ_SMOOTH)
    for k in range(pod):
        box(cx - 12, y + 1 + k, hz1 + pod - k, cx + 12, y + 1 + k, hz1 + pod - k, STAIRS("quartz_stairs", 3))
        box(cx - 12, y + 1, hz1 + pod - k, cx + 12, y + k, hz1 + pod - k, QUARTZ_BRICKS)
        box(cx - 3, y + 2 + k, hz1 + pod - k, cx + 3, y + 2 + k, hz1 + pod - k, RED_CARPET)
    for s in (-1, 1):
        for k in range(pod + 1):
            put(cx + s * 13, y + 1 + k, hz1 + pod - k + 1, QUARTZ_SMOOTH)
        statue(cx + s * 16, y, hz1 + 4, 2)
        brazier(cx + s * 13, y + pod, hz1 + 1)
    colh = 14
    # front portico
    for x in range(hx0 + 2, hx1 - 1, 4):
        column(x, hy + 1, hz1 - 1, colh)
        if abs(x - cx) > 3:
            banner(x, hy + colh - 3, hz1, 3)
    box(hx0 + 1, hy + 1, hz1 - 6, hx1 - 1, hy + colh, hz1 - 6, QUARTZ_BRICKS)
    box(cx - 3, hy + 1, hz1 - 6, cx + 3, hy + 8, hz1 - 6, AIR)
    box(cx - 2, hy + 9, hz1 - 6, cx + 2, hy + 9, hz1 - 6, AIR)
    for x in range(hx0 + 4, hx1 - 3, 6):
        if abs(x - cx) > 6:
            box(x, hy + 4, hz1 - 6, x + 1, hy + 9, hz1 - 6, GLASS)
    # side and back walls
    box(hx0, hy + 1, hz0, hx0, hy + colh, hz1 - 6, QUARTZ_BRICKS); box(hx1, hy + 1, hz0, hx1, hy + colh, hz1 - 6, QUARTZ_BRICKS)
    box(hx0, hy + 1, hz0, hx1, hy + colh, hz0, QUARTZ_BRICKS)
    for z in range(hz0 + 4, hz1 - 7, 6):
        for xw in (hx0, hx1):
            box(xw, hy + 5, z, xw, hy + 10, z + 1, GLASS)
    # interior: the throne hall down the middle between two rows of columns, rooms in the aisles
    tx0, tx1 = cx - 12, cx + 12
    for z in range(hz0 + 3, hz1 - 7, 4):
        column(tx0, hy + 1, z, colh - 1); column(tx1, hy + 1, z, colh - 1)
        put((tx0 + tx1) // 2 - 6, hy + colh - 2, z, LANTERN_HANG); put((tx0 + tx1) // 2 + 6, hy + colh - 2, z, LANTERN_HANG)
    for z in range(hz0 + 2, hz1 - 6):
        box(cx - 2, hy, z, cx + 2, hy, z, RED_WOOL)
        put(cx - 3, hy, z, GOLD) if z % 2 == 0 else None
        put(cx + 3, hy, z, GOLD) if z % 2 == 0 else None
    # the dais and throne at the north end
    box(cx - 6, hy + 1, hz0 + 1, cx + 6, hy + 1, hz0 + 6, QUARTZ_SMOOTH)
    box(cx - 4, hy + 2, hz0 + 1, cx + 4, hy + 2, hz0 + 4, QUARTZ_SMOOTH)
    put(cx, hy + 3, hz0 + 2, STAIRS("quartz_stairs", 3))
    box(cx - 1, hy + 3, hz0 + 1, cx + 1, hy + 5, hz0 + 1, GOLD)
    put(cx - 1, hy + 3, hz0 + 2, GOLD); put(cx + 1, hy + 3, hz0 + 2, GOLD)
    box(cx - 2, hy + 6, hz0 + 1, cx + 2, hy + 6, hz0 + 1, GOLD)
    for s in (-1, 1):
        banner(cx + s * 4, hy + 10, hz0 + 1, 3)
        brazier(cx + s * 5, hy + 1, hz0 + 5)
        statue(cx + s * 9, hy, hz0 + 3, 2, GOLD)
    for k in range(-3, 4):
        put(cx + k, hy + 2, hz0 + 5, STAIRS("quartz_stairs", 3)) if False else None
    # aisle rooms: council chamber, treasury, library, Hall of Kings, audience rooms
    aisles = [("council", hx0 + 1, tx0 - 1), ("treasury", tx1 + 1, hx1 - 1)]
    room_kinds = {"council": ["council", "library", "audience", "office"], "treasury": ["treasury", "kings", "office", "library"]}
    for name, ax0, ax1 in aisles:
        zs_ = list(range(hz0 + 1, hz1 - 6, 12))
        for i, rz in enumerate(zs_):
            rz1 = min(rz + 11, hz1 - 7)
            box(ax0, hy + 1, rz1, ax1, hy + 6, rz1, QUARTZ_BRICKS)
            box(ax0, hy + 7, rz, ax1, hy + 7, rz1, PLANKS["dark_oak"])
            dx_ = ax1 if name == "council" else ax0
            box(dx_ + (1 if name == "council" else -1), hy + 1, (rz + rz1) // 2, dx_ + (1 if name == "council" else -1), hy + 3, (rz + rz1) // 2, AIR)
            box(tx0 if name == "council" else tx1, hy + 1, (rz + rz1) // 2 - 1, tx0 if name == "council" else tx1, hy + 3, (rz + rz1) // 2 + 1, AIR)
            palace_room(room_kinds[name][i % 4], ax0, rz, ax1, rz1 - 1, hy)
        # upper floor gallery in the aisles: private quarters
        for rz in range(hz0 + 1, hz1 - 6, 8):
            rz1 = min(rz + 7, hz1 - 7)
            box(ax0, hy + 8, rz1, ax1, hy + colh - 1, rz1, QUARTZ_BRICKS)
            furnish(ax0, rz, ax1, rz1 - 1, hy + 7, rng.choice(["bedroom", "living", "bedroom"]), set())
        box(ax0 + 1, hy + 1, hz1 - 8, ax0 + 1, hy + 8, hz1 - 8, LADDER(2))
    box(hx0, hy + colh + 1, hz0, hx1, hy + colh + 1, hz1, QUARTZ_SMOOTH)
    ring(hx0, hy + colh + 2, hz0, hx1, hy + colh + 2, hz1, RED_TC)
    for x in range(hx0, hx1 + 1, 2):
        put(x, hy + colh + 2, hz1, GOLD)
    k = 0
    while hx0 + k <= hx1 - k:
        yy = hy + colh + 3 + k // 2
        sl = SLAB("brick", top=(k % 2 == 1))
        box(hx0 + k, yy, hz0, hx0 + k, yy, hz1, sl); box(hx1 - k, yy, hz0, hx1 - k, yy, hz1, sl)
        box(hx0 + k + 1, hy + colh + 3, hz1, hx1 - k - 1, yy, hz1, QUARTZ_SMOOTH)
        k += 1
    put(cx, hy + colh + 4 + 9, hz1, GOLD)
    # ---- residential wings with a peristyle garden, and the domed hall
    for (wx0, wx1) in ((cx - 78, cx - 42), (cx + 42, cx + 78)):
        house(wx0, cz - 60, wx1, cz - 34, 3, {"wall": QUARTZ_SMOOTH, "trim": SANDSTONE_SMOOTH, "wood": "dark_oak"}, roof="hip", door_side=2, rich=True)
        domus(wx0, cz - 30, wx1, cz - 8)
    dcx, dcz = px2b(528, 130)
    if rp[dcx, dcz] < 82:
        rotunda(dcx, dcz, 11, 11)
    for k in range(60):
        x, z = rng.randint(cx - 80, cx + 80), rng.randint(cz - 80, cz - 64)
        if rp[x, z] < 82 and get(x, y + 1, z) == AIR:
            cypress(x, y, z, rng.randint(7, 11))
    # ---- the grand stair down the east side of the hill to the city
    sx = cx + 84
    for k in range(0, PAL_Y + 1):
        x = sx + k
        yy = PAL_Y - k
        box(x, yy - 12, cz - 4, x, yy - 1, cz + 4, STONEBRICK)
        box(x, yy, cz - 4, x, yy, cz + 4, STAIRS("stone_brick_stairs", 1))
        box(x, yy + 1, cz - 3, x, yy + 6, cz + 3, AIR)
        put(x, yy + 1, cz - 4, SLAB("stone_brick")); put(x, yy + 1, cz + 4, SLAB("stone_brick"))
        if k % 6 == 0:
            put(x, yy + 2, cz - 4, LANTERN); put(x, yy + 2, cz + 4, LANTERN)
    box(cx + 70, y + 1, cz - 3, sx, y + 4, cz + 3, AIR)
    box(cx + 70, y, cz - 3, sx, y, cz + 3, P_DIORITE)
    print("palace")
    return (cx, y + 1, cz + 60)


def palace_room(kind, x0, z0, x1, z1, y):
    f = y + 1
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if kind == "council":
        # a long table of state with chairs on both sides
        for x in range(x0 + 2, x1 - 1):
            put(x, f, cz, FENCE["dark_oak"]); put(x, f + 1, cz, RED_CARPET)
            put(x, f, cz - 1, STAIRS("dark_oak_stairs", 3)); put(x, f, cz + 1, STAIRS("dark_oak_stairs", 2))
        put(x0 + 1, f, cz, STAIRS("quartz_stairs", 1)); banner(x0, f + 3, cz, 5) if False else None
        for x in range(x0 + 1, x1, 3):
            put(x, f + 4, z0, LANTERN_HANG)
    elif kind == "treasury":
        for x in range(x0 + 1, x1):
            put(x, f, z0, GOLD if x % 2 else BARREL(1)); chest(x, f, z1, 2, [("gold_ingot", 16), ("gold_nugget", 32), ("emerald", 6)]) if x % 3 == 0 else None
        put(cx, f, cz, GOLD); put(cx, f + 1, cz, GOLD)
    elif kind == "library":
        for x in range(x0 + 1, x1):
            box(x, f, z0, x, f + 2, z0, BOOKSHELF); box(x, f, z1, x, f + 2, z1, BOOKSHELF)
        put(cx, f, cz, LECTERN(0)); put(cx - 2, f, cz, CARTO)
    elif kind == "kings":
        # the Hall of Kings: a ring of thrones for the client kings
        for x in range(x0 + 1, x1, 2):
            put(x, f, z0, STAIRS("quartz_stairs", 3)); put(x, f, z1, STAIRS("quartz_stairs", 2))
            put(x, f + 1, z0 - 0, AIR)
        box(cx - 1, f - 1, cz - 1, cx + 1, f - 1, cz + 1, GOLD)
        put(cx, f, cz, CAMPFIRE)
    elif kind == "audience":
        put(cx, f, z0 + 1, STAIRS("quartz_stairs", 3)); put(cx, f + 1, z0, GOLD)
        for z in range(z0 + 2, z1):
            put(cx, y, z, RED_WOOL)
        put(x0 + 1, f, z1 - 1, BARREL(1)); pot(x0 + 1, f + 1, z1 - 1)
    else:
        furnish(x0, z0, x1, z1, y, "living", set())
    put(cx, y + 5, cz, LANTERN_HANG)


# ------------------------------------------------------------------------------------------------ city fill
def build_lots():
    """Pack the city blocks densely: only the map's wide streets stay open; narrow gaps become 1-block alleys."""
    t0 = time.time()
    from scipy import ndimage as nd
    Rm = INSIDE & ((CLS == "R") | (CLS == "T"))
    Sm = INSIDE & ((CLS == "S") | (CLS == "P"))
    street_core = Sm & (nd.distance_transform_edt(~Rm) >= 4)
    # the avenues: from the heart of the city to every gate, and a ring road just inside the walls
    C = px2b(760, 455)
    for (gx, gz) in GATES:
        L = math.hypot(gx - C[0], gz - C[1])
        for k in range(int(L)):
            x, z = int(C[0] + (gx - C[0]) * k / L), int(C[1] + (gz - C[1]) * k / L)
            AVENUE[x - 3:x + 4, z - 3:z + 4] = True
    dw = nd.distance_transform_edt(INSIDE)
    AVENUE[:] |= INSIDE & (dw > 5) & (dw < 11)
    AVENUE[:] &= ~OCC & ~water
    street_core |= AVENUE
    buildable = INSIDE & ~water & ~OCC & ~street_core & (rp > 142)
    count = {"insula": 0, "house": 0, "domus": 0, "shophouse": 0}
    for (lo, hi, step, minR) in ((12, 21, 3, 0.5), (8, 14, 2, 0.4), (7, 10, 2, 0.3)):
        cand = np.argwhere(buildable[::step, ::step]) * step
        for i in rng.sample(range(len(cand)), len(cand)):
            x, z = cand[i]
            if not buildable[x, z]:
                continue
            for _ in range(5):
                w, d = rng.randint(lo, hi), rng.randint(lo, hi)
                x0, z0 = x - rng.randint(0, w - 1), z - rng.randint(0, d - 1)
                x1, z1 = x0 + w - 1, z0 + d - 1
                if x0 < 2 or z0 < 2 or x1 >= NX - 2 or z1 >= NZ - 2:
                    continue
                if buildable[x0:x1 + 1, z0:z1 + 1].all() and Rm[x0:x1 + 1, z0:z1 + 1].mean() >= minR:
                    break
            else:
                continue
            buildable[x0 - 1:x1 + 2, z0 - 1:z1 + 2] = False
            area = w * d
            r = rng.random()
            if w >= 15 and d >= 15 and r < 0.25:
                domus(x0, z0, x1, z1); count["domus"] += 1
            elif area >= 140 and r < 0.8:
                house(x0, z0, x1, z1, rng.choice([3, 3, 4, 4, 5]), shops=True); count["insula"] += 1
            elif r < 0.7:
                house(x0, z0, x1, z1, rng.choice([2, 2, 3]), shops=True); count["shophouse"] += 1
            else:
                house(x0, z0, x1, z1, rng.choice([1, 2, 2]), shops=False); count["house"] += 1
    print("lots", count, "%.1fs" % (time.time() - t0))


def build_country():
    t0 = time.time()
    # fields: irregular parcels (nearest of scattered seeds), each with its own crop, hedged and pathed at the edges
    from scipy.spatial import cKDTree
    seeds = np.c_[np.random.RandomState(3).uniform(0, NX, 900), np.random.RandomState(4).uniform(0, NZ, 900)]
    kinds = np.random.RandomState(5).randint(0, 7, 900)
    dirs = np.random.RandomState(6).randint(0, 2, 900)
    fx, fz = np.nonzero(~INSIDE & (CLS == "F") & ~water & ~OCC)
    _, fid = cKDTree(seeds).query(np.c_[fx, fz])
    lab = np.full((NX, NZ), -1, np.int32)
    lab[fx, fz] = fid
    for x, z, f_ in zip(fx, fz, fid):
        y = int(H[x, z])
        edge = (lab[min(x + 1, NX - 1), z] != f_) or (lab[x, min(z + 1, NZ - 1)] != f_)
        if edge:
            if (x + z) % 3:
                put(x, y, z, PATH)
            else:
                put(x, y + 1, z, LEAVES_OAK)
            continue
        kind = kinds[f_]
        row = z if dirs[f_] else x
        if kind <= 2:
            if row % 9 == 4:
                put(x, y, z, WATER)
            else:
                put(x, y, z, FARMLAND); put(x, y + 1, z, (WHEAT, CARROTS, POTATOES)[kind])
        elif kind == 3:                     # vineyard rows
            if row % 3 == 0:
                put(x, y + 1, z, FENCE["oak"]); put(x, y + 2, z, LEAVES_OAK)
            else:
                put(x, y, z, COARSE)
        elif kind == 4:                     # olive grove
            if (x % 7 == 3) and (z % 7 == 3):
                olive(x, y, z)
        else:                               # meadow
            r = rng.random()
            if r < 0.07:
                put(x, y + 1, z, TALLGRASS)
            elif r < 0.085:
                put(x, y + 1, z, rng.choice([POPPY, DANDELION, ALLIUM]))
    # villas and farmsteads at the map's villa spots
    vx, vz = np.nonzero(~INSIDE & (CLS == "V") & ~OCC)
    vc = np.argwhere(((~INSIDE & (CLS == "V") & ~OCC))[::14, ::14]) * 14
    for x, z in vc:
        if OCC[x - 8:x + 9, z - 8:z + 9].any():
            continue
        w, d = rng.randint(14, 20), rng.randint(14, 20)
        if rng.random() < 0.6:
            domus(x - w // 2, z - d // 2, x + w // 2, z + d // 2)
        else:
            house(x - 5, z - 5, x + 5, z + 5, 2, roof="hip")
            box(x + 7, int(H[x + 7, z]) + 1, z - 4, x + 7, int(H[x + 7, z]) + 1, z + 4, FENCE["oak"])
    # roads out of the gates toward the map's edge
    for (gx, gz) in GATES:
        dx, dz = gx - (NX // 2), gz - (NZ // 2)
        L = math.hypot(dx, dz)
        dx, dz = dx / L, dz / L
        x, z = float(gx), float(gz)
        for k in range(700):
            x += dx; z += dz
            dx += rng.uniform(-0.02, 0.02); dz += rng.uniform(-0.02, 0.02)
            n = math.hypot(dx, dz); dx /= n; dz /= n
            X, Z = int(x), int(z)
            if not (4 <= X < NX - 4 and 4 <= Z < NZ - 4) or water[X, Z]:
                break
            for a in range(-2, 3):
                for b2 in range(-2, 3):
                    if not OCC[X + a, Z + b2]:
                        pave(X + a, Z + b2, int(H[X + a, Z + b2]), "road")
                        box(X + a, int(H[X + a, Z + b2]) + 1, Z + b2, X + a, int(H[X + a, Z + b2]) + 2, Z + b2, AIR)
            if k % 40 == 20:
                cypress(X + 4, int(H[X + 4, Z]), Z, 8)
    print("country %.1fs" % (time.time() - t0))


def build_trees():
    tx, tz = np.nonzero((CLS == "T") & ~OCC & ~water)
    sel = rng.sample(range(len(tx)), len(tx) // 22)
    for i in sel:
        tree(tx[i], tz[i])
    # the palace hill terraces: rows of cypresses
    hx, hz = np.nonzero((rp > 86) & (rp < 140))
    sel = rng.sample(range(len(hx)), len(hx) // 40)
    for i in sel:
        x, z = hx[i], hz[i]
        if not OCC[x, z] or True:
            if get(x, int(H[x, z]) + 1, z) == AIR and V[x, int(H[x, z]) - Y0, z] == GRASS:
                cypress(x, int(H[x, z]), z, rng.randint(7, 10))


# ------------------------------------------------------------------------------------------------ export
def write_world(out_dir, spawn, name="Imperium - The Capital"):
    import leveldb
    t0 = time.time()
    os.makedirs(os.path.join(out_dir, "db"), exist_ok=True)
    db = leveldb.LevelDB(os.path.join(out_dir, "db"), create_if_missing=True)
    stone = np.full((16, 16, 16), STONE, dtype=np.uint16)
    bottom = stone.copy(); bottom[:, 0, :] = BEDROCK
    enc_stone = BR.encode_subchunk(stone, 0)
    be_by_chunk = {}
    for (x, y, z, data) in BE:
        be_by_chunk.setdefault((x >> 4, z >> 4), []).append(BR.nbt(data))
    n = 0
    for cx in range(NX // 16):
        batch = {}
        for cz in range(NZ // 16):
            col = V[cx * 16:cx * 16 + 16, :, cz * 16:cz * 16 + 16]
            batch[BR.chunk_key(cx, cz, 0x2C)] = bytes([40])
            for sy in (-4, -3, -2):
                sub = bottom if sy == -4 else stone
                batch[BR.chunk_key(cx, cz, 0x2F, sy)] = BR.encode_subchunk(sub, sy) if sy == -4 else enc_stone[:2] + bytes([sy & 0xFF]) + enc_stone[3:]
            for sy in range(-1, (Y0 + NY) // 16):
                y0 = sy * 16 - Y0
                sub = col[:, y0:y0 + 16, :]
                if not sub.any():
                    continue
                batch[BR.chunk_key(cx, cz, 0x2F, sy)] = BR.encode_subchunk(sub, sy)
            # heightmap: first air above the highest block, relative to y = -64
            nz_ = (col != AIR)
            top = np.where(nz_.any(axis=1), NY - 1 - np.argmax(nz_[:, ::-1, :], axis=1), 0) + Y0 + 1 + 64
            batch[BR.chunk_key(cx, cz, 0x2B)] = BR.data3d(top.T)
            batch[BR.chunk_key(cx, cz, 0x36)] = (2).to_bytes(4, "little")
            if (cx, cz) in be_by_chunk:
                batch[BR.chunk_key(cx, cz, 0x31)] = b"".join(be_by_chunk[(cx, cz)])
            n += 1
        db.putBatch(batch)
    db.compact()
    db.close()
    open(os.path.join(out_dir, "level.dat"), "wb").write(BR.level_dat(name, spawn, BR.flat_layers(0)))
    open(os.path.join(out_dir, "levelname.txt"), "w").write(name)
    print("wrote %d chunks, %d block entities, %.1fs" % (n, len(BE), time.time() - t0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "minecraft_out"))
    args = ap.parse_args()
    T0 = time.time()
    build_terrain()
    spawn = build_palace()
    build_capitol()
    build_forum()
    build_colosseum()
    build_circus()
    for (px, py) in ((1300, 600), (370, 640), (905, 135)):
        x, z = px2b(px, py)
        if not OCC[x - 28:x + 29, z - 20:z + 21].any():
            build_baths(x, z)
    for (px, py) in ((265, 448),):
        x, z = px2b(px, py)
        rotunda(x, z, 12, 12)
    for (px, py, w, d) in ((1010, 778, 23, 33), (610, 360, 21, 31), (930, 590, 21, 31), (440, 445, 21, 31)):
        x, z = px2b(px, py)
        if not OCC[x - w // 2 - 2:x + w // 2 + 3, z - d // 2 - 4:z + d // 2 + 5].any():
            temple(x - w // 2, z - d // 2, w, d, 2, 9)
    build_walls()
    build_bridges()
    build_aqueduct()
    build_harbour()
    build_lots()
    build_streets()
    build_trees()
    build_country()
    os.makedirs(args.out, exist_ok=True)
    import preview
    preview.set_palette(BL.COLORS)
    preview.topdown(V, Y0, 0.5).save(os.path.join(args.out, "map_small.png"))
    preview.topdown(V, Y0, 1).save(os.path.join(args.out, "map_full.png"))
    np.save(os.path.join(args.out, "V.npy"), V)
    np.savez_compressed(os.path.join(args.out, "preview_cache.npz"), H=H, colors=np.array(BL.COLORS, dtype=np.uint8))
    json.dump(BL.NAMES, open(os.path.join(args.out, "palette.json"), "w"))
    world_dir = os.path.join(args.out, "world")
    import shutil
    shutil.rmtree(world_dir, ignore_errors=True)
    write_world(world_dir, spawn)
    BR.package(world_dir, os.path.join(args.out, "Imperium_Capital.mcworld"))
    global V_SAVED
    print("total %.0fs" % (time.time() - T0))
    return V


if __name__ == "__main__":
    main()
