"""Bedrock world writer: little-endian NBT, sub-chunk palettes, chunk records, level.dat and .mcworld packaging.

Chunk records written per column (key = x, z as int32 LE + tag [+ sub-chunk index]):
  0x2C Version (byte), 0x2F SubChunkPrefix v9 (persistent NBT palette), 0x2B Data3D (heightmap + biomes),
  0x31 BlockEntity (concatenated NBT), 0x36 FinalizedState (int32 = 2).
"""
import io
import json
import os
import struct
import time
import zipfile

import numpy as np

from blocks import NAMES, VERSION

# ------------------------------------------------------------------------------------------------ NBT (little endian)
TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE, TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND = range(11)


class Byte(int):
    pass


class Short(int):
    pass


class Long(int):
    pass


class Float(float):
    pass


class List(list):
    def __init__(self, tag, items=()):
        super().__init__(items)
        self.tag = tag


def _tag_of(v):
    if isinstance(v, Byte) or isinstance(v, bool):
        return TAG_BYTE
    if isinstance(v, Short):
        return TAG_SHORT
    if isinstance(v, Long):
        return TAG_LONG
    if isinstance(v, int):
        return TAG_INT
    if isinstance(v, (Float, float)):
        return TAG_FLOAT
    if isinstance(v, str):
        return TAG_STRING
    if isinstance(v, List):
        return TAG_LIST
    if isinstance(v, dict):
        return TAG_COMPOUND
    raise TypeError(type(v))


def _payload(out, tag, v):
    if tag == TAG_BYTE:
        out.write(struct.pack("<b", int(v)))
    elif tag == TAG_SHORT:
        out.write(struct.pack("<h", int(v)))
    elif tag == TAG_INT:
        out.write(struct.pack("<i", int(v)))
    elif tag == TAG_LONG:
        out.write(struct.pack("<q", int(v)))
    elif tag == TAG_FLOAT:
        out.write(struct.pack("<f", float(v)))
    elif tag == TAG_STRING:
        b = v.encode("utf-8")
        out.write(struct.pack("<H", len(b)) + b)
    elif tag == TAG_LIST:
        out.write(struct.pack("<bi", v.tag if len(v) else TAG_END, len(v)))
        for item in v:
            _payload(out, v.tag, item)
    elif tag == TAG_COMPOUND:
        for k, item in v.items():
            t = _tag_of(item)
            kb = k.encode("utf-8")
            out.write(struct.pack("<bH", t, len(kb)) + kb)
            _payload(out, t, item)
        out.write(b"\x00")


def nbt(root, name=""):
    out = io.BytesIO()
    nb = name.encode()
    out.write(struct.pack("<bH", TAG_COMPOUND, len(nb)) + nb)
    _payload(out, TAG_COMPOUND, root)
    return out.getvalue()


def _state_value(v):
    if isinstance(v, bool):
        return Byte(v)
    if isinstance(v, int):
        return v if v > 1 or v < 0 else Byte(v) if False else v
    return v


# Bedrock block states: booleans ("*_bit", "persistent", "hanging", ...) are TAG_Byte, numbers TAG_Int, text TAG_String.
BYTE_STATES = {"infiniburn_bit", "top_slot_bit", "upside_down_bit", "open_bit", "upper_block_bit", "door_hinge_bit", "head_piece_bit", "occupied_bit",
               "persistent_bit", "update_bit", "hanging", "extinguished", "powered_bit", "toggle_bit", "deprecated", "attached_bit", "in_wall_bit"}


def block_nbt(name, states):
    st = {}
    for k, v in states.items():
        if k in BYTE_STATES:
            st[k] = Byte(int(v))
        elif isinstance(v, int):
            st[k] = int(v)
        else:
            st[k] = str(v)
    return nbt({"name": name, "states": st, "version": VERSION})


PALETTE_NBT = None


def _palette_nbt():
    global PALETTE_NBT
    if PALETTE_NBT is None or len(PALETTE_NBT) != len(NAMES):
        PALETTE_NBT = [block_nbt(n, s) for n, s in NAMES]
    return PALETTE_NBT


