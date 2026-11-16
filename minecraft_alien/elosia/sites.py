import numpy as np
from scipy import ndimage
hm = np.load('/home/user/elosia/heightmap.npy').astype(np.float32) + 63
R = 3072; O = R + 16
# central 3000 x 3000 at 2-block resolution, trees smoothed out with a median filter
x0 = O - 1500; sub = hm[x0:x0 + 3000:2, x0:x0 + 3000:2]
sm = ndimage.median_filter(sub, size=7)
water = sm <= 63.5
def site_score(size):
    k = size // 2 + 4                     # footprint (in 2-block cells) + margin
    mean = ndimage.uniform_filter(sm, k)
    sq = ndimage.uniform_filter(sm * sm, k)
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    wet = ndimage.uniform_filter(water.astype(np.float32), k)
    gy, gx = np.gradient(sm)
    slope = ndimage.uniform_filter(np.hypot(gx, gy), k)
    yy, xx = np.mgrid[0:sm.shape[0], 0:sm.shape[1]]
    dist = np.hypot((xx - 750) * 2, (yy - 750) * 2)      # blocks from 0,0
    s = std + slope * 4 + wet * 200 + np.maximum(0, 66 - mean) * 5 + np.maximum(0, mean - 140) * 0.5 + dist * 0.004
    return s, mean, std
res = {}
for size in (96, 112, 128):
    s, mean, std = site_score(size)
    res[size] = (s, mean, std)
np.save('/home/user/elosia/score128.npy', res[128][0])
# best 'city' region: minimise the sum of the best 5 footprints within a 520-block window
s96 = res[96][0]
best = []
cand = ndimage.minimum_filter(s96, size=40)
for (zi, xi) in zip(*np.nonzero((s96 == cand))):
    best.append((s96[zi, xi], (xi * 2 - 1500), (zi * 2 - 1500), res[96][1][zi, xi], res[96][2][zi, xi]))
best.sort()
for b in best[:25]:
    print(f'score {b[0]:6.2f}  x {b[1]:5d} z {b[2]:5d}  mean y {b[3]:5.1f}  std {b[4]:4.1f}')
