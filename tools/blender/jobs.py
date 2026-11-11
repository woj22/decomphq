"""Blender render worker. Usage: python3 tools/blender/jobs.py <rawdir> <job> [<job> ...]

Writes raw RGBA renders (unquantised) into <rawdir>; tools/procgen/post.py turns them into palette sprites.
Raw names: static `<id>.png`; animated `<id>__f<i>.png`; characters `<id>__<anim>_<f>_<d>.png`;
busts/portraits `<id>.png` (faces are drawn in post).
"""
import math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'procgen'))
from lib import Ctx, HU, ZPX  # noqa: E402
import kit  # noqa: E402
from rig import Rig, DemonRig, CHARS  # noqa: E402
from spec import SPRITES, CHAR_ANIMS, CHARS as CHAR_TYPES, char_cell, CASE_SOULS, PORTRAITS  # noqa: E402

SAMPLES = 64


def shot(ctx, sid, suffix=''):
    sp = SPRITES[sid]
    ctx.render(sid + suffix, *sp['size'], sp['origin'])
    ctx.new_kit()


def j_walls(ctx):
    for ax in 'xy':
        kit.wall(ctx, ax); shot(ctx, f'wall_plain_{ax}')
    kit.corner(ctx); shot(ctx, 'wall_corner')
    kit.wall(ctx, 'x', plaque=True); shot(ctx, 'wall_plaque_x')
    kit.wall(ctx, 'y', hatch=True); shot(ctx, 'works_hatch_y')


def j_windows(ctx):
    for ax in 'xy':
        for g in ('gold', 'red'):
            kit.wall(ctx, ax, 'window', glass=g); shot(ctx, f'wall_window_{g}_{ax}')


def j_doors(ctx):
    for ax in 'xy':
        for st, nm in (('plain', 'wall_door'), ('gilt', 'wall_door_gilt'), ('ember', 'wall_door_ember')):
            kit.wall(ctx, ax, 'door', door=st); shot(ctx, f'{nm}_{ax}')


def j_kerbs(ctx):
    kit.kerb(ctx, 'x'); shot(ctx, 'wall_kerb_x')
    kit.kerb(ctx, 'y'); shot(ctx, 'wall_kerb_y')
    kit.kerb(ctx, 'c'); shot(ctx, 'wall_kerb_corner')
    kit.stairs(ctx); shot(ctx, 'stairs_up')
    kit.kerb_door(ctx, 'x'); shot(ctx, 'wall_kerb_door_x')
    kit.kerb_door(ctx, 'y'); shot(ctx, 'wall_kerb_door_y')


def j_brazier(ctx):
    for f in range(4):
        kit.brazier(ctx, f); shot(ctx, 'brazier_0', f'__f{f}')


def j_torch(ctx):
    for ax in 'xy':
        for f in range(4):
            kit.wall_torch(ctx, ax, f); shot(ctx, f'wall_torch_{ax}', f'__f{f}')


def j_banner(ctx):
    for f in range(2):
        kit.banner(ctx, f); shot(ctx, 'banner_red', f'__f{f}')


def j_desks(ctx):
    for t, sid in enumerate(('desk_clerk', 'desk_clerk_tray1', 'desk_clerk_tray2')):
        kit.desk(ctx, tray=t); shot(ctx, sid)
    kit.desk(ctx, tray=1, superior=True); shot(ctx, 'desk_superior')
    kit.desk_registrar(ctx); shot(ctx, 'desk_registrar')


def j_furn(ctx):
    kit.dais(ctx); shot(ctx, 'dais')
    kit.stool(ctx); shot(ctx, 'stool')
    kit.bench(ctx); shot(ctx, 'bench')
    kit.bench(ctx, soul=True); shot(ctx, 'bench_soul')
    kit.bench(ctx, ivy=True); shot(ctx, 'ivy_bench')
    kit.lectern(ctx); shot(ctx, 'lectern')
    kit.counter(ctx); shot(ctx, 'counter')


def j_quarters(ctx):
    kit.bed(ctx); shot(ctx, 'bed')
    kit.bed(ctx, sleeper=True); shot(ctx, 'bed_sleeper')
    kit.bed(ctx, soul=True); shot(ctx, 'bed_soul')
    kit.washstand(ctx); shot(ctx, 'washstand')
    for ax in 'xy':
        kit.cell_bars(ctx, ax); shot(ctx, f'cell_bars_{ax}')
        kit.cell_door(ctx, ax); shot(ctx, f'cell_door_{ax}')
    for mk in range(16):
        kit.cell_bars_mask(ctx, mk); shot(ctx, f'cell_bars_m{mk}')
    for mk in (5, 10):
        kit.cell_bars_mask(ctx, mk, door=True); shot(ctx, f'cell_door_m{mk}')


def j_hell(ctx):
    kit.hell_gate(ctx); shot(ctx, 'hell_gate')
    kit.hell_gate(ctx, opened=True); shot(ctx, 'hell_gate_open')
    kit.chain_post(ctx); shot(ctx, 'chain_post')
    for f in range(4):
        kit.brazier_hell(ctx, f); shot(ctx, 'brazier_hell', f'__f{f}')
    kit.crystal_pedestal(ctx); shot(ctx, 'crystal_pedestal')
    kit.cauldron(ctx); shot(ctx, 'cauldron')


def j_shelves(ctx):
    kit.shelf(ctx); shot(ctx, 'shelf_books')
    kit.shelf(ctx, empty=True); shot(ctx, 'shelf_empty')


def j_rails(ctx):
    kit.rope_post(ctx); shot(ctx, 'rope_post')
    kit.queue_rail(ctx); shot(ctx, 'queue_rail_x')
    kit.queue_post(ctx); shot(ctx, 'queue_post')


