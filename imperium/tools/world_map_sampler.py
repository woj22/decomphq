"""Vanilla-style map of a Bedrock world at map scale 4 (one map pixel per 16x16 blocks = one chunk):
the most common surface colour of each chunk in Minecraft's map palette, shaded like the game does."""
import os, struct, sys, time, collections, multiprocessing as mp
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapworld import decode

# Minecraft map base colours
MC = dict(NONE=None, GRASS=(127, 178, 56), SAND=(247, 233, 163), WOOL=(199, 199, 199), FIRE=(255, 0, 0), ICE=(160, 160, 255), METAL=(167, 167, 167),
          PLANT=(0, 124, 0), SNOW=(255, 255, 255), CLAY=(164, 168, 184), DIRT=(151, 109, 77), STONE=(112, 112, 112), WATER=(64, 64, 255),
          WOOD=(143, 119, 72), QUARTZ=(255, 252, 245), ORANGE=(216, 127, 51), MAGENTA=(178, 76, 216), LIGHT_BLUE=(102, 153, 216), YELLOW=(229, 229, 51),
          LIME=(127, 204, 25), PINK=(242, 127, 165), GRAY=(76, 76, 76), LIGHT_GRAY=(153, 153, 153), CYAN=(76, 127, 153), PURPLE=(127, 63, 178),
          BLUE=(51, 76, 178), BROWN=(102, 76, 51), GREEN=(102, 127, 51), RED=(153, 51, 51), BLACK=(25, 25, 25), GOLD=(250, 238, 77),
          DIAMOND=(92, 219, 213), LAPIS=(74, 128, 255), EMERALD=(0, 217, 58), PODZOL=(129, 86, 49), NETHER=(112, 2, 0),
          T_WHITE=(209, 177, 161), T_ORANGE=(159, 82, 36), T_YELLOW=(186, 133, 36), T_LIGHT_GRAY=(135, 107, 98), T_RED=(142, 60, 46),
          T_BROWN=(76, 50, 35), T_BLACK=(37, 22, 16), DEEPSLATE=(100, 100, 100), RAW_IRON=(216, 175, 147), LICHEN=(127, 167, 150))
DYES = ['white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime', 'pink', 'gray', 'light_gray', 'silver', 'cyan', 'purple', 'blue', 'brown', 'green', 'red', 'black']
DYE_MC = dict(white='SNOW', orange='ORANGE', magenta='MAGENTA', light_blue='LIGHT_BLUE', yellow='YELLOW', lime='LIME', pink='PINK', gray='GRAY',
              light_gray='LIGHT_GRAY', silver='LIGHT_GRAY', cyan='CYAN', purple='PURPLE', blue='BLUE', brown='BROWN', green='GREEN', red='RED', black='BLACK')

def mapcolour(name):
    n = name.replace('minecraft:', '')
    for d in sorted(DYES, key=len, reverse=True):
        if n.startswith(d + '_'):
            if 'terracotta' in n:
                return 'T_' + DYE_MC[d].replace('SNOW', 'WHITE') if ('T_' + DYE_MC[d].replace('SNOW', 'WHITE')) in MC else 'T_RED'
            if any(k in n for k in ('wool', 'carpet', 'concrete', 'glass', 'bed', 'banner', 'shulker', 'candle')):
                return DYE_MC[d]
    rules = [('water', 'WATER'), ('kelp', 'WATER'), ('seagrass', 'WATER'), ('bubble', 'WATER'), ('lava', 'FIRE'), ('fire', 'FIRE'), ('magma', 'NETHER'),
             ('packed_ice', 'ICE'), ('blue_ice', 'ICE'), ('ice', 'ICE'), ('powder_snow', 'SNOW'), ('snow', 'SNOW'),
             ('cherry_leaves', 'PINK'), ('azalea', 'PLANT'), ('leaves', 'PLANT'), ('vine', 'PLANT'), ('lily', 'PLANT'), ('fern', 'PLANT'),
             ('short_grass', 'PLANT'), ('tall_grass', 'PLANT'), ('flower', 'PLANT'), ('bush', 'PLANT'), ('sapling', 'PLANT'), ('bamboo', 'PLANT'),
             ('cactus', 'PLANT'), ('sugar_cane', 'PLANT'), ('reeds', 'PLANT'), ('wheat', 'PLANT'), ('carrots', 'PLANT'), ('potatoes', 'PLANT'),
             ('dandelion', 'PLANT'), ('poppy', 'PLANT'), ('tulip', 'PLANT'), ('orchid', 'PLANT'), ('allium', 'PLANT'), ('bluet', 'PLANT'), ('daisy', 'PLANT'),
             ('cornflower', 'PLANT'), ('lilac', 'PLANT'), ('rose', 'PLANT'), ('peony', 'PLANT'), ('sunflower', 'PLANT'), ('moss', 'GREEN'),
             ('grass_block', 'GRASS'), ('grass_path', 'DIRT'), ('dirt_path', 'DIRT'), ('mycelium', 'PURPLE'), ('podzol', 'PODZOL'), ('mud', 'CYAN'),
             ('farmland', 'DIRT'), ('coarse_dirt', 'DIRT'), ('rooted_dirt', 'DIRT'), ('dirt', 'DIRT'), ('grass', 'GRASS'),
             ('red_sandstone', 'ORANGE'), ('red_sand', 'ORANGE'), ('sandstone', 'SAND'), ('sand', 'SAND'), ('gravel', 'STONE'), ('clay', 'CLAY'),
             ('terracotta', 'T_ORANGE'), ('hardened_clay', 'T_ORANGE'), ('calcite', 'T_WHITE'), ('dripstone', 'T_BROWN'),
             ('deepslate', 'DEEPSLATE'), ('tuff', 'T_BLACK'), ('basalt', 'BLACK'), ('blackstone', 'BLACK'), ('obsidian', 'BLACK'), ('granite', 'DIRT'),
             ('diorite', 'QUARTZ'), ('quartz', 'QUARTZ'), ('andesite', 'STONE'), ('cobble', 'STONE'), ('stone', 'STONE'), ('ore', 'STONE'),
             ('cherry', 'T_WHITE'), ('spruce', 'PODZOL'), ('dark_oak', 'BROWN'), ('birch', 'SAND'), ('acacia', 'ORANGE'), ('jungle', 'DIRT'),
             ('mangrove', 'RED'), ('crimson', 'NETHER'), ('warped', 'CYAN'), ('oak', 'WOOD'), ('planks', 'WOOD'), ('log', 'WOOD'), ('wood', 'WOOD'),
             ('brick', 'RED'), ('hay', 'YELLOW'), ('pumpkin', 'ORANGE'), ('melon', 'LIME'), ('gold', 'GOLD'), ('iron', 'METAL'), ('copper', 'ORANGE'),
             ('wool', 'SNOW'), ('glass', 'NONE'), ('torch', 'NONE'), ('lantern', 'METAL'), ('rail', 'NONE'), ('bedrock', 'STONE'), ('prismarine', 'CYAN')]
    for k, c in rules:
        if k in n:
            return c
    return 'STONE'

