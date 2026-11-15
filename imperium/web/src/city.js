// The imperial capital, laid out from the painted overhead map (reference/city_map.png -> data/citymap.json).
// Land use comes from the map grid: R roofs (city blocks), S streets, W water, T trees, F fields, V villas.
// Landmarks are hand-placed at their map positions. World: y up, +X east, +Z south, 2 m per map pixel.
import * as THREE from 'three';
import { Builder, MAT, mesh, rand, rr, pick, setSeed } from './lowpoly.js';
import * as A from './archetypes.js';

export const PX = 2.0;
export const px2w = (px, py) => [(px - 760) * PX, (py - 450) * PX];
let MAP = null;
export async function loadMap(url) { MAP = await (await fetch(url)).json(); return MAP; }

export const PALACE = px2w(465, 165);        // centre of the Palatine plateau
export const CAPITOL = px2w(760, 365);
// the player's terrace sits on the plateau's edge, looking down the slope toward the capitol
export const TERRACE = (() => { const dx = CAPITOL[0] - PALACE[0], dz = CAPITOL[1] - PALACE[1], l = Math.hypot(dx, dz); return [PALACE[0] + dx / l * 118, PALACE[1] + dz / l * 118]; })();
export const FORUM = px2w(760, 515);
export const COLOSSEUM = px2w(1085, 350);
export const CIRCUS = px2w(230, 570);
export const HILL_H = 60;

export function cls(x, z) {
  if (!MAP) return 'F';
  const i = Math.floor((x / PX + 760) / 4), j = Math.floor((z / PX + 450) / 4);
  if (i < 0 || j < 0 || i >= MAP.w || j >= MAP.h) return 'F';
  return MAP.rows[j][i];
}
function orient(x, z) {
  const i = Math.floor((x / PX + 760) / 4), j = Math.floor((z / PX + 450) / 4);
  if (!MAP || i < 0 || j < 0 || i >= MAP.w || j >= MAP.h) return 0;
  return (MAP.orient[j].charCodeAt(i) - 97) * Math.PI / 18;
}
function waterNear(x, z) {
  let n = 0;
  for (const dx of [-6, 0, 6]) for (const dz of [-6, 0, 6]) if (cls(x + dx, z + dz) === 'W') n++;
  return n / 9;
}
const g = (x, z, c, r, h) => h * Math.exp(-((x - c[0]) ** 2 + (z - c[1]) ** 2) / (r * r));
const ss = (a, b, t) => { const u = Math.min(1, Math.max(0, (t - a) / (b - a))); return u * u * (3 - 2 * u); };
export function height(x, z) {
  let y = 0;
  const dp = Math.hypot(x - PALACE[0], z - PALACE[1]);
  y += HILL_H * ss(250, 128, dp);
  y += g(x, z, CAPITOL, 110, 7);
  y -= 3.2 * waterNear(x, z);
  // countryside: gentle hills outside the map, rising to ridges on the horizon
  const ox = Math.max(0, Math.abs(x) - 1500), oz = Math.max(0, Math.abs(z - 120) - 1000);
  const out = Math.hypot(ox, oz);
  y += out * 0.035 + g(x, z, [-2600, -2400], 1500, 140) + g(x, z, [2400, 3200], 1800, 120) + g(x, z, [-900, 3600], 1400, 160) + g(x, z, [3600, -900], 1600, 110);
  y += g(x, z, [-1400, -700], 420, 30) + g(x, z, [-1300, 300], 380, 18);
  y += 0.5 * Math.sin(x / 37) * Math.cos(z / 53) + (out > 0 ? 3 * Math.sin(x / 210) * Math.cos(z / 170) : 0);
  return y;
}

