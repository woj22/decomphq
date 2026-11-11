"""Architecture + prop builders. Every builder works in a cell-local frame (cell centre at the world origin, floor z=0)
and is rendered by a job in jobs.py. Wall modules are drawn for the `_x` orientation (slab on the near/SW edge of the
cell, y in [-0.5, -0.5+T], face looking -Y) and rotated +90° for `_y` (slab on the +X edge, face looking +X).
"""
import math
from lib import HU, STOREY, ZPX, arch_pts

T = 0.25            # wall slab thickness (BU)
H = STOREY          # wall height = one storey (96 px)
Y0 = -0.5           # face plane of the wall (near edge)

STONE = dict(c1='4b4654', c2='37323f', mortar='1a1722')


def wall_mat(ctx, tone=0):
    tones = [('4b4654', '3f3a49' if False else '37323f', '1a1722'), ('66616e', '4b4654', '27232f')]
    c1, c2, mo = tones[tone]
    return ctx.brick(f'wallbrick{tone}', c1, c2, mo, bw=1 / 3, bh=6 / ZPX, mort=0.03, wall=True)


def _finish(root, axis):
    if axis == 'y':
        root.rotation_euler = (0, 0, math.radians(90))


def wall(ctx, axis='x', opening=None, glass='gold', door=None, plaque=False, hatch=False, crenel=True):
    """opening: None | 'window' | 'door'. door style: 'plain'|'gilt'|'ember'."""
    root = ctx.empty('wall')
    m = ctx.m
    wm = wall_mat(ctx)
    trim, trim_d, ink = m('8a8591'), m('66616e'), m('1a1722')
    slab = ctx.box((-.5, Y0, 0), (.5, Y0 + T, H), wm, root, 'slab')
    parts = []
    # plinth (2 courses) and string course
    parts.append(ctx.box((-.5, Y0 - .03, 0), (.5, Y0 + T, 12 / ZPX), trim_d, root))
    parts.append(ctx.box((-.5, Y0 - .02, 0.55), (.5, Y0 + T, 0.55 + 4 / ZPX), trim_d, root))
    # cornice cap + parapet with merlons
    ctx.box((-.5, Y0 - .05, H - 5 / ZPX), (.5, Y0 + T + .02, H), trim, root)
    if crenel:
        ctx.box((-.5, Y0, H), (.5, Y0 + T, H + 3 / ZPX), trim_d, root)
        for x0 in (-.5, -0.125, 0.25):
            w = 0.125 if x0 in (-.5, .25 + .125) else 0.25
            if x0 == -.5:
                ctx.box((-.5, Y0, H), (-.5 + .125, Y0 + T, H + 8 / ZPX), trim_d, root)
            elif x0 == .25:
                ctx.box((.375, Y0, H), (.5, Y0 + T, H + 8 / ZPX), trim_d, root)
            else:
                ctx.box((-.125, Y0, H), (.125, Y0 + T, H + 8 / ZPX), trim_d, root)
    # buttress piers: half at each end (adjacent cells complete them)
    for sx in (-1, 1):
        x_in, x_out = sx * .5 - sx * .07, sx * .5
        lo_x, hi_x = min(x_in, x_out), max(x_in, x_out)
        ctx.box((lo_x, Y0 - .10, 0), (hi_x, Y0 + .01, 0.9), trim_d, root)          # stepped buttress foot
        ctx.box((lo_x, Y0 - .06, 0.9), (hi_x, Y0 + .01, H - 5 / ZPX), wm, root)
        ctx.box((lo_x, Y0 - .12, 0.86), (hi_x, Y0 - .06, 0.9 + 3 / ZPX), trim, root)  # weathering
    cx = 0.0
    if opening == 'window':
        hw, base, spring = 0.17, 0.62, 0.92
        cutter = ctx.arch(hw, spring, 0.6, None, parent=root, name='cut'); cutter.location = (cx, Y0, base)
        ctx.cut(slab, cutter)
        # chamfered surround
        sur = ctx.arch(hw + .045, spring + .02, 0.05, trim, parent=root, name='surround'); sur.location = (cx, Y0 - .01, base - .02)
        cut2 = ctx.arch(hw, spring, 0.3, None, parent=root, name='cut2'); cut2.location = (cx, Y0, base)
        ctx.cut(sur, cut2)
        gcol, gcore = ('e0a83e', 'fff3c4') if glass == 'gold' else ('b3261e', 'e8552b')
        g = ctx.arch(hw, spring, 0.02, m(gcol, 2.2, 'f6d67a' if glass == 'gold' else 'e8552b'), parent=root, name='glass')
        g.location = (cx, Y0 + T * 0.6, base)
        g2 = ctx.arch(hw * 0.55, spring * 0.7, 0.02, m(gcore, 3.0), parent=root, name='glass2')
        g2.location = (cx, Y0 + T * 0.6 - .01, base + 0.12)
        lead = m('27232f')
        ctx.box((cx - .012, Y0 + T * .45, base), (cx + .012, Y0 + T * .55, base + spring + .26), lead, root)
        for zz in (base + .30, base + spring):
            ctx.box((cx - hw, Y0 + T * .45, zz), (cx + hw, Y0 + T * .55, zz + .025), lead, root)
        ctx.box((cx - hw - .05, Y0 - .06, base - .07), (cx + hw + .05, Y0 + .02, base), trim, root)   # sill
    if opening == 'door':
        hw, spring = 0.27, 0.86
        cutter = ctx.arch(hw, spring, 0.8, None, parent=root, name='cut'); cutter.location = (cx, Y0, 0)
        ctx.cut(slab, cutter)
        for p in parts:
            c = ctx.arch(hw, spring, 0.8, None, parent=root, name='cutp'); c.location = (cx, Y0, 0); ctx.cut(p, c)
        style = door or 'plain'
        ring_m = {'plain': trim, 'gilt': m('e0a83e', 0.25, 'e0a83e'), 'ember': m('74161b')}[style]
        ring = ctx.arch(hw + .07, spring + .03, 0.07, ring_m, parent=root, name='ring'); ring.location = (cx, Y0 - .02, 0)
        c3 = ctx.arch(hw, spring, 0.4, None, parent=root, name='cut3'); c3.location = (cx, Y0, 0); ctx.cut(ring, c3)
        back_y = Y0 + T - .03
        if style == 'plain':
            wood = ctx.brick('planks', '5a3f2e', '5a3f2e', '27232f', bw=0.09, bh=4.0, mort=0.08, wall=True)
            leaf = ctx.arch(hw, spring, 0.04, wood, parent=root, name='leaf'); leaf.location = (cx, back_y - .06, 0)
            iron = m('27232f')
            for zz in (0.18, 0.62):
                ctx.box((cx - hw, back_y - .1, zz), (cx + hw, back_y - .07, zz + .04), iron, root)
            ctx.box((cx - .01, back_y - .1, 0), (cx + .01, back_y - .07, spring + .4), m('1a1722'), root)
            ctx.sphere(.022, (cx + .07, back_y - .1, .5), m('a8742a'), parent=root)
            ctx.sphere(.022, (cx - .07, back_y - .1, .5), m('a8742a'), parent=root)
        elif style == 'gilt':
            leaf = ctx.arch(hw, spring, 0.02, m('f6d67a', 2.4), parent=root, name='light'); leaf.location = (cx, back_y, 0)
            core = ctx.arch(hw * .6, spring * .8, 0.02, m('fff3c4', 3.5), parent=root, name='core'); core.location = (cx, back_y - .01, 0)
            # gold leaf: inner ring + finial + trim on piers
            ctx.cyl(.035, 0, spring + hw * 1.73 + .05, spring + hw * 1.73 + .25, m('e0a83e', .3, 'f6d67a'), seg=6, loc=(cx, Y0 - .03), parent=root)
            ctx.sphere(.04, (cx, Y0 - .03, spring + hw * 1.73 + .06), m('e0a83e', .3, 'f6d67a'), parent=root)
            ctx.box((cx - hw - .07, Y0 - .06, 0), (cx - hw, Y0 + .02, 12 / ZPX), m('a8742a'), root)
            ctx.box((cx + hw, Y0 - .06, 0), (cx + hw + .07, Y0 + .02, 12 / ZPX), m('a8742a'), root)
            ctx.box((cx - hw, Y0 - .03, 0), (cx + hw, back_y, .015), m('e0a83e'), root)   # gilt threshold
        else:  # ember
            leaf = ctx.arch(hw, spring, 0.02, m('b3261e', 2.0, 'e8552b'), parent=root, name='glow'); leaf.location = (cx, back_y, 0)
            core = ctx.arch(hw * .55, spring * .55, 0.02, m('e8552b', 3.0), parent=root, name='core'); core.location = (cx, back_y - .01, 0)
            iron = m('1a1722')
            for i in range(-2, 3):
                ctx.box((cx + i * .1 - .012, Y0 + .02, 0), (cx + i * .1 + .012, Y0 + .05, spring + .45 - abs(i) * .12), iron, root)
            for zz in (0.3, 0.7):
                ctx.box((cx - hw, Y0 + .02, zz), (cx + hw, Y0 + .05, zz + .03), iron, root)
            ctx.box((cx - hw - .07, Y0 - .06, 0), (cx - hw, Y0 + .02, 12 / ZPX), m('3a0f14'), root)
            ctx.box((cx + hw, Y0 - .06, 0), (cx + hw + .07, Y0 + .02, 12 / ZPX), m('3a0f14'), root)
    if plaque:
        ctx.box((cx - .24, Y0 - .03, .78), (cx + .24, Y0, 1.42), m('a8742a'), root)
        ctx.box((cx - .20, Y0 - .045, .82), (cx + .20, Y0 - .02, 1.38), m('27232f'), root)
        for i in range(5):
            zz = 1.28 - i * .1
            ctx.box((cx - .15, Y0 - .05, zz), (cx + .15 - (i % 2) * .06, Y0 - .04, zz + .025), m('8a8591'), root)
        ctx.sphere(.05, (cx, Y0 - .05, 1.46), m('e0a83e'), parent=root, scale=(1, .4, 1))
    if hatch:
        cutter = ctx.box((cx - .26, Y0 - .2, .62), (cx + .26, Y0 + .6, 1.18), None, root, name='cut'); ctx.cut(slab, cutter)
        ctx.box((cx - .26, Y0 + T - .05, .62), (cx + .26, Y0 + T - .03, 1.18), m('e0a83e', 1.4, 'f6d67a'), root)
        ctx.box((cx - .32, Y0 - .14, .58), (cx + .32, Y0 + .02, .64), m('5a3f2e'), root)        # counter shelf
        ctx.box((cx - .3, Y0 - .03, 1.18), (cx + .3, Y0, 1.24), trim, root)
        # shutter propped up
        ctx.box((cx - .28, Y0 - .16, 1.22), (cx + .28, Y0 - .1, 1.26), m('5a3f2e'), root)
        ctx.box((cx - .2, Y0 - .03, 1.32), (cx + .2, Y0 - .01, 1.48), m('a8742a'), root)        # sign
        ctx.box((cx - .16, Y0 - .04, 1.37), (cx + .16, Y0 - .02, 1.42), m('37323f'), root)
        ctx.box((cx - .1, Y0 - .12, .64), (cx + .02, Y0 - .02, .67), m('b5b0b8'), root)        # ledger on shelf
    _finish(root, axis)
    return root


