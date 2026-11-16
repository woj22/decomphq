"""Copy the KayKit models the planet uses (CC0, by Kay Lousberg - www.kaylousberg.com) into the Godot project.

    git clone --depth 1 https://github.com/KayKit-Game-Assets/<pack> <SRC>/<pack>   (see PACKS)
    python3 alien_planet/tools/sync_kaykit.py <SRC>

Only the listed models (plus their .bin buffers and textures) are copied, to keep the mobile build small.
"""
import glob, json, os, shutil, sys

PACKS = {
    'medieval': ('kaykit-medieval-hexagon-pack-1.0', [
        'building_tavern_red', 'building_home_A_red', 'building_home_B_red', 'building_grain', 'building_windmill_red',
        'building_well_red', 'building_market_red', 'building_lumbermill_red', 'building_blacksmith_red',
        'fence_wood_straight', 'fence_wood_straight_gate', 'trees_A_medium', 'trees_B_large', 'trees_A_small',
        'tree_single_A', 'tree_single_B', 'crate_A_big', 'crate_B_small', 'crate_long_A', 'barrel', 'sack',
        'wheelbarrow', 'tent', 'flag_red', 'pallet', 'bucket_water', 'resource_lumber']),
    'city': ('kaykit-city-builder-bits-1.0', ['watertower', 'bench', 'box_A', 'box_B']),
    'space': ('kaykit-space-base-bits-1.0', [
        'spacetruck', 'spacetruck_trailer', 'spacetruck_large', 'windturbine_tall', 'basemodule_A', 'cargodepot_A',
        'containers_A', 'containers_B', 'lights', 'drill_structure', 'solarpanel', 'cargo_A_stacked']),
    'proto': ('kaykit-prototype-bits-1.0', ['Pallet_Small_Decorated_A', 'Barrel_A']),
    'adventurers': ('kaykit-character-pack-adventures-1.0', ['Knight', 'Barbarian', 'Mage', 'Rogue', 'Rogue_Hooded']),
    'skeletons': ('kaykit-character-pack-skeletons-1.0', ['Skeleton_Warrior', 'Skeleton_Minion']),
}
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'godot', 'assets', 'kaykit')


def main(src):
    for key, (repo, names) in PACKS.items():
        out = os.path.join(DST, key)
        os.makedirs(out, exist_ok=True)
        files = glob.glob(os.path.join(src, repo, '**', 'gltf', '**', '*.gl*'), recursive=True)
        files = [f for f in files if '/fbx/' not in f]
        for n in names:
            cand = [f for f in files if os.path.basename(f).rsplit('.', 1)[0] == n]
            if not cand:
                raise SystemExit(f'missing {n} in {repo}')
            f = sorted(cand, key=len)[0]
            shutil.copy(f, out)
            if f.endswith('.gltf'):
                j = json.load(open(f))
                for b in j.get('buffers', []) + j.get('images', []):
                    if b.get('uri') and not b['uri'].startswith('data:'):
                        shutil.copy(os.path.join(os.path.dirname(f), b['uri']), out)
        lic = glob.glob(os.path.join(src, repo, 'LICENSE*'))
        if lic:
            shutil.copy(lic[0], os.path.join(out, 'LICENSE.txt'))
        print(key, len(names), 'models')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/home/user/kaykit-game-assets')
