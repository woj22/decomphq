import sys, math, time; sys.path.insert(0, '.')
from lib import *
from mathutils import Vector
import bpy
def lin(h):
    c = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(((x+0.055)/1.055)**2.4 if x > 0.04045 else x/12.92 for x in c)
SAMPLES = int(sys.argv[1]); FTYPE = sys.argv[2]; FILT = float(sys.argv[3]); tag = sys.argv[4]
T0 = time.time()
def new():
    s = reset(SAMPLES, FILT); s.cycles.pixel_filter_type = FTYPE
    k = sun(s, (0,0,0), (1.0, 0.95, 0.88), 4.5)
    k.rotation_euler = Vector((0.45, 0.8, -1.3)).to_track_quat('-Z', 'Y').to_euler()
    f = sun(s, (0,0,0), (0.55, 0.45, 0.9), 0.6)
    f.rotation_euler = Vector((-0.9, -0.2, -0.6)).to_track_quat('-Z', 'Y').to_euler()
    M = {}
    M['floor'] = mat_stone('floor', lin('66616e'), lin('4b4654'), lin('27232f'), bw=0.5, bh=0.5, mort=0.04)
    M['wall'] = mat_stone('wall', lin('4b4654'), lin('66616e'), lin('1a1722'), wall=True, bw=0.25, bh=0.128, mort=0.035)
    for n, h in dict(trim='8a8591', dark='1a1722', ink='0d0b12', robe='43325c', robe2='27232f', skin='b5b0b8',
                     gold='e0a83e', red='b3261e', wood='5a3f2e', iron='37323f', paper='b5b0b8', lilac='6a5484').items():
        M[n] = mat_flat(n, lin(h))
    M['glass'] = mat_flat('glass', lin('e0a83e'), emit=1.6, ecol=lin('f6d67a'))
    M['glass2'] = mat_flat('glass2', lin('fff3c4'), emit=3.0, ecol=lin('fff3c4'))
    M['fire'] = mat_flat('fire', lin('e8552b'), emit=3.0, ecol=lin('e8552b'))
    M['fire2'] = mat_flat('fire2', lin('f6d67a'), emit=4.0, ecol=lin('f6d67a'))
    M['soul'] = mat_flat('soul', lin('cfe0e6'), emit=0.18)
    return s, M

def wall(s, M, axis='x', window=True, H=96/ZPX):
    """wall on the far edge of the tile. axis x: along X at y=+0.375; axis y: along Y at x=-0.375."""
    root = bpy.data.objects.new('wallroot', None); s.collection.objects.link(root)
    y = 0.375; t = 0.125
    w = box(s, 'wall', (-.5, y-t, 0), (.5, y+t, H), M['wall'])
    ps = [w, box(s, 'plinth', (-.5, y-t-.05, 0), (.5, y+t, 0.2), M['trim']),
          box(s, 'cornice', (-.5, y-t-.05, H-0.1), (.5, y+t, H), M['trim']),
          box(s, 'string', (-.5, y-t-.025, 0.5), (.5, y+t, 0.56), M['trim'])]
    if window:
        cut = arch_prism(s, 'cut', 0.21, 0.8, 0.2); cut.location = (0, y-t, 0.62); cut.hide_render = True
        md = w.modifiers.new('b', 'BOOLEAN'); md.object = cut; md.operation = 'DIFFERENCE'; md.solver = 'EXACT'
        g = arch_prism(s, 'glass', 0.21, 0.8, 0.02, M['glass']); g.location = (0, y-t+0.09, 0.62)
        g2 = arch_prism(s, 'glass2', 0.12, 0.45, 0.02, M['glass2']); g2.location = (0, y-t+0.08, 0.72)
        ps += [cut, g, g2, box(s, 'mull', (-.02, y-t+.03, 0.62), (.02, y-t+.07, 1.75), M['ink']),
               box(s, 'tran', (-.21, y-t+.03, 1.08), (.21, y-t+.07, 1.12), M['ink']),
               box(s, 'sill', (-.27, y-t-.05, 0.56), (.27, y-t, 0.62), M['trim'])]
    for p in ps: p.parent = root
    if axis == 'y': root.rotation_euler = (0, 0, math.radians(90))
    return root

