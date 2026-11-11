"""Builds every 3D model for Last Carriage with Blender (bpy) and exports glTF binaries into assets/models/.

    python3 last-carriage/tools/build_models.py      (needs `pip install bpy`, Blender 5.x as a module)

Outputs: carriage.glb, passenger.glb (one rig with every hair/beard/hat/costume piece as its own node; the
game shows the pieces each historical figure needs and recolours the Outfit/Accent/Skin/Hair materials),
pine_a.glb, pine_b.glb, pine_c.glb, lamp_post.glb.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_lib import (box, cyl, deform, delete_verts, empty, export, g, mat, merge, place, reset,  # noqa: E402
                         solidify, sphere, skin_body, subsurf, torus, tube)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'models')
os.makedirs(OUT, exist_ok=True)

L, W = 16.0, 3.0          # carriage length (z -8..8) and width (x -1.5..1.5)
WALL_TOP = 2.05           # where the arched roof starts
ROOF_RISE = 0.45
WIN_Y0, WIN_Y1 = 0.95, 1.85
WINDOWS = [-6, -4, -2, 0, 2, 4, 6]   # window centres (the table bays sit at -4, 0, 4)
WIN_W = 1.78
BAYS = [-4, 0, 4]


# =============================================================== carriage
def carriage():
    reset()
    wood = mat('Wood', '#6b4226', 0.55)
    wood_dk = mat('WoodDark', '#3b2416', 0.5)
    brass = mat('Brass', '#c9a04e', 0.32, 1.0)
    uph = mat('Upholstery', '#7a1f2b', 0.95)
    cream = mat('Cream', '#e7dcc2', 0.8)
    carpet = mat('Carpet', '#3d2a35', 1.0)
    runner = mat('Runner', '#6a2a36', 1.0)
    curtain = mat('Curtain', '#2f4a3c', 0.9)
    glass = mat('Glass', '#b9d3f0', 0.05, alpha=0.2)
    glow = mat('LampGlow', '#fff1d0', 0.4, emit='#ffe2b0', strength=6.0)
    shade = mat('LampShade', '#f2d9a6', 0.8, emit='#ffc26a', strength=2.5)
    linen = mat('Linen', '#f1ece0', 0.9)
    leather = mat('Leather', '#6e3d1f', 0.6)
    leather2 = mat('Leather2', '#2f3b4a', 0.6)
    ceramic = mat('Ceramic', '#f3f1ea', 0.25)
    black = mat('Black', '#121214', 0.5)
    tea = mat('Tea', '#5a2d10', 0.1)

    parts = []
    P = parts.append

    # floor + runner
    P(box('floor', (W, 0.06, L), (0, -0.03, 0), carpet))
    P(box('runner', (0.72, 0.012, L - 0.2), (0, 0.006, 0), runner, bevel=0.004, seg=1))

    # walls, both sides
    for s in (-1, 1):
        x = s * W / 2
        P(box('lower', (0.08, WIN_Y0, L), (x, WIN_Y0 / 2, 0), wood))
        # raised panel mouldings on the lower wall, one per window bay
        for wz in WINDOWS:
            P(box('panel', (0.02, 0.6, 1.5), (x - s * 0.045, 0.5, wz), wood, bevel=0.012))
            P(box('panel_in', (0.012, 0.46, 1.34), (x - s * 0.06, 0.5, wz), wood_dk, bevel=0.006, seg=1))
        P(box('dado', (0.16, 0.05, L), (x - s * 0.06, WIN_Y0 + 0.01, 0), wood_dk, bevel=0.015))           # window sill
        P(box('kick', (0.03, 0.1, L), (x - s * 0.05, 0.05, 0), wood_dk))
        # pillars between windows and the end pieces
        edges = [-L / 2] + [z for w in WINDOWS for z in (w - WIN_W / 2, w + WIN_W / 2)] + [L / 2]
        for a, b in zip(edges[0::2], edges[1::2]):
            P(box('pillar', (0.1, WIN_Y1 - WIN_Y0, b - a), (x, (WIN_Y0 + WIN_Y1) / 2, (a + b) / 2), cream))
        # window frames (rounded look from bevels) and glass
        for wz in WINDOWS:
            fy = (WIN_Y0 + WIN_Y1) / 2
            for dz in (-1, 1):
                P(box('jamb', (0.12, WIN_Y1 - WIN_Y0, 0.05), (x - s * 0.01, fy, wz + dz * (WIN_W / 2 - 0.02)), wood_dk, bevel=0.012))
            for yy in (WIN_Y0 + 0.03, WIN_Y1 - 0.025):
                P(box('rail', (0.12, 0.05, WIN_W), (x - s * 0.01, yy, wz), wood_dk, bevel=0.012))
            P(box('mullion', (0.03, 0.03, WIN_W - 0.04), (x, WIN_Y1 - 0.24, wz), wood_dk, bevel=0.008))  # top-light bar
            # tied-back curtains at both sides of every window, with folds
            for dz in (-1, 1):
                zc = wz + dz * (WIN_W / 2 + 0.02)
                if s < 0 and abs(zc - 0.8) < 0.4:
                    continue                          # keep the player's window seat clear
                pts, radii = [], []
                for i in range(13):
                    t = i / 12
                    y = WIN_Y1 + 0.02 - t * (WIN_Y1 - WIN_Y0 - 0.05)
                    tie = math.exp(-((t - 0.55) / 0.12) ** 2)        # pinched where the tie-back is
                    pts.append((x - s * 0.1, y, zc - dz * 0.05 * (1 - tie) * math.sin(t * math.pi)))
                    radii.append(0.075 - 0.045 * tie + 0.02 * t)
                c = tube('curtain', pts, radii, curtain, segs=14)
                deform(c, lambda X, Y, Z, s=s: (X + s * 0.012 * math.sin(Z * 90 + Y * 3), Y, Z))  # vertical pleats
                P(c)
                P(torus('tieback', 0.042, 0.008, (x - s * 0.1, WIN_Y1 - 0.55 * (WIN_Y1 - WIN_Y0), zc), brass, rot=(90, 0, 0), segs=16, rsegs=6))
            # roller blind, rolled up
            P(cyl('blind', 0.035, 0.035, WIN_W - 0.06, (x - s * 0.09, WIN_Y1 - 0.06, wz), linen, rot=(90, 0, 0), segs=12))
        # glass panes: one pane per window
        for wz in WINDOWS:
            P(box('pane', (0.01, WIN_Y1 - WIN_Y0 - 0.06, WIN_W - 0.06), (x + s * 0.02, (WIN_Y0 + WIN_Y1) / 2, wz), glass))
        P(box('upper', (0.08, WALL_TOP - WIN_Y1, L), (x, (WIN_Y1 + WALL_TOP) / 2, 0), cream))
        P(cyl('curtain_rod', 0.012, 0.012, L, (x - s * 0.1, WIN_Y1 + 0.03, 0), brass, rot=(90, 0, 0), segs=10))
        # luggage rack: two brass rails, brackets at each pillar, slats
        rx0, rx1 = x - s * 0.08, x - s * 0.42
        for rx in (rx0 + -s * 0.02, rx1):
            P(cyl('rack_rail', 0.014, 0.014, L - 0.3, (rx, 1.97, 0), brass, rot=(90, 0, 0), segs=10))
        for z in range(-7, 8, 2):
            P(tube('bracket', [(x - s * 0.05, 2.12, z), (rx1, 1.97, z), (x - s * 0.05, 1.86, z)], 0.012, brass, segs=8))
        for i in range(int((L - 0.4) / 0.12)):
            z = -L / 2 + 0.25 + i * 0.12
            P(cyl('slat', 0.006, 0.006, 0.34, ((rx0 + rx1) / 2, 1.965, z), brass, rot=(0, 0, 90), segs=6, smooth=False))

    # arched roof with ribs, cove light strips and globe lamps
    N = 24
    roof_pts = [(math.cos(math.pi * i / N) * W / 2, WALL_TOP + math.sin(math.pi * i / N) * ROOF_RISE) for i in range(N + 1)]
    import bmesh
    bm = bmesh.new()
    rows = []
    for z in (-L / 2, L / 2):
        rows.append([bm.verts.new(g(x, y, z)) for x, y in roof_pts])
    for i in range(N):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    from blender_lib import _obj
    roof = _obj('roof', bm, cream, smooth=True)
    P(roof)
    for z in range(-7, 8, 2):
        P(tube('rib', [(x * 0.985, y - 0.01, z) for x, y in roof_pts], 0.018, wood_dk, segs=6, cap=False))
    for s in (-1, 1):
        P(box('cove', (0.1, 0.03, L - 0.4), (s * 1.3, WALL_TOP + 0.09, 0), glow))
        P(box('cornice', (0.14, 0.06, L), (s * 1.42, WALL_TOP + 0.02, 0), wood_dk, bevel=0.015))
    for z in range(-6, 7, 2):
        P(cyl('rose', 0.07, 0.05, 0.05, (0, WALL_TOP + ROOF_RISE - 0.03, z), brass, segs=16))
        P(sphere('globe', 0.11, (0, WALL_TOP + ROOF_RISE - 0.15, z), glow, segs=20, rings=12))
        P(torus('globe_ring', 0.08, 0.012, (0, WALL_TOP + ROOF_RISE - 0.07, z), brass, segs=20, rsegs=6))

    # end walls with a door, door window and brass fittings
    for e in (-1, 1):
        z = e * L / 2
        for s in (-1, 1):
            P(box('endwall', (1.05, WALL_TOP + ROOF_RISE, 0.08), (s * 0.925, (WALL_TOP + ROOF_RISE) / 2, z), wood))
            P(box('endpanel', (0.8, 0.9, 0.02), (s * 0.925, 0.6, z - e * 0.05), wood_dk, bevel=0.01))
            P(box('endpanel_up', (0.8, 0.7, 0.02), (s * 0.925, 1.5, z - e * 0.05), wood_dk, bevel=0.01))
        P(box('lintel', (0.8, 0.5, 0.08), (0, 2.25, z), wood))
        P(box('door', (0.76, 1.98, 0.05), (0, 0.99, z - e * 0.01), wood_dk, bevel=0.01))
        P(box('door_win', (0.42, 0.55, 0.02), (0, 1.45, z - e * 0.04), glass))
        P(box('door_win_frame', (0.5, 0.63, 0.015), (0, 1.45, z - e * 0.035), brass, bevel=0.005))
        P(sphere('knob', 0.03, (0.28, 1.0, z - e * 0.07), brass))
        P(box('kick', (0.7, 0.2, 0.01), (0, 0.12, z - e * 0.04), brass))

    # bays: double seats facing each other over a table, both sides of the aisle
    for bz in BAYS:
        for s in (-1, 1):
            xc = s * 0.87
            for face in (-1, 1):                     # -1 = faces -z (row at +z), +1 = faces +z
                z = bz - face * 0.82
                base = box('seat_base', (1.02, 0.36, 0.5), (xc, 0.18, z), wood_dk, bevel=0.02)
                P(base)
                back_z = z - face * 0.3
                P(box('seat_shell', (1.06, 1.05, 0.08), (xc, 0.83, back_z - face * 0.05), wood, bevel=0.025))
                for k in (-1, 1):
                    sx = xc + k * 0.255
                    c = subsurf(box('cushion', (0.48, 0.14, 0.5), (sx, 0.44, z + face * 0.01), uph, bevel=0.04, seg=1), 1)
                    P(c)
                    b = subsurf(box('back', (0.47, 0.72, 0.12), (sx, 0.88, back_z), uph, bevel=0.045, seg=1, rot=(face * -8, 0, 0)), 1)
                    P(b)
                    # buttoned tufting
                    for by in (0.72, 0.95):
                        P(sphere('button', 0.012, (sx, by, back_z + face * 0.07), uph, segs=8, rings=6))
                    P(box('antimacassar', (0.3, 0.16, 0.01), (sx, 1.17, back_z + face * 0.09), linen, rot=(face * -8, 0, 0)))
                P(box('armrest', (0.07, 0.08, 0.46), (s * 0.33 if s > 0 else -0.33, 0.6, z), wood, bevel=0.025))
            # table
            P(box('table', (1.05, 0.045, 0.74), (s * 0.9, 0.745, bz), wood, bevel=0.018))
            P(box('table_rim', (1.07, 0.02, 0.76), (s * 0.9, 0.715, bz), wood_dk, bevel=0.008))
            P(cyl('table_leg', 0.035, 0.035, 0.72, (s * 0.55, 0.36, bz), brass, segs=12))
            P(cyl('table_foot', 0.14, 0.12, 0.02, (s * 0.55, 0.01, bz), brass, segs=20))
            P(box('table_bracket', (0.06, 0.12, 0.3), (s * 1.43, 0.68, bz), brass, bevel=0.01))
            # table lamp by the window
            lx = s * 1.27
            P(cyl('lamp_base', 0.05, 0.04, 0.02, (lx, 0.775, bz), brass, segs=16))
            P(cyl('lamp_stem', 0.008, 0.008, 0.2, (lx, 0.875, bz), brass, segs=8))
            P(cyl('lamp_shade', 0.075, 0.045, 0.09, (lx, 1.0, bz), shade, segs=20, cap=False))
            P(sphere('lamp_bulb', 0.02, (lx, 0.985, bz), glow, segs=10, rings=6))

    # tea for four on our table (left side, bay 0), a teapot and a folded newspaper
    for (cx, cz) in ((-1.1, 0.24), (-0.66, 0.24), (-0.66, -0.24), (-1.1, -0.24)):
        P(cyl('saucer', 0.055, 0.06, 0.008, (cx, 0.772, cz), ceramic, segs=20))
        P(cyl('cup', 0.035, 0.042, 0.055, (cx, 0.805, cz), ceramic, segs=18, cap=True))
        P(cyl('tea', 0.039, 0.039, 0.002, (cx, 0.828, cz), tea, segs=18))
        P(torus('handle', 0.015, 0.004, (cx + 0.045, 0.805, cz), ceramic, rot=(90, 0, 0), segs=10, rsegs=5))
    P(sphere('teapot', 0.08, (-0.88, 0.84, -0.02), ceramic, scale=(1, 0.8, 1)))
    P(sphere('lid', 0.035, (-0.88, 0.9, -0.02), ceramic, scale=(1, 0.5, 1)))
    P(tube('spout', [(-0.81, 0.82, -0.02), (-0.76, 0.86, -0.02), (-0.73, 0.89, -0.02)], [0.015, 0.011, 0.008], ceramic, segs=8))
    P(torus('pot_handle', 0.04, 0.008, (-0.96, 0.85, -0.02), ceramic, rot=(90, 0, 0), segs=12, rsegs=5))
    P(box('newspaper', (0.22, 0.012, 0.3), (-0.88, 0.773, 0.2), linen, rot=(0, 12, 0)))

    # luggage on the racks: suitcases with straps, a hat box
    random.seed(4)
    for (x, z, w, h, d, m) in [(-1.23, -0.4, 0.6, 0.16, 0.36, leather), (-1.23, 0.55, 0.5, 0.2, 0.32, leather2),
                               (1.23, -3.6, 0.55, 0.18, 0.34, leather), (1.25, 4.3, 0.45, 0.14, 0.3, leather2),
                               (-1.24, 4.6, 0.6, 0.18, 0.35, leather), (1.24, 0.3, 0.5, 0.16, 0.34, leather)]:
        y = 1.99 + h / 2
        P(box('case', (d, h, w), (x, y, z), m, bevel=0.02))
        for dz in (-w / 4, w / 4):
            P(box('strap', (d + 0.006, h + 0.006, 0.03), (x, y, z + dz), mat('Strap', '#3a2414', 0.5)))
        P(tube('case_handle', [(x, y + h / 2, z - 0.06), (x, y + h / 2 + 0.04, z), (x, y + h / 2, z + 0.06)], 0.01, m, segs=6))
    P(cyl('hatbox', 0.16, 0.16, 0.2, (1.24, 2.09, -0.5), mat('Hatbox', '#c9b28a', 0.7), segs=24))
    # coat hooks with a coat and a scarf hanging on the pillars of our bay
    for z in (-1, 3):
        P(tube('hook', [(1.45, 1.75, z), (1.38, 1.75, z), (1.36, 1.8, z)], 0.008, brass, segs=6))
    P(tube('coat', [(1.4, 1.72, -1.0), (1.38, 1.4, -1.0), (1.38, 1.1, -1.0)], [0.06, 0.13, 0.15], mat('Coat', '#2a2c33', 0.9), segs=14))
    P(tube('scarf', [(1.38, 1.74, 3.0), (1.36, 1.5, 3.0), (1.37, 1.3, 3.0)], [0.03, 0.035, 0.03], mat('Scarf', '#8a2a2a', 0.9), segs=10))

    # heater grilles under the seats along the walls
    for s in (-1, 1):
        for bz in BAYS:
            P(box('heater', (0.04, 0.12, 2.2), (s * 1.44, 0.1, bz), black, bevel=0.01))

    merge_by_material(parts, keep={'Glass': 'Windows'})
    export(os.path.join(OUT, 'carriage.glb'))


def merge_by_material(objs, keep):
    """One mesh per material (the Glass one gets a fixed name so the game can give it the frost shader)."""
    groups = {}
    for o in objs:
        groups.setdefault(o.data.materials[0].name if o.data.materials else 'none', []).append(o)
    for name, group in groups.items():
        merge(group, keep.get(name, 'Carriage_' + name))


# =============================================================== outside
def pine(name, seed, height):
    reset()
    random.seed(seed)
    needles = mat('Needles', '#1e3324', 0.95)
    snow = mat('Snow', '#e9eef5', 0.6)
    bark = mat('Bark', '#3b2a1e', 1.0)
    parts = [cyl('trunk', 0.12, 0.06, height * 0.4, (0, height * 0.2, 0), bark, segs=8)]
    tiers = 5
    for i in range(tiers):
        t = i / tiers
        r = (1 - t) * height * 0.28 + 0.15
        y0 = height * (0.18 + t * 0.72)
        h = height * 0.32 * (1 - t * 0.4)
        c = cyl('tier', r, 0.02, h, (0, y0 + h / 2, 0), needles, segs=12, cap=True)
        # ragged hem: alternate the bottom ring in and out, droop the tips
        deform(c, lambda x, y, z, r=r, h=h: (x * (1 + 0.18 * math.sin(math.atan2(z, x) * 6)) if y < -h / 2 + 0.01 else x,
                                                y - (0.06 if y < -h / 2 + 0.01 and math.sin(math.atan2(z, x) * 6) > 0 else 0),
                                                z * (1 + 0.18 * math.sin(math.atan2(z, x) * 6)) if y < -h / 2 + 0.01 else z))
        parts.append(c)
        sc = cyl('snowcap', r * 0.82, 0.02, h * 0.55, (0.02, y0 + h * 0.62, -0.01), snow, segs=12)
        deform(sc, lambda x, y, z: (x * (1 + 0.12 * math.sin(math.atan2(z, x) * 5 + 1)), y, z * (1 + 0.12 * math.sin(math.atan2(z, x) * 5 + 1))))
        parts.append(sc)
    parts.append(sphere('mound', 0.6, (0, 0, 0), snow, scale=(1.4, 0.35, 1.3), segs=16, rings=8))
    merge(parts, 'Pine')
    export(os.path.join(OUT, name + '.glb'))


def lamp_post():
    reset()
    iron = mat('Iron', '#1b1d22', 0.5, 0.6)
    glow = mat('LampGlow', '#fff1d0', 0.4, emit='#ffd38a', strength=8.0)
    snow = mat('Snow', '#e9eef5', 0.6)
    parts = [cyl('post', 0.07, 0.05, 3.2, (0, 1.6, 0), iron, segs=12),
             cyl('foot', 0.14, 0.1, 0.4, (0, 0.2, 0), iron, segs=12),
             tube('arm', [(0, 3.0, 0), (0.25, 3.15, 0), (0.45, 3.1, 0)], 0.025, iron, segs=8),
             cyl('cage', 0.12, 0.16, 0.3, (0.45, 2.85, 0), glow, segs=6),
             cyl('hood', 0.2, 0.05, 0.12, (0.45, 3.06, 0), iron, segs=6),
             cyl('hood_snow', 0.17, 0.04, 0.06, (0.45, 3.14, 0), snow, segs=6),
             sphere('drift', 0.5, (0, 0, 0), snow, scale=(1.3, 0.3, 1.1), segs=14, rings=8)]
    merge(parts, 'LampPost')
    export(os.path.join(OUT, 'lamp_post.glb'))


if __name__ == '__main__':
    which = sys.argv[1:] or ['carriage', 'passenger', 'outside']
    if 'carriage' in which:
        carriage()
    if 'passenger' in which:
        from build_passenger import passenger
        passenger(OUT)
    if 'outside' in which:
        pine('pine_a', 1, 6.0)
        pine('pine_b', 2, 4.2)
        pine('pine_c', 3, 8.0)
        lamp_post()
