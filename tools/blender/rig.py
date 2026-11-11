"""Parametric hooded-figure rig (characters, souls, portrait busts).

Front = -Y. Dir index i (canonical order sw, w, nw, n, ne, e, se, s) = root rotation -45°·i about Z.
Proportions are tuned for a ~36 px figure (0.92 BU) in a 32x56 cell, feet at (16,48).
"""
import math

DIRS = ['sw', 'w', 'nw', 'n', 'ne', 'e', 'se', 's']

CHARS = {
    'chr_player':      dict(robe='43325c', hem='e0a83e', belt='a8742a', hood='pointed', face='b5b0b8', prop='ledger'),
    'chr_player_r2':   dict(robe='43325c', hem='e0a83e', belt='e0a83e', hood='pointed', face='b5b0b8', prop='ledger',
                            cuffs='e0a83e', trim='e0a83e'),
    'chr_clerk_grey':  dict(robe='37323f', hem='8a8591', belt='1a1722', hood='round', face='b5b0b8', prop='scroll'),
    'chr_clerk_lilac': dict(robe='43325c', hem='9a86ad', belt='27232f', hood='round', face='b5b0b8', prop=None,
                            cuffs='9a86ad'),
    'chr_archivist':   dict(robe='5a3f2e', hem='6b4a1e', belt='27232f', hood='round', face='b5b0b8', prop='book',
                            hunch=True, specs=True),
    'chr_guard':       dict(robe='27232f', hem='b3261e', belt='6b4a1e', hood='helmet', face='b5b0b8', prop='spear',
                            tabard='b3261e'),
}
for i in range(4):
    CHARS[f'chr_soul_{i}'] = dict(soul=True, variant=i)


SLEEVE = {'43325c': '6a5484', '37323f': '4b4654', '5a3f2e': '6b4a1e', '27232f': '37323f'}


