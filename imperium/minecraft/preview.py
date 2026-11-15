"""Preview renders of the generated world: a shaded top-down map and isometric close-ups."""
import numpy as np
from PIL import Image
import blocks as BL

PAL = None


def set_palette(colors):
    global PAL
    PAL = np.asarray(colors, dtype=np.float32)


def topdown(V, Y0, scale=1, region=None):
    NX, NY, NZ = V.shape
    x0, z0, x1, z1 = region or (0, 0, NX, NZ)
    sub = V[x0:x1, :, z0:z1]
    nz = sub != 0
    top = NY - 1 - np.argmax(nz[:, ::-1, :], axis=1)
    ids = np.take_along_axis(sub, top[:, None, :], axis=1)[:, 0, :]
    pal = PAL if PAL is not None else np.array(BL.COLORS, dtype=np.float32)
    rgb = pal[ids]
    # hillshade from the height field
    h = top.astype(np.float32)
    gx = np.roll(h, -1, 0) - h
    gz = np.roll(h, -1, 1) - h
    shade = np.clip(1.0 + (-gx * 0.5 - gz * 0.35) * 0.18, 0.55, 1.25)
    rgb = np.clip(rgb * shade[..., None] * (0.82 + 0.18 * np.clip((h - h.min()) / 60, 0, 1))[..., None], 0, 255)
    img = Image.fromarray(rgb.transpose(1, 0, 2).astype(np.uint8))
    if scale != 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.NEAREST if scale > 1 else Image.LANCZOS)
    return img


def iso(V, Y0, x0, z0, w, d, y0=-2, y1=80, px=4, cut=None):
    """Isometric view of a region (looking from the south-east). cut: hide blocks above this y (to show interiors)."""
    sub = V[x0:x0 + w, y0 - Y0:y1 - Y0, z0:z0 + d].copy()
    if cut is not None:
        sub[:, cut - y0:, :] = 0
    pal = PAL if PAL is not None else np.array(BL.COLORS, dtype=np.float32)
    xs, ys, zs = np.nonzero(sub)
    ids = sub[xs, ys, zs]
    # exposed blocks only
    W, Hh, D = sub.shape
    pad = np.pad(sub != 0, 1)
    exposed = ~(pad[xs + 2, ys + 1, zs + 1] & pad[xs + 1, ys + 2, zs + 1] & pad[xs + 1, ys + 1, zs + 2])
    xs, ys, zs, ids = xs[exposed], ys[exposed], zs[exposed], ids[exposed]
    # screen projection: x right-down, z left-down, y up
    sx = (xs - zs) * px + (D + 2) * px
    sy = ((xs + zs) * px) // 2 - ys * px + Hh * px
    depth = xs + zs + ys
    order = np.argsort(depth)
    Wimg, Himg = (W + D + 4) * px, ((W + D) * px) // 2 + Hh * px + 4 * px
    img = np.zeros((Himg, Wimg, 3), np.float32)
    img[:] = (205, 170, 190)
    for i in order:
        c = pal[ids[i]]
        X, Y = sx[i], sy[i]
        # top face lighter, two sides darker
        img[Y:Y + px // 2, X - px:X + px] = c * 1.08
        img[Y + px // 2:Y + px + px // 2, X - px:X] = c * 0.86
        img[Y + px // 2:Y + px + px // 2, X:X + px] = c * 0.7
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
