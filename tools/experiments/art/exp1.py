import sys, math, time; sys.path.insert(0, '.')
from lib import *
from mathutils import Vector
import bpy
def lin(h):
    c = [int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(((x+0.055)/1.055)**2.4 if x > 0.04045 else x/12.92 for x in c)
SAMPLES = int(sys.argv[1]) if len(sys.argv) > 1 else 16
FILT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01
tag = sys.argv[3] if len(sys.argv) > 3 else 'a'

def lights(s):
    k = sun(s, (0,0,0), (1.0, 0.93, 0.85), 3.2)
    k.rotation_euler = Vector((0.35, 0.8, -1.0)).to_track_quat('-Z', 'Y').to_euler()
    f = sun(s, (0,0,0), (0.55, 0.45, 0.9), 0.5)
    f.rotation_euler = Vector((-0.9, -0.2, -0.6)).to_track_quat('-Z', 'Y').to_euler()

def mats():
    M = {}
    M['floor'] = mat_stone('floor', lin('4b4654'), lin('37323f'), lin('1a1722'), bw=0.5, bh=0.5, mort=0.035)
    M['wall'] = mat_stone('wall', lin('4b4654'), lin('66616e'), lin('1a1722'), wall=True, bw=0.34, bh=0.17, mort=0.03)
    M['trim'] = mat_flat('trim', lin('8a8591'))
    M['dark'] = mat_flat('dark', lin('1a1722'))
    M['glass'] = mat_flat('glass', lin('e0a83e'), emit=2.2, ecol=lin('f6d67a'))
    M['robe'] = mat_flat('robe', lin('43325c'))
    M['robe2'] = mat_flat('robe2', lin('27232f'))
    M['skin'] = mat_flat('skin', lin('b5b0b8'))
    M['gold'] = mat_flat('gold', lin('e0a83e'))
    M['red'] = mat_flat('red', lin('b3261e'))
    M['soul'] = mat_flat('soul', lin('cfe0e6'), emit=0.6)
    return M

def tile(s, M, x=0, y=0):
    return box(s, 'tile', (x-.5, y-.5, -.25), (x+.5, y+.5, 0), M['floor'])

def wall_window(s, M, x=0, y=0.4, H=96/ZPX, window=True):
    w = box(s, 'wall', (x-.5, y-.1, 0), (x+.5, y+.1, H), M['wall'])
    box(s, 'plinth', (x-.5, y-.14, 0), (x+.5, y+.1, 0.16), M['trim'])
    box(s, 'cornice', (x-.5, y-.14, H-0.12), (x+.5, y+.1, H), M['trim'])
    if window:
        cut = arch_prism(s, 'cut', 0.2, 0.75, 0.5); cut.location = (x, y, 0.55); cut.hide_render = True
        cut.display_type = 'WIRE'
        md = w.modifiers.new('b', 'BOOLEAN'); md.object = cut; md.operation = 'DIFFERENCE'; md.solver = 'EXACT'
        g = arch_prism(s, 'glass', 0.2, 0.75, 0.02, M['glass']); g.location = (x, y+0.02, 0.55)
        box(s, 'mull', (x-.015, y-.03, 0.55), (x+.015, y, 1.6), M['dark'])
        box(s, 'tran', (x-.2, y-.03, 0.95), (x+.2, y, 0.98), M['dark'])
    return w

def clerk(s, M, robe='robe', soul=False, phase=0.0, x=0, y=0):
    """facing -Y at rot 0. returns parent empty."""
    e = bpy.data.objects.new('ch', None); s.collection.objects.link(e); e.location = (x, y, 0)
    r = M['soul'] if soul else M[robe]
    sk = M['soul'] if soul else M['skin']
    bob = 0.02*abs(math.sin(phase)); sw = 0.06*math.sin(phase)
    parts = [cone(s, 'body', 0.2, 0.11, 0, 0.56+bob, r, seg=10),
             sphere(s, 'hood', 0.135, (0, 0.015, 0.68+bob), r, (1, 1.05, 1.1)),
             sphere(s, 'face', 0.085, (0, -0.07, 0.66+bob), sk, (1, 0.7, 1.05)),
             cone(s, 'armL', 0.05, 0.045, 0.28, 0.52, r, seg=6, loc=(-0.15, -0.03+sw)),
             cone(s, 'armR', 0.05, 0.045, 0.28, 0.52, r, seg=6, loc=(0.15, -0.03-sw))]
    if not soul:
        parts.append(box(s, 'sash', (-0.125, -0.19, 0.30), (0.125, 0.15, 0.34), M['gold']))
    for p in parts: p.parent = e
    return e

out = {}
# --- floor tile 64x48
s = reset(SAMPLES, FILT); M = mats(); lights(s); tile(s, M)
aim(s, 64, 48, (0, 0, -8/ZPX)); out['tile'] = render(s, f'raw_tile_{tag}.png')
# --- wall with window 66x130 (1px pad for outline) , tile origin diamond centre at y=H-17
s = reset(SAMPLES, FILT); M = mats(); lights(s); wall_window(s, M)
W, H = 64, 128
aim(s, W, H, (0, 0, (H/2-16)/ZPX)); out['wall'] = render(s, f'raw_wall_{tag}.png')
# --- characters 32x48, feet (origin) at y = 48-8
for nm, kw in (('clerk', {}), ('soul', dict(soul=True)), ('guard', dict(robe='robe2'))):
    s = reset(SAMPLES, FILT); M = mats(); lights(s); e = clerk(s, M, **kw)
    aim(s, 32, 48, (0, 0, (24-8)/ZPX))
    ts = []
    for d in range(8):
        e.rotation_euler = (0, 0, math.radians(45*d))
        ts.append(render(s, f'raw_{nm}_{tag}_{d}.png'))
    out[nm] = ts
print('TIMES', {k: (round(sum(v)/len(v), 3), [round(x,2) for x in v]) if isinstance(v, list) else round(v, 3) for k, v in out.items()})
