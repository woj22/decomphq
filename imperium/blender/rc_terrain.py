"""Stage 3: the terrain - a faceted heightfield following rc_common.terrain_z over the view wedge."""
import math

from mathutils import Matrix

import rc_common as R
from city import Acc


def build_terrain():
    R.clear("Terrain")
    a = Acc("Terrain")
    half = math.radians(64)
    # radial rings with geometric spacing: fine near the palace, coarse toward the horizon
    radii = [40.0]
    while radii[-1] < 16000:
        radii.append(radii[-1] * 1.045 + 3.0)
    na = 70
    grid = []
    for r in radii:
        row = []
        for i in range(na + 1):
            t = -half + 2 * half * i / na
            x, y = -math.sin(t) * r, -math.cos(t) * r
            row.append((x, y, R.terrain_z(x, y) - 0.05))
        grid.append(row)
    for j in range(len(radii) - 1):
        for i in range(na):
            p = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            zc = sum(q[2] for q in p) / 4 - R.CITY
            col = "c8b28e" if zc < 30 else "b9a47e" if zc < 80 else "a8986e"
            a.poly(p[::-1], a.key(col, 0.95))
    a.T = Matrix.Identity(4)
    o = a.build()
    R.move_to(o, "Terrain")
    print("terrain faces:", len(o.data.polygons))
    return o
