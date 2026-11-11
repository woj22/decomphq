#!/usr/bin/env python3
"""Compose an area from the generated sprites to check assembly (sort order, wall alignment, doors, seams).

Usage: python3 tools/preview_area.py <area.json | grid.txt> out.png [--scale N] [--no-crowd]
Input is the CONTRACTS §2 area JSON (game/data/areas/area_*.json or tools/procgen/fixtures/*.json), or a plain
ASCII grid file (PROJECT §10.2 legend). Mimics the Engine: sprite at Iso.cell_to_local(cell) - origin, floors first,
then decals, additive light pools, then everything else Y-sorted on its cell centre.
"""
import glob, json, os, sys, random
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'game', 'assets')
NPCS = os.path.join(ROOT, 'game', 'data', 'npcs')

DEFAULT_LEGEND = {
    '#': {'kind': 'wall'}, 'k': {'kind': 'kerb'}, 'D': {'kind': 'door'}, '.': {'kind': 'floor'},
    's': {'kind': 'stair'}, 'g': {'kind': 'floor', 'floor': 'floor_goldseam'}, 'T': {'kind': 'prop', 'prop': 'statue_first_clerk'},
    'B': {'kind': 'prop', 'prop': 'brazier_0'}, 'p': {'kind': 'wall', 'sprite': 'auto_plaque'}, 'q': {'kind': 'queue'},
    'r': {'kind': 'prop', 'prop': 'queue_rail_x'}, 'd': {'kind': 'prop', 'prop': 'desk_clerk'}, 'o': {'kind': 'seat', 'prop': 'stool'},
    'b': {'kind': 'seat', 'prop': 'bench_soul'}, 'c': {'kind': 'prop', 'prop': 'counter'}, 'S': {'kind': 'prop', 'prop': 'shelf_books'},
    'e': {'kind': 'prop', 'prop': 'shelf_empty'}, 'x': {'kind': 'prop', 'prop': 'rope_post'}, 'n': {'kind': 'prop', 'prop': 'ivy_bench'},
    't': {'kind': 'prop', 'prop': 'ticket_booth'}, '=': {'kind': 'floor', 'floor': 'floor_carpet_red', 'prop': 'dais', 'h_hu': 1},
}


class Sprites:
    def __init__(self):
        self.s, self.img = {}, {}
        for p in glob.glob(os.path.join(ASSETS, '**', '*.json'), recursive=True):
            d = json.load(open(p))
            im = Image.open(os.path.join(os.path.dirname(p), d['image'])).convert('RGBA')
            for k, v in d['sprites'].items():
                self.s[k] = v; self.img[k] = im

    def get(self, sid, frame=0, dir_i=7, anim='idle'):
        v = self.s[sid]; x, y, w, h = v['rect']
        if v.get('kind') == 'character':
            cw, ch = v['cell']; a = v['anims'].get(anim) or v['anims']['idle']
            x, y, w, h = x + dir_i * cw, y + (a['row'] + frame % a['frames']) * ch, cw, ch
        elif v.get('frames'):
            x += (frame % v['frames']) * w
        return self.img[sid].crop((x, y, x + w, y + h)), v['origin']


def cell_to_local(cx, cy):
    return (cx - cy) * 32 + 32, (cx + cy) * 16 + 16


def load_area(path):
    if path.endswith('.json'):
        return json.load(open(path))
    grid = [l.rstrip('\n') for l in open(path) if l.strip()]
    grid = [l.split()[0] for l in grid]
    return {'id': os.path.basename(path), 'grid': grid, 'legend': DEFAULT_LEGEND, 'floor': 'floor_flag',
            'backdrop': 'none', 'objects': [], 'decor': [], 'windows': [], 'spawns': {}}


def npc_sprite(npc):
    p = os.path.join(NPCS, npc + '.json')
    if os.path.exists(p):
        return json.load(open(p)).get('sprite') or None
    return 'chr_clerk_grey'


