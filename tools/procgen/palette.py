"""Border-24 palette (PROJECT §7.1) and UI tokens (§9.5) — the single palette source for the art build."""
import numpy as np

RAMPS = {
    'ink':   ['0d0b12', '1a1722', '27232f', '37323f', '4b4654', '66616e', '8a8591', 'b5b0b8'],
    'purple': ['2a1f3d', '43325c', '6a5484', '9a86ad'],
    'gold':  ['6b4a1e', 'a8742a', 'e0a83e', 'f6d67a', 'fff3c4'],
    'red':   ['3a0f14', '74161b', 'b3261e', 'e8552b'],
    'wood':  ['5a3f2e'],
    'soul':  ['cfe0e6', '8fa3b3'],
}
BORDER24 = [h for r in RAMPS.values() for h in r]
assert len(BORDER24) == 24
EMISSIVE = ['fff3c4', 'f6d67a', 'e8552b']
SOUL_ONLY = ['cfe0e6', '8fa3b3']
UI_EXTRA = ['e6d9b8', 'cbb98f', '2a2320', 'ede6d6', 'a59e90', '8b3fd9']  # parchment, shade, ink, text, dim, RM0 violet


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lin(h):
    """hex -> linear RGB (for Blender materials)."""
    return tuple(((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in rgb(h))


C = {}  # named shortcuts: C['ink0'] .. C['ink7'], C['gold2'] ...
for name, ramp in RAMPS.items():
    for i, h in enumerate(ramp):
        C[f'{name}{i}'] = rgb(h)

PAL = np.array([rgb(h) for h in BORDER24], float)
PAL_UI = np.array([rgb(h) for h in BORDER24 + UI_EXTRA], float)
AMBIENT = np.array(rgb('9e94cc'), float) / 255.0
