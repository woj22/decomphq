"""Sprite specification shared by the Blender jobs (render side) and the post/pack side (pure python, no bpy).

Every world sprite: id -> dict(group, size=(w,h), origin=(x,y), kind, [solid, frames, fps, footprint, additive, ...]).
`src` says who draws it: 'blender' (tools/blender/jobs.py) or 'pil' (tools/procgen/*.py).
"""
DIRS = ['sw', 'w', 'nw', 'n', 'ne', 'e', 'se', 's']
SPRITES = {}


def S(sid, group, size, origin, kind, src='blender', job=None, **kw):
    d = dict(group=group, size=tuple(size), origin=tuple(origin), kind=kind, src=src, job=job)
    d.update(kw)
    SPRITES[sid] = d


# ---------------------------------------------------------------- tiles (numpy-drawn, exact pixel control)
for i in range(4):
    S(f'floor_flag_{i}', 'tiles', (64, 32), (32, 16), 'floor', 'pil')
for i in range(2):
    S(f'floor_flag_edge_{i}', 'tiles', (64, 48), (32, 16), 'floor', 'pil')
for i in range(3):
    S(f'floor_carpet_red_{i}', 'tiles', (64, 32), (32, 16), 'floor', 'pil')
for i in range(2):
    S(f'floor_goldseam_{i}', 'tiles', (64, 32), (32, 16), 'floor', 'pil')
S('decal_inlay_ring', 'tiles', (256, 128), (128, 64), 'decal', 'pil', footprint=[4, 4])

# ---------------------------------------------------------------- walls
W = dict(size=(64, 128), origin=(32, 112), kind='wall', solid=True)
for ax in 'xy':
    S(f'wall_plain_{ax}', 'walls', job='walls', **W)
    S(f'wall_window_gold_{ax}', 'walls', job='windows', **W)
    S(f'wall_window_red_{ax}', 'walls', job='windows', **W)
    S(f'wall_door_{ax}', 'walls', job='doors', **dict(W, kind='door'))
    S(f'wall_door_gilt_{ax}', 'walls', job='doors', **dict(W, kind='door'))
    S(f'wall_door_ember_{ax}', 'walls', job='doors', **dict(W, kind='door'))
S('wall_corner', 'walls', job='walls', **W)
S('wall_plaque_x', 'walls', job='walls', **W)
S('works_hatch_y', 'walls', job='walls', **W)
for ax in 'xy':
    S(f'wall_kerb_{ax}', 'walls', (64, 48), (32, 32), 'kerb', job='kerbs', solid=True, underlay='floor_flag_0')
S('wall_kerb_corner', 'walls', (64, 48), (32, 32), 'kerb', job='kerbs', solid=True, underlay='floor_flag_0')
S('stairs_up', 'walls', (64, 80), (32, 64), 'stair', job='kerbs', height_hu=2)