def j_booth(ctx):
    kit.ticket_booth(ctx); shot(ctx, 'ticket_booth')


def j_statue(ctx):
    kit.statue(ctx); shot(ctx, 'statue_first_clerk')


def j_char(ctx, cid):
    (cw, ch), origin = char_cell(cid)
    rig = (DemonRig if CHARS[cid].get('demon') else Rig)(ctx, CHARS[cid])
    for anim, n, _fps in CHAR_ANIMS[CHAR_TYPES[cid]]:
        for f in range(n):
            rig.pose(anim, f)
            for d in range(8):
                rig.face(d)
                ctx.render(f'{cid}__{anim}_{f}_{d}', cw, ch, origin)
    ctx.new_kit()


# ---- busts & portraits: same rig, magnified camera, facing the viewer (dir 's' = 7)
BUST_SOULS = {  # case soul -> (variant, accessory)
    's001': (3, 'bun'), 's002': (1, 'sideburns'), 's003': (0, 'flatcap'),
    's004': (0, 'helmet'), 's007': (0, 'bowler'), 's008': (3, 'kerchief'),
}
PORTRAIT_RIGS = {
    'por_marrow': ('chr_clerk_lilac', dict(hem='e0a83e')), 'por_pell': ('chr_archivist', {}),
    'por_wren': ('chr_clerk_grey', {}), 'por_grist': ('chr_guard', {}), 'por_registrar': ('chr_clerk_grey', dict(hood='pointed', robe='27232f')),
    'por_works': ('chr_clerk_grey', dict(hem='a8742a')), 'por_soul': ('chr_soul_0', {}),
    'por_nan': ('chr_soul_2', dict(acc='bun')), 'por_oddy': ('chr_soul_1', dict(acc='tophat')),
}


def accessory(ctx, rig, acc):
    hd = rig.head
    m2 = ctx.m('8fa3b3', .2); m1 = ctx.m('cfe0e6', .25)
    if acc == 'bun':
        ctx.sphere(.055, (0, .08, .1), m2, parent=hd); ctx.sphere(.1, (0, .02, .05), m2, scale=(1.02, 1, .9), parent=hd)
    elif acc == 'sideburns':
        for sx in (-1, 1):
            ctx.sphere(.04, (sx * .085, -.01, -.02), m2, scale=(.6, 1, 1.4), parent=hd)
        ctx.box((-.06, -.14, -.25), (.06, -.08, -.12), m2, parent=rig.body)  # cravat
    elif acc == 'flatcap':
        ctx.sphere(.105, (0, .0, .07), m2, scale=(1.05, 1.1, .55), parent=hd)
        ctx.cyl(.07, .08, .05, .07, m2, seg=10, loc=(0, -.09), scale=(1.3, 1), parent=hd)
    elif acc == 'helmet':
        ctx.sphere(.115, (0, 0, .07), m2, scale=(1, 1, .6), parent=hd)
        ctx.cyl(.17, .15, .04, .06, m2, seg=14, parent=hd)
    elif acc == 'bowler':
        ctx.sphere(.09, (0, 0, .1), m2, scale=(1, 1, .9), parent=hd)
        ctx.cyl(.14, .14, .07, .085, m2, seg=14, parent=hd)
    elif acc == 'tophat':
        ctx.cyl(.08, .085, .08, .26, m2, seg=12, parent=hd)
        ctx.cyl(.14, .14, .07, .09, m2, seg=14, parent=hd)
    elif acc == 'kerchief':
        ctx.sphere(.106, (0, .015, .045), m2, scale=(1.02, 1.02, 1.0), parent=hd)
        ctx.sphere(.04, (0, .11, -.02), m2, parent=hd)
        ctx.sphere(.092, (0, -.025, .0), m1, parent=hd)


BUST_TZ = .7


def bust_shot(ctx, name, size, zoom):
    # head centre at z~.66 -> place it at ~40% height
    w = h = size
    s = ctx.s
    s.render.resolution_x = w; s.render.resolution_y = h
    from lib import R_VEC, U_VEC, D_VEC, PPU
    s.camera.data.ortho_scale = size / (PPU * zoom)
    target = (0, 0, BUST_TZ)
    from mathutils import Vector
    s.camera.location = Vector(target) + D_VEC * 40 - U_VEC * (0.06)
    s.render.filepath = os.path.join(ctx.outdir, name + '.png')
    import bpy
    bpy.ops.render.render(write_still=True)


def j_busts(ctx):
    for cs in CASE_SOULS:
        var, acc = BUST_SOULS[cs]
        rig = Rig(ctx, CHARS[f'chr_soul_{var}'])
        accessory(ctx, rig, acc)
        rig.pose('idle', 0); rig.face(7)
        bust_shot(ctx, f'bust_case_{cs}', 96, 4.2)
        ctx.new_kit()


def j_portraits(ctx):
    for pid in PORTRAITS:
        base, extra = PORTRAIT_RIGS[pid]
        extra = dict(extra)
        acc = extra.pop('acc', None)
        rig = Rig(ctx, CHARS[base], extra)
        if acc:
            accessory(ctx, rig, acc)
        rig.pose('idle', 0); rig.face(7)
        bust_shot(ctx, pid, 64, 3.0)
        ctx.new_kit()


JOBS = {n[2:]: f for n, f in globals().items() if n.startswith('j_') and n != 'j_char'}


def run(job, ctx):
    if job.startswith('char:'):
        j_char(ctx, job[5:])
    else:
        JOBS[job](ctx)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    ctx = Ctx(out, samples=SAMPLES, threads=int(os.environ.get('ART_THREADS', '1')))
    for job in sys.argv[2:]:
        t = time.time()
        run(job, ctx)
        print(f'JOB {job} {time.time() - t:.2f}s', flush=True)


if __name__ == '__main__':
    main()
