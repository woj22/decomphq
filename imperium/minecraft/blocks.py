"""Block palette for the Bedrock city.

Blocks are written with Bedrock 1.18.10 names and states and tagged with that block version, so current
Bedrock clients upgrade them on load (the game ships upgrade schemas for every older version).
Each block gets a small integer id used in the world array; 0 is air.
"""
VERSION = 17959425        # 1.18.10.1 -> (1 << 24) | (18 << 16) | (10 << 8) | 1

_ids = {}
NAMES = []     # id -> (name, states)
COLORS = []    # id -> preview rgb


def B(name, states=None, rgb=(200, 0, 200)):
    """Register (or look up) a block and return its id."""
    states = states or {}
    key = (name, tuple(sorted(states.items())))
    if key not in _ids:
        _ids[key] = len(NAMES)
        NAMES.append((name if ":" in name else "minecraft:" + name, dict(states)))
        COLORS.append(rgb)
    return _ids[key]


AIR = B("air", {}, (0, 0, 0))
BEDROCK = B("bedrock", {"infiniburn_bit": 0}, (40, 40, 40))
STONE = B("stone", {"stone_type": "stone"}, (125, 125, 125))
DIRT = B("dirt", {"dirt_type": "normal"}, (134, 96, 67))
GRASS = B("grass", {}, (110, 150, 60))
COARSE = B("dirt", {"dirt_type": "coarse"}, (120, 86, 60))
PATH = B("grass_path", {}, (150, 125, 70))
SAND = B("sand", {"sand_type": "normal"}, (219, 207, 163))
GRAVEL = B("gravel", {}, (136, 126, 126))
WATER = B("water", {"liquid_depth": 0}, (60, 100, 190))
FARMLAND = B("farmland", {"moisturized_amount": 7}, (110, 75, 45))

ANDESITE = B("stone", {"stone_type": "andesite"}, (136, 136, 137))
P_ANDESITE = B("stone", {"stone_type": "andesite_smooth"}, (132, 134, 133))
DIORITE = B("stone", {"stone_type": "diorite"}, (188, 188, 188))
P_DIORITE = B("stone", {"stone_type": "diorite_smooth"}, (192, 193, 194))
P_GRANITE = B("stone", {"stone_type": "granite_smooth"}, (154, 106, 89))
STONEBRICK = B("stonebrick", {"stone_brick_type": "default"}, (122, 121, 122))
MOSSY_BRICK = B("stonebrick", {"stone_brick_type": "mossy"}, (115, 121, 105))
CHISELED_SB = B("stonebrick", {"stone_brick_type": "chiseled"}, (119, 119, 119))
SMOOTH_STONE = B("smooth_stone", {}, (158, 158, 158))
COBBLE = B("cobblestone", {}, (128, 127, 127))

QUARTZ = B("quartz_block", {"chisel_type": "default", "pillar_axis": "y"}, (236, 230, 223))
QUARTZ_SMOOTH = B("quartz_block", {"chisel_type": "smooth", "pillar_axis": "y"}, (236, 230, 223))
QUARTZ_PILLAR = B("quartz_block", {"chisel_type": "lines", "pillar_axis": "y"}, (235, 229, 221))
QUARTZ_PILLAR_X = B("quartz_block", {"chisel_type": "lines", "pillar_axis": "x"}, (235, 229, 221))
QUARTZ_PILLAR_Z = B("quartz_block", {"chisel_type": "lines", "pillar_axis": "z"}, (235, 229, 221))
QUARTZ_CHISELED = B("quartz_block", {"chisel_type": "chiseled", "pillar_axis": "y"}, (231, 226, 218))
QUARTZ_BRICKS = B("quartz_bricks", {}, (234, 229, 221))
SANDSTONE = B("sandstone", {"sand_stone_type": "default"}, (216, 203, 155))
SANDSTONE_CUT = B("sandstone", {"sand_stone_type": "cut"}, (217, 206, 159))
SANDSTONE_SMOOTH = B("sandstone", {"sand_stone_type": "smooth"}, (223, 214, 170))
SANDSTONE_CHISELED = B("sandstone", {"sand_stone_type": "heiroglyphs"}, (216, 203, 155))
RED_SANDSTONE = B("red_sandstone", {"sand_stone_type": "default"}, (186, 99, 29))
BRICKS = B("brick_block", {}, (150, 97, 83))
TERRACOTTA = B("hardened_clay", {}, (152, 94, 67))
GOLD = B("gold_block", {}, (246, 208, 61))


def TC(color, rgb):
    return B("stained_hardened_clay", {"color": color}, rgb)


def WOOL(color, rgb):
    return B("wool", {"color": color}, rgb)


def CARPET(color, rgb):
    return B("carpet", {"color": color}, rgb)


def CONCRETE(color, rgb):
    return B("concrete", {"color": color}, rgb)


