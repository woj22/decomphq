"""Floors, decals and FX drawn directly in Border-24 with numpy (exact pixel control, seamless tiling)."""
import math
import numpy as np
from palette import rgb


def _h(*a):
    """deterministic hash -> [0,1)"""
    x = 0x9E3779B1
    for v in a:
        x = (x ^ (int(v) & 0xFFFFFFFF)) * 0x85EBCA6B & 0xFFFFFFFF
        x ^= x >> 13
    return (x & 0xFFFF) / 65536.0


def uv_grid(w, h, ox, oy, ss=1):
    """cell coords (u=cx, v=cy) for each pixel centre relative to origin."""
    py, px = np.mgrid[0:h, 0:w].astype(float)
    dx, dy = px + .5 - ox, py + .5 - oy
    a, b = dx / 32, dy / 16          # a = X+Y = u - v ; b = X-Y = u + v   (X=u, Y=-v)
    u = (a + b) / 2
    v = (b - a) / 2
    return u, v


def diamond_mask(u, v, nu=1, nv=1):
    return (u >= -.5) & (u < nu - .5) & (v >= -.5) & (v < nv - .5)


def paint(shape, ids, colours):
    out = np.zeros((*shape, 4), np.uint8)
    for k, c in colours.items():
        m = ids == k
        out[m, :3] = rgb(c); out[m, 3] = 255
    return out


def slab_ids(u, v, variant):
    U, V = u + .5, v + .5        # tile spans [0,1)
    if variant == 0:      # 2x2
        i, j = np.floor(U * 2), np.floor(V * 2)
    elif variant == 1:    # running bond along u
        j = np.floor(V * 2); i = np.floor(U * 2 + (j % 2) * .5)
    elif variant == 2:    # one long slab + two
        j = np.floor(V * 2)
        i = np.where(j % 2 == 0, np.floor(U), np.floor(U * 2) + 10)
    else:                 # 3 rows
        j = np.floor(V * 3); i = np.floor(U * 2 + (j % 2) * .5)
    return i * 97 + j * 13 + np.floor(U) * 1009 + np.floor(V) * 7919


def flagstone(w=64, h=32, ox=32, oy=16, variant=0, seed=0):
    u, v = uv_grid(w, h, ox, oy)
    ids = slab_ids(u, v, variant)
    # mortar where right or lower neighbour differs (one-sided -> 1 px lines, seamless)
    pad_r = slab_ids(*uv_grid(w + 1, h, ox, oy), variant)[:, 1:]
    pad_d = slab_ids(*uv_grid(w, h + 1, ox, oy), variant)[1:, :]
    mortar = (ids != pad_r) | (ids != pad_d)
    hi_l = slab_ids(*uv_grid(w + 1, h, ox + 1, oy), variant)[:, :w]   # left neighbour
    hi_u = slab_ids(*uv_grid(w, h + 1, ox, oy + 1), variant)[:h, :]   # upper neighbour
    lit = ((ids != hi_l) | (ids != hi_u)) & ~mortar
    shades = ['37323f', '43325c', '37323f', '4b4654', '43325c']
    out = np.zeros((h, w, 4), np.uint8)
    uniq = np.unique(ids)
    for k in uniq:
        m = ids == k
        c = shades[int(_h(k, seed, variant) * len(shades))]
        out[m, :3] = rgb(c)
    out[lit, :3] = rgb('4b4654')
    # speckle / wear
    py, px = np.mgrid[0:h, 0:w]
    sp = np.vectorize(lambda x, y: _h(x * 31 + y, seed, 5))(px, py)
    out[(sp < .035) & ~mortar, :3] = rgb('27232f')
    out[(sp > .975) & ~mortar, :3] = rgb('4b4654')
    out[mortar, :3] = rgb('1a1722')
    if variant == 3:   # crack
        crack = np.abs((u - .1) * .8 + np.sin(v * 7) * .06 - v * .3) < .018
        out[crack & (np.abs(v) < .4), :3] = rgb('1a1722')
    mask = diamond_mask(u, v)
    out[..., 3] = np.where(mask, 255, 0)
    out[~mask] = 0
    return out


def floor_edge(variant):
    """64x48: flagstone top plus a 16 px stone skirt on the SE (0) or SW (1) edge."""
    out = np.zeros((48, 64, 4), np.uint8)
    out[:32] = flagstone(variant=0, seed=40 + variant)
    py, px = np.mgrid[0:48, 0:64]
    for y in range(48):
        for x in range(64):
            if out[y, x, 3]:
                continue
            # skirt: below the lower edge of the diamond
            if variant == 0 and x >= 32:
                top = 32 - (x + .5 - 32) / 2
            elif variant == 1 and x < 32:
                top = 16 + (x + .5) / 2
            else:
                continue
            if top <= y + .5 < top + 16:
                d = y + .5 - top
                c = '27232f' if variant == 0 else '37323f'
                if int(d) in (5, 11): c = '1a1722'
                if d < 2: c = '4b4654' if variant == 1 else '37323f'
                out[y, x, :3] = rgb(c); out[y, x, 3] = 255
    return out


def carpet(variant):
    u, v = uv_grid(64, 32, 32, 16)
    out = flagstone(variant=0, seed=70 + variant)
    if variant == 0:
        band = np.ones_like(u, bool); edge = np.zeros_like(u, bool)
    else:
        q = v if variant == 1 else u    # runner along cx (variant 1) or along cy (variant 2)
        band = np.abs(q) < .36; edge = band & (np.abs(q) > .29)
    U, V = u + .5, v + .5
    pat = ((np.floor(U * 4) + np.floor(V * 4)) % 2 == 0)
    m = band & diamond_mask(u, v)
    out[m, :3] = np.where(pat[m][:, None], rgb('74161b'), rgb('74161b'))
    dia = (np.abs(((U * 4) % 1) - .5) + np.abs(((V * 4) % 1) - .5)) < .18
    out[m & dia, :3] = rgb('b3261e')
    out[edge & diamond_mask(u, v), :3] = rgb('a8742a')
    return out


