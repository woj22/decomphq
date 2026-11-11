"""Procedural tiling textures for the carriage (numpy + Pillow): wood grain, seat moquette, carpet, ceiling.

    python3 last-carriage/tools/make_textures.py
"""
import os

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'textures')
N = 512
rng = np.random.default_rng(7)


def tile_noise(n, octaves, seed):
    """Seamless value noise: sum of random fields upsampled with wrap-around."""
    r = np.random.default_rng(seed)
    acc = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        k = 4 * 2 ** o
        f = r.random((k, k))
        f = np.kron(f, np.ones((n // k, n // k)))
        for ax in (0, 1):  # smooth with a wrapped box blur
            for _ in range(2):
                f = (np.roll(f, n // k // 2, ax) + f) / 2
        acc += f * amp
        tot += amp
        amp *= 0.5
    return acc / tot


def save(name, rgb):
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name))
    print('wrote', name)


y, x = np.mgrid[0:N, 0:N] / N
# wood: rings warped by noise, grain running along x
warp = tile_noise(N, 4, 1)
rings = np.sin((y * 14 + warp * 3.0) * np.pi * 2) * 0.5 + 0.5
fine = tile_noise(N, 6, 2)
streak = np.sin((y * 90 + fine * 6) * np.pi * 2) * 0.5 + 0.5
t = 0.55 * rings ** 2.2 + 0.3 * streak * fine + 0.15 * fine
base = np.array([128, 80, 46])
dark = np.array([62, 34, 18])
save('wood.png', base * (1 - t[..., None]) + dark * t[..., None])

# moquette: a classic railway seat pattern of diamonds and small dots on deep red, with pile noise
c = (x * 8) % 1, (y * 8) % 1
d = np.abs(c[0] - 0.5) + np.abs(c[1] - 0.5)
diamond = (np.abs(d - 0.32) < 0.05).astype(float)
dot = ((c[0] - 0.5) ** 2 + (c[1] - 0.5) ** 2 < 0.012).astype(float)
cross = (((c[0] < 0.04) | (c[0] > 0.96)) & ((c[1] < 0.04) | (c[1] > 0.96))).astype(float)
pile = tile_noise(N, 6, 3)
red = np.array([118, 26, 40]) * (0.8 + 0.35 * pile[..., None])
gold = np.array([196, 150, 70]) * (0.85 + 0.2 * pile[..., None])
navy = np.array([40, 34, 62]) * (0.85 + 0.2 * pile[..., None])
m = red * (1 - diamond[..., None]) + gold * diamond[..., None]
m = m * (1 - dot[..., None]) + navy * dot[..., None]
m = m * (1 - cross[..., None]) + gold * cross[..., None]
save('moquette.png', m)

# carpet: plum with a faint repeating lozenge border pattern and fibre noise
fib = tile_noise(N, 7, 4)
cc = (x * 4) % 1, (y * 4) % 1
loz = (np.abs(np.abs(cc[0] - 0.5) + np.abs(cc[1] - 0.5) - 0.35) < 0.03).astype(float)
carpet = np.array([66, 42, 56]) * (0.75 + 0.4 * fib[..., None])
carpet = carpet * (1 - 0.35 * loz[..., None]) + np.array([120, 84, 60]) * 0.35 * loz[..., None]
save('carpet.png', carpet)

# ceiling / cream paint with soft mottling
mot = tile_noise(N, 5, 5)
save('cream.png', np.array([231, 220, 194]) * (0.9 + 0.12 * mot[..., None]))