// ------------------------------------------------------------------------------------------------ build
export function buildCity(scene, { quality = 1 } = {}) {
  setSeed(21);
  const group = new THREE.Group();
  group.name = 'City';
  scene.add(group);
  const [x0, z0] = px2w(0, 0), [x1, z1] = px2w(1536, 1024);

  // ---- terrain: a fine grid over the map, a coarse polar skirt to the horizon
  const fieldCols = [0xc9a65a, 0xb39a52, 0x8f9a4a, 0xa88a4c, 0x7e8a44, 0xc0a868, 0x9c7c48];
  const groundCol = (x, z) => {
    const c = cls(x, z);
    if (c === 'W') return 0x5d6b58;
    if (c === 'S' || c === 'P') return 0xc8ae8a;
    if (c === 'R') return 0xbca282;
    if (c === 'T') return 0x5d7238;
    if (c === 'V') return 0xbfa47c;
    if (height(x, z) > 25 && Math.hypot(x - PALACE[0], z - PALACE[1]) < 340) return 0x6f8a42;   // palace gardens
    const fi = Math.floor(x / 70 + Math.sin(z / 90) * 0.6), fj = Math.floor(z / 55);
    return fieldCols[Math.abs((fi * 7 + fj * 13) % fieldCols.length)];
  };
  const tb = new Builder(0.04);
  const S = 16;
  const nx = Math.ceil((x1 - x0) / S), nz = Math.ceil((z1 - z0) / S);
  const hv = [];
  for (let j = 0; j <= nz; j++) { hv.push([]); for (let i = 0; i <= nx; i++) { const x = x0 + i * S, z = z0 + j * S; hv[j].push([x, height(x, z), z]); } }
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const a = hv[j][i], b = hv[j][i + 1], c = hv[j + 1][i + 1], d = hv[j + 1][i];
    const col = groundCol(a[0] + S / 2, a[2] + S / 2);
    tb.quad(a, d, c, b, col);
  }
  const radii = [700]; while (radii[radii.length - 1] < 18000) radii.push(radii[radii.length - 1] * 1.07 + 20);
  const NA = 96;
  const cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
  const inside = (x, z) => x > x0 + 2 && x < x1 - 2 && z > z0 + 2 && z < z1 - 2;
  const P = (r, k) => { const t = k / NA * Math.PI * 2, x = cx + Math.sin(t) * r * 1.5, z = cz - Math.cos(t) * r; return [x, height(x, z) - (inside(x, z) ? 4 : 0.05), z]; };
  for (let k = 0; k < radii.length - 1; k++) for (let i = 0; i < NA; i++) {
    const a = P(radii[k], i), b = P(radii[k], i + 1), c = P(radii[k + 1], i + 1), d = P(radii[k + 1], i);
    const hh = (a[1] + c[1]) / 2;
    tb.quad(a, b, c, d, hh > 90 ? 0x8a8a5a : hh > 40 ? 0x97945a : pick(fieldCols));
  }
  group.add(mesh(tb, MAT.std, { cast: false, receive: true }));

  // ---- water: the river and harbour basin
  const wb = new Builder(0);
  const WC = 8;
  for (let j = 0; j < MAP.h; j++) for (let i = 0; i < MAP.w; i++) {
    if (MAP.rows[j][i] !== 'W') continue;
    const [x, z] = px2w(i * 4, j * 4);
    wb.quad([x - 1, -0.6, z - 1], [x - 1, -0.6, z + WC + 1], [x + WC + 1, -0.6, z + WC + 1], [x + WC + 1, -0.6, z - 1], 0x3f7088);
  }
  const waterMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.08, metalness: 0.0, envMapIntensity: 1.2 });
  const water = new THREE.Mesh(wb.geometry(), waterMat);
  water.receiveShadow = true;
  group.add(water);

  // ---- archetype library
  const winMatA = new THREE.MeshStandardMaterial({ color: 0x3a2a26, emissive: 0xffa040, emissiveIntensity: 0, roughness: 0.7, flatShading: true });
  const winMatB = winMatA.clone();
  const lib = {};
  const make = (cat, fn, n) => {
    lib[cat] = [];
    for (let i = 0; i < n; i++) {
      const b = new Builder(), w = [new Builder(0), new Builder(0)];
      const dims = fn(b, w);
      lib[cat].push({ geo: b.geometry(), wa: w[0].count ? w[0].geometry() : null, wb: w[1].count ? w[1].geometry() : null, dims });
    }
  };
  make('small', A.small, 10); make('insula', A.insula, 14); make('domus', A.domus, 5); make('tower', A.tower, 2);
  make('basilica', A.basilica, 2); make('baths', A.baths, 1); make('rotunda', A.rotunda, 1);
  make('temple', (b) => { const w = rr(12, 18), d = w * 1.4; A.temple(b, w, d, w * 0.55, false, rand() < 0.5); return [w + 4, d + 8]; }, 3);
  make('far', A.far, 10);
  make('cypress', (b) => { A.cypress(b, 0, 0, 0, rr(7, 10)); return [2, 2]; }, 3);
  make('pine', (b) => { A.pine(b, 0, 0, 0, rr(7, 10)); return [4, 4]; }, 2);
  make('boat', (b) => {
    b.loft([[0, 1.2, 4.5], [0.9, 1.8, 6.5], [1.3, 1.9, 7]], 8, 0x6b4a2e, true, true);
    b.box(0, 5, 0, 0.2, 8, 0.2, 0x5a4030);
    b.quad([0, 2, 0.15], [0, 8.6, 0.15], [0, 8.6, 3.2], [0, 2.5, 3.0], pick([0xefe2cc, 0xc8862d, 0x8e1f24]));
    return [4, 14];
  }, 3);

  // ---- occupancy: 4 m cells; landmarks reserve their ground first
  const CELL = 4, occ = new Set();
  const key = (i, j) => i * 100003 + j;
  const reserve = (x, z, r) => { const ri = Math.ceil(r / CELL), ci = Math.floor(x / CELL), cj = Math.floor(z / CELL); for (let i = -ri; i <= ri; i++) for (let j = -ri; j <= ri; j++) occ.add(key(ci + i, cj + j)); };
  const reserveRect = (cx, cz, w, d, yaw = 0) => { for (let u = -w / 2; u <= w / 2; u += 3) for (let v = -d / 2; v <= d / 2; v += 3) reserve(cx + Math.cos(yaw) * u + Math.sin(yaw) * v, cz - Math.sin(yaw) * u + Math.cos(yaw) * v, 1); };
  const free = (x, z, r) => { const ri = Math.ceil(r / CELL), ci = Math.floor(x / CELL), cj = Math.floor(z / CELL); for (let i = -ri; i <= ri; i++) for (let j = -ri; j <= ri; j++) if (occ.has(key(ci + i, cj + j))) return false; return true; };

  const placed = {}; for (const k in lib) placed[k] = lib[k].map(() => []);
  const put = (cat, idx, x, z, yaw, s = 1, sy = 1) => {
    const e = lib[cat][idx], [w, d] = e.dims, c = Math.cos(yaw), sn = Math.sin(yaw);
    let y = Infinity;
    for (const [u, v] of [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2], [0, 0]]) y = Math.min(y, height(x + (c * u + sn * v) * s, z + (-sn * u + c * v) * s));
    if (cat === 'boat') y = -0.8;
    placed[cat][idx].push(new THREE.Matrix4().compose(new THREE.Vector3(x, y - 0.15, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw), new THREE.Vector3(s, s * sy, s)));
  };

  const lm = new Builder();      // all hand-placed landmark geometry
  const lmWin = [new Builder(0), new Builder(0)];
  const houseLM = (...args) => { const b = new Builder(), w = [new Builder(0), new Builder(0)]; A.house(b, w, ...args); lm.append(b); lmWin[0].append(w[0], lm.m); lmWin[1].append(w[1], lm.m); };
  const at = (x, z, yaw = 0, s = 1, dy = 0) => lm.pushT(x, height(x, z) + dy, z, yaw, s);

  // the capitol: a colonnaded precinct with the great temple, facing south down the forum axis
  {
    const [cx2, cz2] = px2w(760, 378);
    reserveRect(cx2, cz2, 380, 270);
    at(cx2, cz2, 0, 1, -1);
    lm.box(0, 1, 0, 350, 2.4, 250, A.MARBLE2);
    for (const [sx, sz, w, d] of [[0, -120, 350, 14], [-170, 0, 14, 250], [170, 0, 14, 250]]) {
      lm.pushT(sx, 2.2, sz); houseLM(w, d, 2, 'gable', 0xefe2cc, { arcade: true }); lm.pop();
    }
    for (let k = 0; k < 10; k++) { lm.prism(-160 + k * 35.5, 2.2, 125, 1.1, 0.9, 11, 8, A.MARBLE); }
    lm.box(0, 13.6, 125, 340, 1.4, 2.6, A.MARBLE);
    // the great temple turns its portico toward the palace
    const ty = Math.atan2(TERRACE[0] - cx2, TERRACE[1] - cz2);
    lm.pushT(0, 2.2, -20, ty, 1.55); lm.box(0, 1.5, 0, 46, 3, 62, A.MARBLE2); lm.pushT(0, 3, 0); A.temple(lm, 30, 44, 15, true, true); lm.pop(); lm.pop();
    // gardens, paths and statues fill the precinct
    for (const [gx, gz, gw, gd] of [[-95, -55, 90, 70], [95, -55, 90, 70], [-95, 60, 90, 60], [95, 60, 90, 60]]) {
      lm.box(gx, 2.45, gz, gw, 0.15, gd, 0x6f8a42);
      lm.box(gx, 2.5, gz, gw * 0.12, 0.16, gd, 0xd8c6a6); lm.box(gx, 2.5, gz, gw, 0.16, gd * 0.12, 0xd8c6a6);
      lm.prism(gx, 2.5, gz, 3.2, 3.4, 0.7, 10, A.MARBLE); lm.prism(gx, 3.2, gz, 2.8, 2.8, 0.05, 10, 0x5f9aa8);
      for (let q = 0; q < 8; q++) A.cypress(lm, gx + rr(-gw / 2 + 4, gw / 2 - 4), 2.4, gz + rr(-gd / 2 + 4, gd / 2 - 4), rr(6, 9));
      for (const [ox, oz] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) A.pine(lm, gx + ox * gw * 0.38, 2.4, gz + oz * gd * 0.38, rr(8, 11));
    }
    for (const sx of [-1, 1]) { lm.pushT(sx * 105, 2.2, 10, 0, 1.0); A.temple(lm, 16, 22, 9, false, true); lm.pop(); }
    for (let k = 0; k < 12; k++) lm.box(0, 2.2 - (k + 1) * 0.3, 128 + k * 1.5, 70, 0.6, 1.5, A.MARBLE);
    lm.pop();
  }
  // the forum: the temple of the deified emperor, its square, fountains down the axis
  {
    const [fx, fz] = px2w(760, 520);
    reserveRect(fx, fz + 40, 150, 300);
    at(fx, fz - 20, 0, 1, 0.2);
    lm.box(0, 0.15, 60, 120, 0.3, 260, 0xd8c6a6);
    lm.pushT(0, 0, -40, 0, 1.4); A.temple(lm, 22, 32, 12, false, true); lm.pop();
    for (const side of [-1, 1]) {
      for (let k = 0; k < 22; k++) lm.prism(side * 52, 0, -10 + k * 9, 0.7, 0.6, 9, 8, A.MARBLE, false, true);
      lm.box(side * 52, 9.4, 85, 2.2, 1.0, 200, A.MARBLE); lm.box(side * 52, 10.1, 85, 2.3, 0.4, 200, A.CRIMSON);
      lm.box(side * 60, 6.5, 85, 12, 13, 200, 0xefe2cc);
      lm.pushT(side * 58, 0, 85); A.roof(lm, 'gable', 16, 200, 13, A.ROOFS[0]); lm.pop();
      for (let k = 0; k < 6; k++) { lm.pushT(side * 50.6, 0, 5 + k * 32, -side * Math.PI / 2); A.banner(lm, 0, 9.2, 0, 2.6, 6); lm.pop(); }
    }
    for (const fzz of [90, 160]) {
      lm.prism(0, 0, fzz, 10, 10.5, 0.9, 16, A.MARBLE); lm.prism(0, 0.9, fzz, 9.4, 9.4, 0.05, 16, 0x5f9aa8);
      lm.prism(0, 0, fzz, 1.6, 1.2, 8, 8, A.MARBLE); lm.box(0, 8.3, fzz, 2.8, 0.6, 2.8, A.GOLD);
    }
    for (let k = 0; k < 14; k++) A.cypress(lm, (k % 2 ? -1 : 1) * 38, 0, 10 + Math.floor(k / 2) * 30, rr(7, 9));
    lm.pop();
  }
  // the colosseum
  {
    const [cx2, cz2] = COLOSSEUM, RX = 128, RZ = 108;
    reserve(cx2, cz2, RX + 6);
    at(cx2, cz2, 0.15);
    const N = 48;
    for (let k = 0; k < N; k++) {
      const a0 = k / N * Math.PI * 2, a1 = (k + 1) / N * Math.PI * 2;
      const P2 = (a, s, y) => [Math.cos(a) * RX * s, y, Math.sin(a) * RZ * s];
      for (let f = 0; f < 4; f++) {      // the arcaded outer wall, four tiers
        const y0 = f * 11, y1 = y0 + 11;
        lm.quad(P2(a1, 1, y0), P2(a0, 1, y0), P2(a0, 1, y1), P2(a1, 1, y1), f === 3 ? 0xe6d6bc : 0xf0e4ce);
        if (f < 3) { const am = (a0 + a1) / 2; lm.poly([P2(am - 0.022, 1.003, y0 + 1.5), P2(am + 0.022, 1.003, y0 + 1.5), P2(am + 0.022, 1.003, y0 + 7), P2(am, 1.003, y0 + 8.6), P2(am - 0.022, 1.003, y0 + 7)].reverse(), 0x5a4038); }
        lm.quad(P2(a0, 1.01, y1 - 0.6), P2(a1, 1.01, y1 - 0.6), P2(a1, 1.01, y1), P2(a0, 1.01, y1), A.MARBLE2);
      }
      for (let r = 0; r < 7; r++) {      // seating tiers falling to the arena
        const s0 = 0.97 - r * 0.06, s1 = s0 - 0.06, y0 = 42 - r * 5.4, y1 = y0 - 5.4;
        lm.quad(P2(a0, s0, y0), P2(a1, s0, y0), P2(a1, s1, y1), P2(a0, s1, y1), r % 2 ? 0xd8c8b0 : 0xe8dcc8);
      }
      lm.quad(P2(a0, 0.55, 4), P2(a1, 0.55, 4), P2(a1, 0, 4), P2(a0, 0, 4), 0xd9b98a);
      lm.quad(P2(a0, 1, 44), P2(a1, 1, 44), P2(a1, 0.97, 42), P2(a0, 0.97, 42), 0xe6d6bc);
    }
    lm.pop();
  }
  // the circus: a long track with a spina, obelisk and turning posts, stands all round
  {
    const [cx2, cz2] = CIRCUS, L = 400, W = 130, yaw = -Math.atan2(80, 160);
    reserveRect(cx2, cz2, L + 20, W + 20, yaw);
    at(cx2, cz2, yaw);
    lm.box(0, 0.2, 0, L - 30, 0.4, W - 30, 0xd9b98a);
    const half = W / 2 - 6;
    for (let k = 0; k <= 40; k++) {
      const u = -L / 2 + 6 + (L - 12) * k / 40;
      if (k < 40) for (const s of [-1, 1]) { lm.box(u + (L - 12) / 80, 5, s * half, (L - 12) / 40, 10, 10, k % 2 ? 0xe8dcc8 : 0xf0e4ce); }
    }
    lm.box(-L / 2 + 6, 6, 0, 12, 12, W - 12, 0xe8d6ba);
    lm.box(0, 1, 0, L * 0.6, 2, 6, A.MARBLE2);
    lm.prism(0, 2, 0, 1.6, 0.9, 22, 4, 0xe2c79a); lm.prism(0, 24, 0, 0.9, 0, 2, 4, A.GOLD);
    for (const s of [-1, 1]) for (let k = 0; k < 3; k++) lm.prism(s * L * 0.3, 2, (k - 1) * 1.5, 0.5, 0, 6, 4, A.GOLD);
    lm.pop();
  }
  // other temples and rotundas from the map
  for (const [ppx, ppy, kind, yaw] of [[580, 232, 'rotunda', 0.4], [265, 448, 'rotunda', 0.6], [1010, 778, 'temple', 0.3], [610, 360, 'temple', 0.0], [930, 590, 'temple', -0.2], [440, 445, 'temple', 0.5]]) {
    const [x, z] = px2w(ppx, ppy);
    reserve(x, z, 30);
    put(kind, kind === 'temple' ? Math.floor(rand() * 3) : 0, x, z, yaw, 1.4);
  }
  for (const [ppx, ppy] of [[1300, 600], [370, 640], [905, 135]]) { const [x, z] = px2w(ppx, ppy); reserve(x, z, 34); put('baths', 0, x, z, 0.2, 1.1); }

  // the palace on its plateau: great halls and a domed hall around the player's terrace
  {
    const T = TERRACE, yawT = Math.atan2(-(CAPITOL[0] - T[0]), -(CAPITOL[1] - T[1]));
    reserve(PALACE[0], PALACE[1], 150);
    const blocks = [[-30, 70, 120, 60, 4], [110, 40, 60, 140, 3], [-140, 10, 70, 120, 3], [-30, 190, 160, 50, 3], [-150, 160, 70, 70, 4], [90, 170, 60, 60, 3]];
    lm.pushT(T[0], HILL_H, T[1], yawT);
    for (const [bx, bz, w, d, fl] of blocks) { lm.pushT(bx, 0, bz); houseLM(w, d, fl, 'hip', pick([0xefe2cc, 0xf2e6d2, 0xe8d3b0]), { arcade: true, portico: true }); lm.pop(); }
    lm.pushT(-130, 0, 90); lm.prism(0, 0, 0, 22, 22, 18, 16, A.MARBLE2); lm.loft([[18, 23, 23], [26, 19, 19], [32, 12, 12], [35, 2, 2]], 16, 0xc99a45, true, false); lm.pop();
    for (let k = 0; k < 40; k++) { const x = rr(-200, 200), z = rr(25, 230); if (Math.hypot(x, z - 60) > 40) A.cypress(lm, x, -1, z, rr(8, 12)); }
    lm.pop();
  }

  // the city wall with towers and gates, following the map outline
  const WALL = MAP.wall.map(([a, b]) => px2w(a, b));
  const GATES = [[65, 505], [430, 772], [745, 835], [1100, 137], [1262, 248], [1395, 405], [1425, 505], [1450, 770]].map(([a, b]) => px2w(a, b));
  {
    for (let k = 0; k < WALL.length; k++) {
      const p = WALL[k], q = WALL[(k + 1) % WALL.length];
      const L = Math.hypot(q[0] - p[0], q[1] - p[1]), yaw = Math.atan2(-(q[1] - p[1]), q[0] - p[0]);
      const n = Math.ceil(L / 6);
      for (let i = 0; i < n; i++) {
        const t = (i + 0.5) / n, x = p[0] + (q[0] - p[0]) * t, z = p[1] + (q[1] - p[1]) * t;
        if (GATES.some(([gx, gz]) => Math.hypot(gx - x, gz - z) < 14)) continue;
        const y = height(x, z);
        lm.pushT(x, y, z, yaw);
        lm.box(0, 6, 0, L / n + 0.1, 12, 5, 0xe0cba8);
        lm.box(0, 12.2, 0, L / n + 0.2, 0.5, 5.6, 0xeadbc0);
        if (i % 2 === 0) for (const s of [-1, 1]) lm.box(0, 13.3, s * 2.5, 2.2, 1.8, 0.6, 0xe0cba8);
        lm.pop();
        reserve(x, z, 4);
      }
      for (let i = 0; i <= Math.floor(L / 130); i++) {
        const t = i / Math.max(1, Math.floor(L / 130)), x = p[0] + (q[0] - p[0]) * t, z = p[1] + (q[1] - p[1]) * t;
        if (GATES.some(([gx, gz]) => Math.hypot(gx - x, gz - z) < 25)) continue;
        lm.pushT(x, height(x, z), z, yaw);
        lm.box(0, 9, 0, 11, 18, 11, 0xe4d0ae);
        A.roof(lm, 'hip', 11, 11, 18, A.ROOFS[1]);
        lm.pop();
      }
    }
    for (const [gx, gz] of GATES) {
      const yaw = Math.atan2(gx, gz);
      lm.pushT(gx, height(gx, gz), gz, yaw + Math.PI / 2);
      for (const s of [-1, 1]) { lm.box(0, 11, s * 12, 13, 22, 12, 0xe8d6b6); A.roof(lm, 'hip', 13, 12, 22, A.ROOFS[0]); }
      lm.box(0, 16, 0, 10, 8, 14, 0xe8d6b6);
      lm.box(0, 20.3, 0, 10.6, 0.6, 14.6, A.MARBLE);
      lm.box(0, 14.5, 7.05, 4, 1.4, 0.1, A.GOLD);
      lm.pop();
      // a road out into the countryside
      let x = gx, z = gz, dx = gx - 20, dz = gz - 120; const dl = Math.hypot(dx, dz); dx /= dl; dz /= dl;
      for (let k = 0; k < 40; k++) {
        const nx2 = x + dx * 40, nz2 = z + dz * 40;
        if (cls(nx2, nz2) === 'W') break;
        const ux = -dz * 4, uz = dx * 4;
        lm.quad([x - ux, height(x - ux, z - uz) + 0.2, z - uz], [nx2 - ux, height(nx2 - ux, nz2 - uz) + 0.2, nz2 - uz], [nx2 + ux, height(nx2 + ux, nz2 + uz) + 0.2, nz2 + uz], [x + ux, height(x + ux, z + uz) + 0.2, z + uz], 0xc8ae8a);
        x = nx2; z = nz2; dx += rr(-0.08, 0.08); dz += rr(-0.08, 0.08); const l2 = Math.hypot(dx, dz); dx /= l2; dz /= l2;
      }
    }
  }
  // bridges over the river
  for (const [[ax, ay], [bx, by]] of [[[1148, 122], [1215, 80]], [[1290, 255], [1395, 255]], [[1372, 410], [1492, 410]], [[1440, 505], [1530, 505]], [[1445, 795], [1530, 795]]]) {
    const [p0x, p0z] = px2w(ax, ay), [p1x, p1z] = px2w(bx, by);
    const L = Math.hypot(p1x - p0x, p1z - p0z), yaw = Math.atan2(-(p1z - p0z), p1x - p0x);
    lm.pushT((p0x + p1x) / 2, 0, (p0z + p1z) / 2, yaw);
    lm.box(0, 7, 0, L + 10, 1.6, 9, 0xd8c4a4);
    for (const s of [-1, 1]) lm.box(0, 8.3, s * 4.3, L + 10, 1.0, 0.5, 0xe0cdb0);
    const na = Math.max(2, Math.round(L / 24));
    for (let k = 0; k <= na; k++) lm.box(-L / 2 + L * k / na, 2.5, 0, 4, 9, 8.4, 0xd0bc9c);
    lm.pop();
  }
  // the aqueduct striding in from the north-west hills to the palace
  {
    const pts = [px2w(80, -300), px2w(270, 148), px2w(560, 42), px2w(760, -260)].map(([x, z]) => [x, z]);
    for (let s = 0; s < 2; s++) {
      const [ax, az] = pts[s === 0 ? 1 : 2], [bx, bz] = pts[s === 0 ? 2 : 3];
      const L = Math.hypot(bx - ax, bz - az), n = Math.floor(L / 16), yaw = Math.atan2(-(bz - az), bx - ax);
      for (let k = 0; k < n; k++) {
        const t = (k + 0.5) / n, x = ax + (bx - ax) * t, z = az + (bz - az) * t, y = height(x, z), top = Math.max(y + 18, 28);
        lm.pushT(x, 0, z, yaw);
        lm.box(-6.5, (y + top) / 2, 0, 3, top - y, 3.4, 0xd8c4a4);
        lm.box(0, top + 1.4, 0, 16, 2.8, 3.6, 0xe0cdb0);
        lm.box(0, top - 2.2, 0, 16, 1.2, 3.4, 0xd8c4a4);
        lm.pop();
      }
    }
  }
  // boats in the harbour and on the river
  for (let k = 0; k < 400 && placed.boat.flat().length < 46; k++) {
    const [x, z] = px2w(rr(1150, 1430), rr(560, 1000));
    if (cls(x, z) === 'W' && cls(x + 8, z) === 'W' && cls(x - 8, z) === 'W' && cls(x, z + 8) === 'W' && cls(x, z - 8) === 'W') put('boat', Math.floor(rand() * 3), x, z, rr(0, 6.28), 1);
  }

  // ---- the general fill: every roof cell on the map gets buildings, oriented to its streets
  const cellsR = [];
  for (let j = 0; j < MAP.h; j++) for (let i = 0; i < MAP.w; i++) { const c = MAP.rows[j][i]; if (c === 'R' || c === 'V' || c === 'T') cellsR.push([i, j, c]); }
  for (let k = cellsR.length - 1; k > 0; k--) { const r = Math.floor(rand() * (k + 1)); [cellsR[k], cellsR[r]] = [cellsR[r], cellsR[k]]; }
  const T0 = TERRACE;
  let built = 0, trees = 0;
  const footprintOK = (x, z, w, d, yaw, want) => {
    const c = Math.cos(yaw), s = Math.sin(yaw);
    for (const [u, v] of [[0, 0], [-0.4, -0.4], [0.4, -0.4], [0.4, 0.4], [-0.4, 0.4]]) {
      const cc = cls(x + c * u * w + s * v * d, z - s * u * w + c * v * d);
      if (!want.includes(cc)) return false;
    }
    return true;
  };
  for (const [i, j, c] of cellsR) {
    for (let attempt = 0; attempt < 2; attempt++) {
      const [x, z] = px2w(i * 4 + 2 + rr(-1.5, 1.5), j * 4 + 2 + rr(-1.5, 1.5));
      if (c === 'T') {
        if (!free(x, z, 1.5)) continue;
        const t = rand() < 0.6 ? 'cypress' : 'pine';
        put(t, Math.floor(rand() * lib[t].length), x, z, rr(0, 6.28), rr(0.8, 1.3), rr(0.9, 1.3));
        reserve(x, z, 1); trees++;
        continue;
      }
      const dist = Math.hypot(x - T0[0], z - T0[1]);
      let cat;
      if (c === 'V') cat = rand() < 0.6 ? 'domus' : 'small';
      else if (dist > 1300 * quality) cat = 'far';
      else { const r = rand(); cat = r < 0.012 ? 'tower' : r < 0.06 ? 'domus' : r < 0.55 ? 'insula' : 'small'; }
      const idx = Math.floor(rand() * lib[cat].length);
      const s = rr(0.85, 1.1);
      const [w, d] = lib[cat][idx].dims;
      const yaw = Math.PI / 2 - orient(x, z) + (rand() < 0.5 ? 0 : Math.PI) + rr(-0.05, 0.05);
      if (!footprintOK(x, z, w * s, d * s, yaw, c === 'V' ? 'VF' : 'RT')) {
        if (cat !== 'small' && cat !== 'far') continue;
      }
      const rad = Math.max(w, d) * s * 0.4;
      if (!free(x, z, rad)) continue;
      reserve(x, z, rad);
      put(cat, idx, x, z, yaw, s, cat === 'insula' || cat === 'far' ? rr(0.85, 1.2) : 1);
      built++;
      break;
    }
  }

  // infill: a second pass of small houses squeezes into what is left of each block
  for (const [i, j, c] of cellsR) {
    if (c !== 'R') continue;
    const [x, z] = px2w(i * 4 + 2, j * 4 + 2);
    const s = rr(0.7, 0.95), idx = Math.floor(rand() * lib.small.length), [w, d] = lib.small[idx].dims;
    const rad = Math.max(w, d) * s * 0.36;
    if (!free(x, z, rad)) continue;
    const far = Math.hypot(x - T0[0], z - T0[1]) > 1300 * quality;
    reserve(x, z, rad);
    const yaw = Math.PI / 2 - orient(x, z) + (rand() < 0.5 ? 0 : Math.PI);
    if (far) put('far', Math.floor(rand() * lib.far.length), x, z, yaw, s * 0.7, 1); else put('small', idx, x, z, yaw, s, rr(0.9, 1.3));
    built++;
  }

  group.add(mesh(lm, MAT.std, { cast: false, receive: true }));
  if (lmWin[0].count) group.add(mesh(lmWin[0], winMatA, { cast: false }));
  if (lmWin[1].count) group.add(mesh(lmWin[1], winMatB, { cast: false }));

  // ---- instanced meshes
  const tint = new THREE.Color();
  let instances = 0;
  for (const cat in lib) {
    lib[cat].forEach((e, i) => {
      const list = placed[cat][i];
      if (!list.length) return;
      for (const [geo, mat] of [[e.geo, MAT.std], [e.wa, winMatA], [e.wb, winMatB]]) {
        if (!geo) continue;
        const im = new THREE.InstancedMesh(geo, mat, list.length);
        list.forEach((m, k) => {
          im.setMatrixAt(k, m);
          if (mat === MAT.std) { const v = 0.92 + ((k * 7919) % 15) / 100; im.setColorAt(k, tint.setRGB(v, v * 0.99, v * 0.97)); }
        });
        im.receiveShadow = true;
        im.computeBoundingSphere();
        group.add(im);
      }
      instances += list.length;
    });
  }
  console.log('city: buildings', built, 'trees', trees, 'instances', instances);
  return { group, winMatA, winMatB, waterMat };
}