WHITE_TC = TC("white", (209, 178, 161))
ORANGE_TC = TC("orange", (161, 83, 37))
YELLOW_TC = TC("yellow", (186, 133, 35))
RED_TC = TC("red", (143, 61, 46))
LIGHT_GRAY_TC = TC("silver", (135, 106, 97))
PINK_TC = TC("pink", (161, 78, 78))
BROWN_TC = TC("brown", (77, 51, 35))
WHITE_CONCRETE = CONCRETE("white", (207, 213, 214))
RED_WOOL = WOOL("red", (161, 39, 34))
RED_CARPET = CARPET("red", (161, 39, 34))
YELLOW_CARPET = CARPET("yellow", (249, 198, 39))
PURPLE_CARPET = CARPET("purple", (121, 42, 172))
WHITE_CARPET = CARPET("white", (233, 236, 236))
GREEN_CARPET = CARPET("green", (84, 109, 27))
BLUE_CARPET = CARPET("blue", (53, 57, 157))
BROWN_CARPET = CARPET("brown", (114, 71, 40))
AWNING_COLORS = [WOOL("red", (161, 39, 34)), WOOL("white", (233, 236, 236)), WOOL("yellow", (249, 198, 39)), WOOL("green", (84, 109, 27)),
                 WOOL("orange", (240, 118, 19)), WOOL("brown", (114, 71, 40))]

PLANKS = {w: B("planks", {"wood_type": w}, c) for w, c in (("oak", (162, 130, 78)), ("spruce", (115, 85, 49)), ("birch", (192, 175, 121)),
                                                          ("dark_oak", (67, 43, 20)), ("acacia", (168, 90, 50)), ("jungle", (160, 115, 81)))}
LOG_OAK = B("log", {"old_log_type": "oak", "pillar_axis": "y"}, (109, 85, 50))
LOG_SPRUCE = B("log", {"old_log_type": "spruce", "pillar_axis": "y"}, (58, 37, 16))
LOG_DARK = B("log2", {"new_log_type": "dark_oak", "pillar_axis": "y"}, (60, 46, 26))
LEAVES_OAK = B("leaves", {"old_leaf_type": "oak", "persistent_bit": 1, "update_bit": 0}, (60, 110, 30))
LEAVES_SPRUCE = B("leaves", {"old_leaf_type": "spruce", "persistent_bit": 1, "update_bit": 0}, (45, 80, 45))
LEAVES_DARK = B("leaves2", {"new_leaf_type": "dark_oak", "persistent_bit": 1, "update_bit": 0}, (55, 95, 30))
LEAVES_ACACIA = B("leaves2", {"new_leaf_type": "acacia", "persistent_bit": 1, "update_bit": 0}, (80, 120, 35))

GLASS = B("glass", {}, (200, 220, 230))
PANE = B("glass_pane", {}, (190, 210, 220))
FENCE = {w: B("fence", {"wood_type": w}, PLANKS_c) for w, PLANKS_c in (("oak", (162, 130, 78)), ("spruce", (115, 85, 49)), ("dark_oak", (67, 43, 20)), ("birch", (192, 175, 121)))}
IRON_BARS = B("iron_bars", {}, (110, 110, 110))
BOOKSHELF = B("bookshelf", {}, (115, 90, 55))
CRAFTING = B("crafting_table", {}, (120, 75, 45))
CAULDRON = B("cauldron", {"cauldron_liquid": "water", "fill_level": 6}, (60, 60, 60))
HAY = B("hay_block", {"deprecated": 0, "pillar_axis": "y"}, (166, 136, 38))
FLOWER_POT = B("flower_pot", {"update_bit": 0}, (120, 65, 50))
POPPY = B("red_flower", {"flower_type": "poppy"}, (200, 30, 30))
ALLIUM = B("red_flower", {"flower_type": "allium"}, (190, 120, 220))
DANDELION = B("yellow_flower", {}, (240, 220, 40))
TALLGRASS = B("tallgrass", {"tall_grass_type": "tall"}, (100, 140, 50))
WHEAT = B("wheat", {"growth": 7}, (200, 180, 80))
CARROTS = B("carrots", {"growth": 7}, (80, 150, 40))
POTATOES = B("potatoes", {"growth": 7}, (90, 140, 40))
LANTERN = B("lantern", {"hanging": 0}, (240, 180, 80))
LANTERN_HANG = B("lantern", {"hanging": 1}, (240, 180, 80))
SEA_LANTERN = B("seaLantern", {}, (200, 220, 210))
GLOWSTONE = B("glowstone", {}, (250, 210, 130))
TORCH = B("torch", {"torch_facing_direction": "top"}, (255, 210, 90))
CAMPFIRE = B("campfire", {"direction": 0, "extinguished": 0}, (255, 140, 40))
BELL = B("bell", {"attachment": "standing", "direction": 0, "toggle_bit": 0}, (240, 200, 60))
LOOM = B("loom", {"direction": 0}, (140, 110, 80))
SMITHING = B("smithing_table", {}, (60, 50, 50))
CARTO = B("cartography_table", {}, (100, 80, 60))
FLETCH = B("fletching_table", {}, (170, 150, 100))
ANVIL = B("anvil", {"damage": "undamaged", "direction": 0}, (70, 70, 70))
COMPOSTER = B("composter", {"composter_fill_level": 0}, (110, 80, 40))
SPONGE_DUMMY = None


