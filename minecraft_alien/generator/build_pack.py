"""Build the Bedrock behaviour pack: alien villages and farmlands as .mcstructure tiles + build functions.

    python3 minecraft_alien/generator/build_pack.py
Output (minecraft_alien/):
    AlienWorlds.mcpack           tap on a phone / double-click to import into Minecraft Bedrock
    maps/<layout>_map.png        top-down map (16-block chunk grid)
    maps/<layout>_preview.png    isometric preview
"""
import json, math, os, shutil, sys, time, uuid, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from layouts import LAYOUTS  # noqa: E402

OUT = os.path.dirname(HERE)
PACK = os.path.join(OUT, 'build', 'AlienWorlds_BP')
TILE = 64
NS = 'alien'
# Fixed UUIDs so re-imports update the same pack instead of adding a duplicate.
HEADER_UUID = 'b2a4f6d1-7c3e-4e8a-9f21-3d5c7a9e1b42'
MODULE_UUID = 'c9e1d3f5-2b4a-4c6d-8e0f-1a3b5c7d9e2f'


def main(only=None):
    t0 = time.time()
    if os.path.exists(PACK):
        shutil.rmtree(PACK)
    os.makedirs(os.path.join(PACK, 'structures', NS))
    os.makedirs(os.path.join(PACK, 'functions', NS))
    os.makedirs(os.path.join(OUT, 'maps'), exist_ok=True)
    index = []
    for key, (fn, title, desc) in LAYOUTS.items():
        if only and key not in only:
            continue
        v = fn()
        nx, nz = math.ceil(v.w / TILE), math.ceil(v.d / TILE)
        tiles = []
        for i in range(nx):
            for j in range(nz):
                w = min(TILE, v.w - i * TILE)
                d = min(TILE, v.d - j * TILE)
                name = f'{key}_{i}_{j}'
                with open(os.path.join(PACK, 'structures', NS, name + '.mcstructure'), 'wb') as fh:
                    fh.write(v.to_mcstructure(i * TILE, j * TILE, w, d))
                tiles.append((name, i * TILE, j * TILE))
        # functions: stand in the middle of a flat area, run prepare, wait a few seconds, run build
        hx, hz = v.w // 2, v.d // 2
        dy = -(v.G + 1)     # ground surface ends up just under your feet
        fdir = os.path.join(PACK, 'functions', NS, key)
        os.makedirs(fdir)
        pad = 8
        with open(os.path.join(fdir, 'prepare.mcfunction'), 'w') as fh:
            fh.write(f'# {title}: load the chunks of the {v.w} x {v.d} area centred on you (max 100 chunks)\n')
            fh.write(f'tickingarea add ~-{hx + pad} ~ ~-{hz + pad} ~{v.w - hx + pad} ~ ~{v.d - hz + pad} alien_{key} true\n')
            fh.write(f'say Preparing {title}... wait ~5 seconds, then run: /function {NS}/{key}/build\n')
        with open(os.path.join(fdir, 'build.mcfunction'), 'w') as fh:
            fh.write(f'# {title}: {desc}\n# Builds a {v.w} x {v.h} x {v.d} area centred on you; ground level = your feet.\n')
            for name, x0, z0 in tiles:
                fh.write(f'structure load {NS}:{name} ~{x0 - hx} ~{dy} ~{z0 - hz}\n')
            fh.write(f'say {title} built. Run /function {NS}/{key}/finish when it has all appeared.\n')
        with open(os.path.join(fdir, 'finish.mcfunction'), 'w') as fh:
            fh.write(f'tickingarea remove alien_{key}\nsay Ticking area removed.\n')
        v.map_png(os.path.join(OUT, 'maps', f'{key}_map.png'), 4, f'{title}  {v.w}x{v.d}  (grid = 16-block chunks)')
        v.iso_png(os.path.join(OUT, 'maps', f'{key}_preview.png'), 3)
        blocks = int((v.a != 0).sum())
        index.append(dict(key=key, title=title, desc=desc, size=[v.w, v.h, v.d], tiles=len(tiles), blocks=blocks,
                          palette=v.names[1:]))
        print(f'{key:16s} {v.w}x{v.h}x{v.d} tiles={len(tiles)} solid={blocks} palette={len(v.names)} ({time.time() - t0:.1f}s)')
    manifest = {
        'format_version': 2,
        'header': {'name': 'Alien Worlds: villages & farmlands', 'description':
                   'Alien villages and large farmlands as structures. /function alien/<place>/prepare then build.',
                   'uuid': HEADER_UUID, 'version': [1, 0, 0], 'min_engine_version': [1, 19, 0]},
        'modules': [{'type': 'data', 'uuid': MODULE_UUID, 'version': [1, 0, 0]}],
    }
    with open(os.path.join(PACK, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)
    shutil.copy(os.path.join(OUT, 'maps', f'{list(LAYOUTS)[0]}_preview.png'), os.path.join(PACK, 'pack_icon.png'))
    mcpack = os.path.join(OUT, 'AlienWorlds.mcpack')
    with zipfile.ZipFile(mcpack, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(PACK):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, PACK))
    with open(os.path.join(OUT, 'maps', 'index.json'), 'w') as fh:
        json.dump(index, fh, indent=1)
    print(f'wrote {mcpack} ({os.path.getsize(mcpack) / 1e6:.2f} MB) in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main(sys.argv[1:] or None)
