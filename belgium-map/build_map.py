"""Build index.html from template.html + provinces.geojson.

Projects the province polygons to SVG path strings (equirectangular,
corrected for latitude) and injects them into the template.

    python3 belgium-map/build_map.py
"""
import json, math, pathlib

HERE = pathlib.Path(__file__).parent
KEYS = {
    "04000": "brussels", "10000": "antwerp", "20001": "flemish-brabant",
    "20002": "walloon-brabant", "30000": "west-flanders", "40000": "east-flanders",
    "50000": "hainaut", "60000": "liege", "70000": "limburg",
    "80000": "luxembourg", "90000": "namur",
}
W = 1000
LAT0 = 50.5
K = math.cos(math.radians(LAT0))

gj = json.loads((HERE / "provinces.geojson").read_text())
rings_by = {}
for f in gj["features"]:
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    rings_by[KEYS[f["properties"]["AdPrKey"]]] = polys

pts = [p for polys in rings_by.values() for poly in polys for ring in poly for p in ring]
minx = min(p[0] for p in pts) * K; maxx = max(p[0] for p in pts) * K
miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
pad = 20
s = (W - 2 * pad) / (maxx - minx)
H = round((maxy - miny) * s + 2 * pad)

def proj(p):
    return (pad + (p[0] * K - minx) * s, pad + (maxy - p[1]) * s)

def centroid(ring):
    a = cx = cy = 0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        c = x0 * y1 - x1 * y0
        a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    a /= 2
    return abs(a), cx / (6 * a), cy / (6 * a)

out = {}
for key, polys in rings_by.items():
    d = []
    best = (0, 0, 0)
    for poly in polys:
        for i, ring in enumerate(poly):
            pr = [proj(p) for p in ring]
            d.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pr) + "Z")
            if i == 0:
                c = centroid(pr)
                if c[0] > best[0]:
                    best = c
    out[key] = {"d": "".join(d), "cx": round(best[1], 1), "cy": round(best[2], 1)}

def lonlat(lon, lat):
    x, y = proj((lon, lat)); return [round(x, 1), round(y, 1)]

geo = {"w": W, "h": H, "shapes": out,
       # a few real cities, placed by real coordinates
       "cities": {
           "brussels": lonlat(4.3517, 50.8503), "antwerp": lonlat(4.4025, 51.2194),
           "ghent": lonlat(3.7174, 51.0543), "bruges": lonlat(3.2247, 51.2093),
           "leuven": lonlat(4.7005, 50.8798), "hasselt": lonlat(5.3378, 50.9307),
           "mons": lonlat(3.9523, 50.4542), "liege": lonlat(5.5797, 50.6326),
           "namur": lonlat(4.8719, 50.4674), "arlon": lonlat(5.8167, 49.6833),
           "wavre": lonlat(4.6075, 50.7170),
       }}
tpl = (HERE / "template.html").read_text()
body = tpl.replace("__GEO__", json.dumps(geo, separators=(",", ":")))
(HERE / "index.html").write_text(body)
print("wrote index.html", W, "x", H, len(body), "bytes")