def corner(ctx):
    """pier at the near corner of cell (0,0): x in [.5-T, .5], y in [-.5, -.5+T], slightly taller, with pinnacle."""
    m = ctx.m
    wm = wall_mat(ctx)
    x0, x1, y0, y1 = .5 - T - .06, .5 + .02, -.52, -.5 + T + .06
    ctx.box((x0, y0, 0), (x1, y1, H + 4 / ZPX), wm)
    ctx.box((x0 - .02, y0 - .02, 0), (x1 + .02, y1 + .02, 12 / ZPX), m('66616e'))
    ctx.box((x0 - .02, y0 - .02, H - 2 / ZPX), (x1 + .02, y1 + .02, H + 6 / ZPX), m('8a8591'))
    cxp, cyp = (x0 + x1) / 2, (y0 + y1) / 2
    ctx.cyl(.15, 0, H + 6 / ZPX, H + 26 / ZPX, m('66616e'), seg=4, loc=(cxp, cyp), smooth=False).rotation_euler = (0, 0, math.radians(45))
    ctx.sphere(.035, (cxp, cyp, H + 27 / ZPX), m('8a8591'))


def kerb(ctx, axis='x', corner_=False):
    m = ctx.m
    top, side = m('8a8591'), ctx.brick('kerbbrick', '4b4654', '37323f', '1a1722', bw=1 / 3, bh=6 / ZPX, mort=0.03)
    h = HU
    if axis in ('x', 'c'):
        ctx.box((-.5, -.5, 0), (.5, -.5 + .2, h - 3 / ZPX), side)
        ctx.box((-.5, -.53, h - 3 / ZPX), (.5, -.5 + .22, h), top)
    if axis in ('y', 'c'):
        ctx.box((.5 - .2, -.5, 0), (.5, .5, h - 3 / ZPX), side)
        ctx.box((.5 - .22, -.53 if axis == 'c' else -.5, h - 3 / ZPX), (.53, .5, h), top)


