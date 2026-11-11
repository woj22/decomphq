"""Procedural backdrops (Gilt sky/skyline, Ember sky/skyline, void fog): float paintings, Bayer-quantised to Border-24."""
import numpy as np
from palette import rgb, PAL, BORDER24

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5
WGT = np.array([0.30, 0.59, 0.11]) ** 0.5


def C(h):
    return np.array(rgb(h), float)


def quant(img, allowed, dither=28.0, alpha=None):
    h, w, _ = img.shape
    th = BAYER[np.arange(h)[:, None] % 4, np.arange(w)[None, :] % 4]
    x = np.clip(img + th[..., None] * dither, 0, 255)
    pal = np.array([rgb(c) for c in allowed], float)
    d = (((x[..., None, :] - pal) * WGT) ** 2).sum(-1)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = pal[d.argmin(-1)].astype(np.uint8)
    out[..., 3] = 255 if alpha is None else alpha
    if alpha is not None:
        out[alpha == 0] = 0
    return out


def vnoise(w, h, cell, seed, periodic=False):
    rng = np.random.RandomState(seed)
    gw, gh = int(np.ceil(w / cell)) + 1, int(np.ceil(h / cell)) + 1
    g = rng.rand(gh + 1, gw + 1)
    if periodic:
        g[:, -1] = g[:, 0]; g[-1, :] = g[0, :]
        gw2, gh2 = w // cell, h // cell
        g = rng.rand(gh2, gw2)
        g = np.pad(g, ((0, 2), (0, 2)), mode='wrap')
    y, x = np.mgrid[0:h, 0:w] / cell
    x0, y0 = x.astype(int), y.astype(int)
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = g[y0, x0], g[y0, x0 + 1]
    c, d = g[y0 + 1, x0], g[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(w, h, cell, seed, oct=4, periodic=False):
    s, amp, tot = 0, 1, 0
    for o in range(oct):
        c = max(2, cell // (2 ** o))
        s = s + amp * vnoise(w, h, c, seed + o, periodic); tot += amp; amp *= .5
    return s / tot


def lerp_ramp(t, stops):
    """t in [0,1] -> colour by piecewise-linear stops [(t, hex)]."""
    out = np.zeros(t.shape + (3,))
    ts = [s[0] for s in stops]; cs = [C(s[1]) for s in stops]
    for k in range(3):
        out[..., k] = np.interp(t, ts, [c[k] for c in cs])
    return out


# ---------------------------------------------------------------- spires
def towers(w, h, rng, n, base_lo, base_hi, wmin, wmax, hmin, hmax):
    """returns mask (h,w) bool, window mask, lit-side mask"""
    m = np.zeros((h, w), bool); win = np.zeros((h, w), bool); lit = np.zeros((h, w), bool)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(n):
        cx = rng.uniform(0, w); tw = rng.uniform(wmin, wmax); th = rng.uniform(hmin, hmax)
        base = rng.uniform(base_lo, base_hi)
        sp_h = tw * rng.uniform(1.6, 3.2)
        th = min(th, base - sp_h - tw * .9 - 4)
        top = base - th
        body = (np.abs(xx - cx) < tw / 2) & (yy > top) & (yy < h)
        spire = (yy <= top) & (yy > top - sp_h) & (np.abs(xx - cx) < (tw / 2) * (yy - (top - sp_h)) / sp_h)
        tower = body | spire
        # corner pinnacles
        for sx in (-1, 1):
            px = cx + sx * tw / 2
            ph = tw * .9
            tower |= (yy <= top + 2) & (yy > top - ph) & (np.abs(xx - px) < 2.2 * (yy - (top - ph)) / ph + .5)
        # buttress steps
        bw = tw * .35
        for sx in (-1, 1):
            tower |= (np.abs(xx - (cx + sx * (tw / 2 + bw / 2))) < bw / 2) & (yy > top + th * .45 + (np.abs(xx - cx) - tw / 2) * 1.6)
        m |= tower
        lit |= tower & (xx < cx)
        # lancet windows
        nwin = max(1, int(tw // 7))
        for i in range(nwin):
            wx = cx - tw / 2 + (i + .5) * tw / nwin
            for row in range(int(th // 26)):
                wy = top + 10 + row * 26
                if wy + 12 > h: break
                if rng.rand() < .45: continue
                win |= (np.abs(xx - wx) < 1.2) & (yy > wy) & (yy < wy + 11) & body
                win |= (np.abs(xx - wx) < .7) & (yy > wy - 2) & (yy <= wy) & body
    return m, win, lit


def heaven_sky(w=640, h=360):
    y, x = np.mgrid[0:h, 0:w].astype(float)
    t = y / h
    sky = lerp_ramp(t, [(0, '9a86ad'), (.35, 'e0a83e'), (.7, 'f6d67a'), (1, 'fff3c4')])
    glow = np.exp(-(((x - w * .25) / (w * .35)) ** 2 + ((y - h * .55) / (h * .45)) ** 2))
    sky = sky + (C('fff3c4') - sky) * glow[..., None] * .8
    rays = (np.sin((x - y * .35) / 23.0) > .93) & (y < h * .8)
    sky = np.where(rays[..., None], sky + (C('fff3c4') - sky) * .18, sky)
    n = fbm(w, h, 96, 3)
    bands = np.clip((n - .48) * 4, 0, 1) * np.clip(1 - np.abs(t - .55) * 2.2, 0, 1)
    cloud = lerp_ramp(np.clip(n * 1.4 - .2, 0, 1), [(0, '9a86ad'), (.5, 'b5b0b8'), (1, 'fff3c4')])
    sky = sky * (1 - bands[..., None]) + cloud * bands[..., None]
    lower = np.clip((t - .72) * 4, 0, 1) * np.clip(fbm(w, h, 48, 9) * 1.6 - .2, 0, 1)
    sky = sky * (1 - lower[..., None]) + C('b5b0b8') * lower[..., None]
    return quant(sky, ['9a86ad', 'b5b0b8', 'e0a83e', 'f6d67a', 'fff3c4', '8a8591'])


def heaven_skyline(w=960, h=240):
    rng = np.random.RandomState(21)
    img = np.zeros((h, w, 3)); a = np.zeros((h, w), np.uint8)
    layers = [(40, 120, 170, 10, 24, 60, 140, ('f6d67a', 'fff3c4', 'fff3c4')),
              (26, 150, 200, 14, 34, 70, 150, ('e0a83e', 'f6d67a', 'fff3c4')),
              (16, 175, 230, 18, 40, 70, 140, ('a8742a', 'e0a83e', 'fff3c4'))]
    for n, blo, bhi, wmin, wmax, hmin, hmax, (body, lit, win) in layers:
        m, wn, lt = towers(w, h, rng, n, blo, bhi, wmin, wmax, hmin, hmax)
        img[m] = C(body); img[m & lt] = C(lit); img[m & wn] = C(win if body != 'f6d67a' else 'e0a83e')
        a[m] = 255
        # cloud bank in front of each layer
        y, x = np.mgrid[0:h, 0:w]
        cl = (y > blo + 10 + 18 * fbm(w, h, 40, n + blo)) & (y < h)
        cl &= fbm(w, h, 30, n * 7) > .38
        sh = fbm(w, h, 14, n * 3 + 1)
        cc = lerp_ramp(np.clip((sh - .3) * 2 + (blo + 30 - y) / 60, 0, 1), [(0, '9a86ad'), (.45, 'b5b0b8'), (1, 'fff3c4')])
        img[cl] = cc[cl]
        a[cl] = 255
    img = img + np.array([0, 0, 0])
    return quant(img, ['9a86ad', 'b5b0b8', 'a8742a', 'e0a83e', 'f6d67a', 'fff3c4', '6b4a1e'], dither=22, alpha=a)


def hell_sky(w=640, h=360):
    y, x = np.mgrid[0:h, 0:w].astype(float)
    t = y / h
    sky = lerp_ramp(t, [(0, '1a1722'), (.35, '3a0f14'), (.75, '74161b'), (1, 'b3261e')])
    glow = np.exp(-(((x - w * .7) / (w * .3)) ** 2 + ((y - h * .9) / (h * .3)) ** 2))
    sky = sky + (C('e8552b') - sky) * glow[..., None] * .7
    n = fbm(w, h, 80, 5)
    smoke = np.clip((n - .45) * 3, 0, 1) * np.clip(1 - t * .6, 0, 1)
    sky = sky * (1 - smoke[..., None] * .8) + C('27232f') * smoke[..., None] * .8
    streak = (np.abs(((y + x * .08 + 20 * n) % 46) - 23) < 1.5) & (t > .3)
    sky = np.where(streak[..., None], sky * .75 + C('74161b') * .25, sky)
    return quant(sky, ['0d0b12', '1a1722', '27232f', '3a0f14', '74161b', 'b3261e', 'e8552b'])


def hell_skyline(w=960, h=240):
    rng = np.random.RandomState(66)
    img = np.zeros((h, w, 3)); a = np.zeros((h, w), np.uint8)
    y, x = np.mgrid[0:h, 0:w]
    layers = [(30, 110, 170, 14, 34, 60, 150, ('3a0f14', '74161b')),
              (18, 150, 210, 20, 50, 80, 170, ('1a1722', '3a0f14')),
              (10, 190, 240, 28, 60, 90, 170, ('0d0b12', '1a1722'))]
    for i, (n, blo, bhi, wmin, wmax, hmin, hmax, (body, rim)) in enumerate(layers):
        m, wn, lt = towers(w, h, rng, n, blo, bhi, wmin, wmax, hmin, hmax)
        img[m] = C(body)
        edge = m & ~np.roll(m, 1, axis=1)
        img[edge] = C(rim)
        img[m & wn] = C('e8552b' if i > 0 else 'b3261e')
        a[m] = 255
    # lava glow band at the base + chains of smoke
    lava = (y > h - 30 + 10 * fbm(w, h, 50, 3)) & (fbm(w, h, 20, 4) > .55)
    img[lava] = C('b3261e'); img[lava & (fbm(w, h, 10, 8) > .6)] = C('e8552b'); a[lava] = 255
    return quant(img, ['0d0b12', '1a1722', '27232f', '3a0f14', '74161b', 'b3261e', 'e8552b'], dither=6, alpha=a)


def void_fog(w=256, h=128):
    n = fbm(w, h, 64, 12, periodic=True)
    y = np.mgrid[0:h, 0:w][0] / h
    img = lerp_ramp(np.clip(n * 1.3 - .1, 0, 1), [(0, '1a1722'), (.4, '2a1f3d'), (.7, '43325c'), (1, '6a5484')])
    return quant(img, ['1a1722', '2a1f3d', '43325c', '6a5484'], dither=40)


BACKDROPS = {'bg_heaven_sky': heaven_sky, 'bg_heaven_skyline': heaven_skyline, 'bg_hell_sky': hell_sky,
             'bg_hell_skyline': hell_skyline, 'bg_void_fog': void_fog}
