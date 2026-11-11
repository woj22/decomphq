"""Builds the Snowbound cast on the shared base (tools/people.py) and exports assets/people/<id>.glb.

    python3 snowbound/tools/build_people.py [id ...] [--preview=DIR]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,I001
from mathutils import Vector  # noqa: E402

import blib  # noqa: E402
from blib import box, cyl, delete_verts, mat, solidify, sphere, torus, tube  # noqa: E402
import people  # noqa: E402
from people import Person, V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'people')
os.makedirs(OUT, exist_ok=True)
PREVIEW = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--preview=')), None)
ONLY = [a for a in sys.argv[1:] if not a.startswith('--')]


def M(name, col, rough=0.75, metal=0.0, **kw):
    return mat(name, col, rough, metal, **kw)


# ------------------------------------------------------------------ hair styles (all ours)
def hair(p, hd, style, col):
    """Sculpted hair: a cap shell cut away around the face, plus the style's own volumes."""
    hc, R = hd['hc'], hd['R']
    m = M('Hair_' + col.lstrip('#'), col, 0.6)
    s = R / 0.115
    parts = []

    def cap(keep_below=-0.05, face_line=0.065, scale=1.08, back_long=0.0):
        c = sphere('hair', R * scale, hc(0, 0, 0), m, scale=(0.95, 1.1, 1.07), segs=40, rings=24)
        delete_verts(c, lambda x, y, z: (z > 0.02 * s and y < (face_line - 3.0 * (x / s) ** 2 + 0.012 * math.cos(x / s * 40)) * s)
                     or y < keep_below * s or (abs(x) > 0.085 * s and -0.045 * s < y < 0.03 * s and -0.03 * s < z < 0.04 * s))
        return solidify(c, 0.014 * s)
    if style == 'short':
        parts.append(cap())
    elif style == 'slick':          # combed back with a middle parting (Tesla)
        parts += [cap(face_line=0.075), tube('part', [hc(0, 0.125, 0.07), hc(0, 0.135, -0.02)], 0.002 * s, M('Skin_part', '#c8a088'), segs=5)]
    elif style == 'tousled':        # Napoleon: short with a forelock
        parts += [cap(face_line=0.06), sphere('forelock', 0.03 * s, hc(0.02, 0.085, 0.085), m, scale=(1.4, 0.6, 0.7), segs=12, rings=8)]
    elif style == 'bob':
        parts.append(cap(keep_below=-0.11, face_line=0.07))
    elif style == 'bun':
        parts += [cap(face_line=0.075), sphere('bun', 0.045 * s, hc(0, 0.04, -0.125), m, segs=18, rings=12),
                  tube('part', [hc(0, 0.13, 0.065), hc(0, 0.14, -0.01)], 0.0022 * s, M('Skin_part2', '#e0bca0'), segs=5)]
    elif style == 'bald_ring':
        c = sphere('ring', R * 1.05, hc(0, 0, 0), m, scale=(0.94, 1.1, 1.05), segs=36, rings=20)
        delete_verts(c, lambda x, y, z: y > 0.03 * s or (z > 0.02 * s and y < 0.05 * s) or y < -0.05 * s or (abs(x) > 0.07 * s and y < -0.01 * s and z > -0.03 * s))
        parts.append(solidify(c, 0.012 * s))
    elif style == 'topknot':
        parts += [cap(face_line=0.08), sphere('knot', 0.032 * s, hc(0, 0.14, -0.01), m, segs=16, rings=10)]
    elif style == 'cropped':
        parts.append(cap(face_line=0.06, scale=1.05))
    p.rigid(parts, 'head', 'Hair')