def stairs(ctx):
    m = ctx.m
    st, nose = m('66616e'), m('8a8591')
    n = 4
    for i in range(n):
        y0 = -.5 + i / n
        z1 = (i + 1) * (2 * HU) / n
        ctx.box((-.5, y0, 0), (.5, .5, z1), st)
        ctx.box((-.5, y0 - .01, z1 - 2 / ZPX), (.5, y0 + .04, z1), nose)


# ------------------------------------------------------------------ props
def brazier(ctx, f):
    m = ctx.m
    iron, iron2 = m('37323f'), m('27232f')
    ctx.cyl(.15, .06, 0, .06, iron2, seg=8)
    ctx.cyl(.035, .03, .06, .44, iron, seg=8)
    for a in range(3):
        aa = math.radians(120 * a + 15)
        ctx.box((math.cos(aa) * .1 - .015, math.sin(aa) * .1 - .015, 0), (math.cos(aa) * .1 + .015, math.sin(aa) * .1 + .015, .12), iron2)
    ctx.cyl(.07, .17, .42, .56, iron, seg=10)
    ctx.cyl(.17, .17, .56, .58, m('4b4654'), seg=10)
    ctx.cyl(.15, .15, .55, .57, m('b3261e', 2.0, 'e8552b'), seg=10)  # embers
    sway = [0, .025, -.01, -.025][f]
    hgt = [.30, .26, .33, .28][f]
    fl = ctx.cyl(.13, 0, .56, .56 + hgt, m('e8552b', 3.0), seg=7)
    fl.rotation_euler = (sway * 4, sway * 3, 0)
    fl2 = ctx.cyl(.08, 0, .56, .56 + hgt * .7, m('f6d67a', 3.5), seg=6, loc=(sway, -.02))
    ctx.cyl(.04, 0, .56, .56 + hgt * .4, m('fff3c4', 4.0), seg=5, loc=(sway, -.05))


def wall_torch(ctx, axis, f):
    root = ctx.empty('torch')
    m = ctx.m
    y = -.5
    ctx.box((-.04, y - .03, 1.05), (.04, y + .01, 1.25), m('27232f'), root)            # plate
    arm = ctx.box((-.015, y - .16, 1.12), (.015, y - .02, 1.15), m('37323f'), root)
    ctx.cyl(.035, .05, 1.15, 1.33, m('37323f'), seg=8, loc=(0, y - .16), parent=root)
    hgt = [.20, .17, .23, .18][f]; sw = [0, .02, -.01, -.02][f]
    ctx.cyl(.06, 0, 1.33, 1.33 + hgt, m('e8552b', 3.0), seg=6, loc=(sw, y - .16), parent=root)
    ctx.cyl(.035, 0, 1.33, 1.33 + hgt * .7, m('f6d67a', 3.5), seg=5, loc=(sw, y - .18), parent=root)
    _finish(root, axis)