# ---------------------------------------------------------------- props
P = dict(kind='prop', solid=True, outline=True)
S('brazier_0', 'props', (32, 48), (16, 40), job='brazier', frames=4, fps=6, emissive=True, **P)
S('wall_torch_x', 'props', (32, 48), (37, 66), job='torch', frames=4, fps=6, **dict(P, solid=False))
S('wall_torch_y', 'props', (32, 48), (-5, 66), job='torch', frames=4, fps=6, **dict(P, solid=False))
S('banner_red', 'props', (32, 112), (16, 104), job='banner', frames=2, fps=2, **P)
S('desk_clerk', 'props', (64, 64), (32, 48), job='desks', **P)
S('desk_clerk_tray1', 'props', (64, 64), (32, 48), job='desks', **P)
S('desk_clerk_tray2', 'props', (64, 64), (32, 48), job='desks', **P)
S('desk_superior', 'props', (64, 80), (32, 60), job='desks', **P)
S('desk_registrar', 'props', (64, 80), (32, 60), job='desks', **P)
S('dais', 'props', (64, 48), (32, 32), job='furn', height_hu=1, **dict(P, outline=False))
S('stool', 'props', (32, 32), (16, 24), job='furn', **P)
S('bench', 'props', (64, 56), (32, 40), job='furn', **P)
S('bench_soul', 'props', (64, 64), (32, 48), job='furn', **P)
S('ivy_bench', 'props', (64, 56), (32, 40), job='furn', **P)
S('lectern', 'props', (32, 56), (16, 48), job='furn', **P)
S('shelf_books', 'props', (64, 128), (32, 104), job='shelves', **P)
S('shelf_empty', 'props', (64, 128), (32, 104), job='shelves', **P)
S('counter', 'props', (64, 64), (32, 44), job='furn', **P)
S('rope_post', 'props', (64, 48), (32, 36), job='rails', **P)
S('queue_rail_x', 'props', (64, 48), (32, 34), job='rails', **P)
S('queue_post', 'props', (16, 32), (8, 26), job='rails', **P)
S('ticket_booth', 'props', (64, 128), (32, 104), job='booth', **P)
S('statue_first_clerk', 'props', (128, 192), (64, 160), job='statue', footprint=[2, 2], **P)

# ---------------------------------------------------------------- fx (numpy)
S('shadow_blob', 'fx', (32, 16), (16, 8), 'fx', 'pil')
S('select_ring', 'fx', (32, 16), (16, 8), 'fx', 'pil', frames=4, fps=8)
S('light_pool_gold', 'fx', (192, 96), (96, 48), 'fx', 'pil', additive=True)
S('light_pool_red', 'fx', (192, 96), (96, 48), 'fx', 'pil', additive=True)
S('dust_mote', 'fx', (8, 8), (4, 4), 'fx', 'pil', frames=4, fps=6)
S('tap_marker', 'fx', (16, 8), (8, 4), 'fx', 'pil', frames=4, fps=10)

# ---------------------------------------------------------------- characters
CHAR_ANIMS = {
    'std':   [('idle', 2, 2), ('walk', 4, 8), ('work', 2, 2)],
    'guard': [('idle', 2, 2), ('walk', 4, 8), ('attention', 1, 1)],
    'soul':  [('idle', 4, 4), ('walk', 4, 8)],
}
CHARS = {
    'chr_player': 'std', 'chr_player_r2': 'std', 'chr_clerk_grey': 'std', 'chr_clerk_lilac': 'std',
    'chr_archivist': 'std', 'chr_guard': 'guard',
    'chr_soul_0': 'soul', 'chr_soul_1': 'soul', 'chr_soul_2': 'soul', 'chr_soul_3': 'soul',
}
CHAR_CELL = {'guard': (32, 64)}
CHAR_ORIGIN = {'guard': (16, 56)}


def char_cell(cid):
    t = CHARS[cid]
    return CHAR_CELL.get(t, (32, 56)), CHAR_ORIGIN.get(t, (16, 48))


# ---------------------------------------------------------------- portraits / busts (rendered from the rig)
CASE_SOULS = ['s001', 's002', 's003', 's004', 's007', 's008']
EXPRESSIONS = ['neutral', 'distressed', 'relieved']
PORTRAITS = ['por_marrow', 'por_pell', 'por_wren', 'por_grist', 'por_registrar', 'por_works', 'por_soul', 'por_nan', 'por_oddy']

AUDIO = ['sfx_tap', 'sfx_page', 'sfx_quill', 'sfx_door', 'sfx_stamp', 'sfx_bell', 'sfx_link',
         'amb_court', 'amb_hall', 'amb_records', 'amb_booths', 'amb_chamber']
BACKDROPS = {'bg_heaven_sky': (640, 360), 'bg_heaven_skyline': (960, 240), 'bg_hell_sky': (640, 360),
             'bg_hell_skyline': (960, 240), 'bg_void_fog': (256, 128)}