def beard(p, hd, style, col):
    hc, R = hd['hc'], hd['R']
    s = R / 0.115
    m = M('Beard_' + col.lstrip('#'), col, 0.65)
    parts = []
    if style in ('scholar', 'full'):
        # a tapering beard from the jaw, and a long moustache
        jaw = sphere('jaw', R * 1.06, hc(0, 0, 0), m, scale=(0.86, 1.06, 1.0), segs=36, rings=22)
        delete_verts(jaw, lambda x, y, z: y > -0.03 * s or z < -0.02 * s or (abs(x) < 0.04 * s and y > -0.098 * s and z > 0))
        parts.append(solidify(jaw, 0.012 * s))
        if style == 'scholar':
            parts.append(tube('point', [hc(0, -0.1, 0.075), hc(0, -0.15, 0.08), hc(0, -0.22, 0.07), hc(0, -0.29, 0.055)], [0.03 * s, 0.026 * s, 0.016 * s, 0.003 * s], m, segs=14))
    if style in ('scholar', 'full', 'moustache', 'walrus'):
        drop = 0.04 if style in ('scholar', 'walrus') else 0.02
        for sx in (-1, 1):
            parts.append(tube('mous', [hc(0, -0.052, 0.116), hc(sx * 0.02, -0.056, 0.113), hc(sx * 0.036, -0.06 - drop * 0.5, 0.104), hc(sx * 0.04, -0.06 - drop, 0.096)],
                              [0.006 * s, 0.0075 * s, 0.006 * s, 0.002 * s], m, segs=8))
    if style == 'goatee':
        parts.append(sphere('goatee', 0.022 * s, hc(0, -0.112, 0.1), m, scale=(1, 1.3, 0.8), segs=12, rings=8))
    p.rigid(parts, 'head', 'Beard')


def coat_details(p, buttons=None, lapels=None, rows=1, n=5, spacing=0.06, x=0.035):
    J = p.J
    parts = []
    front_z = 0.115 * p.build + 0.03 * p.belly
    top = J['neck'].y - 0.07
    if lapels:
        for sx in (-1, 1):
            parts.append(tube('lapel', [(sx * 0.055, J['neck'].y - 0.02, front_z - 0.045), (sx * 0.085, top - 0.06, front_z), (sx * 0.035, J['waist'].y + 0.05, front_z + 0.005)],
                              [0.012, 0.018, 0.008], lapels, segs=8))
    if buttons:
        for r in range(rows):
            bx = x if rows == 1 else (x if r == 0 else -x)
            for i in range(n):
                parts.append(sphere('button', 0.009, (bx, top - 0.02 - i * spacing, front_z + 0.006), buttons, scale=(1, 1, 0.5), segs=10, rings=6))
    return p.rigid(parts, 'chest', 'CoatDetails')


def wing_collar(p, white, tie=None, bow=None):
    J = p.J
    z = 0.06
    y = J['neck'].y + 0.02
    parts = [cyl('collar', 0.058 * p.k, 0.056 * p.k, 0.045, (0, y, -0.012), white, segs=24, cap=False)]
    if bow:
        parts += [cyl('bow_l', 0.0, 0.022, 0.035, (-0.018, y - 0.03, z), bow, rot=(0, 0, 90), segs=8),
                  cyl('bow_r', 0.022, 0.0, 0.035, (0.018, y - 0.03, z), bow, rot=(0, 0, 90), segs=8),
                  sphere('knot', 0.008, (0, y - 0.03, z + 0.004), bow, segs=8, rings=6)]
    if tie:
        parts.append(tube('tie', [(0, y - 0.03, z), (0, y - 0.1, z + 0.02), (0, y - 0.2, z + 0.03)], [0.012, 0.016, 0.018], tie, segs=6))
    return p.rigid(parts, 'chest', 'Collar')