def banner(ctx, f):
    """wall-hung banner on a bracket at the cell's near corner (works on both _x and _y wall cells)."""
    m = ctx.m
    root = ctx.empty('banner', (.56, -.56, 0))
    root.rotation_euler = (0, 0, math.radians(45))
    ctx.box((-.03, .0, 2.0), (.03, .1, 2.06), m('27232f'), root)
    ctx.box((-.27, -.02, 2.06), (.27, .02, 2.1), m('37323f'), root)
    for sx in (-.27, .27):
        ctx.sphere(.03, (sx, 0, 2.08), m('e0a83e'), parent=root)
    sw = [0, .03][f]
    pts = [(-.22, 2.06), (.22, 2.06), (.22 + sw, .98), (0 + sw, 1.16), (-.22 + sw, .98)]
    cl = ctx.poly_prism(pts, .02, m('b3261e'), parent=root)
    tr = ctx.poly_prism([(-.22, 2.06), (.22, 2.06), (.22, 1.98), (-.22, 1.98)], .025, m('e0a83e'), parent=root)
    tr.location = (0, -.005, 0)
    for zz in (1.86, 1.2):
        ctx.poly_prism([(-.22 + sw * (2.06 - zz), zz), (.22 + sw * (2.06 - zz), zz), (.22, zz - .03), (-.22, zz - .03)], .025, m('74161b'), parent=root).location = (0, -.005, 0)
    ctx.cyl(.075, .075, -.01, .01, m('e0a83e'), seg=4, loc=(sw * .5, 0), parent=root).rotation_euler = (math.radians(90), 0, 0)
    ctx.cyl(.075, .075, -.01, .01, m('e0a83e'), seg=4, loc=(sw * .5, 0), parent=root).location = (sw * .5, -.02, 1.58)
    ctx.box((-.012 + sw * .5, -.03, 1.36), (.012 + sw * .5, -.015, 1.8), m('e0a83e'), root)


def kerb_door(ctx, axis='x'):
    """low gateway for a door cell on a near kerb row: two piers, threshold, lantern; floor shows through."""
    root = ctx.empty('kdoor')
    m = ctx.m
    side = ctx.brick('kerbbrick', '4b4654', '37323f', '1a1722', bw=1 / 3, bh=6 / ZPX, mort=0.03)
    for sx in (-1, 1):
        x0, x1 = (-.5, -.3) if sx < 0 else (.3, .5)
        ctx.box((x0, -.5, 0), (x1, -.28, .78), side, root)
        ctx.box((x0 - .02, -.52, .78), (x1 + .02, -.26, .84), m('8a8591'), root)
        ctx.cyl(.1, 0, .84, 1.1, m('66616e'), seg=4, loc=((x0 + x1) / 2, -.39), parent=root, smooth=False).rotation_euler = (0, 0, math.radians(45))
    ctx.box((-.3, -.5, 0), (.3, -.28, .02), m('8a8591'), root)
    ctx.box((-.42, -.56, .5), (-.38, -.5, .66), m('27232f'), root)
    ctx.box((-.43, -.6, .56), (-.37, -.54, .68), m('f6d67a', 3.0), root)
    _finish(root, axis)


def desk(ctx, tray=0, superior=False):
    m = ctx.m
    wood, dark, paper = m('5a3f2e'), m('27232f'), m('b5b0b8')
    w = .44 if not superior else .5
    d = .26 if not superior else .32
    top = .44 if not superior else .5
    ctx.box((-w, -d, top - .05), (w, d, top), wood)
    ctx.box((-w + .02, -d + .02, 0), (-w + .22, d - .02, top - .05), wood)
    ctx.box((w - .22, -d + .02, 0), (w - .02, d - .02, top - .05), wood)
    ctx.box((-w + .22, -d + .2, .12), (w - .22, d - .04, top - .05), dark)      # modesty panel
    for zz in (.12, .26):
        ctx.box((-w + .06, -d + .01, zz), (-w + .18, -d + .02, zz + .02), m('a8742a'))  # drawer pulls
    if superior:
        ctx.box((-w - .02, -d - .02, 0), (w + .02, d + .02, .06), dark)
        ctx.box((-w, -d - .01, top - .08), (w, -d, top - .05), m('a8742a'))   # gilt edge
        ctx.box((-.1, -.1, top), (.1, .1, top + .03), m('b3261e'))            # blotter
        ctx.cyl(.035, .03, top, top + .14, m('37323f'), seg=8, loc=(.32, .12))  # stamp
        ctx.cyl(.05, .05, top + .14, top + .17, m('a8742a'), seg=8, loc=(.32, .12))
    # papers + ledger
    ctx.box((-.30, -.16, top), (-.06, .06, top + .015), paper)
    ctx.box((-.04, -.18, top), (.12, -.04, top + .03), m('43325c'))
    ctx.cyl(.025, .025, top, top + .05, m('1a1722'), seg=6, loc=(.18, -.14))          # inkwell
    ctx.box((.17, -.15, top + .05), (.18, -.1, top + .16), m('b5b0b8'))                # quill
    # in-tray with stack
    ctx.box((.12, .0, top), (.38, .2, top + .04), m('37323f'))
    stack = [0.0, .06, .16][tray]
    if stack:
        ctx.box((.14, .02, top + .04), (.36, .18, top + .04 + stack), paper)
        if tray == 2:
            ctx.box((.17, .0, top + .04 + stack), (.38, .17, top + .06 + stack), paper).rotation_euler = (0, 0, .3)
    # candle
    ctx.cyl(.025, .025, top, top + .1, m('b5b0b8'), seg=6, loc=(-.36, .16))
    ctx.cyl(.022, 0, top + .1, top + .18, m('f6d67a', 3.5), seg=5, loc=(-.36, .16))


