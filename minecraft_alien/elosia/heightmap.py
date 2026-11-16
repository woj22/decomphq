"""Fast whole-world heightmap from Bedrock Data3D records (no subchunk decoding)."""
import struct, time, numpy as np
from leveldb import LevelDB
t = time.time()
db = LevelDB('/home/user/elosia/work/Elosia/db')
R = 3072
N = 2 * R // 16 + 2
hm = np.full((N * 16, N * 16), -999, dtype=np.int16)
n = 0
for k, v in db.iterate():
    if len(k) == 9 and k[8] == 0x2B:     # overworld Data3D
        cx, cz = struct.unpack('<ii', k[:8])
        h = np.frombuffer(v[:512], dtype='<i2').reshape(16, 16)   # [z][x]
        ix, iz = (cx + R // 16 + 1) * 16, (cz + R // 16 + 1) * 16
        if 0 <= ix < hm.shape[1] - 15 and 0 <= iz < hm.shape[0] - 15:
            hm[iz:iz + 16, ix:ix + 16] = h - 64
            n += 1
print('chunks with Data3D', n, round(time.time() - t, 1), 's')
np.save('/home/user/elosia/heightmap.npy', hm)
valid = hm > -999
print('height range', hm[valid].min(), hm[valid].max(), 'median', np.median(hm[valid]))
