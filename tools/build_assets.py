#!/usr/bin/env python3
"""Regenerate everything under game/assets/ (deterministic). Usage: python3 tools/build_assets.py [--keep-raw DIR]

Pipeline: Blender jobs (tools/blender/jobs.py, N parallel worker processes, Cycles CPU) -> raw RGBA renders
-> tools/procgen/post.py (ambient tint, Border-24 quantise, outline) -> atlases + JSON manifests (CONTRACTS §1).
Numpy/Pillow assets (floors, fx, backdrops, ui, audio) are generated in parallel. Fails on off-palette pixels.
"""
import json, math, os, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'procgen'))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import post, spec, tiles, palette  # noqa: E402
from palette import rgb  # noqa: E402

ASSETS = os.path.join(ROOT, 'game', 'assets')
WORKERS = int(os.environ.get('ART_WORKERS', str(os.cpu_count() or 4)))
GAIN = 1.45          # exposure applied with the ambient tint (keeps the cold tint, restores mid-tones)

# Blender jobs with rough cost (s) for load balancing
JOBS = [('walls', 3.3), ('windows', 2.1), ('doors', 3.4), ('kerbs', .7), ('brazier', 1.2), ('torch', 1.5),
        ('banner', .6), ('desks', 1.6), ('furn', 2.0), ('shelves', 2.5), ('quarters', 3.0), ('rails', .8), ('booth', .5), ('statue', 1.2),
        ('busts', 2.0), ('portraits', 2.5)] + [(f'char:{c}', 4.2 if spec.CHARS[c] != 'soul' else 3.3) for c in spec.CHARS]