SKIP = ('air', 'light_block', 'structure_void', 'barrier')

def work(args):
    dbdir, chunks = args
    import leveldb
    db = leveldb.LevelDB(dbdir)
    ids, kinds, airy, wet = {}, [], [], []
    def gid(n):
        if n not in ids:
            ids[n] = len(kinds); k = mapcolour(n); kinds.append(k)
            airy.append(any(n.endswith(':' + s) or s in n for s in SKIP) or k == 'NONE')
            wet.append(k == 'WATER')
        return ids[n]
    out = []
    for n_, (cx, cz, hmb) in enumerate(chunks):
        if n_ % 5000 == 0:
            print(dbdir[-4:], n_, len(chunks), flush=True)
        top = np.frombuffer(hmb, dtype='<i2', count=256).reshape(16, 16).T.astype(np.int32) - 1
        ylo, yhi = int(top.min()) - 40, int(top.max()) + 1
        layers = []
        for sy in range(ylo >> 4, (yhi >> 4) + 1):
            try:
                names, idx = decode(db.get(struct.pack('<iiBb', cx, cz, 0x2F, sy)))
                lut = np.array([gid(n) for n in names] + [gid('minecraft:air')], np.int32)
                layers.append(lut[np.minimum(idx, len(names))])
            except KeyError:
                layers.append(np.full((16, 16, 16), gid('minecraft:air'), np.int32))
        G = np.concatenate(layers, axis=2)
        y0 = (ylo >> 4) * 16
        ys = np.arange(G.shape[2]) + y0
        A, Wt = np.array(airy)[G], np.array(wet)[G]
        under = ys[None, None, :] <= top[:, :, None] + 1
        v1 = ~A & under
        hi = G.shape[2] - 1 - np.argmax(v1[:, :, ::-1], axis=2)
        blk = np.take_along_axis(G, hi[:, :, None], axis=2)[:, :, 0]
        v2 = ~A & ~Wt & under
        bed = G.shape[2] - 1 - np.argmax(v2[:, :, ::-1], axis=2)
        kind = np.array(kinds)[blk].reshape(-1)
        c = collections.Counter(kind).most_common(1)[0][0]
        surf = (hi + y0).astype(float)
        depth = float(np.mean(np.where(np.array(wet)[blk], hi - bed, 0)))
        out.append((cx, cz, c, float(np.mean(surf[~np.array(wet)[blk]])) if (~np.array(wet)[blk]).any() else float(np.mean(surf)), depth))
    db.close()
    return out

def main(dbdir, out, ncpu=4, limit=None):
    import leveldb
    t = time.time()
    db = leveldb.LevelDB(dbdir)
    chunks = [(struct.unpack_from('<i', k)[0], struct.unpack_from('<i', k, 4)[0], bytes(v[:512])) for k, v in db.iterate() if len(k) == 9 and k[8] == 0x2B]
    db.close()
    if limit:
        chunks = chunks[:limit]
    dirs = []
    for i in range(ncpu):
        d = dbdir.rstrip('/') + '_w%d' % i
        if not os.path.exists(d):
            os.system('cp -r "%s" "%s"' % (dbdir, d))
        dirs.append(d)
    res = []
    with mp.get_context("spawn").Pool(ncpu) as pool:
        parts = [(dirs[i], chunks[i::ncpu]) for i in range(ncpu)]
        for r in pool.imap_unordered(work, parts):
            res += r
            print("progress", len(res), "%.0fs" % (time.time() - t), flush=True)
    import pickle
    pickle.dump(res, open(out, 'wb'))
    print('chunks', len(res), '%.0fs' % (time.time() - t))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], limit=int(sys.argv[3]) if len(sys.argv) > 3 else None)