def goldseam(variant):
    u, v = uv_grid(64, 32, 32, 16)
    out = flagstone(variant=1, seed=90 + variant)
    q = v if variant == 0 else u
    seam = np.abs(q) < .035
    m = seam & diamond_mask(u, v)
    out[m, :3] = rgb('a8742a')
    hl = m & (np.abs(q + .02) < .012)
    out[hl, :3] = rgb('e0a83e')
    return out


def inlay_ring():
    w, h, ox, oy = 256, 128, 128, 64
    py, px = np.mgrid[0:h, 0:w].astype(float)
    dx, dy = (px + .5 - ox) / 32, (py + .5 - oy) / 16   # elliptical 2:1 -> cell units
    # back to ground-plane coords (rotated diamond -> circle in uv)
    a, b = dx, dy
    gu, gv = (a + b) / 2, (b - a) / 2
    r = np.sqrt(gu ** 2 + gv ** 2)
    ang = np.arctan2(gv, gu)
    out = np.zeros((h, w, 4), np.uint8)
    ring_o = (r > 1.66) & (r < 1.82)
    ring_i = (r > 1.18) & (r < 1.28)
    spokes = (r > 1.28) & (r < 1.62) & (np.abs(((ang / (2 * np.pi) * 16) % 1) - .5) < .07)
    runes = (r > 1.36) & (r < 1.52) & (np.abs(((ang / (2 * np.pi) * 16) % 1) - .5) > .25) & \
            (np.abs(((ang / (2 * np.pi) * 48) % 1) - .5) < .12)
    for m, c in ((ring_o, 'a8742a'), (ring_i, 'a8742a'), (spokes, '6b4a1e'), (runes, '6b4a1e')):
        out[m, :3] = rgb(c); out[m, 3] = 255
    hl = ((r > 1.69) & (r < 1.74)) | ((r > 1.2) & (r < 1.23))
    out[hl & (out[..., 3] > 0), :3] = rgb('e0a83e')
    # scorch: the Hell (screen-right) half is burnt
    sx = px + .5 - ox
    scorch = (sx > 10) & (out[..., 3] > 0)
    noise = np.vectorize(lambda x, y: _h(x // 2, y // 2, 77))(px.astype(int), py.astype(int))
    burnt = scorch & (noise < np.clip((sx - 10) / 100, 0, .85))
    out[burnt, :3] = rgb('3a0f14')
    out[burnt & (noise < .25), :3] = rgb('27232f')
    return out


# ------------------------------------------------------------------ FX
def ellipse_mask(w, h, cx, cy, rx, ry):
    py, px = np.mgrid[0:h, 0:w].astype(float)
    return ((px + .5 - cx) / rx) ** 2 + ((py + .5 - cy) / ry) ** 2


def shadow_blob():
    d = ellipse_mask(32, 16, 16, 8, 11, 5)
    out = np.zeros((16, 32, 4), np.uint8)
    out[d < 1, :3] = rgb('0d0b12'); out[d < 1, 3] = 90
    out[d < .55, 3] = 125
    return out


def select_ring(f):
    out = np.zeros((16, 32, 4), np.uint8)
    rx = [12.5, 13.5, 14.5, 13.5][f]
    d = ellipse_mask(32, 16, 16, 8, rx, rx / 2)
    ring = (d < 1) & (d > .62)
    out[ring, :3] = rgb('e0a83e'); out[ring, 3] = 255
    top = ring & (np.mgrid[0:16, 0:32][0] < 8)
    out[top, :3] = rgb('a8742a')
    if f == 2:
        out[ring & ~top, :3] = rgb('f6d67a')
    return out


def light_pool(kind):
    w, h = 192, 96
    d = np.sqrt(ellipse_mask(w, h, 96, 48, 95, 47.5))
    out = np.zeros((h, w, 4), np.uint8)
    cols = (['3a0f14', '74161b', 'b3261e', 'e8552b'] if kind == 'red' else ['6b4a1e', 'a8742a', 'e0a83e', 'f6d67a'])
    bands = [(1.0, cols[0], 70), (.78, cols[0], 110), (.56, cols[1], 120), (.36, cols[1], 150), (.18, cols[2], 140)]
    for r, c, a in bands:
        m = d < r
        out[m, :3] = rgb(c); out[m, 3] = a
    return out


def dust_mote(f):
    out = np.zeros((8, 8, 4), np.uint8)
    y = [4, 3, 3, 4][f]; x = [3, 3, 4, 4][f]
    out[y, x] = (*rgb('b5b0b8'), 200)
    if f in (1, 2):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            out[y + dy, x + dx] = (*rgb('8a8591'), 120)
    return out


def tap_marker(f):
    out = np.zeros((8, 16, 4), np.uint8)
    r = [7.5, 6, 4.5, 3][f]
    py, px = np.mgrid[0:8, 0:16].astype(float)
    d = np.abs(px + .5 - 8) / 2 + np.abs(py + .5 - 4)
    ring = (d < r / 2 + .5) & (d > r / 2 - .6)
    out[ring, :3] = rgb('f6d67a' if f < 2 else 'e0a83e'); out[ring, 3] = 255
    return out
