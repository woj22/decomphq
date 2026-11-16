import numpy as np
from scipy import ndimage
hm = np.load('/home/user/elosia/heightmap.npy').astype(np.float32) + 63
O = 3072 + 16
def stats(x, z, size, margin=12):
    a = hm[O + z - size // 2 - margin:O + z + size // 2 + margin, O + x - size // 2 - margin:O + x + size // 2 + margin]
    a = ndimage.median_filter(a, 9)
    return dict(mean=round(float(a.mean()), 1), p5=float(np.percentile(a, 5)), p95=float(np.percentile(a, 95)),
                water=round(float((a <= 63).mean()), 3))
cands = [(4, -108), (-362, 28), (282, -218), (40, -314), (-142, -230), (-230, -106), (-108, -308), (446, -334), (-368, 214), (486, -46)]
for size in (96, 128):
    print('size', size)
    for c in cands:
        print(' ', c, stats(*c, size))