def run_blender(raw):
    bins = [[] for _ in range(WORKERS)]; load = [0.0] * WORKERS
    for j, c in sorted(JOBS, key=lambda t: -t[1]):
        i = load.index(min(load)); bins[i].append(j); load[i] += c
    procs = []
    for b in bins:
        if b:
            procs.append(subprocess.Popen([sys.executable, os.path.join(ROOT, 'tools', 'blender', 'jobs.py'), raw] + b,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    ok = True
    for p in procs:
        out, _ = p.communicate()
        if p.returncode != 0:
            ok = False
            print(out[-4000:])
    if not ok:
        raise SystemExit('blender job failed')


# ------------------------------------------------------------------ pil side (runs in a pool)
def pil_backdrop(name):
    import backdrops
    return name, backdrops.BACKDROPS[name]()


def pil_audio(_):
    import audio
    return 'audio', audio.build(os.path.join(ASSETS, 'audio'))


def pil_tiles(_):
    out = {}
    for i in range(4): out[f'floor_flag_{i}'] = tiles.flagstone(variant=i, seed=i)
    for i in range(2): out[f'floor_flag_edge_{i}'] = tiles.floor_edge(i)
    for i in range(3): out[f'floor_carpet_red_{i}'] = tiles.carpet(i)
    for i in range(2): out[f'floor_goldseam_{i}'] = tiles.goldseam(i)
    out['decal_inlay_ring'] = tiles.inlay_ring()
    out['shadow_blob'] = tiles.shadow_blob()
    out['select_ring'] = np.hstack([tiles.select_ring(f) for f in range(4)])
    out['light_pool_gold'] = tiles.light_pool('gold'); out['light_pool_red'] = tiles.light_pool('red')
    out['dust_mote'] = np.hstack([tiles.dust_mote(f) for f in range(4)])
    out['tap_marker'] = np.hstack([tiles.tap_marker(f) for f in range(4)])
    return 'tiles', out


def pil_ui(_):
    import ui
    return 'ui', ui.build()


# ------------------------------------------------------------------ post
def q_sprite(raw, sid, sp, suffix=''):
    a = post.load(os.path.join(raw, sid + suffix + '.png'))
    out = post.quantise(a, 'world', outline=False, gain=GAIN)
    if sp.get('outline'):
        if _touch(out, sid):
            raise SystemExit(f'edge contact: {sid}{suffix}')
        post.add_outline(out, post.INK)
    return out


def _touch(out, sid):
    if sid.startswith('wall_torch'):
        return False
    return post.edge_contact(out)


def world_sprites(raw, tiles_out):
    groups = {}
    for sid, sp in spec.SPRITES.items():
        g = sp['group']
        if sp['src'] == 'pil':
            img = tiles_out[sid]
        elif sp.get('frames'):
            img = np.hstack([q_sprite(raw, sid, sp, f'__f{f}') for f in range(sp['frames'])])
        else:
            img = q_sprite(raw, sid, sp)
        if sp.get('underlay'):
            base = np.zeros_like(img)
            fl = tiles_out[sp['underlay']]
            ox, oy = sp['origin']
            base[oy - 16:oy + 16, ox - 32:ox + 32] = fl
            m = img[..., 3] > 0
            base[m] = img[m]
            img = base
        meta = dict(origin=list(sp['origin']), kind=sp['kind'])
        for k in ('solid', 'frames', 'fps', 'footprint', 'additive', 'height_hu', 'mask'):
            if sp.get(k) is not None:
                meta[k] = sp[k]
        meta['_fw'], meta['_fh'] = sp['size']
        groups.setdefault(g, ({}, {}))
        groups[g][0][sid] = img; groups[g][1][sid] = meta
    return groups


def char_sheets(raw):
    sprites, meta = {}, {}
    for cid, t in spec.CHARS.items():
        (cw, ch), origin = spec.char_cell(cid)
        soul = t == 'soul'
        rows, anims, r = [], {}, 0
        for anim, n, fps in spec.CHAR_ANIMS[t]:
            anims[anim] = dict(row=r, frames=n, fps=fps)
            for f in range(n):
                row = []
                for d in range(8):
                    a = post.load(os.path.join(raw, f'{cid}__{anim}_{f}_{d}.png'))
                    q = post.quantise(a, 'soul' if soul else 'world', outline=False, gain=GAIN, alpha=191 if soul else 255)
                    if post.edge_contact(q):
                        raise SystemExit(f'edge contact: {cid} {anim} {f} {d}')
                    post.add_outline(q, post.SOUL_OUT if soul else post.INK, 191 if soul else 255)
                    row.append(q)
                rows.append(np.hstack(row))
                r += 1
        sheet = np.vstack(rows)
        sprites[cid] = sheet
        meta[cid] = dict(origin=list(origin), kind='character', cell=[cw, ch], dirs=spec.DIRS, anims=anims,
                         _fw=sheet.shape[1], _fh=sheet.shape[0])
        if soul:
            meta[cid]['alpha_baked'] = 0.75
    return sprites, meta


# ---- portraits / busts
def _bg(size, kind):
    yy, xx = np.mgrid[0:size, 0:size]
    d = np.sqrt((xx + .5 - size / 2) ** 2 + (yy + .5 - size * .42) ** 2) / size
    out = np.zeros((size, size, 4), np.uint8)
    cols = ['43325c', '2a1f3d', '1a1722'] if kind == 'soul' else ['37323f', '27232f', '1a1722']
    for r, c in ((9, cols[2]), (.55, cols[1]), (.36, cols[0])):
        out[d < r, :3] = rgb(c)
    out[..., 3] = 255
    # Bayer edge between bands is not used: flat banded vignette (pixel-art friendly)
    out[0, :, :3] = out[-1, :, :3] = out[:, 0, :3] = out[:, -1, :3] = rgb('0d0b12')
    return out


def _face(img, cx, cy, s, expr, col, hooded=False):
    c = np.array(rgb(col), np.uint8)
    e = max(1, round(s))       # eye size
    dx = round(3.4 * s)

    def px(x, y, w=1, h=1, cc=c):
        x, y = int(round(x)), int(round(y))
        img[y:y + h, x:x + w, :3] = cc
    for sx in (-1, 1):
        ex = cx + sx * dx - (e // 2)
        if expr == 'relieved':
            px(ex - (1 if e > 1 else 0), cy, e + (2 if e > 1 else 1), 1)
            px(ex - 1, cy - 1, 1, 1); px(ex + e, cy - 1, 1, 1)
        else:
            px(ex, cy - e + 1, e, e)
        if expr == 'distressed':
            # brows slanting up toward the middle
            px(cx + sx * dx - sx * e, cy - e - 2 * (1 if s < 2 else 2), 1 + e, 1)
            px(cx + sx * (dx + e), cy - e - 1, 1 + e // 2, 1)
        elif not hooded:
            px(cx + sx * dx - e, cy - e - 2, e * 2, 1)
    my = cy + round(3.4 * s)
    mw = round(2.6 * s)
    if expr == 'neutral':
        px(cx - mw // 2, my, mw, 1)
    elif expr == 'distressed':
        px(cx - mw // 2, my, mw, 1); px(cx - mw // 2 - 1, my + 1, 1, 1); px(cx + mw // 2 + (mw % 2), my + 1, 1, 1)
        if s >= 2: px(cx - 1, my + 1, 2, 2)
    else:
        px(cx - mw // 2, my + 1, mw, 1); px(cx - mw // 2 - 1, my, 1, 1); px(cx + mw // 2 + (mw % 2), my, 1, 1)


def _face_px(size, zoom, zh, dist):
    PPU = 64 / math.sqrt(2)
    v = -.5 * dist + .866 * (zh - .7) + .06
    return size / 2, size / 2 - v * PPU * zoom


PORTRAIT_FACE = {  # id -> (zh, dist, kind, face colour on hooded figures)
    'por_marrow': (.67, .12, 'clerk'), 'por_pell': (.585, .17, 'clerk'), 'por_wren': (.67, .12, 'clerk'),
    'por_grist': (.665, .08, 'clerk'), 'por_registrar': (.67, .12, 'clerk'), 'por_works': (.67, .12, 'clerk'),
    'por_soul': (.75, .09, 'soul'), 'por_nan': (.69, .14, 'soul'), 'por_oddy': (.71, .09, 'soul'),
}


def portraits(raw):
    sprites, meta = {}, {}
    for pid in spec.PORTRAITS:
        zh, dist, kind = PORTRAIT_FACE[pid]
        a = post.load(os.path.join(raw, pid + '.png'))
        q = post.quantise(a, 'soul' if kind == 'soul' else 'world', gain=GAIN)
        if kind != 'soul':
            fx, fy = _face_px(64, 3.0, zh, dist)
            _face(q, fx, fy, 1.5, 'neutral', '27232f', hooded=True)
            if pid == 'por_pell':
                for sx in (-1, 1):
                    q[int(fy) - 2, int(fx + sx * 5) - 2:int(fx + sx * 5) + 2, :3] = rgb('fff3c4')
        else:
            fx, fy = _face_px(64, 3.0, zh, dist)
            _face(q, fx, fy, 1.5, 'neutral', '6a5484')
        post.add_outline(q, post.SOUL_OUT if kind == 'soul' else post.INK)
        bg = _bg(64, kind)
        m = q[..., 3] > 0
        bg[m] = q[m]
        sprites[pid] = bg
        meta[pid] = dict(origin=[0, 0], kind='portrait')
    for cs in spec.CASE_SOULS:
        a = post.load(os.path.join(raw, f'bust_case_{cs}.png'))
        base = post.quantise(a, 'soul', gain=GAIN)
        var = {'s001': 3, 's002': 1, 's003': 0, 's004': 0, 's007': 0, 's008': 3}[cs]
        zh = .64 * [1, .93, .88, 1.02][var] + .08
        fx, fy = _face_px(96, 4.2, zh, .095)
        for ex in spec.EXPRESSIONS:
            q = base.copy()
            _face(q, fx, fy, 2.2, ex, '43325c')
            post.add_outline(q, post.SOUL_OUT)
            bg = _bg(96, 'soul'); m = q[..., 3] > 0; bg[m] = q[m]
            sid = f'bust_case_{cs}_{ex}'
            sprites[sid] = bg; meta[sid] = dict(origin=[0, 0], kind='bust')
    return sprites, meta


def main():
    t0 = time.time()
    keep = None
    if '--keep-raw' in sys.argv:
        keep = sys.argv[sys.argv.index('--keep-raw') + 1]
    raw = keep or tempfile.mkdtemp(prefix='art_raw_')
    os.makedirs(raw, exist_ok=True)
    for g in ('tiles', 'walls', 'props', 'characters', 'fx', 'backdrops', 'ui', 'portraits', 'audio'):
        d = os.path.join(ASSETS, g)          # remove our outputs only (keep Godot's .import sidecars)
        for fn in (os.listdir(d) if os.path.isdir(d) else []):
            if fn.endswith(('.png', '.json', '.wav')):
                os.remove(os.path.join(d, fn))
    pool = ProcessPoolExecutor(max_workers=2)
    futs = [pool.submit(pil_tiles, 0), pool.submit(pil_ui, 0), pool.submit(pil_audio, 0)] + \
           [pool.submit(pil_backdrop, n) for n in spec.BACKDROPS]
    run_blender(raw)
    t_bl = time.time() - t0
    res = dict(f.result() for f in futs[:3])
    bds = dict(f.result() for f in futs[3:])
    pool.shutdown()

    errors = []
    groups = world_sprites(raw, res['tiles'])
    cs, cm = char_sheets(raw)
    groups['characters'] = (cs, cm)
    for g, (sprites, meta) in sorted(groups.items()):
        img = post.write_atlas(os.path.join(ASSETS, g), g, sprites, meta)
        bad = post.lint(img, allow_alpha=g in ('fx', 'characters'))
        if bad:
            errors.append(f'{g}: {bad} off-palette / non-binary-alpha pixels')
    # ui + portraits (UI tokens allowed)
    ui_meta = {k: dict(origin=[0, 0], kind='ui') for k in res['ui']}
    import ui as uimod
    for k, s in uimod.SLICES.items():
        ui_meta[k]['slice'] = s
    img = post.write_atlas(os.path.join(ASSETS, 'ui'), 'ui', res['ui'], ui_meta)
    if post.lint(img, ui=True, allow_alpha=True):
        errors.append('ui: off-palette pixels')
    ps, pm = portraits(raw)
    img = post.write_atlas(os.path.join(ASSETS, 'portraits'), 'portraits', ps, pm)
    if post.lint(img, ui=True):
        errors.append('portraits: off-palette pixels')
    # backdrops: one PNG + manifest each
    bdir = os.path.join(ASSETS, 'backdrops'); os.makedirs(bdir, exist_ok=True)
    for n, arr in sorted(bds.items()):
        Image.fromarray(arr, 'RGBA').save(os.path.join(bdir, n + '.png'), optimize=True)
        if post.lint(arr):
            errors.append(f'{n}: off-palette')
        with open(os.path.join(bdir, n + '.json'), 'w') as f:
            json.dump(dict(atlas=n, image=n + '.png', sprites={n: dict(rect=[0, 0, arr.shape[1], arr.shape[0]],
                      origin=[0, 0], kind='backdrop', tileable=(n == 'bg_void_fog'))}), f, indent=1)
    # completeness check against CONTRACTS §1.1
    ids = set()
    for root, _, files in os.walk(ASSETS):
        for fn in files:
            if fn.endswith('.json'):
                ids |= set(json.load(open(os.path.join(root, fn)))['sprites'])
    missing = [i for i in required_ids() if i not in ids]
    if missing:
        errors.append(f'missing ids: {missing}')
    amiss = [a for a in spec.AUDIO if not os.path.exists(os.path.join(ASSETS, 'audio', a + '.wav'))]
    if amiss:
        errors.append(f'missing audio: {amiss}')
    if not keep:
        shutil.rmtree(raw, ignore_errors=True)
    print(f'art build: {len(ids)} sprite ids, blender {t_bl:.1f}s, total {time.time() - t0:.1f}s')
    if errors:
        print('ERRORS:\n  ' + '\n  '.join(errors))
        raise SystemExit(1)


def required_ids():
    r = [f'floor_flag_{i}' for i in range(4)] + [f'floor_carpet_red_{i}' for i in range(3)] + \
        [f'floor_goldseam_{i}' for i in range(2)] + ['decal_inlay_ring']
    r += ['wall_plain_x', 'wall_plain_y', 'wall_window_gold_x', 'wall_window_gold_y', 'wall_window_red_x', 'wall_window_red_y',
          'wall_door_x', 'wall_door_y', 'wall_door_gilt_x', 'wall_door_gilt_y', 'wall_door_ember_x', 'wall_door_ember_y',
          'wall_corner', 'wall_kerb_x', 'wall_kerb_y', 'wall_kerb_corner', 'stairs_up', 'wall_plaque_x', 'works_hatch_y']
    r += ['brazier_0', 'wall_torch_x', 'wall_torch_y', 'banner_red', 'desk_clerk', 'desk_superior', 'dais', 'stool', 'bench',
          'bench_soul', 'lectern', 'shelf_books', 'shelf_empty', 'counter', 'rope_post', 'queue_rail_x', 'queue_post',
          'ticket_booth', 'statue_first_clerk', 'ivy_bench', 'desk_registrar']
    r += ['chr_player', 'chr_player_r2', 'chr_clerk_grey', 'chr_clerk_lilac', 'chr_archivist', 'chr_guard'] + \
         [f'chr_soul_{i}' for i in range(4)]
    r += ['shadow_blob', 'select_ring', 'light_pool_gold', 'light_pool_red', 'dust_mote', 'tap_marker']
    r += list(spec.BACKDROPS)
    r += ['icon_map', 'icon_journal', 'icon_pause', 'icon_soul', 'icon_obol', 'icon_order', 'icon_crest_r1', 'icon_crest_r2',
          'pip_full', 'pip_empty', 'icon_link', 'icon_halo', 'icon_flame', 'stamp_heaven', 'stamp_hell', 'stamp_rm0',
          'icon_lamp', 'icon_key', 'icon_quill', 'btn_action', 'parchment_9', 'panel_9']
    r += spec.PORTRAITS + [f'bust_case_{c}_{e}' for c in spec.CASE_SOULS for e in spec.EXPRESSIONS]
    return r


if __name__ == '__main__':
    main()