def dais(ctx):
    m = ctx.m
    ctx.box((-.5, -.5, 0), (.5, .5, HU - 2 / ZPX), ctx.brick('daisbrick', '4b4654', '37323f', '1a1722', bw=1 / 3, bh=6 / ZPX, mort=0.03))
    ctx.box((-.5, -.5, HU - 2 / ZPX), (.5, .5, HU), m('66616e'))
    ctx.box((-.42, -.5, HU), (.42, .5, HU + .01), m('74161b'))
    ctx.box((-.34, -.5, HU), (.34, .5, HU + .012), m('b3261e'))
    for sx in (-.38, .38):
        ctx.box((sx - .02, -.5, HU), (sx + .02, .5, HU + .014), m('e0a83e'))


def stool(ctx):
    m = ctx.m
    ctx.cyl(.12, .12, .24, .28, m('5a3f2e'), seg=10)
    for a in range(3):
        aa = math.radians(120 * a + 30)
        ctx.box((math.cos(aa) * .07 - .015, math.sin(aa) * .07 - .015, 0), (math.cos(aa) * .07 + .015, math.sin(aa) * .07 + .015, .24), m('27232f'))


def bench(ctx, soul=False, ivy=False):
    m = ctx.m
    wood = m('5a3f2e')
    ctx.box((-.48, -.16, .22), (.48, .12, .27), wood)
    ctx.box((-.48, .10, .27), (.48, .14, .58), wood)
    ctx.box((-.48, .09, .48), (.48, .15, .53), m('27232f'))
    for sx in (-.42, .42):
        ctx.box((sx - .03, -.14, 0), (sx + .03, .12, .22), m('27232f'))
        ctx.box((sx - .03, .09, 0), (sx + .03, .15, .6), m('27232f'))
    if ivy:
        leaf = [m('43325c'), m('6a5484'), m('2a1f3d')]
        import random
        rnd = random.Random(3)
        for i in range(70):
            x = rnd.uniform(-.48, .48); z = rnd.uniform(0, .62) * (1 - abs(x) * .3)
            y = .15 if rnd.random() < .6 else rnd.uniform(-.16, .12)
            if y < .1: z = rnd.choice([rnd.uniform(0, .22), .27])
            ctx.sphere(.035, (x, y - .01, z), leaf[i % 3], seg=6, rings=4)
        for i in range(6):
            x = -.4 + i * .16
            ctx.box((x - .006, .155, 0), (x + .006, .165, .6), m('2a1f3d'))
    if soul:
        sm = m('cfe0e6', .35)
        ctx.cyl(.13, .10, .27, .55, sm, seg=10, loc=(-.18, -.02))
        ctx.sphere(.085, (-.18, -.02, .64), sm)
        ctx.box((-.30, -.24, .18), (-.06, -.04, .3), sm)  # knees/lap
        ctx.cyl(.12, .09, .27, .52, sm, seg=10, loc=(.22, .0))
        ctx.sphere(.08, (.22, 0, .6), sm)


def lectern(ctx):
    m = ctx.m
    ctx.cyl(.14, .1, 0, .05, m('27232f'), seg=8)
    ctx.cyl(.04, .04, .05, .78, m('5a3f2e'), seg=8)
    t = ctx.box((-.17, -.13, .76), (.17, .13, .8), m('5a3f2e')); t.rotation_euler = (math.radians(-25), 0, 0)
    b = ctx.box((-.15, -.11, .8), (.15, .11, .83), m('b5b0b8')); b.rotation_euler = (math.radians(-25), 0, 0)
    ctx.box((-.006, -.11, .8), (.006, .11, .84), m('66616e')).rotation_euler = (math.radians(-25), 0, 0)


def shelf(ctx, empty=False):
    m = ctx.m
    wood, dark = m('5a3f2e'), m('1a1722')
    h = 2.3
    ctx.box((-.46, -.22, 0), (.46, .44, h), dark)              # carcass interior
    ctx.box((-.48, -.24, 0), (-.42, .44, h), wood)
    ctx.box((.42, -.24, 0), (.48, .44, h), wood)
    ctx.box((-.48, -.24, h), (.48, .46, h + .08), wood)
    ctx.box((-.5, -.26, h + .08), (.5, .48, h + .12), m('27232f'))
    cols = ['74161b', '43325c', '5a3f2e', '6b4a1e', '37323f', 'a8742a', '2a1f3d', '66616e']
    import random
    rnd = random.Random(11 if not empty else 12)
    shelves = [0.08 + i * .44 for i in range(5)]
    for si, z in enumerate(shelves):
        ctx.box((-.44, -.24, z - .04), (.44, .44, z), wood)
        if empty and si in (1, 2, 3):
            if si == 2:
                ctx.box((-.3, -.18, z), (-.2, .3, z + .02), m('66616e'))   # dust / a slip of paper
            continue
        x = -.41
        while x < .38:
            bw = rnd.choice([.05, .06, .07, .08])
            if x + bw > .41: break
            bh = rnd.uniform(.24, .36)
            col = m(rnd.choice(cols))
            if rnd.random() < .12:
                x += bw; continue
            ctx.box((x, -.2, z), (x + bw - .008, .4, z + bh), col)
            ctx.box((x, -.205, z + bh * .7), (x + bw - .008, -.2, z + bh * .7 + .02), m('a8742a'))
            x += bw
    # side face books (visible +X side): spines on the +X face through an open side? keep solid side, add plaque
    ctx.box((-.12, -.27, h - .02), (.12, -.25, h + .06), m('a8742a'))