class Rig:
    def __init__(self, ctx, spec, extra=None):
        self.ctx, self.p = ctx, dict(spec)
        if extra:
            self.p.update(extra)
        self.build()

    def mat(self, h, emit=0.0, ecol=None):
        return self.ctx.m(h, emit, ecol)

    def build(self):
        c, p = self.ctx, self.p
        self.root = c.empty('root')
        self.body = c.empty('body', parent=self.root)
        soul = p.get('soul')
        if soul:
            return self.build_soul()
        robe = self.mat(p['robe']); hem = self.mat(p['hem']); face = self.mat(p['face'], .55)
        sleeve = self.mat(p.get('sleeve') or SLEEVE.get(p['robe'], p['robe']))
        b = self.body
        k = 0.92 if p.get('hunch') else 1.0
        self.k = k
        # robe: flared cone, slightly elliptical; hem band; belt
        c.cyl(.165, .085, 0, .53 * k, robe, seg=16, scale=(1, .86), parent=b)
        c.cyl(.172, .163, 0, .05, hem, seg=16, scale=(1, .86), parent=b)
        if p.get('tabard'):
            tab = self.mat(p['tabard'])
            c.cyl(.18, .108, .08, .52 * k, tab, seg=16, scale=(.62, .9), loc=(0, -.006), parent=b)
            c.box((-.03, -.18, .30), (.03, -.10, .36), self.mat('e0a83e'), parent=b)
        c.cyl(.122, .118, .31 * k, .34 * k, self.mat(p['belt']), seg=12, scale=(1, .86), parent=b)
        # shoulders / yoke
        c.sphere(.14, (0, .01, .49 * k), robe, scale=(1.08, .72, .45), parent=b)
        # head group (hunched figures lean forward)
        self.head = c.empty('head', (0, 0, .64 * k), parent=b)
        hd = self.head
        if p.get('hunch'):
            hd.location = (0, -.05, .60 * k)
        hood = p['hood']
        if hood == 'helmet':
            c.sphere(.105, (0, .015, .02), self.mat('37323f'), scale=(1, 1, 1.05), parent=hd)       # mail coif
            c.sphere(.078, (0, -.055, .015), face, scale=(.95, .7, 1.05), parent=hd)
            c.sphere(.11, (0, 0, .085), self.mat('66616e'), scale=(1, 1, .72), parent=hd)           # kettle hat
            c.cyl(.165, .15, .07, .09, self.mat('4b4654'), seg=14, parent=hd)                        # brim
            c.cyl(.012, 0, .14, .2, self.mat('e0a83e'), seg=4, parent=hd)
        else:
            tm = self.mat(p.get('trim') or p['robe'])
            c.sphere(.138, (0, .025, .045), robe, scale=(1, 1.05, 1.08), parent=hd)
            c.sphere(.118, (0, -.035, .03), tm if p.get('trim') else sleeve, scale=(1.02, .8, 1.05), parent=hd)  # cowl rim
            c.sphere(.096, (0, -.06, .025), self.mat('0d0b12'), scale=(.95, .7, 1.05), parent=hd)     # shadowed opening
            c.sphere(.07, (0, -.1, .01), face, scale=(.9, .55, .95), parent=hd)
            if hood == 'pointed':
                tip = c.cyl(.085, 0, 0, .22, robe, seg=10, loc=(0, 0), parent=hd)
                tip.location = (0, .07, .2); tip.rotation_euler = (math.radians(28), 0, 0)
            else:
                tip = c.cyl(.09, .03, 0, .12, robe, seg=10, parent=hd)
                tip.location = (0, .06, .15); tip.rotation_euler = (math.radians(20), 0, 0)
            if p.get('specs'):
                for sx in (-.03, .03):
                    c.sphere(.02, (sx, -.145, .03), self.mat('fff3c4', 3.0), parent=hd)
        # arms: pivot at shoulder, sleeve hangs along -Z
        self.arms = []
        for sx in (-1, 1):
            pv = c.empty('arm', (sx * .165, .0, .5 * k), parent=b)
            c.cyl(.064, .044, -.27, 0, sleeve, seg=10, parent=pv)
            if p.get('cuffs'):
                c.cyl(.064, .06, -.27, -.235, self.mat(p['cuffs']), seg=10, parent=pv)
            c.sphere(.036, (0, -.005, -.295), face, parent=pv)
            self.arms.append(pv)
        # feet
        self.feet = []
        for sx in (-1, 1):
            f = c.sphere(.045, (sx * .07, -.06, .025), self.mat('1a1722'), scale=(1, 1.7, .7), parent=self.root)
            self.feet.append(f)
        # props
        pr = p.get('prop')
        self.prop = None
        if pr == 'ledger':
            g = c.empty('ledger', (0, 0, 0), parent=b)
            c.box((-.03, -.24, .28), (.10, -.15, .46), self.mat('b5b0b8'), parent=g)
            c.box((-.035, -.245, .28), (.105, -.235, .46), self.mat('6a5484'), parent=g)
            self.prop = g
        elif pr == 'scroll':
            g = c.empty('scroll', (0, 0, 0), parent=b)
            s = c.cyl(.03, .03, -.07, .07, self.mat('b5b0b8'), seg=8, parent=g)
            s.location = (.08, -.19, .34); s.rotation_euler = (0, math.radians(90), 0)
            self.prop = g
        elif pr == 'book':
            g = c.empty('book', (0, 0, 0), parent=b)
            c.box((-.12, -.27, .16), (.12, -.15, .38), self.mat('74161b'), parent=g)
            c.box((-.11, -.28, .17), (.11, -.27, .37), self.mat('b5b0b8'), parent=g)
            c.box((-.12, -.275, .25), (.12, -.265, .28), self.mat('e0a83e'), parent=g)
            self.prop = g
        elif pr == 'spear':
            g = c.empty('spear', (0, 0, 0), parent=self.root)
            c.cyl(.016, .016, .0, 1.12, self.mat('5a3f2e'), seg=6, loc=(.21, -.07), parent=g)
            c.cyl(.034, 0, 1.12, 1.27, self.mat('e0a83e'), seg=4, loc=(.21, -.07), parent=g, smooth=False)
            c.cyl(.03, .03, 1.1, 1.13, self.mat('b5b0b8'), seg=6, loc=(.21, -.07), parent=g)
            self.prop = g

    def build_soul(self):
        c, p = self.ctx, self.p
        v = p.get('variant', 0)
        sm = self.mat('cfe0e6', .25)
        sm2 = self.mat('8fa3b3', .2)
        b = self.body
        sc = [(1, 1, 1), (1.22, 1.15, .93), (.95, .95, .88), (1, 1, 1.02)][v]
        self.k = sc[2]
        k = sc[2]
        self.tail = c.cyl(.06, .14, .0, .2, sm2, seg=12, parent=b, scale=(sc[0], sc[1] * .86))
        c.cyl(.14, .095, .2, .54 * k, sm, seg=14, scale=(sc[0], sc[1] * .86), parent=b)
        c.sphere(.13, (0, .01, .52 * k), sm, scale=(1.0 * sc[0], .7, .5), parent=b)
        self.head = c.empty('head', (0, 0, .64 * k), parent=b)
        hd = self.head
        if v == 2:
            hd.location = (0, -.05, .6 * k)
        c.sphere(.098, (0, 0, .03), sm, scale=(.95, .95, 1.08), parent=hd)
        if v == 3:   # long hair / shawl
            c.sphere(.105, (0, .03, .04), sm2, scale=(1.05, 1.0, 1.05), parent=hd)
            c.cyl(.1, .14, -.24, -.02, sm2, seg=12, loc=(0, .05), parent=hd)
            c.sphere(.096, (0, -.02, .02), sm, parent=hd)
        if v == 1:
            c.sphere(.06, (0, .07, .1), sm2, parent=hd)        # bun
        self.arms = []
        for sx in (-1, 1):
            pv = c.empty('arm', (sx * .135 * sc[0], .0, .49 * k), parent=b)
            c.cyl(.048, .036, -.25, 0, sm, seg=8, parent=pv)
            self.arms.append(pv)
        if v == 2:
            g = c.empty('cane', parent=self.root)
            c.cyl(.014, .014, 0, .42, sm2, seg=6, loc=(.17, -.14), parent=g)
            self.prop = g
        else:
            self.prop = None
        self.feet = []
        if v == 2:
            self.body.rotation_euler = (math.radians(-8), 0, 0)

    # ---------------------------------------------------------------- poses
    def pose(self, anim, f):
        p = self.p
        soul = p.get('soul')
        k = self.k
        bob, swing, fl, fr = 0.0, 0.0, 0.0, 0.0
        armL = armR = 0.0
        spread = 0.0
        if anim == 'walk':
            ph = f * math.pi / 2
            swing = math.cos(ph)
            bob = 0.026 * abs(math.sin(ph))
            armL, armR = -0.5 * swing, 0.5 * swing
            fl, fr = -.09 * swing, .09 * swing
        elif anim == 'idle':
            if soul:
                bob = [0.0, .026, .052, .026][f]
                armL, armR = [0.0, .06, .1, .06][f], -[0.0, .06, .1, .06][f]
            else:
                bob = [0.0, -0.013][f]
                armL, armR = 0.05 * f, -0.05 * f
        elif anim == 'work':
            bob = [0.0, -0.012][f]
            armL, armR = -0.95, [-1.05, -0.8][f]
        elif anim == 'attention':
            bob = 0.013
        self.body.location = (0, 0, bob + (0.05 if soul else 0))
        if soul:
            self.tail.rotation_euler = (0, 0.0, 0)
            self.tail.location = (0, 0.02 * swing if anim == 'walk' else 0, 0.0)
        # props that occupy a hand
        pr = p.get('prop')
        if pr in ('ledger', 'book') and anim != 'work':
            armR = -0.75
            if pr == 'book':
                armL = -0.75
        if pr == 'spear':
            armR = -0.35
            if anim == 'attention':
                armL = 0.0
        if pr == 'scroll' and anim != 'work':
            armR = -0.55
        spr = 0.06 if not soul else 0.03
        self.arms[0].rotation_euler = (armL, -spr, 0)
        self.arms[1].rotation_euler = (armR, spr, 0)
        if self.feet:
            self.feet[0].location.y = -.06 + fl
            self.feet[1].location.y = -.06 + fr
        if self.prop is not None:
            if pr == 'spear':
                self.prop.location = (0, 0.0 if anim != 'attention' else 0.0, bob)
                self.prop.rotation_euler = (0.06 * swing if anim == 'walk' else 0, 0, 0)
                if anim == 'attention':
                    self.prop.location = (-.21, -.06, bob)
            elif pr in ('ledger', 'book', 'scroll'):
                self.prop.hide_render = (anim == 'work')
                if pr == 'book':
                    self.prop.hide_render = False
                    self.prop.location = (0, (-.02 if anim == 'work' else 0), (-.08 if anim == 'work' else 0))

    def face(self, d):
        self.root.rotation_euler = (0, 0, math.radians(-45 * d))
