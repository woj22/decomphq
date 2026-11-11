"""The seated passenger: a skin-modifier body, a modelled head (jaw, nose, lidded eyes, brows, ears, lips) and a
wardrobe of nodes the game switches on per historical figure: Hair_*, Beard_*, Hat_* (children of Head) and
Costume_* (children of the root). Materials named Outfit / Accent / Skin / Lips / Hair / Iris are recoloured in game.

The model faces +z (Godot), sits on a bench whose cushion top is y = 0.51, with its hands on a table top at y = 0.77.
"""
import math
import os

from blender_lib import (box, cyl, deform, delete_verts, empty, export, mat, merge, place, reset, solidify,
                         sphere, skin_body, subsurf, torus, tube)

HEAD_PIVOT = (0.0, 1.11, -0.05)     # neck joint: the game turns the Head node about this
HC = (0.0, 1.235, -0.04)            # head centre
HR = 0.115                          # head radius


def hc(x, y, z):
    """Point relative to the head centre."""
    return (HC[0] + x, HC[1] + y, HC[2] + z)


def passenger(out_dir):
    reset()
    outfit = mat('Outfit', '#3a4a6a', 0.85)
    accent = mat('Accent', '#c9a04e', 0.6)
    skin = mat('Skin', '#e0b48e', 0.55)
    lips = mat('Lips', '#a8605a', 0.45)
    hair = mat('Hair', '#3a2618', 0.75)
    eyew = mat('EyeWhite', '#f2efe8', 0.15)
    iris = mat('Iris', '#3a2a1c', 0.1)
    gold = mat('Gold', '#d8ac4a', 0.28, 1.0)
    steel = mat('Steel', '#b8bcc4', 0.25, 1.0)
    white = mat('White', '#f2efe6', 0.8)
    black = mat('Black', '#141416', 0.55)
    leaf = mat('Leaf', '#4f7a2a', 0.6)
    petal = mat('Petal', '#d0243c', 0.6)
    petal2 = mat('Petal2', '#f2a81e', 0.6)
    fur = mat('Fur', '#6b5236', 1.0)
    leather = mat('Leather', '#5a3618', 0.55)
    pearl = mat('Pearl', '#f4eee2', 0.2)
    jade = mat('Jade', '#2f8a5a', 0.3)
    glassm = mat('Lens', '#9cc4d8', 0.05, 0.5)

    # ------------------------------------------------------------------ body
    V = [(0, 0.60, -0.12), (0, 0.76, -0.11), (0, 0.95, -0.07), (0, 1.1, -0.06),
         (-0.18, 1.07, -0.06), (-0.23, 0.84, 0.22), (-0.12, 0.815, 0.50),
         (0.18, 1.07, -0.06), (0.23, 0.84, 0.22), (0.12, 0.815, 0.50),
         (-0.1, 0.56, -0.04), (-0.11, 0.57, 0.36), (-0.11, 0.12, 0.42),
         (0.1, 0.56, -0.04), (0.11, 0.57, 0.36), (0.11, 0.12, 0.42)]
    E = [(0, 1), (1, 2), (2, 3), (2, 4), (4, 5), (5, 6), (2, 7), (7, 8), (8, 9),
         (0, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15)]
    R = [(0.17, 0.14), (0.15, 0.11), (0.18, 0.12), (0.075, 0.07),
         0.065, 0.052, 0.04, 0.065, 0.052, 0.04,
         0.09, 0.075, 0.05, 0.09, 0.075, 0.05]
    body = [skin_body('torso', V, E, R, outfit, subsurf=2),
            cyl('neck', 0.052, 0.048, 0.12, (0, 1.12, -0.05), skin, segs=16)]
    for s in (-1, 1):
        body.append(sphere('hand', 0.045, (s * 0.1, 0.80, 0.57), skin, scale=(0.95, 0.6, 1.45), rot=(0, s * 15, 0), segs=16, rings=10))
        body.append(sphere('thumb', 0.018, (s * 0.06, 0.805, 0.55), skin, scale=(1, 0.9, 1.9), rot=(0, s * -35, 0), segs=10, rings=6))
        body.append(cyl('cuff', 0.045, 0.045, 0.04, (s * 0.125, 0.815, 0.49), accent, rot=(-80, s * 12, 0), segs=14))
        body.append(box('shoe', (0.1, 0.07, 0.22), (s * 0.11, 0.035, 0.47), black, bevel=0.03))
    merge(body, 'Body')

    head = empty('Head', HEAD_PIVOT)

    # ------------------------------------------------------------------ head
    skull = sphere('skull', HR, HC, skin, scale=(0.9, 1.08, 1.0), segs=32, rings=20)

    def shape_head(x, y, z):
        t = max(0.0, -y / HR)                       # 0 at the equator, 1 at the chin
        k = 1 - 0.32 * t ** 1.4                     # narrow jaw
        x, z = x * k, z * (1 - 0.15 * t ** 2)
        if z > 0 and t > 0.4:
            z += 0.012 * (t - 0.4)                  # chin forward
        if z < 0:
            z *= 1.05                               # fuller back of the skull
        if y > 0.02 and z > 0.04:
            z -= 0.008 * (y / HR)                   # sloped forehead
        if z > 0:
            for ex in (-0.04, 0.04):                # eye sockets
                z -= 0.013 * math.exp(-((x - ex) ** 2 + (y - 0.01) ** 2 * 1.6) / 0.00035)
            z += 0.005 * math.exp(-((y - 0.04) ** 2) / 0.0002) * math.exp(-(x ** 2) / 0.004)  # brow ridge
        return x, y, z
    deform(skull, shape_head)
    parts = [skull]
    parts.append(tube('nose', [hc(0, 0.02, 0.098), hc(0, -0.01, 0.112), hc(0, -0.035, 0.122)], [0.011, 0.014, 0.017], skin, segs=12))
    parts.append(sphere('nose_tip', 0.017, hc(0, -0.037, 0.118), skin, scale=(1.25, 0.85, 1), segs=14, rings=8))
    for s in (-1, 1):
        ex = s * 0.04
        parts.append(sphere('eye', 0.0185, hc(ex, 0.011, 0.088), eyew, segs=18, rings=12))
        parts.append(sphere('iris', 0.0105, hc(ex, 0.011, 0.1035), iris, scale=(1, 1, 0.4), segs=16, rings=8))
        parts.append(sphere('pupil', 0.0052, hc(ex, 0.011, 0.1072), mat('Pupil', '#080808', 0.05), scale=(1, 1, 0.4), segs=10, rings=6))
        parts.append(sphere('glint', 0.0022, hc(ex + 0.004, 0.015, 0.1085), mat('Glint', '#ffffff', 0.1, emit='#ffffff', strength=2.0), segs=6, rings=4))
        lid = sphere('lid', 0.0205, hc(ex, 0.011, 0.088), skin, segs=18, rings=12)
        delete_verts(lid, lambda x, y, z: y < 0.009)          # upper lid: the top third of the eye
        parts.append(solidify(lid, 0.0025))
        low = sphere('lowlid', 0.0198, hc(ex, 0.011, 0.088), skin, segs=18, rings=12)
        delete_verts(low, lambda x, y, z: y > -0.012)
        parts.append(solidify(low, 0.002))
        parts.append(sphere('ear', 0.03, hc(s * 0.1, 0.0, -0.005), skin, scale=(0.4, 1.1, 0.75), segs=12, rings=8))
        parts.append(tube('brow', [hc(s * 0.016, 0.042, 0.104), hc(s * 0.04, 0.05, 0.103), hc(s * 0.064, 0.043, 0.093)], 0.0055, hair, segs=6))
    merge(parts, 'HeadMesh', parent=head)

    mouth = empty('Mouth', hc(0, -0.068, 0.104), parent=head)
    merge([sphere('upper_lip', 0.026, hc(0, -0.064, 0.104), lips, scale=(1, 0.28, 0.42), segs=16, rings=8),
           sphere('lower_lip', 0.022, hc(0, -0.074, 0.103), lips, scale=(1, 0.32, 0.45), segs=16, rings=8)], 'Lips', parent=mouth)

    # ------------------------------------------------------------------ hair
    def cap(name, keep_below=-0.05, face_line=0.065, r=HR * 1.08, extra=()):
        c = sphere(name, r, HC, hair, scale=(0.95, 1.1, 1.07), segs=40, rings=22)
        delete_verts(c, lambda x, y, z: (z > 0.02 and y < face_line - 3.0 * x * x + 0.012 * math.cos(x * 40)) or y < keep_below
                     or (abs(x) > 0.085 and -0.045 < y < 0.03 and -0.03 < z < 0.04))   # face, hairline, ears
        solidify(c, 0.016)
        return merge([c, *extra], name, parent=head)

    cap('Hair_Short')
    cap('Hair_Long', extra=[sphere('back', 0.1, hc(0, -0.09, -0.07), hair, scale=(1.2, 1.9, 0.6), segs=20, rings=12)])
    cap('Hair_Bob', keep_below=-0.11)
    cap('Hair_Bun', extra=[sphere('bun', 0.05, hc(0, 0.05, -0.12), hair, segs=16, rings=10),
                           tube('part', [hc(0, 0.135, 0.06), hc(0, 0.14, 0.0)], 0.004, mat('Skin', ''), segs=6)])
    cap('Hair_Braids', extra=[torus('braid', 0.098, 0.024, hc(0, 0.085, -0.01), hair, rot=(-14, 0, 0), segs=28, rsegs=8)])
    ring = sphere('Hair_Bald', HR * 1.05, HC, hair, scale=(0.94, 1.1, 1.05), segs=32, rings=18)
    delete_verts(ring, lambda x, y, z: y > 0.03 or (z > 0.02 and y < 0.05) or y < -0.05 or (abs(x) > 0.07 and y < -0.01 and z > -0.03))
    merge([solidify(ring, 0.012)], 'Hair_Bald', parent=head)
    curls = []
    for i in range(46):                                   # wild curly hair (Newton's own, or a natural wig)
        a = i * 2.39996
        yy = 0.12 - (i / 46) * 0.32
        rr = 0.11 + 0.03 * (i / 46)
        x, z = math.cos(a) * rr, math.sin(a) * rr
        if z > 0.02 and yy < 0.05:
            continue
        curls.append(sphere('curl', 0.042, hc(x * 0.95, yy, z * 0.95 - 0.02), hair, segs=12, rings=8))
    merge(curls, 'Hair_Curly', parent=head)

    # ------------------------------------------------------------------ beards
    def jaw(name, keep_above, mouth_gap=True, extra=()):
        b = sphere(name, HR * 1.08, HC, hair, scale=(0.9, 1.08, 1.0), segs=32, rings=20)
        deform(b, shape_head)
        delete_verts(b, lambda x, y, z: y > keep_above or z < -0.035
                     or (mouth_gap and abs(x) < 0.045 and y > -0.1 and z > 0)
                     or (name == 'Beard_Chin' and abs(x) < 0.06 and y > -0.085 and z > 0))   # Lincoln: no moustache
        solidify(b, 0.014)
        return merge([b, *extra], name, parent=head)
    jaw('Beard_Full', -0.02, extra=[sphere('long', 0.055, hc(0, -0.13, 0.05), hair, scale=(1.15, 1.35, 0.75), segs=18, rings=10)])
    jaw('Beard_Chin', -0.02)
    jaw('Beard_Short', -0.035)
    merge([tube('mous', [hc(-0.045, -0.07, 0.1), hc(-0.02, -0.056, 0.114), hc(0, -0.054, 0.117),
                         hc(0.02, -0.056, 0.114), hc(0.045, -0.07, 0.1)], [0.005, 0.009, 0.009, 0.009, 0.005], hair, segs=8)],
          'Beard_Moustache', parent=head)
    merge([tube('drooping', [hc(-0.05, -0.13, 0.085), hc(-0.04, -0.07, 0.105), hc(-0.015, -0.055, 0.116), hc(0.015, -0.055, 0.116),
                             hc(0.04, -0.07, 0.105), hc(0.05, -0.13, 0.085)], [0.004, 0.008, 0.009, 0.009, 0.008, 0.004], hair, segs=8),
           sphere('tuft', 0.018, hc(0, -0.115, 0.105), hair, scale=(1, 1.6, 0.8), segs=10, rings=8)], 'Beard_Droop', parent=head)
    merge([sphere('goatee', 0.022, hc(0, -0.112, 0.1), hair, scale=(1, 1.3, 0.8), segs=12, rings=8),
           tube('mous2', [hc(-0.03, -0.062, 0.106), hc(0, -0.054, 0.117), hc(0.03, -0.062, 0.106)], 0.006, hair, segs=6)],
          'Beard_Goatee', parent=head)

    # ------------------------------------------------------------------ hats
    top = HC[1] + HR * 1.08
    crown = [cyl('band', 0.105, 0.11, 0.05, hc(0, 0.1, -0.005), gold, segs=28, cap=False)]
    for i in range(8):
        a = math.tau * i / 8
        p = hc(math.sin(a) * 0.106, 0.15, math.cos(a) * 0.106 - 0.005)
        crown.append(cyl('spike', 0.016, 0.0, 0.06, p, gold, segs=6))
        crown.append(sphere('pearl', 0.008, (p[0], p[1] + 0.033, p[2]), pearl, segs=8, rings=6))
    crown.append(sphere('jewel', 0.012, hc(0, 0.1, 0.108), petal, segs=10, rings=6))
    merge(crown, 'Hat_Crown', parent=head)

    egypt = [cyl('diadem', 0.112, 0.112, 0.025, hc(0, 0.06, 0.0), gold, rot=(-8, 0, 0), segs=28, cap=False),
             tube('uraeus', [hc(0, 0.07, 0.112), hc(0, 0.1, 0.12), hc(0, 0.12, 0.112)], [0.008, 0.01, 0.012], gold, segs=8),
             sphere('cobra_hood', 0.016, hc(0, 0.13, 0.11), gold, scale=(1.3, 1.1, 0.5), segs=10, rings=6)]
    for i in range(10):
        egypt.append(sphere('bead', 0.009, hc(-0.1 + 0.022 * i, -0.115, -0.0 + 0.03 * math.sin(i / 9 * math.pi)), gold, segs=8, rings=6))
    merge(egypt, 'Hat_Egypt', parent=head)

    laurel = []
    for s in (-1, 1):
        for i in range(9):
            a = math.radians(-70 + i * 17) * s
            laurel.append(sphere('leaf', 0.022, hc(math.sin(a) * 0.112, 0.07 + i * 0.002, math.cos(a) * 0.112 - 0.02), leaf,
                                 scale=(0.45, 0.25, 1), rot=(30, math.degrees(a) + s * 50, 0), segs=10, rings=6))
    merge(laurel, 'Hat_Laurel', parent=head)

    merge([sphere('beret', 0.12, hc(0.02, 0.1, -0.01), mat('Beret', '#2a2238', 0.9), scale=(1.15, 0.38, 1.1), rot=(0, 0, -10), segs=24, rings=12),
           sphere('stalk', 0.008, hc(0.02, 0.15, 0), black, segs=6, rings=4)], 'Hat_Beret', parent=head)

    bic = sphere('bicorne', 0.2, hc(0, 0.12, -0.01), black, scale=(1.0, 0.45, 0.32), segs=28, rings=14)
    delete_verts(bic, lambda x, y, z: y < -0.01)
    merge([solidify(bic, 0.01), sphere('cockade', 0.022, hc(0.1, 0.15, 0.03), mat('Tricolour', '#c03030', 0.6), scale=(1, 1, 0.3), segs=12, rings=8),
           torus('gold_edge', 0.2, 0.004, hc(0, 0.115, -0.01), gold, scale=(1, 1, 0.32), segs=40, rsegs=4)], 'Hat_Bicorne', parent=head)

    merge([cyl('brim', 0.165, 0.165, 0.012, hc(0, 0.1, 0), black, segs=32),
           cyl('crown', 0.1, 0.108, 0.24, hc(0, 0.22, 0), black, segs=32),
           cyl('band', 0.103, 0.103, 0.03, hc(0, 0.12, 0), mat('Band', '#2a2a32', 0.4), segs=32, cap=False)], 'Hat_TopHat', parent=head)

    bowl = sphere('bowler', 0.112, hc(0, 0.09, 0), black, scale=(1, 0.95, 1.05), segs=28, rings=14)
    delete_verts(bowl, lambda x, y, z: y < -0.005)
    merge([bowl, torus('brim', 0.135, 0.016, hc(0, 0.09, 0), black, scale=(1, 0.5, 1.08), segs=32, rsegs=8)], 'Hat_Bowler', parent=head)

    merge([torus('fur_brim', 0.11, 0.035, hc(0, 0.08, 0), fur, segs=28, rsegs=10),
           cyl('cone', 0.115, 0.03, 0.17, hc(0, 0.17, 0), mat('Felt', '#7a1f1f', 0.8), segs=24),
           sphere('knob', 0.02, hc(0, 0.26, 0), gold, segs=10, rings=6)], 'Hat_Fur', parent=head)

    wig = sphere('wig', HR * 1.12, HC, white, scale=(0.96, 1.08, 1.05), segs=32, rings=18)
    delete_verts(wig, lambda x, y, z: (z > 0.03 and y < 0.06) or y < -0.03)
    wig_parts = [solidify(wig, 0.012)]
    for s in (-1, 1):
        for k in range(2):
            wig_parts.append(cyl('roll', 0.022, 0.022, 0.07, hc(s * 0.115, 0.0 - k * 0.045, 0.0), white, rot=(90, 0, 0), segs=14))
    wig_parts += [tube('queue', [hc(0, -0.02, -0.12), hc(0, -0.1, -0.13), hc(0, -0.17, -0.12)], [0.02, 0.016, 0.01], white, segs=10),
                  torus('ribbon', 0.02, 0.008, hc(0, -0.05, -0.128), black, rot=(0, 0, 90), segs=12, rsegs=6)]
    merge(wig_parts, 'Hat_Wig', parent=head)

    flowers = []
    for i, (a, m) in enumerate([(-50, petal), (-20, petal2), (10, petal), (40, mat('Petal3', '#e0508a', 0.6)), (70, petal2)]):
        r = math.radians(a)
        c = hc(math.sin(r) * 0.09, 0.115 - abs(a) * 0.0006, math.cos(r) * 0.03 - 0.02)
        for k in range(5):
            b = math.tau * k / 5
            flowers.append(sphere('petal', 0.022, (c[0] + math.cos(b) * 0.018, c[1] + math.sin(b) * 0.018, c[2] + 0.02), m,
                                  scale=(1, 1, 0.45), segs=10, rings=6))
        flowers.append(sphere('centre', 0.01, (c[0], c[1], c[2] + 0.028), petal2, segs=8, rings=6))
        flowers.append(sphere('leaf', 0.02, (c[0] + 0.02, c[1] - 0.025, c[2]), leaf, scale=(0.5, 1, 0.3), segs=8, rings=6))
    merge(flowers, 'Hat_Flowers', parent=head)

    scarf_m = mat('Headscarf', '#a8442e', 0.85)
    sc = sphere('scarf', HR * 1.1, HC, scarf_m, scale=(0.95, 1.1, 1.08), segs=32, rings=18)
    delete_verts(sc, lambda x, y, z: (z > 0.04 and y < 0.07) or y < -0.02)
    merge([solidify(sc, 0.012), sphere('knot', 0.03, hc(0, 0.14, 0.06), scarf_m, scale=(1.3, 0.8, 0.8), segs=12, rings=8)], 'Hat_Headscarf', parent=head)

    merge([sphere('ncap', 0.1, hc(0, 0.09, -0.04), white, scale=(1.1, 0.6, 1.0), segs=20, rings=10),
           box('frill', (0.2, 0.03, 0.02), hc(0, 0.09, 0.06), white, bevel=0.008)], 'Hat_NurseCap', parent=head)

    merge([box('scholar', (0.16, 0.08, 0.15), hc(0, 0.135, -0.01), black, bevel=0.02),
           box('board', (0.2, 0.012, 0.24), hc(0, 0.18, -0.01), black, bevel=0.004),
           cyl('pin', 0.006, 0.006, 0.2, hc(0, 0.14, -0.01), gold, rot=(0, 0, 90), segs=6)], 'Hat_Scholar', parent=head)

    av = sphere('aviator', HR * 1.1, HC, leather, scale=(0.95, 1.1, 1.06), segs=32, rings=18)
    delete_verts(av, lambda x, y, z: (z > 0.045 and y < 0.07 and y > -0.08) or y < -0.1 or (z > 0.06 and y < -0.02))
    gog = [solidify(av, 0.012)]
    for s in (-1, 1):
        gog.append(torus('goggle', 0.026, 0.009, hc(s * 0.04, 0.11, 0.09), mat('Chrome', '#9aa0a8', 0.2, 1.0), rot=(70, 0, 0), segs=16, rsegs=6))
        gog.append(cyl('lens', 0.024, 0.024, 0.006, hc(s * 0.04, 0.11, 0.09), glassm, rot=(70, 0, 0), segs=16))
    gog.append(tube('strap', [hc(-0.07, 0.1, 0.07), hc(0, 0.12, 0.1), hc(0.07, 0.1, 0.07)], 0.006, leather, segs=6))
    merge(gog, 'Hat_Aviator', parent=head)

    # ------------------------------------------------------------------ costume pieces (children of the root)
    # tailored coat: lapels, shirtfront, buttons
    coat = [sphere('shirtfront', 0.045, (0, 1.02, 0.06), mat('Shirt', '#e9e3d6', 0.8), scale=(1, 1.45, 0.25), segs=14, rings=10)]
    for s in (-1, 1):
        coat.append(tube('lapel', [(s * 0.05, 1.09, 0.045), (s * 0.075, 1.0, 0.085), (s * 0.04, 0.88, 0.095)], [0.012, 0.016, 0.008], mat('Lapel', '#22232a', 0.6), segs=8))
    for i in range(4):
        coat.append(sphere('button', 0.011, (0.035, 0.94 - i * 0.065, 0.1 - i * 0.003), accent, scale=(1, 1, 0.5), segs=8, rings=6))
    merge(coat, 'Costume_Coat')

    merge([cyl('bow_l', 0.0, 0.025, 0.04, (-0.02, 1.07, 0.06), black, rot=(0, 0, 90), segs=8),
           cyl('bow_r', 0.025, 0.0, 0.04, (0.02, 1.07, 0.06), black, rot=(0, 0, 90), segs=8),
           sphere('knot', 0.009, (0, 1.07, 0.065), black, segs=8, rings=6)], 'Costume_Bowtie')

    merge([sphere('cravat', 0.035, (0, 1.06, 0.06), white, scale=(1.2, 1, 0.8), segs=12, rings=8),
           sphere('fall', 0.03, (0, 1.0, 0.075), white, scale=(1, 1.8, 0.5), segs=12, rings=8)], 'Costume_Cravat')

    ruff = []
    for i in range(26):
        a = math.tau * i / 26
        ruff.append(sphere('pleat', 0.04, (math.sin(a) * 0.09, 1.11, math.cos(a) * 0.08 - 0.06), white, scale=(0.55, 0.75, 1), rot=(0, math.degrees(a), 0), segs=10, rings=8))
    merge(ruff, 'Costume_Ruff')

    merge([cyl('usekh', 0.21, 0.065, 0.06, (0, 1.06, -0.05), gold, segs=32, cap=False),
           cyl('usekh_band', 0.17, 0.11, 0.022, (0, 1.073, -0.05), mat('Lapis', '#1f4fa8', 0.3), segs=32, cap=False),
           cyl('usekh_band2', 0.215, 0.205, 0.012, (0, 1.03, -0.05), mat('Carnelian', '#b8402a', 0.3), segs=32, cap=False)], 'Costume_Usekh')

    toga_pts = [(0.17, 1.08, -0.05), (0.08, 1.02, 0.12), (-0.08, 0.86, 0.13), (-0.17, 0.7, 0.07)]
    merge([tube('toga', toga_pts, [0.06, 0.07, 0.07, 0.06], white, segs=14),
           tube('stripe', [(p[0], p[1] - 0.05, p[2] + 0.02) for p in toga_pts], 0.015, mat('Purple', '#5a1f6a', 0.7), segs=8),
           sphere('fibula', 0.018, (0.16, 1.07, 0.0), gold, scale=(1, 1, 0.5), segs=10, rings=6)], 'Costume_Toga')

    ep = []
    for s in (-1, 1):
        ep.append(sphere('epaulette', 0.06, (s * 0.2, 1.08, -0.06), gold, scale=(1, 0.3, 1), segs=16, rings=8))
        for k in range(9):
            a = math.radians(-60 + k * 15)
            ep.append(cyl('fringe', 0.006, 0.006, 0.05, (s * (0.2 + math.sin(a) * 0.058 * s), 1.05, -0.06 + math.cos(a) * 0.058), gold, segs=5))
        for i in range(5):
            ep.append(sphere('button', 0.01, (s * 0.06, 1.0 - i * 0.055, 0.09), gold, scale=(1, 1, 0.5), segs=8, rings=6))
    ep.append(sphere('lapels_white', 0.04, (0, 0.98, 0.065), mat('Shirt', ''), scale=(1.0, 1.6, 0.25), segs=12, rings=8))
    ep.append(tube('sash', [(-0.17, 1.03, 0.0), (0.0, 0.85, 0.13), (0.16, 0.67, 0.05)], 0.02, mat('Sash', '#b0262a', 0.5), segs=10))
    merge(ep, 'Costume_Military')

    armour = [sphere('breastplate', 0.17, (0, 0.93, -0.05), steel, scale=(1.05, 1.05, 0.82), segs=24, rings=14)]
    for s in (-1, 1):
        armour.append(sphere('pauldron', 0.07, (s * 0.19, 1.06, -0.06), steel, scale=(1, 0.65, 1), segs=16, rings=10))
    armour.append(tube('fleur', [(0, 1.0, 0.09), (0, 0.9, 0.09)], 0.008, gold, segs=6))
    armour.append(tube('fleur_x', [(-0.03, 0.97, 0.092), (0.03, 0.97, 0.092)], 0.006, gold, segs=6))
    merge(armour, 'Costume_Armour')

    merge([box('apron', (0.16, 0.22, 0.015), (0, 0.9, 0.075), mat('Apron', '#e6e2d8', 0.9), bevel=0.012, rot=(-10, 0, 0)),
           tube('collar', [(-0.07, 1.08, 0.0), (0, 1.08, 0.07), (0.07, 1.08, 0.0)], 0.014, white, segs=8)], 'Costume_Apron')

    merge([torus('scarf', 0.07, 0.03, (0, 1.08, -0.05), white, segs=20, rsegs=8),
           tube('tail', [(0.04, 1.06, 0.03), (0.07, 0.96, 0.09), (0.06, 0.85, 0.1)], [0.03, 0.028, 0.02], white, segs=10)], 'Costume_Scarf')

    shawl_m = mat('Shawl', '#6a5a48', 1.0)
    shawl = [sphere('shawl_knot', 0.03, (0, 0.95, 0.1), shawl_m, scale=(1.2, 1, 0.8), segs=12, rings=8)]
    for s in (-1, 1):   # draped over each shoulder from the back, crossing at the chest
        shawl.append(tube('drape', [(s * 0.12, 1.1, -0.16), (s * 0.2, 1.09, -0.05), (s * 0.15, 1.04, 0.07), (s * 0.05, 0.96, 0.1), (-s * 0.02, 0.92, 0.1)],
                          [0.04, 0.05, 0.045, 0.035, 0.025], shawl_m, segs=12))
    merge(shawl, 'Costume_Shawl')

    beads = [sphere('bead', 0.016, (math.sin(math.tau * i / 22) * 0.085, 1.06 - 0.03 * max(0, math.cos(math.tau * i / 22)),
                                    math.cos(math.tau * i / 22) * 0.1 - 0.04), jade, segs=8, rings=6) for i in range(22)]
    merge(beads, 'Costume_Beads')

    pearls = [sphere('pearl', 0.01, (math.sin(math.tau * i / 30) * 0.09, 1.04 - 0.08 * max(0, math.cos(math.tau * i / 30)) ** 2,
                                     math.cos(math.tau * i / 30) * 0.105 - 0.04), pearl, segs=8, rings=6) for i in range(30)]
    merge(pearls, 'Costume_Pearls')

    merge([torus('fur_collar', 0.12, 0.05, (0, 1.06, -0.06), fur, segs=24, rsegs=10)], 'Costume_FurCollar')

    robe = []
    for s in (-1, 1):
        robe.append(tube('robe_collar', [(s * 0.075, 1.11, -0.03), (s * 0.04, 1.02, 0.085), (-s * 0.012, 0.9, 0.1)], 0.016, accent, segs=8))
    robe.append(tube('robe_belt', [(-0.16, 0.8, 0.02), (0, 0.8, 0.13), (0.16, 0.8, 0.02)], 0.02, accent, segs=8))
    merge(robe, 'Costume_Robe')

    merge([tube('neckline', [(-0.1, 1.07, -0.02), (0, 1.04, 0.075), (0.1, 1.07, -0.02)], 0.012, accent, segs=8),
           torus('belt', 0.16, 0.012, (0, 0.78, -0.08), accent, scale=(1, 1, 0.9), segs=28, rsegs=6)], 'Costume_Dress')

    export(os.path.join(out_dir, 'passenger.glb'))