# ------------------------------------------------------------------ the cast
def confucius():
    p = Person('confucius', height=1.7, build=0.95, age=68)
    p.build_armature()
    robe = M('Robe_indigo', '#252c4a', 0.8)
    cream = M('Cream', '#e4d8bc', 0.85)
    skin = M('Skin_c', '#d6ab84', 0.55)
    p.body(robe, skin, legs=robe, arms=robe)
    hd = p.head(skin, M('Lips_c', '#a46a5a', 0.45), '#3a3632', iris='#2a1c12', brow_col='#8a847c', age=68)
    p.hands(skin, cuff=robe)
    p.skirt('Robe', robe, p.J['waist'].y, 0.05, 0.17, 0.3, depth=0.85)
    for s, sx in (('L', 1), ('R', -1)):   # wide sleeves hanging from the forearm
        e, w = p.J['elbow' + s], p.J['wrist' + s]
        sl = cyl('sleeve', 0.05, 0.12, (w - e).length + 0.06, (e + w) / 2 + V(0, -0.02, 0), robe, segs=20, cap=False,
                 rot=(0, 0, -sx * math.degrees(math.atan2(abs(w.x - e.x), e.y - w.y))))
        p.rigid([solidify(sl, 0.006)], 'forearm.' + s, 'Sleeve_' + s)
    J = p.J
    collar = []
    for k in range(25):
        a = -math.pi + math.tau * k / 24
        front = max(0.0, math.cos(a)) ** 1.5
        collar.append((math.sin(a) * 0.075, J['neck'].y + 0.01 - 0.1 * front, math.cos(a) * 0.075 - 0.01))
    p.rigid([tube('collar', collar, 0.016, cream, segs=10, cap=False),
             tube('cross', [(0.07, J['neck'].y - 0.01, 0.03), (0.0, J['neck'].y - 0.1, 0.11), (-0.11, J['waist'].y + 0.06, 0.1)], [0.016, 0.017, 0.014], cream, segs=10)], 'chest', 'Collar')
    sash = M('Sash_black', '#16120f', 0.6)
    p.rigid([cyl('sash', 0.165, 0.165, 0.07, (0, J['waist'].y - 0.02, -0.005), sash, segs=36, cap=False),
             tube('sash_end', [(0.05, J['waist'].y - 0.03, 0.15), (0.06, J['waist'].y - 0.25, 0.17), (0.065, J['waist'].y - 0.45, 0.17)], [0.022, 0.02, 0.018], sash, segs=8)], 'hips', 'Sash')
    hair(p, hd, 'topknot', '#5a5550')
    hc, s = hd['hc'], hd['R'] / 0.115
    p.rigid([cyl('cap', 0.042 * s, 0.036 * s, 0.05 * s, hc(0, 0.155, -0.01), M('Lacquer', '#0e0e0e', 0.25), segs=20),
             cyl('pin', 0.0035, 0.0035, 0.12 * s, hc(0, 0.16, -0.01), M('Jade', '#4f8a6a', 0.2), rot=(0, 0, 90), segs=8)], 'head', 'Cap')
    beard(p, hd, 'scholar', '#a29c94')
    p.shoes(M('Shoe_cloth', '#141210', 0.7))
    return p


def napoleon():
    p = Person('napoleon', height=1.69, build=1.02, age=45, belly=0.15)
    p.build_armature()
    navy = M('Coat_navy', '#1d2a5a', 0.7)
    white = M('White_wool', '#e8e4da', 0.8)
    skin = M('Skin_n', '#e8c2a2', 0.55)
    gold = M('Gold', '#d0a448', 0.3, 0.8)
    p.body(navy, skin, legs=white, arms=navy, chest_front=white)
    hd = p.head(skin, M('Lips_n', '#b07468', 0.45), '#3a2a1e', iris='#4a5a6a')
    p.hands(skin, cuff=M('Cuff_red', '#a8282a', 0.6))
    J = p.J
    p.skirt('CoatTails', navy, J['waist'].y, J['knee' + 'L'].y + 0.12, 0.15, 0.2, depth=0.9, back_only=True)
    coat_details(p, buttons=gold, lapels=M('Lapel_red', '#a8282a', 0.6), rows=2, n=6, spacing=0.05, x=0.06)
    ep = []
    for s in 'LR':
        sh = J['shoulder' + s]
        ep.append(sphere('epaulette', 0.055, sh + V(0, 0.035, 0.0), gold, scale=(1, 0.28, 1), segs=16, rings=8))
        for i in range(9):
            a = math.radians(-60 + i * 15)
            ep.append(cyl('fringe', 0.005, 0.005, 0.05, sh + V(math.copysign(1, sh.x) * math.sin(a) * 0.05, 0.005, math.cos(a) * 0.05), gold, segs=5))
    p.rigid(ep, 'chest', 'Epaulettes')
    p.rigid([tube('sash', [(-0.17, J['chest'].y + 0.08, 0.0), (0.0, J['waist'].y + 0.02, 0.15), (0.16, J['hips'].y - 0.02, 0.07)], 0.022, M('Sash_red', '#b02a2a', 0.5), segs=10)], 'chest', 'Sash')
    hair(p, hd, 'tousled', '#3a2a1c')
    hc, s = hd['hc'], hd['R'] / 0.115
    bic = sphere('bicorne', 0.2 * s, hc(0, 0.125, -0.01), M('Felt_black', '#121214', 0.6), scale=(1.0, 0.48, 0.32), segs=32, rings=16)
    delete_verts(bic, lambda x, y, z: y < -0.005)
    p.rigid([solidify(bic, 0.01), torus('gold_edge', 0.2 * s, 0.004, hc(0, 0.124, -0.01), gold, scale=(1, 1, 0.32), segs=40, rsegs=4),
             sphere('cockade', 0.024 * s, hc(0.1, 0.16, 0.035), M('Tricolour', '#c03030', 0.6), scale=(1, 1, 0.3), segs=12, rings=8)], 'head', 'Bicorne')
    boots = M('Boot_black', '#0f0e0e', 0.3)
    p.shoes(boots, boot=0.36)
    return p