def clerk(s, M, robe='robe', soul=False, phase=0.0, hat=None):
    e = bpy.data.objects.new('ch', None); s.collection.objects.link(e)
    r = M['soul'] if soul else M[robe]; sk = M['soul'] if soul else M['skin']
    bob = 0.025*abs(math.sin(phase)); sw = 0.07*math.sin(phase)
    parts = [cone(s, 'body', 0.19, 0.10, 0, 0.55+bob, r, seg=10),
             sphere(s, 'head', 0.105, (0, 0, 0.66+bob), r if not soul else sk, (1, 1, 1.1)),
             cone(s, 'armL', 0.05, 0.04, 0.26, 0.5+bob, r, seg=6, loc=(-0.15, -0.02+sw)),
             cone(s, 'armR', 0.05, 0.04, 0.26, 0.5+bob, r, seg=6, loc=(0.15, -0.02-sw))]
    if not soul:
        parts += [cone(s, 'hoodtip', 0.10, 0.0, 0.70+bob, 0.86+bob, r, seg=8, loc=(0, 0.03)),
                  sphere(s, 'face', 0.07, (0, -0.065, 0.645+bob), sk, (0.9, 0.6, 1.0)),
                  cone(s, 'hem', 0.2, 0.19, 0.0, 0.05, M['gold'] if robe == 'robe' else M['red'], seg=10),
                  box(s, 'book', (-0.06, -0.2, 0.3), (0.06, -0.13, 0.42), M['paper'] if robe == 'robe' else M['iron'])]
    if hat == 'spear':
        parts += [box(s, 'spear', (0.19, -0.05, 0.0), (0.215, -0.025, 1.0), M['trim']),
                  cone(s, 'tip', 0.04, 0, 1.0, 1.12, M['gold'], seg=4, loc=(0.2, -0.037))]
    for p in parts: p.parent = e
    return e

def brazier(s, M):
    cone(s, 'stem', 0.05, 0.04, 0, 0.42, M['iron'], seg=6); cone(s, 'foot', 0.14, 0.05, 0, 0.06, M['iron'], seg=6)
    cone(s, 'bowl', 0.07, 0.16, 0.42, 0.54, M['iron'], seg=8)
    cone(s, 'fl', 0.12, 0.0, 0.54, 0.80, M['fire'], seg=6); cone(s, 'fl2', 0.07, 0.0, 0.54, 0.70, M['fire2'], seg=6)

def desk(s, M):
    box(s, 'top', (-.42, -.25, .40), (.42, .25, .46), M['wood'])
    box(s, 'pedl', (-.40, -.22, 0), (-.18, .22, .40), M['wood']); box(s, 'pedr', (.18, -.22, 0), (.40, .22, .40), M['wood'])
    box(s, 'paper', (-.28, -.12, .46), (-.05, .08, .48), M['paper']); box(s, 'stack', (.1, -.05, .46), (.3, .15, .56), M['paper'])
    box(s, 'candle', (.33, -.2, .46), (.37, -.16, .58), M['paper']); cone(s, 'cf', 0.03, 0, 0.58, 0.66, M['fire2'], seg=4, loc=(.35, -.18))

times = {}
def shot(s, name, W, H, base_y):   # tile-centre (world origin) lands at pixel row base_y
    aim(s, W, H, (0, 0, (H/2-(H-base_y))/ZPX)); times[name] = render(s, f'raw_{tag}_{name}.png')

s, M = new(); box(s, 'tile', (-.5, -.5, -.25), (.5, .5, 0), M['floor']); shot(s, 'floor', 64, 48, 16+0) if False else None
aim(s, 64, 48, (0, 0, -8/ZPX)); times['floor'] = render(s, f'raw_{tag}_floor.png')
for ax in 'xy':
    for win in (True, False):
        s, M = new(); wall(s, M, ax, win); shot(s, f'wall_{ax}_{"win" if win else "plain"}', 64, 128, 112)
s, M = new(); brazier(s, M); shot(s, 'brazier', 32, 48, 40)
s, M = new(); desk(s, M); shot(s, 'desk', 64, 64, 48)
for nm, kw in (('clerk', {}), ('soul', dict(soul=True)), ('guard', dict(robe='robe2', hat='spear'))):
    ts = []
    for fr in range(4):
        s, M = new(); e = clerk(s, M, phase=fr*math.pi/2, **kw)
        aim(s, 32, 56, (0, 0, (28-8)/ZPX))
        for d in range(8):
            e.rotation_euler = (0, 0, math.radians(45*d)); ts.append(render(s, f'raw_{tag}_{nm}_{fr}_{d}.png'))
    times[nm] = sum(ts)
print('TIMES', {k: round(v, 3) for k, v in times.items()}, 'TOTAL wall-clock', round(time.time()-T0, 2))