def counter(ctx):
    m = ctx.m
    wood = m('5a3f2e')
    ctx.box((-.5, -.3, 0), (.5, .2, .56), ctx.brick('counterplank', '5a3f2e', '5a3f2e', '27232f', bw=.2, bh=.14, mort=.04, wall=True))
    ctx.box((-.5, -.36, .56), (.5, .24, .62), m('6b4a1e'))
    ctx.box((-.5, -.33, 0), (.5, -.3, .06), m('27232f'))
    ctx.box((-.3, -.24, .62), (-.02, -.02, .66), m('b5b0b8'))
    ctx.box((-.28, -.22, .66), (-.04, -.04, .68), m('8a8591'))
    ctx.box((.1, -.2, .62), (.3, 0, .74), m('74161b'))
    ctx.box((.11, -.19, .74), (.29, -.01, .77), m('43325c'))


def rope_post(ctx):
    m = ctx.m
    ctx.cyl(.08, .06, 0, .05, m('6b4a1e'), seg=8)
    ctx.cyl(.022, .022, .05, .5, m('a8742a'), seg=6)
    ctx.sphere(.04, (0, 0, .52), m('e0a83e'))
    # rope swags toward +X and -Y (connects along runs)
    for d in ((1, 0), (0, -1)):
        pts = []
        for i in range(7):
            t = i / 6
            pts.append((d[0] * .5 * t, d[1] * .5 * t, .46 - .14 * math.sin(math.pi * t)))
        for a, b in zip(pts, pts[1:]):
            mid = [(a[k] + b[k]) / 2 for k in range(3)]
            ctx.sphere(.022, mid, m('b3261e'), seg=6, rings=4, scale=(1 + 2.5 * abs(d[0]), 1 + 2.5 * abs(d[1]), 1))


def queue_rail(ctx):
    m = ctx.m
    for x in (-.5, .5):
        ctx.cyl(.035, .035, 0, .42, m('37323f'), seg=6, loc=(x, 0))
        ctx.sphere(.045, (x, 0, .44), m('a8742a'))
    ctx.box((-.5, -.018, .36), (.5, .018, .4), m('6b4a1e'))
    ctx.box((-.5, -.012, .18), (.5, .012, .2), m('37323f'))


def queue_post(ctx):
    m = ctx.m
    ctx.cyl(.06, .05, 0, .03, m('27232f'), seg=6)
    ctx.cyl(.03, .03, 0, .42, m('37323f'), seg=6)
    ctx.sphere(.045, (0, 0, .44), m('a8742a'))


def ticket_booth(ctx):
    m = ctx.m
    wood = m('5a3f2e')
    ctx.box((-.42, -.38, 0), (.42, .42, 1.5), ctx.brick('boothplank', '5a3f2e', '5a3f2e', '27232f', bw=.12, bh=4, mort=.06))
    ctx.box((-.46, -.42, 0), (.46, .46, .08), m('27232f'))
    # window with counter
    ctx.box((-.28, -.33, .62), (.28, -.31, 1.12), m('e0a83e', 1.3, 'f6d67a'))
    ctx.box((-.34, -.48, .56), (.34, -.36, .62), m('6b4a1e'))
    for x in (-.1, .1):
        ctx.box((x - .01, -.39, .62), (x + .01, -.37, 1.12), m('1a1722'))
    ctx.box((-.36, -.42, 1.12), (.36, -.36, 1.17), m('6b4a1e'))
    # "NOW SERVING" sign board
    ctx.box((-.3, -.44, 1.22), (.3, -.4, 1.42), m('1a1722'))
    for i, x in enumerate((-.22, -.12, -.02, .08, .18)):
        ctx.box((x, -.45, 1.3), (x + .06, -.44, 1.36), m('f6d67a', 2.0))
    # pointed roof
    roof = ctx.cyl(.66, .0, 1.5, 2.2, m('37323f'), seg=4, smooth=False); roof.rotation_euler = (0, 0, math.radians(45))
    ctx.cyl(.62, .62, 1.5, 1.56, m('6b4a1e'), seg=4, smooth=False).rotation_euler = (0, 0, math.radians(45))
    ctx.sphere(.05, (0, 0, 2.23), m('e0a83e'))


def desk_registrar(ctx):
    m = ctx.m
    ctx.box((-.48, -.3, 0), (.48, .3, .78), ctx.brick('regplank', '5a3f2e', '5a3f2e', '27232f', bw=.16, bh=.2, mort=.04))
    ctx.box((-.5, -.34, .78), (.5, .34, .84), m('6b4a1e'))
    ctx.box((-.5, -.34, 0), (.5, -.3, .08), m('27232f'))
    ctx.box((-.44, -.31, .5), (.44, -.3, .56), m('a8742a'))
    # big ledger + bell + lamp
    ctx.box((-.34, -.24, .84), (.02, .08, .88), m('b5b0b8'))
    ctx.box((-.34, -.26, .84), (.02, -.22, .87), m('74161b'))
    ctx.cyl(.06, .02, .84, .92, m('e0a83e'), seg=8, loc=(.2, -.18))
    ctx.sphere(.018, (.2, -.18, .93), m('a8742a'))
    ctx.cyl(.02, .02, .84, 1.12, m('37323f'), seg=6, loc=(.36, .16))
    ctx.cyl(.07, .05, 1.12, 1.22, m('f6d67a', 2.5), seg=6, loc=(.36, .16))
    ctx.cyl(.08, 0, 1.22, 1.3, m('37323f'), seg=6, loc=(.36, .16))
    # spike of tickets
    ctx.cyl(.008, .008, .84, 1.0, m('8a8591'), seg=4, loc=(.1, .16))
    for i in range(4):
        ctx.box((.06, .12, .86 + i * .025), (.14, .2, .87 + i * .025), m('b5b0b8'))


