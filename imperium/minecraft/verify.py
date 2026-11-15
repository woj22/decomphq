"""Read the written world back with LevelDB and decode sub-chunks independently, comparing with the source array."""
import io, json, struct, sys, random
import numpy as np
import leveldb

def read_nbt(buf, pos):
    def payload(t, pos):
        if t == 1: return struct.unpack_from('<b', buf, pos)[0], pos + 1
        if t == 2: return struct.unpack_from('<h', buf, pos)[0], pos + 2
        if t == 3: return struct.unpack_from('<i', buf, pos)[0], pos + 4
        if t == 4: return struct.unpack_from('<q', buf, pos)[0], pos + 8
        if t == 5: return struct.unpack_from('<f', buf, pos)[0], pos + 4
        if t == 8:
            n = struct.unpack_from('<H', buf, pos)[0]; return buf[pos + 2:pos + 2 + n].decode(), pos + 2 + n
        if t == 9:
            et, n = struct.unpack_from('<bi', buf, pos); pos += 5; out = []
            for _ in range(n):
                v, pos = payload(et, pos); out.append(v)
            return out, pos
        if t == 10:
            d = {}
            while True:
                tt = buf[pos]; pos += 1
                if tt == 0: return d, pos
                n = struct.unpack_from('<H', buf, pos)[0]; name = buf[pos + 2:pos + 2 + n].decode(); pos += 2 + n
                d[name], pos = payload(tt, pos)
        raise ValueError(t)
    t = buf[pos]; n = struct.unpack_from('<H', buf, pos + 1)[0]
    return payload(t, pos + 3 + n)

def decode_sub(buf):
    ver, nl, yi = struct.unpack_from('<BBb', buf, 0); pos = 3
    hdr = buf[pos]; pos += 1
    bits = hdr >> 1
    per = 32 // bits; nw = -(-4096 // per)
    words = np.frombuffer(buf, dtype='<u4', count=nw, offset=pos); pos += nw * 4
    n = struct.unpack_from('<i', buf, pos)[0]; pos += 4
    pal = []
    for _ in range(n):
        d, pos = read_nbt(buf, pos); pal.append(d)
    idx = ((words[:, None] >> (np.arange(per) * bits)) & ((1 << bits) - 1)).reshape(-1)[:4096]
    return yi, pal, idx.reshape(16, 16, 16)   # x, z, y

world, out = sys.argv[1], sys.argv[2]
db = leveldb.LevelDB(world + '/db')
V = np.load(out + '/V.npy', mmap_mode='r')
names = json.load(open(out + '/palette.json'))
keys = list(db.keys())
print('keys', len(keys), 'tags', sorted({k[8] for k in keys if len(k) in (9, 10)}))
rnd = random.Random(1); bad = 0; checked = 0
for _ in range(300):
    cx, cz, sy = rnd.randrange(128), rnd.randrange(88), rnd.randrange(-1, 6)
    k = struct.pack('<iiBb', cx, cz, 0x2F, sy)
    try:
        v = db.get(k)
    except Exception:
        continue
    yi, pal, idx = decode_sub(v)
    assert yi == sy
    got = np.array([[[pal[i]['name'] for i in row] for row in plane] for plane in idx.transpose(0, 2, 1)])   # x, y, z
    src = V[cx * 16:cx * 16 + 16, sy * 16 + 16:sy * 16 + 32, cz * 16:cz * 16 + 16]
    exp = np.array(names, dtype=object)[src][..., 0] if False else np.vectorize(lambda i: names[i][0])(src)
    checked += 1
    if not (got == exp).all():
        bad += 1
print('sub-chunks checked', checked, 'mismatches', bad)
ld = open(world + '/level.dat', 'rb').read()
print('level.dat header', struct.unpack_from('<ii', ld, 0), 'keys', list(read_nbt(ld, 8)[0].keys())[:8])
bek = [k for k in keys if len(k) == 9 and k[8] == 0x31][:1]
if bek:
    d, _ = read_nbt(db.get(bek[0]), 0)
    print('first block entity', {k: d[k] for k in list(d)[:6]})
