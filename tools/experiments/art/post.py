import numpy as np
from PIL import Image
PAL_HEX = """0d0b12 1a1722 27232f 37323f 4b4654 66616e 8a8591 b5b0b8
2a1f3d 43325c 6a5484 9a86ad
6b4a1e a8742a e0a83e f6d67a fff3c4
3a0f14 74161b b3261e e8552b
5a3f2e cfe0e6 8fa3b3""".split()
PAL = np.array([[int(h[i:i+2],16) for i in (0,2,4)] for h in PAL_HEX], float)
BAYER = np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])/16.0 - 0.5

def quantise(im, dither=0.0, alpha_cut=128, outline=None, keep_alpha=False, pal=PAL):
    a = np.asarray(im.convert('RGBA')).astype(float)
    rgb, al = a[..., :3], a[..., 3]
    # un-premultiply look: Cycles PNG is straight alpha already
    if dither:
        h, w = al.shape
        th = BAYER[np.arange(h)[:, None] % 4, np.arange(w)[None, :] % 4]
        rgb = np.clip(rgb + th[..., None]*dither, 0, 255)
    wgt = np.array([0.30, 0.59, 0.11])**0.5
    d = (((rgb[:, :, None, :] - pal[None, None]) * wgt)**2).sum(-1)
    idx = d.argmin(-1)
    out = pal[idx]
    mask = al >= alpha_cut
    A = np.where(mask, 255, 0) if not keep_alpha else np.where(al > 24, (np.round(al/85)*85), 0)
    res = np.dstack([out, A]).astype(np.uint8)
    res[A == 0] = 0
    if outline is not None:
        m = A > 0; p = np.pad(m, 1)
        nb = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
        edge = nb & ~m
        res[edge] = (*outline, 255)
    return Image.fromarray(res, 'RGBA')

def up(im, k=6, bg=(60, 50, 80)):
    b = Image.new('RGBA', im.size, (*bg, 255)); b.alpha_composite(im)
    return b.resize((im.width*k, im.height*k), Image.NEAREST)