def compose(area, S, crowd=True):
    grid = area['grid']; H_ = len(grid); W_ = len(grid[0])
    legend = dict(DEFAULT_LEGEND); legend.update(area.get('legend', {}))
    pad_x, pad_top, pad_bot = 48, 176, 40
    W = (W_ + H_) * 32 + pad_x * 2
    H = (W_ + H_) * 16 + pad_top + pad_bot
    off = np.array([pad_x + H_ * 32 - 32, pad_top - 16])
    canvas = Image.new('RGBA', (W, H), (13, 11, 18, 255))
    # backdrop
    bd = area.get('backdrop', 'none')
    fog, _ = S.get('bg_void_fog')
    for yy in range(0, H, fog.height):
        for xx in range(0, W, fog.width):
            canvas.alpha_composite(fog, (xx, yy))
    if bd == 'court':
        for name, x0 in (('bg_heaven', 0), ('bg_hell', W // 2)):
            sky, _ = S.get(name + '_sky'); sl, _ = S.get(name + '_skyline')
            hw = W - W // 2 if x0 else W // 2
            sx = 0 if x0 == 0 else max(0, sky.width - hw)
            half = Image.new('RGBA', (hw, H))
            half.alpha_composite(sky.crop((sx, 0, sx + hw, sky.height)), (0, 0))
            sx = 0 if x0 == 0 else sl.width - hw
            half.alpha_composite(sl.crop((sx, 0, sx + hw, sl.height)), (0, sky.height - sl.height))
            canvas.alpha_composite(half, (x0, 0))
    floors, decals, adds, items = [], [], [], []
    rnd = random.Random(1)
    windows = {tuple(w['cell']): w['glass'] for w in area.get('windows', [])}
    doors = {tuple(o['cell']): o.get('style', 'plain') for o in area.get('objects', []) if o['type'] in ('door', 'soul_door')}
    statue_done = False

    def place(sid, cx, cy, layer, sort=None, frame=0, dir_i=7, anim='idle', h_px=0, alpha=None):
        if sid not in S.s:
            print('missing sprite', sid); return
        im, (ox, oy) = S.get(sid, frame, dir_i, anim)
        lx, ly = cell_to_local(cx, cy)
        pos = (int(round(lx - ox + off[0])), int(round(ly - oy + off[1] - h_px)))
        key = (ly if sort is None else sort)
        (floors if layer == 0 else decals if layer == 1 else adds if layer == 2 else items).append((key, layer, len(items), im, pos))

    for cy, row in enumerate(grid):
        for cx, ch in enumerate(row):
            L = legend.get(ch, {'kind': 'floor'})
            kind = L['kind']
            last_r, last_c = cy == H_ - 1, cx == W_ - 1
            ax = 'x' if (cy == 0 or last_r) else 'y'
            fam = L.get('floor', area.get('floor', 'floor_flag'))
            if kind in ('floor', 'prop', 'queue', 'seat', 'decal', 'stair'):
                if kind == 'queue':
                    fam = 'floor_goldseam'
                n = {'floor_flag': 4, 'floor_carpet_red': 3, 'floor_goldseam': 2}.get(fam, 1)
                var = (cx * 7 + cy * 13 + (cx * cy) % 5) % n
                if fam == 'floor_goldseam': var = 0
                if fam == 'floor_carpet_red': var = 0
                place(f'{fam}_{var}', cx, cy, 0)
            if kind == 'wall':
                sid = L.get('sprite')
                if sid == 'auto_plaque':
                    sid = 'wall_plaque_x' if cy == 0 else 'works_hatch_y'
                if not sid:
                    if (cx, cy) == (0, 0): sid = 'wall_corner'
                    elif (cx, cy) in windows: sid = f'wall_window_{windows[(cx, cy)]}_{ax}'
                    else: sid = f'wall_plain_{ax}'
                place(sid, cx, cy, 3, sort=cell_to_local(cx, cy)[1] - .3)
            elif kind == 'kerb':
                sid = 'wall_kerb_corner' if (last_r and last_c) else ('wall_kerb_x' if last_r else 'wall_kerb_y')
                place(sid, cx, cy, 3, sort=cell_to_local(cx, cy)[1] + 8)
            elif kind == 'door':
                st = doors.get((cx, cy), 'plain')
                sid = {'plain': 'wall_door', 'gilt': 'wall_door_gilt', 'ember': 'wall_door_ember'}[st] + f'_{ax}'
                near = last_r or last_c
                if not near:
                    place(sid, cx, cy, 3, sort=cell_to_local(cx, cy)[1] - .3)
                else:
                    kd = f'wall_kerb_door_{ax}'
                    place(kd if kd in S.s else sid, cx, cy, 3, sort=cell_to_local(cx, cy)[1] + 8)
            elif kind == 'stair':
                rows = [y for y, r in enumerate(grid) if ch in r]
                h = (max(rows) - cy) * 32
                place('stairs_up', cx, cy, 3, sort=cell_to_local(cx, cy)[1] - 1, h_px=h)
            pr = L.get('prop')
            if pr == 'statue_first_clerk':
                if not statue_done:
                    statue_done = True
                    cells = [(x, y) for y, r in enumerate(grid) for x, c in enumerate(r) if c == ch]
                    mx = (min(c[0] for c in cells) + max(c[0] for c in cells)) / 2
                    my = (min(c[1] for c in cells) + max(c[1] for c in cells)) / 2
                    place(pr, mx, my, 3, sort=cell_to_local(max(c[0] for c in cells), max(c[1] for c in cells))[1])
            elif pr == 'dais':
                place('dais', cx, cy, 0)
            elif pr:
                place(pr, cx, cy, 3)
    # decor
    for d in area.get('decor', []):
        sid = d['sprite']; cx, cy = d['cell']
        if sid not in S.s:
            place(sid, cx, cy, 3); continue
        v = S.s[sid]
        fp = d.get('footprint') or v.get('footprint')
        if fp and fp != [1, 1]:
            cx, cy = cx + (fp[0] - 1) / 2, cy + (fp[1] - 1) / 2
        if v.get('additive'):
            place(sid, cx, cy, 2)
        elif v['kind'] == 'decal':
            place(sid, cx, cy, 1)
        else:
            place(sid, cx, cy, 3, sort=cell_to_local(cx, cy)[1] + .1)
    # actors
    def actor(sid, cx, cy, d=7, anim='idle', frame=0, ring=False, h=0):
        place('shadow_blob', cx, cy, 1)
        if ring: place('select_ring', cx, cy, 1, frame=1)
        place(sid, cx, cy, 3, sort=cell_to_local(cx, cy)[1] + .5, dir_i=d, anim=anim, frame=frame, h_px=h)
    DI = {k: i for i, k in enumerate(['sw', 'w', 'nw', 'n', 'ne', 'e', 'se', 's'])}
    for o in area.get('objects', []):
        if o['type'] == 'npc':
            sp = npc_sprite(o['npc'])
            if o.get('conditions') or not sp: continue
            cx, cy = o['cell']
            L = legend.get(grid[cy][cx], {})
            actor(sp, cx, cy, DI.get(o.get('facing', 's'), 7), anim='idle', h=16 * L.get('h_hu', 0))
    if crowd:
        occupied = {tuple(o['cell']) for o in area.get('objects', [])}
        for zn, z in sorted(area.get('zones', {}).items()):
            if z.get('kind') == 'queue':
                for c in z['cells']:
                    if tuple(c) in occupied: continue
                    if rnd.random() < .82:
                        actor(f'chr_soul_{rnd.randrange(4)}', c[0] + rnd.uniform(-.08, .08), c[1] + rnd.uniform(-.1, .1),
                              d=rnd.choice([5, 6, 4]), frame=rnd.randrange(4))
            elif z.get('kind') == 'wander':
                cells = list(z['cells']); rnd.shuffle(cells)
                for c in cells[:z.get('count', 3)]:
                    actor(rnd.choice(['chr_clerk_grey', 'chr_clerk_lilac', 'chr_clerk_grey']), c[0], c[1],
                          d=rnd.randrange(8), anim='walk', frame=rnd.randrange(4))
        sp = area.get('spawns', {}).get('default')
        if sp:
            actor('chr_player', sp[0], sp[1], d=7, anim='walk', frame=1, ring=True)
    # draw
    for key, layer, _, im, pos in floors:
        canvas.alpha_composite(im, pos)
    for key, layer, _, im, pos in decals:
        canvas.alpha_composite(im, pos)
    base = np.asarray(canvas).astype(np.int32)
    for key, layer, _, im, pos in adds:     # additive light pools
        a = np.asarray(im).astype(np.int32)
        x, y = pos; h, w = a.shape[:2]
        x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
        sub = a[y0 - y:y1 - y, x0 - x:x1 - x]
        base[y0:y1, x0:x1, :3] += (sub[..., :3] * sub[..., 3:4] * 55) // 25500
    canvas = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    for key, layer, i, im, pos in sorted(items, key=lambda t: (t[0], t[2])):
        canvas.alpha_composite(im, pos)
    return canvas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    scale = int(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1
    if '--scale' in sys.argv: args.remove(str(scale))
    src, out = args[0], args[1]
    area = load_area(src)
    img = compose(area, Sprites(), crowd='--no-crowd' not in sys.argv)
    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.convert('RGB').save(out)
    print('wrote', out, img.size)


if __name__ == '__main__':
    main()
