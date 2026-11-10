import sys; sys.path.insert(0,'.')
from post import *
tag = sys.argv[1]
ink = (13, 11, 18)
def contact(rows, name, k=5):
    W = sum(i.width for i in rows[0]) ; 
    Wm = max(sum(i.width for i in r) for r in rows); Hs = [max(i.height for i in r) for r in rows]
    c = Image.new('RGBA', (Wm, sum(Hs)), (60, 50, 80, 255)); y = 0
    for r, h in zip(rows, Hs):
        x = 0
        for i in r: c.alpha_composite(i, (x, y)); x += i.width
        y += h
    c.resize((c.width*k, c.height*k), Image.NEAREST).save(name)
t = Image.open(f'raw_tile_{tag}.png'); w = Image.open(f'raw_wall_{tag}.png')
qt = quantise(t); qw = quantise(w); qtd = quantise(t, dither=24); qwd = quantise(w, dither=24)
qt.save(f'q_tile_{tag}.png'); qw.save(f'q_wall_{tag}.png')
pad = lambda im, h: (lambda c: (c.alpha_composite(im, (0, h-im.height)), c)[1])(Image.new('RGBA', (im.width, h)))
contact([[pad(t,128), pad(qt,128), pad(qtd,128), w, qw, qwd]], f'c_env_{tag}.png')
rows = []
for nm in ('clerk', 'soul', 'guard'):
    raw = [Image.open(f'raw_{nm}_{tag}_{d}.png') for d in range(8)]
    q = [quantise(i, outline=ink, keep_alpha=False) for i in raw]
    for d, i in enumerate(q): i.save(f'q_{nm}_{tag}_{d}.png')
    rows += [raw, q]
contact(rows, f'c_char_{tag}.png', k=5)
import numpy as np
a = np.asarray(t); print('tile alpha uniq', np.unique(a[...,3])[:10], 'row0 opaque cols', np.where(a[0,:,3]>127)[0], 'row16', np.where(a[16,:,3]>127)[0][[0,-1]], 'row31', np.where(a[31,:,3]>127)[0][[0,-1]])