def statue(ctx):
    """The First Clerk: hooded, winged, lantern on a staff; stepped base on a 2x2 footprint (world origin = footprint centre)."""
    m = ctx.m
    st1, st2, st3 = m('8a8591'), m('66616e'), m('4b4654')
    base = ctx.brick('statbase', '66616e', '4b4654', '27232f', bw=1 / 3, bh=6 / ZPX, mort=.03)
    ctx.box((-.9, -.9, 0), (.9, .9, .2), base)
    ctx.box((-.92, -.92, .2), (.92, .92, .24), st1)
    ctx.box((-.66, -.66, .24), (.66, .66, .48), base)
    ctx.box((-.68, -.68, .48), (.68, .68, .52), st1)
    ctx.box((-.42, -.42, .52), (.42, .42, 1.05), st3)
    ctx.box((-.46, -.46, 1.05), (.46, .46, 1.12), st1)
    ctx.box((-.46, -.46, .52), (.46, .46, .6), st2)
    # inscription plate (front faces)
    ctx.box((-.22, -.43, .7), (.22, -.42, .92), m('a8742a'))
    ctx.box((.42, -.22, .7), (.43, .22, .92), m('6b4a1e'))
    z0 = 1.12
    # robe
    ctx.cyl(.34, .19, z0, z0 + 1.35, st2, seg=16, scale=(1, .85))
    ctx.cyl(.36, .34, z0, z0 + .1, st3, seg=16, scale=(1, .85))
    ctx.sphere(.24, (0, .02, z0 + 1.35), st2, scale=(1.25, .9, .5))                     # shoulders
    # hood (deep cowl, face in shadow)
    ctx.sphere(.2, (0, .04, z0 + 1.62), st1, scale=(1, 1.05, 1.15))
    ctx.cyl(.15, 0, z0 + 1.7, z0 + 1.98, st1, seg=10, loc=(0, .1))
    ctx.sphere(.12, (0, -.1, z0 + 1.58), m('1a1722'), scale=(1, .6, 1.1))
    # wings: two swept, scalloped silhouettes in a plane facing the viewer, behind the shoulders
    wing = [(0, 0), (.25, .25), (.5, .55), (.72, .95), (.82, 1.2), (.7, 1.05), (.74, .82), (.6, .72), (.66, .5),
            (.5, .42), (.54, .2), (.38, .12), (.4, -.12), (.24, -.08), (.22, -.38), (.1, -.25)]
    for sx in (-1, 1):
        pts = [(sx * x, z) for x, z in wing]
        if sx < 0: pts = pts[::-1]
        wg = ctx.poly_prism(pts, .05, st1, name='wing'); wg.location = (-.08 + sx * .1 * .707, .14 + sx * .1 * .707, z0 + 1.2)
        wg.rotation_euler = (0, 0, math.radians(45))
        inner = [(sx * x * .8, z * .85 - .02) for x, z in wing]
        if sx < 0: inner = inner[::-1]
        wi = ctx.poly_prism(inner, .05, st2, name='wing2'); wi.location = (-.05 + sx * .1 * .707, .11 + sx * .1 * .707, z0 + 1.2)
        wi.rotation_euler = (0, 0, math.radians(45))
    # arms + staff + lantern (held out to the viewer's left/front)
    ctx.cyl(.08, .1, z0 + .75, z0 + 1.3, st2, seg=8, loc=(-.3, -.1)).rotation_euler = (math.radians(-20), math.radians(-15), 0)
    ctx.sphere(.07, (-.34, -.22, z0 + .78), st1)
    ctx.cyl(.035, .035, .52, z0 + 2.25, m('6b4a1e'), seg=8, loc=(-.34, -.24))
    lz = z0 + 2.28
    ctx.box((-.42, -.32, lz), (-.26, -.16, lz + .05), m('37323f'))
    ctx.box((-.4, -.3, lz + .05), (-.28, -.18, lz + .25), m('f6d67a', 3.0))
    ctx.box((-.355, -.305, lz + .05), (-.325, -.175, lz + .25), m('fff3c4', 4.0))
    ctx.cyl(.1, .0, lz + .25, lz + .36, m('37323f'), seg=4, loc=(-.34, -.24), smooth=False).rotation_euler = (0, 0, math.radians(45))
    ctx.sphere(.03, (-.34, -.24, lz + .38), m('e0a83e'))
    # other hand holds a ledger to the chest
    ctx.box((.06, -.36, z0 + .85), (.34, -.2, z0 + 1.15), st1)
    ctx.sphere(.07, (.2, -.36, z0 + 1.0), st2)


