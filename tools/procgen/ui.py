"""UI atlas sprites (PROJECT §9.5 tokens + Border-24), drawn at native size with Pillow, no antialiasing."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from palette import rgb

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.path.join(ROOT, 'game', 'assets', 'fonts', 'PixelOperator-Bold.ttf')

GOLD, GOLD_L, GOLD_D, GOLD_DD = rgb('e0a83e'), rgb('f6d67a'), rgb('a8742a'), rgb('6b4a1e')
RED, RED_D, EMBER = rgb('b3261e'), rgb('74161b'), rgb('e8552b')
CHAR, EDGE, INK = rgb('1a1722'), rgb('37323f'), rgb('0d0b12')
PARCH, SHADE, PINK = rgb('e6d9b8'), rgb('cbb98f'), rgb('2a2320')
SOUL, SOUL_D, LIL, LIL_D = rgb('cfe0e6'), rgb('8fa3b3'), rgb('9a86ad'), rgb('6a5484')
VIOLET = rgb('8b3fd9')
STONE, STONE_L, PALE = rgb('4b4654'), rgb('8a8591'), rgb('b5b0b8')


def canvas(w, h):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def outline(im, col=INK):
    a = np.asarray(im).copy()
    m = a[..., 3] > 0
    p = np.pad(m, 1)
    nb = p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    a[nb & ~m] = (*col, 255)
    return Image.fromarray(a)


def icon_map():
    im, d = canvas(24, 24)
    d.polygon([(2, 5), (8, 3), (15, 5), (21, 3), (21, 19), (15, 21), (8, 19), (2, 21)], fill=PARCH)
    d.polygon([(8, 3), (15, 5), (15, 21), (8, 19)], fill=SHADE)
    for x, y in ((4, 15), (6, 13), (8, 12), (10, 11), (12, 9), (14, 9), (16, 8)):
        d.point((x, y), fill=GOLD_D)
    d.line([(16, 12), (19, 15)], fill=RED, width=1); d.line([(19, 12), (16, 15)], fill=RED, width=1)
    return outline(im)


def icon_journal():
    im, d = canvas(24, 24)
    d.rectangle((4, 3, 19, 20), fill=RED_D)
    d.rectangle((6, 3, 19, 18), fill=RED)
    d.rectangle((6, 18, 19, 20), fill=PARCH)
    d.line([(6, 3), (6, 20)], fill=RED_D)
    d.rectangle((9, 7, 16, 9), fill=GOLD)
    d.line([(15, 3), (15, 22)], fill=GOLD_L)
    d.point((15, 22), fill=GOLD_D)
    return outline(im)


def icon_pause():
    im, d = canvas(24, 24)
    d.rectangle((6, 4, 10, 19), fill=PALE); d.rectangle((14, 4, 18, 19), fill=PALE)
    d.line([(10, 4), (10, 19)], fill=STONE_L); d.line([(18, 4), (18, 19)], fill=STONE_L)
    return outline(im)


def icon_soul():
    im, d = canvas(16, 16)
    d.ellipse((5, 1, 10, 6), fill=SOUL)
    d.polygon([(4, 7), (11, 7), (12, 12), (10, 14), (8, 12), (6, 14), (3, 12)], fill=SOUL)
    d.line([(10, 8), (11, 12)], fill=SOUL_D)
    return outline(im, LIL_D)


def icon_obol():
    im, d = canvas(16, 16)
    d.ellipse((2, 2, 13, 13), fill=GOLD_D)
    d.ellipse((2, 2, 12, 12), fill=GOLD)
    d.ellipse((5, 5, 9, 9), outline=GOLD_D)
    d.point((4, 4), fill=GOLD_L); d.point((5, 3), fill=GOLD_L)
    return outline(im)


def icon_order():
    im, d = canvas(16, 16)
    d.polygon([(8, 1), (10, 6), (15, 8), (10, 10), (8, 15), (6, 10), (1, 8), (6, 6)], fill=GOLD)
    d.polygon([(8, 4), (9, 7), (12, 8), (9, 9), (8, 12), (7, 9), (4, 8), (7, 7)], fill=GOLD_L)
    return outline(im)


def crest(rank):
    im, d = canvas(32, 32)
    d.polygon([(4, 4), (27, 4), (27, 16), (16, 29), (4, 16)], fill=CHAR)
    d.polygon([(6, 6), (25, 6), (25, 15), (16, 26), (6, 15)], fill=rgb('43325c'))
    d.line([(4, 4), (27, 4)], fill=GOLD); d.line([(27, 4), (27, 16)], fill=GOLD_D)
    d.line([(4, 4), (4, 16)], fill=GOLD); d.line([(4, 16), (16, 29)], fill=GOLD); d.line([(27, 16), (16, 29)], fill=GOLD_D)
    # quill + scale
    d.line([(11, 22), (20, 9)], fill=PALE); d.line([(19, 9), (21, 8)], fill=PALE)
    d.polygon([(17, 12), (21, 8), (22, 10), (19, 14)], fill=PALE)
    d.line([(10, 12), (14, 12)], fill=GOLD_L)
    if rank >= 2:
        d.polygon([(9, 3), (11, 0), (13, 3), (16, 0), (19, 3), (21, 0), (23, 3), (23, 5), (9, 5)], fill=GOLD)
        d.point((16, 2), fill=EMBER)
    return outline(im)


def pip(full):
    im, d = canvas(16, 16)
    d.polygon([(8, 2), (13, 8), (8, 14), (3, 8)], fill=LIL if full else CHAR, outline=None)
    if full:
        d.polygon([(8, 4), (11, 8), (8, 12), (5, 8)], fill=rgb('cfc3d9') if False else PALE)
    else:
        d.polygon([(8, 2), (13, 8), (8, 14), (3, 8)], outline=LIL_D)
    return outline(im)


def icon_link():
    im, d = canvas(24, 24)
    d.ellipse((2, 8, 13, 15), outline=STONE_L); d.ellipse((3, 9, 12, 14), outline=PALE)
    d.ellipse((11, 8, 22, 15), outline=STONE_L); d.ellipse((12, 9, 21, 14), outline=PALE)
    d.line([(1, 20), (8, 17), (16, 18), (23, 15)], fill=RED)
    return outline(im)


def icon_halo():
    im, d = canvas(24, 24)
    d.ellipse((3, 6, 20, 13), outline=GOLD, width=2)
    d.arc((3, 6, 20, 13), 180, 360, fill=GOLD_L, width=1)
    for x, y in ((11, 1), (11, 17), (3, 16), (19, 16)):
        d.point((x, y), fill=GOLD_L)
    d.line([(11, 15), (11, 21)], fill=GOLD_D)
    return outline(im)


def icon_flame():
    im, d = canvas(24, 24)
    d.polygon([(12, 1), (17, 8), (19, 14), (17, 19), (12, 22), (7, 19), (5, 14), (8, 9), (10, 11)], fill=RED)
    d.polygon([(12, 7), (15, 12), (15, 17), (12, 20), (9, 17), (10, 13)], fill=EMBER)
    d.polygon([(12, 13), (13, 16), (12, 19), (11, 16)], fill=GOLD_L)
    return outline(im)


def stamp(kind):
    im, d = canvas(64, 64)
    c, c2, c3 = (GOLD, GOLD_D, GOLD_L) if kind == 'heaven' else (RED, RED_D, EMBER)
    d.ellipse((3, 3, 60, 60), outline=c, width=3)
    d.ellipse((9, 9, 54, 54), outline=c2, width=1)
    for i in range(16):
        import math
        a = i * math.pi / 8
        x, y = 32 + 24.5 * math.cos(a), 32 + 24.5 * math.sin(a)
        d.point((round(x), round(y)), fill=c)
    if kind == 'heaven':
        d.ellipse((19, 16, 44, 26), outline=c3, width=2)
        d.polygon([(32, 28), (41, 46), (23, 46)], fill=c)
        d.polygon([(32, 33), (37, 43), (27, 43)], fill=c3)
    else:
        d.polygon([(32, 13), (40, 27), (43, 37), (39, 47), (32, 51), (25, 47), (21, 37), (25, 28), (29, 31)], fill=c)
        d.polygon([(32, 25), (37, 34), (37, 43), (32, 47), (27, 43), (28, 35)], fill=c3)
    return im


def text_img(txt, size, col):
    try:
        f = ImageFont.truetype(FONT, size)
    except OSError:
        return None
    m = Image.new('1', (64, 32), 0)
    ImageDraw.Draw(m).text((0, 0), txt, font=f, fill=1)
    a = np.asarray(m)
    out = np.zeros((*a.shape, 4), np.uint8); out[a] = (*col, 255)
    return Image.fromarray(out)


def stamp_rm0():
    im, d = canvas(64, 32)
    d.rectangle((1, 1, 62, 30), outline=VIOLET, width=2)
    d.rectangle((5, 5, 58, 26), outline=VIOLET)
    t = text_img('RM 0', 16, VIOLET)
    if t is not None:
        bb = t.getbbox()
        t = t.crop(bb)
        im.alpha_composite(t, ((64 - t.width) // 2, (32 - t.height) // 2))
    else:
        d.rectangle((16, 11, 47, 20), fill=VIOLET)
    # worn ink: knock out a few pixels deterministically
    a = np.asarray(im).copy()
    yy, xx = np.mgrid[0:32, 0:64]
    a[((xx * 7 + yy * 13) % 23 == 0) & (a[..., 3] > 0)] = 0
    return Image.fromarray(a)


def icon_lamp():
    im, d = canvas(24, 24)
    d.polygon([(8, 7), (16, 7), (14, 4), (10, 4)], fill=STONE)
    d.rectangle((8, 7, 16, 17), fill=GOLD)
    d.rectangle((10, 9, 14, 15), fill=GOLD_L)
    d.rectangle((11, 10, 13, 13), fill=rgb('fff3c4'))
    d.rectangle((7, 17, 17, 19), fill=STONE)
    d.line([(12, 1), (12, 4)], fill=STONE_L)
    return outline(im)


def icon_key():
    im, d = canvas(24, 24)
    d.ellipse((3, 3, 11, 11), outline=GOLD, width=2)
    d.line([(10, 10), (20, 20)], fill=GOLD, width=2)
    d.line([(17, 17), (14, 20)], fill=GOLD, width=2); d.line([(20, 20), (18, 22)], fill=GOLD, width=2)
    d.point((5, 5), fill=GOLD_L)
    return outline(im)


def icon_quill():
    im, d = canvas(24, 24)
    d.polygon([(20, 2), (22, 4), (11, 15), (8, 16), (9, 13)], fill=PALE)
    d.line([(20, 3), (9, 15)], fill=STONE_L)
    d.line([(8, 16), (3, 21)], fill=GOLD_D)
    d.point((3, 21), fill=INK)
    return outline(im)


def btn_action():
    im, d = canvas(64, 64)
    d.ellipse((2, 2, 61, 61), fill=(*CHAR, 235))
    d.ellipse((2, 2, 61, 61), outline=GOLD, width=2)
    d.ellipse((6, 6, 57, 57), outline=EDGE, width=1)
    d.arc((6, 6, 57, 57), 200, 320, fill=GOLD_D)
    return im


def nine(kind):
    im, d = canvas(24, 24)
    if kind == 'parchment':
        d.rectangle((0, 0, 23, 23), fill=PARCH)
        d.rectangle((0, 0, 23, 23), outline=SHADE)
        d.rectangle((1, 1, 22, 22), outline=PARCH)
        d.line([(2, 22), (22, 22)], fill=SHADE); d.line([(22, 2), (22, 22)], fill=SHADE)
        for x, y in ((5, 3), (18, 6), (3, 17)):
            d.point((x, y), fill=SHADE)
    else:
        d.rectangle((0, 0, 23, 23), fill=(*CHAR, 235))
        d.rectangle((0, 0, 23, 23), outline=EDGE)
        d.rectangle((1, 1, 22, 22), outline=INK)
        for x, y in ((0, 0), (23, 0), (0, 23), (23, 23)):
            d.point((x, y), fill=(0, 0, 0, 0))
        for x, y in ((1, 1), (22, 1), (1, 22), (22, 22)):
            d.point((x, y), fill=GOLD)
        d.line([(3, 0), (20, 0)], fill=GOLD_D)
    return im


BTN = {'cross': ('7fa7e8', '5a7ab8'), 'circle': ('e85a5a', 'b04040'), 'triangle': ('4fc9a0', '3a9478'),
       'square': ('e08ad6', 'a8629f')}


def face_button(kind, down=False):
    im, d = canvas(64, 64)
    sym = rgb(BTN[kind][1 if down else 0])
    dy = 2 if down else 0
    if not down:
        d.ellipse((4, 7, 59, 62), fill=INK)                                   # drop shadow / depth
    d.ellipse((4, 3 + dy, 59, 58 + dy), fill=EDGE)                            # 2 px rim
    d.ellipse((6, 5 + dy, 57, 56 + dy), fill=CHAR)
    if down:
        d.arc((6, 5 + dy, 57, 56 + dy), 20, 160, fill=rgb('4b4654'), width=2)  # lower highlight when pressed
    else:
        d.arc((6, 5 + dy, 57, 56 + dy), 200, 340, fill=rgb('4b4654'), width=2)
    cx, cy = 31.5, 30.5 + dy
    if kind == 'cross':
        for a, b in (((-11, -11), (11, 11)), ((-11, 11), (11, -11))):
            d.line([(cx + a[0], cy + a[1]), (cx + b[0], cy + b[1])], fill=sym, width=6)
    elif kind == 'circle':
        d.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), outline=sym, width=5)
    elif kind == 'triangle':
        pts = [(cx, cy - 14), (cx + 14, cy + 10), (cx - 14, cy + 10)]
        d.line(pts + [pts[0]], fill=sym, width=5, joint='curve')
    else:
        d.rectangle((cx - 11, cy - 11, cx + 11, cy + 11), outline=sym, width=5)
    return im


def icon_heart():
    im, d = canvas(16, 16)
    d.polygon([(8, 14), (2, 8), (1, 5), (3, 2), (6, 2), (8, 4), (10, 2), (13, 2), (15, 5), (14, 8)], fill=RED)
    d.point((4, 4), fill=EMBER); d.point((5, 4), fill=EMBER); d.point((4, 5), fill=EMBER)
    d.line([(9, 12), (13, 8)], fill=RED_D)
    return outline(im)


def icon_mana():
    im, d = canvas(16, 16)
    d.polygon([(8, 1), (12, 7), (13, 10), (11, 13), (8, 14), (5, 13), (3, 10), (4, 7)], fill=rgb('6a6ee0'))
    d.polygon([(8, 4), (10, 8), (10, 11), (8, 12)], fill=rgb('7fa7e8'))
    d.point((6, 9), fill=rgb('b8c8f4')); d.point((6, 10), fill=rgb('b8c8f4'))
    return outline(im)


UI = {
    'icon_map': icon_map, 'icon_journal': icon_journal, 'icon_pause': icon_pause, 'icon_soul': icon_soul,
    'icon_obol': icon_obol, 'icon_order': icon_order, 'icon_crest_r1': lambda: crest(1), 'icon_crest_r2': lambda: crest(2),
    'pip_full': lambda: pip(True), 'pip_empty': lambda: pip(False), 'icon_link': icon_link, 'icon_halo': icon_halo,
    'icon_flame': icon_flame, 'stamp_heaven': lambda: stamp('heaven'), 'stamp_hell': lambda: stamp('hell'),
    'stamp_rm0': stamp_rm0, 'icon_lamp': icon_lamp, 'icon_key': icon_key, 'icon_quill': icon_quill,
    'btn_action': btn_action, 'icon_heart': icon_heart, 'icon_mana': icon_mana,
    'btn_cross': lambda: face_button('cross'), 'btn_cross_down': lambda: face_button('cross', True),
    'btn_circle': lambda: face_button('circle'), 'btn_circle_down': lambda: face_button('circle', True),
    'btn_triangle': lambda: face_button('triangle'), 'btn_triangle_down': lambda: face_button('triangle', True),
    'btn_square': lambda: face_button('square'), 'btn_square_down': lambda: face_button('square', True), 'parchment_9': lambda: nine('parchment'), 'panel_9': lambda: nine('panel'),
}
SLICES = {'parchment_9': [8, 8, 8, 8], 'panel_9': [8, 8, 8, 8]}


def build():
    return {k: np.asarray(f().convert('RGBA')) for k, f in UI.items()}
