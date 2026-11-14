"""Side-by-side: reference image (left) and a render (right) at the same height.
python3 imperium/blender/compare.py reference.png render.png out.png"""
import sys
from PIL import Image, ImageDraw

ref, ren, out = sys.argv[1:4]
a, b = Image.open(ref).convert("RGB"), Image.open(ren).convert("RGB")
H = 720
a = a.resize((int(a.width * H / a.height), H), Image.LANCZOS)
b = b.resize((int(b.width * H / b.height), H), Image.LANCZOS)
c = Image.new("RGB", (a.width + b.width + 12, H + 40), (30, 24, 28))
c.paste(a, (0, 40))
c.paste(b, (a.width + 12, 40))
d = ImageDraw.Draw(c)
d.text((10, 12), "REFERENCE", fill=(240, 220, 190))
d.text((a.width + 22, 12), "RENDER", fill=(240, 220, 190))
c.save(out)
print("compare", out)