# ---------------------------------------------------------------- living quarters & cells (owner request)
def bed(ctx, sleeper=False, soul=False):
    """A narrow cot along the x axis: iron frame, straw mattress, purple blanket, pillow at +x."""
    m = ctx.m
    iron = m('27232f')
    for sx in (-.42, .42):
        for sy in (-.19, .19):
            ctx.box((sx - .025, sy - .025, 0), (sx + .025, sy + .025, .22), iron)
    ctx.box((.40, -.21, .1), (.45, .21, .42), iron)  # headboard
    ctx.box((-.45, -.21, .12), (-.40, .21, .30), iron)  # footboard
    ctx.box((-.42, -.2, .16), (.42, .2, .21), m('5a3f2e'))
    ctx.box((-.40, -.18, .21), (.40, .18, .28), m('8a8591'))  # mattress
    ctx.box((-.40, -.185, .27), (.12, .185, .31), m('43325c'))  # blanket
    ctx.box((.20, -.13, .28), (.37, .13, .35), m('b5b0b8'))  # pillow
    if sleeper or soul:
        body = m('cfe0e6', .35) if soul else m('43325c')
        ctx.box((-.36, -.13, .28), (.16, .13, .40), body)  # a shape under the blanket
        ctx.sphere(.08, (.27, 0, .40), m('cfe0e6', .35) if soul else m('8a8591'))


def cell_bars(ctx, axis='x'):
    """A row of iron bars across one cell edge, with top and bottom rails."""
    m = ctx.m
    iron, rail = m('27232f'), m('37323f')
    along_x = axis == 'x'
    def bx(a0, a1, z0, z1, t=.025):
        if along_x:
            return ctx.box((a0, -t, z0), (a1, t, z1), iron)
        return ctx.box((-t, a0, z0), (t, a1, z1), iron)
    for i in range(7):
        a = -.45 + i * .15
        bx(a - .014, a + .014, 0, 1.15, .014)
    if along_x:
        ctx.box((-.5, -.035, 1.1), (.5, .035, 1.18), rail)
        ctx.box((-.5, -.035, 0), (.5, .035, .06), rail)
    else:
        ctx.box((-.035, -.5, 1.1), (.035, .5, 1.18), rail)
        ctx.box((-.035, -.5, 0), (.035, .5, .06), rail)


def cell_door(ctx, axis='x'):
    """Barred cell door: bars plus a heavy lock plate."""
    cell_bars(ctx, axis)
    m = ctx.m
    if axis == 'x':
        ctx.box((.12, -.05, .5), (.26, .05, .66), m('a8742a'))
    else:
        ctx.box((-.05, .12, .5), (.05, .26, .66), m('a8742a'))


# connection bits (grid space): 1 = -cy (Blender +Y), 2 = +cx (+X), 4 = +cy (-Y), 8 = -cx (-X)
BAR_DIRS = {1: (0, 1), 2: (1, 0), 4: (0, -1), 8: (-1, 0)}


def cell_bars_mask(ctx, mask, door=False):
    """Connection-aware iron bars: half-cell arms from the centre to each connected edge, posts at the centre
    (unless straight) and at every arm end, shared top/bottom rails. Arms meet neighbours exactly on the cell edge."""
    m = ctx.m
    iron, rail, post = m('27232f'), m('37323f'), m('4b4654')
    arms = [BAR_DIRS[b] for b in (1, 2, 4, 8) if mask & b]
    straight = mask in (5, 10)
    if not arms:                      # isolated: a short x run with end posts
        arms = [(1, 0), (-1, 0)]; straight = True
    H, t = 1.15, .035

    def seg(d, a0, a1, z0, z1, w):
        dx, dy = d
        if dx:
            lo, hi = sorted((dx * a0, dx * a1))
            return ctx.box((lo, -w, z0), (hi, w, z1), rail if w > .02 else iron)
        lo, hi = sorted((dy * a0, dy * a1))
        return ctx.box((-w, lo, z0), (w, hi, z1), rail if w > .02 else iron)
    for d in arms:
        seg(d, 0, .5, H - .05, H + .03, t)          # top rail
        seg(d, 0, .5, 0, .06, t)                    # bottom rail
        for a in (.125, .25, .375):                 # bars
            dx, dy = d
            x, y = dx * a, dy * a
            ctx.box((x - .014, y - .014, 0), (x + .014, y + .014, H), iron)
        dx, dy = d                                  # end post on the edge (shared with the neighbour)
        x, y = dx * .5, dy * .5
        ctx.box((x - .03, y - .03, 0), (x + .03, y + .03, H + .06), post)
        ctx.box((x - .04, y - .04, H + .06), (x + .04, y + .04, H + .09), rail)
    if straight:
        ctx.box((-.014, -.014, 0), (.014, .014, H), iron)
    else:
        ctx.box((-.045, -.045, 0), (.045, .045, H + .08), post)
        ctx.box((-.055, -.055, H + .08), (.055, .055, H + .11), rail)
        ctx.sphere(.04, (0, 0, H + .15), m('66616e'), seg=8, rings=5)
    if door:
        if mask == 10:
            ctx.box((.12, -.05, .5), (.26, .05, .66), m('a8742a'))
            ctx.box((.17, -.06, .55), (.21, .06, .6), m('1a1722'))
        else:
            ctx.box((-.05, -.26, .5), (.05, -.12, .66), m('a8742a'))
            ctx.box((-.06, -.21, .55), (.06, -.17, .6), m('1a1722'))


def washstand(ctx):
    m = ctx.m
    ctx.box((-.16, -.14, 0), (.16, .14, .5), m('5a3f2e'))
    ctx.cyl(.12, .09, .5, .58, m('b5b0b8'), seg=10)
    ctx.cyl(.05, .04, .58, .74, m('8a8591'), seg=8, loc=(.06, .0))