def nightingale():
    p = Person('nightingale', height=1.66, build=0.92, female=True, age=36)
    p.build_armature()
    dress = M('Dress_grey', '#2e3446', 0.8)
    white = M('Linen_white', '#ece8de', 0.85)
    skin = M('Skin_f', '#efcdb4', 0.55)
    p.body(dress, skin, legs=dress, arms=dress)
    hd = p.head(skin, M('Lips_f', '#b47064', 0.45), '#4a3020', iris='#5a6a7a')
    p.hands(skin, cuff=white)
    J = p.J
    p.skirt('Skirt', dress, J['waist'].y, 0.03, 0.15, 0.36, depth=0.85)
    p.skirt('Apron', white, J['waist'].y - 0.02, 0.2, 0.17, 0.38, depth=0.85, front_only=True, over=p.last_skirt)
    p.rigid([box('bib', (0.16, 0.2, 0.015), (0, J['chest'].y - 0.03, 0.125), white, bevel=0.008),
             cyl('apron_tie', 0.15, 0.15, 0.025, (0, J['waist'].y, -0.0), white, segs=32, cap=False)], 'chest', 'Bib')
    wing_collar(p, white)
    hair(p, hd, 'bun', '#4a3020')
    hc, s = hd['hc'], hd['R'] / 0.115
    capm = M('Lace', '#f2efe8', 0.8)
    c = sphere('cap', 0.1 * s, hc(0, 0.09, -0.04), capm, scale=(1.12, 0.6, 1.0), segs=24, rings=12)
    p.rigid([c, torus('frill', 0.1 * s, 0.01 * s, hc(0, 0.07, -0.03), capm, scale=(1.1, 1, 1), segs=36, rsegs=6)], 'head', 'Cap')
    p.shoes(M('Shoe_black', '#121212', 0.35))
    return p


def tesla():
    p = Person('tesla', height=1.88, build=0.86, age=40)
    p.build_armature()
    black = M('Suit_black', '#16171c', 0.55)
    white = M('Shirt_white', '#ecebe6', 0.7)
    skin = M('Skin_t', '#e6c4a8', 0.55)
    p.body(black, skin, legs=black, arms=black, chest_front=white)
    hd = p.head(skin, M('Lips_t', '#ae7066', 0.45), '#121010', iris='#3a4a5a')
    p.hands(skin, cuff=white)
    J = p.J
    p.skirt('Tails', black, J['waist'].y, J['knee' + 'L'].y + 0.05, 0.14, 0.17, depth=0.9, back_only=True)
    coat_details(p, buttons=M('Button_black', '#0a0a0a', 0.3), lapels=M('Silk_black', '#0c0c0e', 0.3), n=3, spacing=0.05)
    wing_collar(p, white, bow=M('Bow_black', '#0a0a0a', 0.4))
    hair(p, hd, 'slick', '#141210')
    beard(p, hd, 'moustache', '#141210')
    p.shoes(M('Patent', '#0a0a0a', 0.15))
    return p