def FURNACE(f):
    return B("furnace", {"facing_direction": f}, (110, 110, 110))


def BARREL(f=1):
    return B("barrel", {"facing_direction": f, "open_bit": 0}, (130, 95, 55))


def CHEST(f):
    return B("chest", {"facing_direction": f}, (160, 115, 40))


def LECTERN(d):
    return B("lectern", {"direction": d, "powered_bit": 0}, (170, 130, 80))


def LADDER(f):
    return B("ladder", {"facing_direction": f}, (150, 120, 70))


def SLAB(kind, top=False):
    """kind: smooth_stone, sandstone, wood, cobblestone, brick, stone_brick, quartz (stone_slab);
    smooth_quartz, mossy_stone_brick, stone, cut_sandstone (stone_slab4); smooth_sandstone, red_sandstone (stone_slab2);
    andesite, polished_andesite, diorite, polished_diorite, granite, polished_granite (stone_slab3)."""
    s1 = ("smooth_stone", "sandstone", "wood", "cobblestone", "brick", "stone_brick", "quartz", "nether_brick")
    s2 = ("red_sandstone", "purpur", "prismarine_rough", "prismarine_dark", "prismarine_brick", "mossy_cobblestone", "smooth_sandstone", "red_nether_brick")
    s3 = ("end_stone_brick", "smooth_red_sandstone", "polished_andesite", "andesite", "diorite", "polished_diorite", "granite", "polished_granite")
    s4 = ("mossy_stone_brick", "smooth_quartz", "stone", "cut_sandstone", "cut_red_sandstone")
    rgb = {"brick": (150, 90, 75), "quartz": (236, 230, 223), "smooth_quartz": (236, 230, 223), "stone_brick": (122, 121, 122),
           "smooth_sandstone": (223, 214, 170), "sandstone": (216, 203, 155), "red_sandstone": (186, 99, 29), "granite": (154, 106, 89),
           "polished_granite": (154, 106, 89), "smooth_stone": (158, 158, 158), "polished_andesite": (132, 134, 133)}.get(kind, (150, 150, 150))
    if kind in s1:
        return B("stone_slab", {"stone_slab_type": kind, "top_slot_bit": int(top)}, rgb)
    if kind in s2:
        return B("stone_slab2", {"stone_slab_type_2": kind, "top_slot_bit": int(top)}, rgb)
    if kind in s3:
        return B("stone_slab3", {"stone_slab_type_3": kind, "top_slot_bit": int(top)}, rgb)
    if kind in s4:
        return B("stone_slab4", {"stone_slab_type_4": kind, "top_slot_bit": int(top)}, rgb)
    raise KeyError(kind)


def WSLAB(wood, top=False):
    return B("wooden_slab", {"wood_type": wood, "top_slot_bit": int(top)}, (130, 100, 60))


# stairs: weirdo_direction 0 = ascending toward +x (east), 1 = -x (west), 2 = +z (south), 3 = -z (north)
def STAIRS(kind, d, upside=False):
    rgb = {"quartz_stairs": (236, 230, 223), "brick_stairs": (150, 90, 75), "sandstone_stairs": (216, 203, 155), "spruce_stairs": (115, 85, 49),
           "dark_oak_stairs": (67, 43, 20), "oak_stairs": (162, 130, 78), "stone_brick_stairs": (122, 121, 122), "smooth_quartz_stairs": (236, 230, 223),
           "granite_stairs": (154, 106, 89), "smooth_sandstone_stairs": (223, 214, 170)}.get(kind, (150, 150, 150))
    return B(kind, {"upside_down_bit": int(upside), "weirdo_direction": d}, rgb)


# doors: direction 0 = facing east(+x), 1 = south(+z), 2 = west(-x), 3 = north(-z)
def DOOR(kind, d, upper):
    return B(kind, {"direction": d, "door_hinge_bit": 0, "open_bit": 0, "upper_block_bit": int(upper)}, (120, 90, 55))


def TRAPDOOR(kind, d, open_=1, upside=0):
    return B(kind, {"direction": d, "open_bit": open_, "upside_down_bit": upside}, (120, 90, 55))


# beds: direction 0 = south(+z), 1 = west(-x), 2 = north(-z), 3 = east(+x) (foot -> head)
def BED(d, head):
    return B("bed", {"direction": d, "head_piece_bit": int(head), "occupied_bit": 0}, (170, 40, 40))


def WALL_BANNER(f):
    return B("wall_banner", {"facing_direction": f}, (170, 30, 30))


def STANDING_BANNER(rot):
    return B("standing_banner", {"ground_sign_direction": rot}, (170, 30, 30))


def PRESSURE_PLATE():
    return B("wooden_pressure_plate", {"redstone_signal": 0}, (160, 130, 80))


def is_solid_like(bid):
    n = NAMES[bid][0]
    return bid != AIR and not any(k in n for k in ("water", "carpet", "flower", "grass_path", "torch", "lantern", "banner", "door", "ladder", "pane", "fence", "bars", "tallgrass", "wheat", "carrots", "potatoes", "slab", "stairs", "pressure"))
