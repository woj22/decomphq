// Building archetypes for the instanced city: houses, insulae, temples, basilicas, baths, rotundas, trees.
// Each builder writes its body into `b` and its windows into `win[0]` (lit at dusk) / `win[1]` (lit later).
// Buildings face local +Z (the street side). Units are metres.
import { rand, rr, pick } from './lowpoly.js';

export const WALLS = [0xefe2cc, 0xe8d3b0, 0xe6c9a0, 0xf2e6d2, 0xdcc2a0, 0xe9cfb6, 0xd9b48f, 0xf0dcc0, 0xe2b896];
export const ROOFS = [0xb5502f, 0xa8442a, 0xc0623a, 0x9e3f2a, 0xb85a36];
export const MARBLE = 0xf1e9dc, MARBLE2 = 0xe2d6c4, GOLD = 0xc8962e, CRIMSON = 0x8e1f24, DARK = 0x4e3a34;

// ------------------------------------------------------------------------------------------------ archetypes
export function roof(b, kind, w, d, z, col) {
  const ridge = 0x7e3324;
  if (kind === 'flat') {
    b.box(0, z + 0.05, 0, w, 0.1, d, 0xd6c4a6);
    b.box(0, z + 0.45, d / 2 - 0.1, w, 0.8, 0.2, MARBLE2); b.box(0, z + 0.45, -d / 2 + 0.1, w, 0.8, 0.2, MARBLE2);
    b.box(w / 2 - 0.1, z + 0.45, 0, 0.2, 0.8, d, MARBLE2); b.box(-w / 2 + 0.1, z + 0.45, 0, 0.2, 0.8, d, MARBLE2);
    if (rand() < 0.6) { // pergola with an awning
      for (const [px, pz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) b.box(px * w / 4, z + 1.2, pz * d / 4, 0.14, 2.3, 0.14, 0x6b4a2e);
      b.box(0, z + 2.4, 0, w / 2 + 0.6, 0.1, d / 2 + 0.6, pick([0xc8862d, 0x8e1f24, 0x7a5a3a, 0x3d6a5a]));
    }
    if (rand() < 0.5) cypress(b, rr(-w / 4, w / 4), z, rr(-d / 4, d / 4), rr(2.2, 3.5));
    return;
  }
  const o = 0.5, w2 = w / 2 + o, d2 = d / 2 + o;
  if (kind === 'gable') {
    const h = Math.min(w, d) * rr(0.16, 0.2);
    if (w >= d) {
      b.quad([-w2, z, d2], [w2, z, d2], [w2, z + h, 0], [-w2, z + h, 0], col);
      b.quad([w2, z, -d2], [-w2, z, -d2], [-w2, z + h, 0], [w2, z + h, 0], col);
      b.tri([w / 2, z, d / 2], [w / 2, z, -d / 2], [w / 2, z + h, 0], MARBLE2); b.tri([-w / 2, z, -d / 2], [-w / 2, z, d / 2], [-w / 2, z + h, 0], MARBLE2);
      b.tube([[-w2, z + h, 0], [w2, z + h, 0]], [0.13, 0.13], 4, ridge);
    } else {
      b.quad([w2, z, d2], [w2, z, -d2], [0, z + h, -d2], [0, z + h, d2], col);
      b.quad([-w2, z, -d2], [-w2, z, d2], [0, z + h, d2], [0, z + h, -d2], col);
      b.tri([-w / 2, z, d / 2], [w / 2, z, d / 2], [0, z + h, d / 2], MARBLE2); b.tri([w / 2, z, -d / 2], [-w / 2, z, -d / 2], [0, z + h, -d / 2], MARBLE2);
      b.tube([[0, z + h, -d2], [0, z + h, d2]], [0.13, 0.13], 4, ridge);
    }
    return;
  }
  // hip roof, low Roman pitch
  const h = Math.min(w, d) * rr(0.15, 0.19);
  if (w >= d) {
    const rx = w2 - d2;
    b.quad([-w2, z, d2], [w2, z, d2], [rx, z + h, 0], [-rx, z + h, 0], col);
    b.quad([w2, z, -d2], [-w2, z, -d2], [-rx, z + h, 0], [rx, z + h, 0], col);
    b.tri([w2, z, d2], [w2, z, -d2], [rx, z + h, 0], col); b.tri([-w2, z, -d2], [-w2, z, d2], [-rx, z + h, 0], col);
    if (rx > 0.2) b.tube([[-rx, z + h, 0], [rx, z + h, 0]], [0.13, 0.13], 4, ridge);
  } else {
    const rz = d2 - w2;
    b.quad([w2, z, d2], [w2, z, -d2], [0, z + h, -rz], [0, z + h, rz], col);
    b.quad([-w2, z, -d2], [-w2, z, d2], [0, z + h, rz], [0, z + h, -rz], col);
    b.tri([-w2, z, d2], [w2, z, d2], [0, z + h, rz], col); b.tri([w2, z, -d2], [-w2, z, -d2], [0, z + h, -rz], col);
    if (rz > 0.2) b.tube([[0, z + h, -rz], [0, z + h, rz]], [0.13, 0.13], 4, ridge);
  }
  b.poly([[-w2, z, -d2], [w2, z, -d2], [w2, z, d2], [-w2, z, d2]], col);
}

export function cypress(b, x, y, z, h) {
  b.prism(x, y, z, 0.12, 0.1, h * 0.15, 4, 0x5a4030);
  b.prism(x, y + h * 0.12, z, h * 0.14, h * 0.17, h * 0.3, 6, 0x2f5a32, false, true);
  b.prism(x, y + h * 0.42, z, h * 0.17, 0, h * 0.62, 6, 0x376a3a, false, false);
}
export function pine(b, x, y, z, h) {
  b.prism(x, y, z, 0.18, 0.12, h * 0.7, 5, 0x6a4a34, false, false);
  b.prism(x, y + h * 0.62, z, h * 0.22, h * 0.48, h * 0.16, 7, 0x3e6a38, false, true);
  b.prism(x, y + h * 0.78, z, h * 0.48, h * 0.18, h * 0.2, 7, 0x4a7a40, true, false);
}

// windows go into a separate builder so they can glow at night; `win` is [early, late] builders
function facade(b, win, w, d, H, floors, hf, side, wall, arcade) {
  const L = side % 2 === 0 ? w : d, D = side % 2 === 0 ? d : w;
  const rot = [0, Math.PI / 2, Math.PI, -Math.PI / 2][side];
  b.pushT(0, 0, 0, rot); win[0].pushT(0, 0, 0, rot); win[1].pushT(0, 0, 0, rot);
  const n = Math.max(1, Math.floor(L / 2.7));
  const off = D / 2 + 0.03;
  for (let f = 0; f < floors; f++) {
    for (let i = 0; i < n; i++) {
      const x = -L / 2 + (i + 0.5) * (L / n);
      const y0 = f * hf;
      if (f === 0 && arcade) {
        const ww = Math.min(2.0, L / n * 0.72), wh = hf * 0.78;
        const pts = [[x - ww / 2, y0 + 0.6, off], [x + ww / 2, y0 + 0.6, off]];
        for (let k = 0; k <= 5; k++) { const t = k / 5 * Math.PI; pts.push([x + Math.cos(t) * ww / 2, y0 + 0.6 + wh - ww / 2 + Math.sin(t) * ww / 2, off]); }
        pts.splice(2, 0); const arch = [pts[0], pts[1], ...pts.slice(2)];
        (rand() < 0.55 ? win[1] : b).poly(arch, DARK);
        if (rand() < 0.35) b.box(x, y0 + wh + 0.3, off + 0.5, ww + 0.4, 0.08, 1.0, pick([0xc8862d, 0x8e1f24, 0x3d6a5a, 0xd8c8a0]));
      } else if (f > 0 || !arcade) {
        const ww = 0.85, wh = hf * 0.48, yy = y0 + hf * 0.3;
        const r = rand();
        const tgt = r < 0.4 ? win[0] : r < 0.7 ? win[1] : b;
        tgt.quad([x - ww / 2, yy, off], [x + ww / 2, yy, off], [x + ww / 2, yy + wh, off], [x - ww / 2, yy + wh, off], DARK);
        b.box(x, yy - 0.06, off, ww + 0.25, 0.12, 0.16, MARBLE2);
        if (rand() < 0.3) { // shutters
          b.quad([x - ww / 2 - 0.42, yy, off + 0.01], [x - ww / 2, yy, off + 0.01], [x - ww / 2, yy + wh, off + 0.01], [x - ww / 2 - 0.42, yy + wh, off + 0.01], 0x5a6a48);
        }
      }
    }
  }
  b.pop(); win[0].pop(); win[1].pop();
}

export function house(b, win, w, d, floors, kind, wall, opts = {}) {
  const hf = rr(3.0, 3.4), H = floors * hf + 0.4;
  b.box(0, H / 2, 0, w, H, d, wall);
  b.box(0, 0.35, 0, w + 0.12, 0.7, d + 0.12, MARBLE2);
  for (let f = 1; f < floors; f++) b.box(0, f * hf + 0.05, 0, w + 0.14, 0.16, d + 0.14, MARBLE);
  b.box(0, H - 0.1, 0, w + 0.4, 0.3, d + 0.4, MARBLE);
  const arcade = opts.arcade ?? rand() < 0.55;
  for (let s = 0; s < 4; s++) facade(b, win, w, d, H, floors, hf, s, wall, arcade && s !== 2);
  if (opts.portico) {
    const n = Math.max(4, Math.floor(w / 2.4));
    for (let i = 0; i < n; i++) b.prism(-w / 2 + 0.6 + (w - 1.2) * i / (n - 1), 0, d / 2 + 1.6, 0.28, 0.24, hf * 1.1, 6, MARBLE);
    b.box(0, hf * 1.1 + 0.2, d / 2 + 1.6, w, 0.4, 0.8, MARBLE);
    b.box(0, hf * 1.1 + 0.42, d / 2 + 1.1, w, 0.08, 2.2, pick(ROOFS));
  }
  if (opts.balcony && floors > 1) {
    const bw = Math.min(w * 0.5, 4.5);
    b.box(0, hf + 0.1, d / 2 + 0.45, bw, 0.12, 0.9, 0x6b4a2e);
    b.box(0, hf + 0.6, d / 2 + 0.88, bw, 0.9, 0.06, 0x7a5636);
  }
  roof(b, kind, w, d, H, pick(ROOFS));
  return H;
}

export function temple(b, w, d, colh, gold = false, banners = false) {
  const pod = 2.0;
  b.box(0, pod / 2, 0, w + 2.4, pod, d + 2.4, MARBLE2);
  b.box(0, pod - 0.1, 0, w + 2.6, 0.2, d + 2.6, MARBLE);
  for (let i = 0; i < 7; i++) b.box(0, pod * (i + 1) / 14, d / 2 + 1.2 + (7 - i) * 0.42 - 0.2, w * 0.8, pod * (i + 1) / 7, 0.42, MARBLE);
  b.box(0, pod + colh / 2, -d * 0.08, w - 2.6, colh, d * 0.72, 0xefe3cf);
  b.box(0, pod + colh * 0.42, d * 0.28, 2.0, colh * 0.8, 0.1, 0x3a2a28);
  const r = colh * 0.07;
  const nf = Math.max(4, Math.round((w - 1) / (r * 4.6)) | 1) + 1;
  const ns = Math.max(3, Math.round((d - 1) / (r * 4.6)));
  const cols = [];
  for (let i = 0; i < nf; i++) { const x = -w / 2 + 0.7 + (w - 1.4) * i / (nf - 1); cols.push([x, d / 2 - 0.7], [x, -d / 2 + 0.7]); }
  for (let j = 1; j < ns - 1; j++) { const z = -d / 2 + 0.7 + (d - 1.4) * j / (ns - 1); cols.push([-w / 2 + 0.7, z], [w / 2 - 0.7, z]); }
  for (const [x, z] of cols) {
    b.prism(x, pod, z, r * 1.3, r * 1.15, 0.3, 8, MARBLE);
    b.prism(x, pod + 0.3, z, r, r * 0.86, colh - 0.6, 8, MARBLE, false, false);
    b.box(x, pod + colh - 0.15, z, r * 2.6, 0.3, r * 2.6, MARBLE);
  }
  const ez = pod + colh;
  b.box(0, ez + 0.35, 0, w, 0.7, d, MARBLE);
  b.box(0, ez + 0.95, 0, w + 0.05, 0.5, d + 0.05, CRIMSON);
  b.box(0, ez + 0.72, 0, w + 0.08, 0.08, d + 0.08, GOLD);
  b.box(0, ez + 1.3, 0, w + 0.4, 0.22, d + 0.4, MARBLE);
  const gz = ez + 1.4, gh = w * 0.18;
  for (const s of [1, -1]) {
    const z = s * (d / 2 + 0.2);
    const tri = [[-w / 2 - 0.2, gz, z], [w / 2 + 0.2, gz, z], [0, gz + gh, z]];
    b.poly(s > 0 ? tri : [...tri].reverse(), MARBLE);
    const inner = [[-w / 2 + 0.6, gz + 0.2, z + s * 0.06], [w / 2 - 0.6, gz + 0.2, z + s * 0.06], [0, gz + gh - 0.3, z + s * 0.06]];
    b.poly(s > 0 ? inner : [...inner].reverse(), CRIMSON);
  }
  const rc = gold ? 0xc99a45 : pick(ROOFS);
  b.quad([w / 2 + 0.2, gz, d / 2 + 0.2], [w / 2 + 0.2, gz, -d / 2 - 0.2], [0, gz + gh, -d / 2 - 0.2], [0, gz + gh, d / 2 + 0.2], rc);
  b.quad([-w / 2 - 0.2, gz, -d / 2 - 0.2], [-w / 2 - 0.2, gz, d / 2 + 0.2], [0, gz + gh, d / 2 + 0.2], [0, gz + gh, -d / 2 - 0.2], rc);
  b.prism(0, gz + gh, d / 2 + 0.2, 0.5, 0, 1.6, 4, GOLD);
  for (const s of [-1, 1]) b.prism(s * w / 2, gz, d / 2 + 0.2, 0.35, 0, 0.9, 4, GOLD);
  if (banners) for (const s of [-1, 1]) banner(b, s * w * 0.3, ez - 0.4, d / 2 + 0.1, w * 0.12, colh * 0.6);
}

export function banner(b, x, top, z, wd, len, col = CRIMSON) {
  const n = 4;
  for (let i = 0; i < n; i++) {
    const y0 = top - len * i / n, y1 = top - len * (i + 1) / n, s0 = Math.sin(i * 1.3) * 0.06, s1 = Math.sin((i + 1) * 1.3) * 0.06;
    b.quad([x - wd / 2, y1, z + s1], [x + wd / 2, y1, z + s1], [x + wd / 2, y0, z + s0], [x - wd / 2, y0, z + s0], col);
  }
  b.tri([x - wd / 2, top - len, z + 0.01], [x + wd / 2, top - len, z + 0.01], [x, top - len - wd * 0.5, z + 0.01], col);
  b.box(x, top + 0.06, z, wd + 0.3, 0.12, 0.12, GOLD);
  b.quad([x - wd * 0.2, top - len * 0.45, z + 0.04], [x + wd * 0.2, top - len * 0.45, z + 0.04], [x + wd * 0.2, top - len * 0.3, z + 0.04], [x - wd * 0.2, top - len * 0.3, z + 0.04], GOLD);
}

export function basilica(b, win) {
  const w = rr(34, 46), d = rr(16, 20);
  house(b, win, w, d, 2, 'gable', pick(WALLS), { arcade: true, portico: true });
  b.pushT(0, 0, 0); b.box(0, 9.5, 0, w * 0.8, 4, d * 0.45, MARBLE); b.pop();
  roof(b, 'gable', w * 0.8, d * 0.45, 11.5, pick(ROOFS));
  return [w + 2, d + 6];
}
export function rotunda(b) {
  const r = rr(9, 13);
  b.prism(0, 0, 0, r, r, 12, 14, MARBLE2);
  b.prism(0, 12, 0, r + 0.4, r + 0.4, 1.2, 14, MARBLE);
  b.loft([[13.2, r, r], [13.2 + r * 0.35, r * 0.85, r * 0.85], [13.2 + r * 0.65, r * 0.55, r * 0.55], [13.2 + r * 0.8, 0.8, 0.8]], 14, 0xc99a45, true, false);
  b.pushT(0, 0, r + 2); temple(b, r * 1.2, 6, 8, false, false); b.pop();
  return [2 * r + 2, 2 * r + 10];
}
export function baths(b, win) {
  const w = rr(40, 54), d = rr(30, 38);
  house(b, win, w, d, 2, 'flat', 0xe8d3b0, { arcade: true });
  for (const [x, z, r] of [[0, 0, 9], [-w * 0.3, 0, 6], [w * 0.3, 0, 6]]) {
    b.prism(x, 7, z, r, r, 3, 12, MARBLE2);
    b.loft([[10, r, r, x, z], [10 + r * 0.45, r * 0.8, r * 0.8, x, z], [10 + r * 0.75, r * 0.4, r * 0.4, x, z], [10 + r * 0.85, 0.5, 0.5, x, z]], 12, 0xd8c0a0, true, false);
  }
  return [w + 2, d + 2];
}
export function tower(b, win) {
  const s = rr(6, 8), h = rr(20, 28);
  house(b, win, s, s, Math.floor(h / 3.3), 'hip', pick(WALLS), { arcade: false });
  return [s + 2, s + 2];
}
export function domus(b, win) {
  const w = rr(14, 22), d = rr(12, 18);
  house(b, win, w, d, 1, 'hip', pick(WALLS), { arcade: false });
  b.pushT(w * 0.25, 0, d / 2 + 2.5); house(b, win, w * 0.35, 5, 1, 'gable', pick(WALLS), { arcade: false }); b.pop();
  b.box(0, 0.9, d / 2 + 5.5, w, 1.8, 0.4, pick(WALLS));
  cypress(b, -w * 0.3, 0, d / 2 + 3.5, rr(6, 9));
  return [w + 2, d + 8];
}
export function insula(b, win) {
  const w = rr(10, 18), d = rr(10, 16), fl = pick([2, 3, 3, 3, 4]);
  const kind = pick(['hip', 'hip', 'gable', 'flat']);
  house(b, win, w, d, fl, kind, pick(WALLS), { balcony: rand() < 0.45, portico: rand() < 0.12 });
  if (rand() < 0.35) { b.pushT(w / 2 + 2.4, 0, d * 0.15); house(b, win, 4.8, d * 0.6, Math.max(1, fl - 2), 'hip', pick(WALLS), { arcade: false }); b.pop(); }
  return [w + 6, d + 2];
}
export function small(b, win) {
  const w = rr(6, 10), d = rr(6, 10);
  house(b, win, w, d, pick([1, 2, 2]), pick(['hip', 'gable', 'flat', 'gable']), pick(WALLS), {});
  return [w + 1.5, d + 1.5];
}
export function far(b, win) {
  const w = rr(12, 28), d = rr(12, 26), h = rr(6, 15);
  b.box(0, h / 2, 0, w, h, d, pick(WALLS));
  for (let k = 0; k < Math.floor(h / 3.3); k++) {
    const t = rand() < 0.5 ? win[0] : win[1];
    t.quad([-w * 0.4, 1.5 + k * 3.3, d / 2 + 0.03], [w * 0.4, 1.5 + k * 3.3, d / 2 + 0.03], [w * 0.4, 2.4 + k * 3.3, d / 2 + 0.03], [-w * 0.4, 2.4 + k * 3.3, d / 2 + 0.03], DARK);
  }
  roof(b, rand() < 0.75 ? 'hip' : 'flat', w, d, h, pick(ROOFS));
  return [w + 2, d + 2];
}
export function treeClump(b) {
  for (let i = 0; i < 4; i++) (rand() < 0.6 ? cypress : pine)(b, rr(-4, 4), 0, rr(-4, 4), rr(6, 11));
  return [10, 10];
}