def cleopatra():
    p = Person('cleopatra', height=1.65, build=0.9, female=True, age=34)
    p.build_armature()
    linen = M('Linen_gown', '#ece4cc', 0.85)
    gold = M('Gold', '#d0a448', 0.3, 0.8)
    skin = M('Skin_cl', '#c99a74', 0.55)
    p.body(linen, skin, legs=linen, arms=skin)
    hd = p.head(skin, M('Lips_cl', '#8a4a42', 0.4), '#0c0a0a', iris='#2a1a10', kohl=True)
    p.hands(skin)
    J = p.J
    p.skirt('Gown', linen, J['waist'].y + 0.05, 0.03, 0.15, 0.3, depth=0.85)
    p.rigid([cyl('usekh', 0.2, 0.065, 0.07, (0, J['neck'].y - 0.01, -0.02), gold, segs=36, cap=False),
             cyl('usekh_lapis', 0.165, 0.11, 0.025, (0, J['neck'].y + 0.0, -0.02), M('Lapis', '#1f4fa8', 0.3), segs=36, cap=False),
             cyl('usekh_carnelian', 0.205, 0.195, 0.014, (0, J['neck'].y - 0.035, -0.02), M('Carnelian', '#b8402a', 0.3), segs=36, cap=False),
             cyl('belt', 0.15, 0.15, 0.04, (0, J['waist'].y + 0.02, 0), gold, segs=36, cap=False)], 'chest', 'Collar')
    for s in 'LR':
        w = J['wrist' + s]
        p.rigid([torus('bracelet', 0.042, 0.007, w + (J['elbow' + s] - w) * 0.1, gold, segs=20, rsegs=6)], 'forearm.' + s, 'Bracelet_' + s)
    hair(p, hd, 'bob', '#0c0a0a')
    hc, s = hd['hc'], hd['R'] / 0.115
    p.rigid([cyl('diadem', 0.118 * s, 0.118 * s, 0.022 * s, hc(0, 0.06, 0.0), gold, rot=(-8, 0, 0), segs=32, cap=False),
             tube('uraeus', [hc(0, 0.07, 0.118), hc(0, 0.1, 0.126), hc(0, 0.125, 0.118)], [0.008 * s, 0.01 * s, 0.012 * s], gold, segs=8),
             sphere('hood', 0.016 * s, hc(0, 0.135, 0.116), gold, scale=(1.3, 1.1, 0.5), segs=10, rings=6)], 'head', 'Diadem')
    p.shoes(M('Sandal_gold', '#a8803a', 0.4, 0.4))
    return p


def machiavelli():
    p = Person('machiavelli', height=1.72, build=0.84, age=50)
    p.build_armature()
    red = M('Lucco_red', '#7a1a1e', 0.75)
    black = M('Black_wool', '#141214', 0.8)
    skin = M('Skin_m', '#dcb494', 0.55)
    p.body(red, skin, legs=black, arms=red)
    hd = p.head(skin, M('Lips_m', '#a06a60', 0.45), '#1e1612', iris='#2a1e16', age=50)
    p.hands(skin, cuff=M('Cuff_white', '#e8e4da', 0.7))
    J = p.J
    p.skirt('Lucco', red, J['waist'].y + 0.04, 0.06, 0.16, 0.27, depth=0.85)
    p.rigid([tube('collar', [(math.sin(a) * 0.07, J['neck'].y + 0.02, math.cos(a) * 0.07 - 0.01) for a in [math.tau * i / 24 for i in range(25)]], 0.014, M('Shirt_white', '#ecebe6', 0.7), segs=8, cap=False)], 'chest', 'Collar')
    hair(p, hd, 'cropped', '#1e1612')
    hc, s = hd['hc'], hd['R'] / 0.115
    cap = sphere('cap', 0.112 * s, hc(0, 0.05, -0.01), black, scale=(0.98, 1.0, 1.05), segs=28, rings=14)
    delete_verts(cap, lambda x, y, z: y < 0.035 * s)
    p.rigid([solidify(cap, 0.008)], 'head', 'Cap')
    p.shoes(M('Shoe_black', '#121212', 0.35))
    return p


def conductor():
    p = Person('conductor', height=1.76, build=1.12, age=58, belly=0.55)
    p.build_armature()
    navy = M('Uniform_navy', '#1a2236', 0.7)
    brass = M('Brass', '#c9a050', 0.3, 0.8)
    skin = M('Skin_cd', '#e2b898', 0.55)
    p.body(navy, skin, legs=navy, arms=navy)
    hd = p.head(skin, M('Lips_cd', '#a8706a', 0.45), '#8a8682', iris='#4a5a6a', age=58)
    p.hands(skin)
    J = p.J
    p.skirt('Jacket', navy, J['waist'].y, J['hips'].y - 0.16, 0.18, 0.2, depth=0.9)
    coat_details(p, buttons=brass, rows=2, n=5, spacing=0.055, x=0.055)
    wing_collar(p, M('Shirt_white', '#ecebe6', 0.7), tie=M('Tie_black', '#0e0e10', 0.5))
    hair(p, hd, 'short', '#8a8682')
    beard(p, hd, 'walrus', '#9a9692')
    hc, s = hd['hc'], hd['R'] / 0.115
    p.rigid([cyl('cap', 0.112 * s, 0.11 * s, 0.07 * s, hc(0, 0.1, 0.0), navy, segs=28),
             cyl('band', 0.114 * s, 0.114 * s, 0.022 * s, hc(0, 0.075, 0.0), M('Band_black', '#0e0e10', 0.4), segs=28, cap=False),
             box('peak', (0.15 * s, 0.01, 0.07 * s), hc(0, 0.06, 0.12), M('Peak', '#0a0a0a', 0.2), rot=(14, 0, 0)),
             sphere('badge', 0.014 * s, hc(0, 0.1, 0.113), brass, scale=(1.3, 1, 0.4), segs=10, rings=6)], 'head', 'Cap')
    p.shoes(M('Shoe_black', '#121212', 0.3))
    return p


