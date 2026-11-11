"""Post-process raw renders into palette sprites, pack atlases, write manifests, lint (PROJECT §7.4)."""
import json, os
import numpy as np
from PIL import Image
from palette import PAL, PAL_UI, AMBIENT, BORDER24, EMISSIVE, SOUL_ONLY, rgb

INK = rgb('0d0b12')
SOUL_OUT = rgb('6a5484')
_IDX = {h: i for i, h in enumerate(BORDER24)}
EMIS_IDX = [_IDX[h] for h in EMISSIVE]
NON_SOUL = np.array([i for i, h in enumerate(BORDER24) if h not in SOUL_ONLY])
SOUL_SET = np.array([_IDX[h] for h in ('cfe0e6', '8fa3b3', '9a86ad', '6a5484', 'b5b0b8')])
WGT = np.array([0.30, 0.59, 0.11]) ** 0.5


def nearest(rgbf, idxs, pal=PAL):
    p = pal[idxs]
    d = (((rgbf[..., None, :] - p) * WGT) ** 2).sum(-1)
    return idxs[d.argmin(-1)]


def quantise(arr, mode='world', outline=False, tint=True, alpha=255, gain=1.0):
    """arr: HxWx4 uint8 raw render. mode: 'world' (no soul colours) | 'soul' | 'any'."""
    a = arr.astype(float)
    rgbf, al = a[..., :3], a[..., 3]
    mask = al >= 128
    allidx = np.arange(len(PAL))
    pre = nearest(rgbf, allidx)
    emis = np.isin(pre, EMIS_IDX)
    if tint and mode != 'soul':
        t = rgbf * AMBIENT * gain
        rgbf = np.where(emis[..., None], rgbf, t)
    idxs = {'world': NON_SOUL, 'soul': SOUL_SET, 'any': allidx}[mode]
    q = nearest(np.clip(rgbf, 0, 255), idxs)
    if mode == 'world':
        # emissive colours only where the render was emissive
        bad = np.isin(q, EMIS_IDX) & ~emis
        if bad.any():
            q2 = nearest(np.clip(rgbf, 0, 255), np.array([i for i in NON_SOUL if i not in EMIS_IDX]))
            q = np.where(bad, q2, q)
    out = np.zeros(arr.shape, np.uint8)
    out[..., :3] = PAL[q].astype(np.uint8)
    out[..., 3] = np.where(mask, alpha, 0)
    out[~mask] = 0
    if outline:
        add_outline(out, SOUL_OUT if mode == 'soul' else INK, alpha)
    return out


def add_outline(out, col, alpha=255):
    m = out[..., 3] > 0
    p = np.pad(m, 1)
    nb = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    edge = nb & ~m
    out[edge] = (*col, alpha)
    return out


def edge_contact(out):
    a = out[..., 3] > 0
    return bool(a[0].any() or a[-1].any() or a[:, 0].any() or a[:, -1].any())


def load(path):
    return np.asarray(Image.open(path).convert('RGBA'))


# ------------------------------------------------------------------ packing
def pack(items, maxw=2048):
    """items: list of (key, w, h). Shelf packer, deterministic. Returns {key:(x,y)}, (W,H)."""
    order = sorted(items, key=lambda t: (-t[2], -t[1], t[0]))
    pos, x, y, shelf_h, W = {}, 0, 0, 0, 0
    for k, w, h in order:
        if x + w > maxw:
            x, y, shelf_h = 0, y + shelf_h, 0
        pos[k] = (x, y)
        x += w; shelf_h = max(shelf_h, h); W = max(W, x)
    H = y + shelf_h
    return pos, (W, H)


def write_atlas(outdir, name, sprites, meta, maxw=2048):
    """sprites: {id: HxWx4 array (full strip incl. frames)}; meta: {id: manifest dict without rect}."""
    pos, (W, H) = pack([(k, v.shape[1], v.shape[0]) for k, v in sprites.items()], maxw)
    assert W <= 2048 and H <= 2048, f'atlas {name} too big: {W}x{H}'
    img = np.zeros((H, W, 4), np.uint8)
    man = {}
    for k in sorted(sprites):
        v = sprites[k]; x, y = pos[k]
        img[y:y + v.shape[0], x:x + v.shape[1]] = v
        d = dict(meta[k])
        fw = d.pop('_fw', v.shape[1]); fh = d.pop('_fh', v.shape[0])
        man[k] = dict(rect=[x, y, fw, fh], **d)
    os.makedirs(outdir, exist_ok=True)
    Image.fromarray(img, 'RGBA').save(os.path.join(outdir, name + '.png'), optimize=True)
    with open(os.path.join(outdir, name + '.json'), 'w') as f:
        json.dump(dict(atlas=name, image=name + '.png', sprites=man), f, indent=1, sort_keys=True)
    return img


def lint(img, ui=False, allow_alpha=False):
    """returns number of off-palette pixels (alpha>0)."""
    pal = PAL_UI if ui else PAL
    vis = img[..., 3] > 0
    px = img[vis][:, :3].astype(int)
    keys = px[:, 0] * 65536 + px[:, 1] * 256 + px[:, 2]
    pk = (pal[:, 0] * 65536 + pal[:, 1] * 256 + pal[:, 2]).astype(int)
    bad = ~np.isin(keys, pk)
    nbad = int(bad.sum())
    if not allow_alpha:
        nbad += int(((img[..., 3] > 0) & (img[..., 3] < 255)).sum())
    return nbad
