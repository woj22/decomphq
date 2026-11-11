"""Texture prep for Snowbound: neutralise the CC0 Poly Haven fabrics so materials can tint them, and generate the
textures Poly Haven has no match for (damask carpet runner, ceiling paint). Run: python3 snowbound/tools/make_textures.py"""
import os

import numpy as np
from PIL import Image, ImageFilter

T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'textures')
N = 1024


def neutral(name):
    """Greyscale the albedo (keeping its contrast) so a material tint gives the colour."""
    p = os.path.join(T, name + '_albedo.jpg')
    im = Image.open(p).convert('L')
    a = np.asarray(im).astype(float)
    a = (a - a.mean()) / (a.std() + 1e-6) * 28 + 180
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGB').save(os.path.join(T, name + '_grey.jpg'), quality=92)


def tile_noise(n, octaves, seed):
    r = np.random.default_rng(seed)
    acc = np.zeros((n, n))
    amp = tot = 0.0
    amp = 1.0
    for o in range(octaves):
        k = 4 * 2 ** o
        f = np.kron(r.random((k, k)), np.ones((n // k, n // k)))
        img = Image.fromarray((f * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(n / k / 2))
        acc += np.asarray(img) / 255 * amp
        tot += amp
        amp *= 0.5
    return acc / tot


for n in ('floral_jacquard', 'rough_linen', 'velour_velvet'):
    neutral(n)

# carpet runner: deep red field with a gold-and-black border along both edges and a repeating damask lozenge
y, x = np.mgrid[0:N, 0:N] / N           # x across the runner (0..1), y along it (tiles)
fib = tile_noise(N, 6, 3)
red = np.array([92, 18, 28])
gold = np.array([176, 128, 62])
dark = np.array([34, 10, 14])
cx, cy = np.abs(x - 0.5), (y * 4) % 1
loz = np.abs(np.abs(cx * 2.2) + np.abs(cy - 0.5) * 1.1 - 0.42)
motif = (loz < 0.035) | ((np.abs(cx) < 0.06) & (np.abs(cy - 0.5) < 0.06))
leaf = ((np.sin(cy * np.pi * 8 + cx * 30) > 0.92) & (cx > 0.18) & (cx < 0.32))
img = red * (0.78 + 0.35 * fib[..., None])
img = np.where(motif[..., None] | leaf[..., None], gold * (0.75 + 0.3 * fib[..., None]), img)
border = (cx > 0.40) & (cx < 0.46)
inner = (cx > 0.36) & (cx < 0.375)
img = np.where(border[..., None], gold * (0.8 + 0.25 * fib[..., None]), img)
img = np.where((inner | (cx >= 0.46))[..., None], dark * (0.8 + 0.4 * fib[..., None]) + np.array([20, 4, 6]), img)
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(T, 'runner_albedo.jpg'), quality=92)

# ceiling: warm ivory paint with soft mottling and faint roller marks
mot = tile_noise(N, 5, 5)
ceil = np.array([226, 212, 182]) * (0.9 + 0.12 * mot[..., None]) * (1 + 0.02 * np.sin(x * 120)[..., None])
Image.fromarray(np.clip(ceil, 0, 255).astype(np.uint8)).save(os.path.join(T, 'ceiling_albedo.jpg'), quality=92)
# the framed picture: a sepia etching of an alpine valley with a castle, hatched like an engraving
P = 768
ys, xs = np.mgrid[0:P, 0:P // 4 * 3] / P
w = xs.shape[1]
paper = np.array([214, 198, 164]) * (0.94 + 0.08 * tile_noise(P, 4, 9)[:, :w, None])
ink = np.zeros((P, w))
ridge1 = 0.42 + 0.12 * np.sin(xs * 9.0) + 0.06 * np.sin(xs * 23.0 + 1.0)
ridge2 = 0.55 + 0.08 * np.sin(xs * 6.0 + 2.0) + 0.04 * np.sin(xs * 31.0)
hatch = (np.sin((xs + ys) * 260) > 0.55).astype(float)
cross = (np.sin((xs - ys) * 260) > 0.6).astype(float)
ink += ((ys > ridge1) & (ys < ridge2)) * hatch * 0.5
ink += (ys > ridge2) * np.maximum(hatch, cross) * 0.75
ink += (np.abs(ys - ridge1) < 0.004) * 1.0 + (np.abs(ys - ridge2) < 0.004) * 1.0
castle = (np.abs(xs - 0.42) < 0.05) & (ys > ridge1 - 0.12) & (ys < ridge1 + 0.02)
tower = (np.abs(xs - 0.4) < 0.012) & (ys > ridge1 - 0.2) & (ys < ridge1)
ink += (castle | tower) * 0.9
ink += (ys < 0.3) * (np.sin(ys * 600) > 0.85) * 0.25 * (1 - ys / 0.3)
for k in range(14):  # pines in the foreground
    cx, cy, hh = 0.05 + k * 0.07, 0.86 + (k % 3) * 0.03, 0.12
    ink += ((ys > cy - hh) & (ys < cy) & (np.abs(xs - cx) < (ys - (cy - hh)) * 0.35)) * 0.8
frame_border = (xs < 0.03) | (xs > w / P - 0.03) | (ys < 0.03) | (ys > 0.97)
ink = np.clip(ink, 0, 1)
pic = paper * (1 - ink[..., None] * 0.75) + np.array([52, 36, 22]) * ink[..., None] * 0.75
pic = np.where(frame_border[..., None], paper * 0.97, pic)
Image.fromarray(np.clip(pic, 0, 255).astype(np.uint8)).save(os.path.join(T, 'picture_albedo.jpg'), quality=92)
print('textures ok')