def steward():
    p = Person('steward', height=1.64, build=1.0, female=True, age=44, belly=0.1)
    p.build_armature()
    black = M('Dress_black', '#17161a', 0.75)
    white = M('Linen_white', '#ece8de', 0.85)
    skin = M('Skin_s', '#ecc6aa', 0.55)
    p.body(black, skin, legs=black, arms=black)
    hd = p.head(skin, M('Lips_s', '#b07066', 0.45), '#6a4a30', iris='#3a2a1c')
    p.hands(skin, cuff=white)
    J = p.J
    p.skirt('Skirt', black, J['waist'].y, 0.25, 0.15, 0.25, depth=0.85)
    p.skirt('Apron', white, J['waist'].y - 0.02, 0.3, 0.2, 0.31, depth=0.85, front_only=True, over=p.last_skirt)
    p.rigid([cyl('apron_tie', 0.155, 0.155, 0.025, (0, J['waist'].y, 0.0), white, segs=32, cap=False)], 'hips', 'ApronTie')
    wing_collar(p, white)
    hair(p, hd, 'bun', '#6a4a30')
    p.shoes(M('Shoe_black', '#121212', 0.35), heel=0.03)
    return p


CAST = {'confucius': confucius, 'napoleon': napoleon, 'nightingale': nightingale, 'tesla': tesla,
        'cleopatra': cleopatra, 'machiavelli': machiavelli, 'conductor': conductor, 'steward': steward}


def preview(cast, out_dir):
    """Line the built characters up and render them standing and seated."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 40
    sc.render.resolution_x, sc.render.resolution_y = 1800, 760
    sc.view_settings.view_transform = 'AgX'
    blib.world_sky((0.06, 0.05, 0.05), 0.5)
    n = len(cast)
    for i, p in enumerate(cast):
        p.arm.location.x = (i - (n - 1) / 2) * 0.75
    blib.point_light('key', (-3.0, 3.0, 3.5), (1.0, 0.8, 0.6), 1400, 0.6)
    blib.point_light('fill', (3.5, 2.0, 3.0), (0.6, 0.7, 1.0), 600, 0.8)
    blib.point_light('rim', (0.0, 3.0, -3.0), (1.0, 0.85, 0.7), 800, 0.6)
    cd = bpy.data.cameras.new('cam')
    cd.lens = 40
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for name, act, frame in (('stand', 'idle', 0), ('sit', 'sit', 0)):
        for p in cast:
            p.arm.animation_data.action = bpy.data.actions.get(act) if False else None
            tr = p.arm.animation_data.nla_tracks
            for t in tr:
                t.mute = t.name != act
        sc.frame_set(frame)
        cam.location = blib.g(0, 1.0, 6.4)
        d = blib.g(0, 0.95 if name == 'stand' else 0.75, 0) - cam.location
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
        sc.render.filepath = os.path.join(out_dir, f'cast_{name}.png')
        bpy.ops.render.render(write_still=True)
        print('rendered', name)
    cd.lens = 70
    for i, p in enumerate(cast[:4]):
        pass


if __name__ == '__main__':
    built = []
    if PREVIEW:
        blib.reset()
    for cid in (ONLY or list(CAST)):
        if not PREVIEW:
            blib.reset()
        p = CAST[cid]()
        people.standard_actions(p)
        p.finish()
        if not PREVIEW:
            people.export(p, os.path.join(OUT, cid + '.glb'))
        built.append(p)
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        preview(built, PREVIEW)