# ------------------------------------------------------------------------------------------------ sub-chunks
def encode_subchunk(sub, y_index):
    """sub: (16,16,16) array indexed [x, y, z] of global block ids. Returns the v9 SubChunkPrefix value."""
    pal_nbt = _palette_nbt()
    ids, inv = np.unique(sub.transpose(0, 2, 1).reshape(-1), return_inverse=True)   # order x, z, y
    n = len(ids)
    bits = next(b for b in (1, 2, 3, 4, 5, 6, 8, 16) if (1 << b) >= max(n, 2))
    per = 32 // bits
    nwords = -(-4096 // per)
    idx = np.zeros(nwords * per, dtype=np.uint32)
    idx[:4096] = inv.astype(np.uint32)
    idx = idx.reshape(nwords, per)
    shifts = (np.arange(per, dtype=np.uint32) * bits).astype(np.uint32)
    words = np.bitwise_or.reduce(idx << shifts, axis=1).astype("<u4")
    out = io.BytesIO()
    out.write(struct.pack("<BBb", 9, 1, y_index))
    out.write(struct.pack("<B", bits << 1))
    out.write(words.tobytes())
    out.write(struct.pack("<i", n))
    for i in ids:
        out.write(pal_nbt[int(i)])
    return out.getvalue()


def chunk_key(cx, cz, tag, sub=None):
    k = struct.pack("<iiB", cx, cz, tag)
    if sub is not None:
        k += struct.pack("<b", sub)
    return k


def data3d(heights, biome=1, nsub=24):
    out = io.BytesIO()
    out.write(np.asarray(heights, dtype="<i2").reshape(-1).tobytes())
    for _ in range(nsub):
        out.write(struct.pack("<Bi", 1, biome))      # bits 0, runtime: a single palette value
    return out.getvalue()


# ------------------------------------------------------------------------------------------------ level.dat and packaging
def level_dat(name, spawn, flat_layers_json, time_of_day=12600):
    root = {
        "LevelName": name, "GameType": 1, "Difficulty": 0, "Generator": 2, "FlatWorldLayers": flat_layers_json,
        "RandomSeed": Long(20260515), "SpawnX": spawn[0], "SpawnY": spawn[1], "SpawnZ": spawn[2], "StorageVersion": 10, "NetworkVersion": 712,
        "Platform": 2, "WorldVersion": 1, "LimitedWorldOriginX": spawn[0], "LimitedWorldOriginY": spawn[1], "LimitedWorldOriginZ": spawn[2],
        "lastOpenedWithVersion": List(TAG_INT, [1, 21, 20, 0, 0]), "MinimumCompatibleClientVersion": List(TAG_INT, [1, 21, 0, 0, 0]),
        "InventoryVersion": "1.21.20", "LastPlayed": Long(int(time.time())), "Time": Long(time_of_day), "currentTick": Long(0),
        "commandsEnabled": Byte(1), "hasBeenLoadedInCreative": Byte(1), "showcoordinates": Byte(1), "dodaylightcycle": Byte(0),
        "domobspawning": Byte(0), "doweathercycle": Byte(0), "mobgriefing": Byte(0), "dofiretick": Byte(0), "spawnMobs": Byte(0),
        "rainLevel": Float(0.0), "lightningLevel": Float(0.0), "bonusChestEnabled": Byte(0), "startWithMapEnabled": Byte(0),
        "ForceGameType": Byte(0), "SpawnV1Villagers": Byte(0), "isFromWorldTemplate": Byte(0), "immutableWorld": Byte(0),
        "educationFeaturesEnabled": Byte(0), "texturePacksRequired": Byte(0), "spawnradius": 0, "playerssleepingpercentage": 100,
        "naturalregeneration": Byte(1), "keepinventory": Byte(1), "showdeathmessages": Byte(1), "sendcommandfeedback": Byte(1),
        "commandblockoutput": Byte(1), "showtags": Byte(1), "tntexplodes": Byte(0), "falldamage": Byte(1), "firedamage": Byte(1),
        "drowningdamage": Byte(1), "dotiledrops": Byte(1), "doentitydrops": Byte(1), "domobloot": Byte(1), "doinsomnia": Byte(0),
        "doimmediaterespawn": Byte(0), "functioncommandlimit": 10000, "maxcommandchainlength": 65535, "randomtickspeed": 1,
    }
    body = nbt(root)
    return struct.pack("<ii", 10, len(body)) + body


def flat_layers(top_y):
    # post-1.18 flat worlds start at y = -64; grass ends up at top_y
    total = top_y + 64 + 1
    layers = [{"block_name": "minecraft:bedrock", "count": 1}, {"block_name": "minecraft:stone", "count": total - 5},
              {"block_name": "minecraft:dirt", "count": 3}, {"block_name": "minecraft:grass", "count": 1}]
    return json.dumps({"biome_id": 1, "block_layers": layers, "encoding_version": 6, "structure_options": None, "world_version": "version.post_1_18"}) + "\n"


def package(world_dir, out_path):
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(world_dir):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, world_dir))
