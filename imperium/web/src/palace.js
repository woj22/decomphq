// The palace terrace where the evening is played: an oblique balustrade over the city, an Ionic loggia hung
// with laurel banners, the spear statue, braziers with live fire, geometric marble paving, the crimson carpet and
// the palace facade behind. Built in local space (the city lies toward -Z); the floor is y = 0.
import * as THREE from 'three';
import { Builder, MAT, mesh, rand, rr, setSeed } from './lowpoly.js';
import { MARBLE, MARBLE2, GOLD, CRIMSON } from './archetypes.js';

export const balZ = (x) => -5.95 + 0.3055 * (x - 4.9);       // the balustrade line
export const BOUNDS = { x0: -19, x1: 11.2, z1: 12.6 };

function fluted(n, r, depth = 0.06) { const p = []; for (let k = 0; k < 2 * n; k++) { const t = (k / (2 * n)) * Math.PI * 2, rr2 = r * (1 - (k % 2 ? depth : 0)); p.push([Math.cos(t) * rr2, Math.sin(t) * rr2]); } return p; }
function ionic(b, x, z, h, r) {
  b.box(x, 0.18, z, r * 3, 0.36, r * 3, MARBLE2);
  b.loft([[0.36, r * 1.35, r * 1.35, x, z], [0.48, r * 1.42, r * 1.42, x, z], [0.6, r * 1.2, r * 1.2, x, z], [0.68, r * 1.1, r * 1.1, x, z], [0.78, r * 1.2, r * 1.2, x, z], [0.86, r * 1.05, r * 1.05, x, z]], 16, MARBLE);
  const zc = h - 0.9 * r / 0.6;
  // fluted shaft: alternate arris/flute radii around 24 sides
  const F = fluted(12, 1);
  const ring = (y, s) => F.map(([u, v]) => [x + u * r * s, y, z + v * r * s]);
  const rings = [ring(0.86, 1), ring(0.86 + (zc - 0.86) * 0.35, 0.98), ring(zc, 0.86)];
  for (let k = 0; k < 2; k++) for (let i = 0; i < F.length; i++) { const j = (i + 1) % F.length; b.quad(rings[k][j], rings[k][i], rings[k + 1][i], rings[k + 1][j], MARBLE); }
  b.loft([[zc, r * 0.9, r * 0.9, x, z], [zc + 0.1, r * 0.98, r * 0.98, x, z], [zc + 0.16, r * 0.9, r * 0.9, x, z]], 16, GOLD);
  b.loft([[zc + 0.16, r * 0.92, r * 0.92, x, z], [zc + 0.42, r * 1.18, r * 1.18, x, z]], 16, MARBLE);
  for (const s of [-1, 1]) for (const f of [-1, 1]) {
    const pts = [], rad = [];
    for (let k = 0; k < 14; k++) { const t = k / 13 * 2.4 * Math.PI, rr2 = r * 0.38 * (1 - k / 16); pts.push([x + s * (r * 1.12 + Math.cos(t) * rr2 * s), zc + 0.3 - r * 0.15 + Math.sin(t) * rr2, z + f * r * 0.75]); rad.push(r * 0.1 * (1 - k / 20)); }
    b.tube(pts, rad, 6, MARBLE);
  }
  b.box(x, zc + 0.56, z, r * 2.9, 0.24, r * 2.9, MARBLE);
  b.box(x, zc + 0.7, z, r * 3.05, 0.06, r * 3.05, GOLD);
}

// a banner hung from a pivot at its top edge so it can sway; laurel wreath in gold
function bannerMesh(width, length, col = CRIMSON) {
  const b = new Builder(0.02);
  const n = 5;
  for (let i = 0; i < n; i++) {
    const y0 = -length * i / n, y1 = -length * (i + 1) / n;
    b.quad([-width / 2, y1, 0], [width / 2, y1, 0], [width / 2, y0, 0], [-width / 2, y0, 0], col);
  }
  b.tri([-width / 2, -length, 0], [width / 2, -length, 0], [0, -length - width * 0.45, 0], col);
  b.quad([-width / 2, -0.12, 0.012], [width / 2, -0.12, 0.012], [width / 2, -0.06, 0.012], [-width / 2, -0.06, 0.012], GOLD);
  b.quad([-width / 2, -length + 0.04, 0.012], [width / 2, -length + 0.04, 0.012], [width / 2, -length + 0.1, 0.012], [-width / 2, -length + 0.1, 0.012], GOLD);
  // laurel wreath: two arcs of leaves
  const cy = -length * 0.42, R = width * 0.28;
  for (const s of [-1, 1]) for (let k = 0; k < 9; k++) {
    const a = -Math.PI / 2 + s * (0.35 + k * 0.29), lx = Math.cos(a) * R, ly = cy + Math.sin(a) * R;
    const dx = -Math.sin(a) * s * 0.07, dy = Math.cos(a) * s * 0.07;
    b.tri([lx - dy * 0.4, ly + dx * 0.4, 0.014], [lx + dx * 1.6, ly + dy * 1.6, 0.014], [lx + dy * 0.4, ly - dx * 0.4, 0.014], 0xe0b040);
  }
  b.box(0, 0.05, 0, width + 0.3, 0.1, 0.1, GOLD);
  return new THREE.Mesh(b.geometry(), MAT.cloth);
}

export function brazier(group, x, z, s = 0.9) {
  const b = new Builder();
  b.loft([[0, 0.45 * s, 0.45 * s, x, z], [0.2 * s, 0.42 * s, 0.42 * s, x, z], [0.75 * s, 0.22 * s, 0.22 * s, x, z]], 8, 0x8a5a2a);
  b.loft([[0.7 * s, 0.22 * s, 0.22 * s, x, z], [0.82 * s, 0.5 * s, 0.5 * s, x, z], [1.05 * s, 0.68 * s, 0.68 * s, x, z], [1.22 * s, 0.74 * s, 0.74 * s, x, z], [1.27 * s, 0.8 * s, 0.8 * s, x, z]], 10, 0x9a6428, true, false);
  b.loft([[1.18 * s, 0.72 * s, 0.72 * s, x, z], [1.19 * s, 0.72 * s, 0.72 * s, x, z]], 10, 0x2a1008);
  const m = new THREE.Mesh(b.geometry(), MAT.metal);
  m.castShadow = true; m.receiveShadow = true;
  group.add(m);
  // angular flames: a cluster of emissive spikes that flicker
  const flames = new THREE.Group();
  flames.position.set(x, 1.18 * s, z);
  const cols = [new THREE.Color(4.0, 1.5, 0.25), new THREE.Color(3.2, 0.9, 0.12), new THREE.Color(5, 2.6, 0.7)];
  for (let i = 0; i < 9; i++) {
    const fb = new Builder(0);
    const a = (i / 9) * Math.PI * 2 + rand() * 0.4, r = i === 8 ? 0 : rr(0.1, 0.4) * s, h = (i === 8 ? 1.0 : rr(0.55, 1.15)) * s;
    fb.prism(0, 0, 0, (i === 8 ? 0.36 : 0.17) * s, 0, h, 3, 0xffffff, false, false, rand() * 3);
    const f = new THREE.Mesh(fb.geometry(), new THREE.MeshBasicMaterial({ color: cols[i === 8 ? 2 : i % 2], toneMapped: false, fog: false }));
    f.position.set(Math.cos(a) * r, 0, Math.sin(a) * r);
    f.rotation.z = Math.cos(a) * 0.2; f.rotation.x = -Math.sin(a) * 0.2;
    f.userData.base = h; f.userData.ph = rand() * 10;
    flames.add(f);
  }
  group.add(flames);
  const light = new THREE.PointLight(0xff8a3a, 18, 14, 1.6);
  light.position.set(x, 2.2 * s, z);
  light.castShadow = false;
  group.add(light);
  return { flames, light, baseI: light.intensity };
}

export function buildPalace(scene, { cast }) {
  setSeed(11);
  const group = new THREE.Group();
  group.name = 'Terrace';
  scene.add(group);
  const b = new Builder();
  // paving: bordered squares with inset diamonds and a small centre stone
  const S = 2.0;
  for (let i = -10; i < 6; i++) for (let j = -8; j < 7; j++) {
    const x0 = i * S, z0 = j * S, cx = x0 + S / 2, cz = z0 + S / 2;
    if (z0 < balZ(cx) + 0.2 || x0 < BOUNDS.x0 - 1.5 || x0 > BOUNDS.x1 + 0.5) continue;
    const alt = (i + j) % 2 === 0;
    b.quad([x0, 0, z0 + S], [x0 + S, 0, z0 + S], [x0 + S, 0, z0], [x0, 0, z0], alt ? 0xd2c2b4 : 0xc2a288);
    const bb = 0.16;
    b.quad([x0 + bb, 0.004, z0 + S - bb], [x0 + S - bb, 0.004, z0 + S - bb], [x0 + S - bb, 0.004, z0 + bb], [x0 + bb, 0.004, z0 + bb], 0xe6dace);
    const d = S / 2 - bb - 0.05;
    b.quad([cx, 0.008, cz + d], [cx + d, 0.008, cz], [cx, 0.008, cz - d], [cx - d, 0.008, cz], alt ? 0xd2c2b4 : 0xe6dace);
    const e = 0.2;
    b.quad([cx, 0.012, cz + e], [cx + e, 0.012, cz], [cx, 0.012, cz - e], [cx - e, 0.012, cz], 0xb08466);
  }
  // the strip of floor the oblique balustrade leaves: a plain marble edge
  for (let x = BOUNDS.x0 - 2; x < BOUNDS.x1 + 1; x += 1) b.quad([x, 0.002, balZ(x + 0.5) + 0.8], [x + 1, 0.002, balZ(x + 0.5) + 0.8], [x + 1, 0.002, balZ(x + 1) - 0.4], [x, 0.002, balZ(x) - 0.4], 0xe0d4c6);
  // crimson carpet with gold borders from the palace doors toward the balustrade
  const p0 = new THREE.Vector2(-1.2, 13), p1 = new THREE.Vector2(-0.6, balZ(-0.6) + 1.3);
  for (const [w, col, y] of [[3.0, 0xc8862d, 0.016], [2.6, CRIMSON, 0.02], [2.0, 0xc8862d, 0.022], [1.9, CRIMSON, 0.024]]) {
    b.quad([p0.x - w / 2, y, p0.y], [p0.x + w / 2, y, p0.y], [p1.x + w / 2, y, p1.y], [p1.x - w / 2, y, p1.y], col);
  }
  // balustrade
  const BR = new THREE.Vector2(BOUNDS.x1 + 1, balZ(BOUNDS.x1 + 1)), BL = new THREE.Vector2(BOUNDS.x0 - 2.5, balZ(BOUNDS.x0 - 2.5));
  const L = BR.distanceTo(BL), dir = BL.clone().sub(BR).normalize(), yaw = Math.atan2(-dir.y, dir.x), mid = BR.clone().add(BL).multiplyScalar(0.5);
  b.box(mid.x, 0.13, mid.y, L, 0.26, 0.75, MARBLE2, yaw);
  b.box(mid.x, 1.02, mid.y, L, 0.2, 0.82, MARBLE, yaw);
  b.box(mid.x, 0.9, mid.y, L - 0.1, 0.06, 0.66, GOLD, yaw);
  const n = Math.floor(L / 0.42);
  for (let k = 0; k < n; k++) {
    const p = BR.clone().addScaledVector(dir, L * (k + 0.5) / n);
    if (k % 7 === 3) { b.box(p.x, 0.55, p.y, 0.62, 0.92, 0.62, MARBLE, yaw); continue; }
    b.loft([[0.26, 0.1, 0.1, p.x, p.y], [0.44, 0.18, 0.18, p.x, p.y], [0.58, 0.12, 0.12, p.x, p.y], [0.74, 0.09, 0.09, p.x, p.y], [0.86, 0.13, 0.13, p.x, p.y], [0.92, 0.11, 0.11, p.x, p.y]], 8, 0xdccfba);
  }
  // cornice, then the substructure dropping down the hill
  const off = new THREE.Vector2(-dir.y, dir.x).multiplyScalar(0.7);
  b.box(mid.x + off.x, -0.5, mid.y + off.y, L + 30, 1.0, 1.4, MARBLE, yaw);
  b.box(mid.x + off.x * 2.2, -31, mid.y + off.y * 2.2, L + 60, 60, 2.0, 0xd9c8a8, yaw);
  for (let k = 0; k < 9; k++) { const q = BR.clone().addScaledVector(dir, -15 + k * 8.5).add(off.clone().multiplyScalar(2.6)); b.box(q.x, -32, q.y, 2.4, 62, 1.2, 0xe2d2b4, yaw); }
  // the Ionic loggia on the left with its entablature, and a colonnade running back along the west side
  const cols = [[-5.9, -8.3], [-7.6, -9.4], [-9.3, -10.5]];
  for (const [x, z] of cols) ionic(b, x, z, 6.2, 0.5);
  const c0 = new THREE.Vector2(...cols[0]), c1 = new THREE.Vector2(...cols[2]), cd = c1.clone().sub(c0), cyaw = Math.atan2(-cd.y, cd.x), cm = c0.clone().add(c1).multiplyScalar(0.5);
  b.box(cm.x, 7.1, cm.y, cd.length() + 2.4, 1.0, 2.4, MARBLE, cyaw);
  b.box(cm.x, 7.75, cm.y, cd.length() + 2.5, 0.3, 2.5, GOLD, cyaw);
  b.box(cm.x, 8.2, cm.y, cd.length() + 2.6, 0.6, 2.6, CRIMSON, cyaw);
  b.box(cm.x, 8.7, cm.y, cd.length() + 3.0, 0.4, 3.0, MARBLE, cyaw);
  for (let z = -8; z <= 10; z += 3) ionic(b, -18, z, 6.2, 0.5);
  b.box(-18, 7.1, 1, 2.4, 1.0, 21, MARBLE); b.box(-18, 8.2, 1, 2.6, 0.6, 21, CRIMSON); b.box(-18, 8.7, 1, 3.0, 0.4, 21, MARBLE);
  b.box(-23, 5, 1, 8, 10, 24, 0xe8d6ba); b.box(-21, 9.8, -9, 12, 1, 6, MARBLE);
  // the palace facade behind: a great doorway between columns, a pediment, windows
  b.box(-4, 8, 15.5, 34, 16, 3, 0xe8d6ba);
  b.box(-4, 0.3, 14, 34, 0.6, 1.2, MARBLE2);
  for (const x of [-15, -9, 0.6, 7]) ionic(b, x, 13.6, 9.5, 0.62);
  b.box(-4, 10.6, 13.6, 30, 1.2, 2.2, MARBLE); b.box(-4, 11.4, 13.6, 30.2, 0.4, 2.3, GOLD); b.box(-4, 12.1, 13.6, 30.4, 1.0, 2.6, CRIMSON); b.box(-4, 12.8, 13.6, 31, 0.5, 3, MARBLE);
  b.tri([-19.5, 13.05, 12.4], [11.5, 13.05, 12.4], [-4, 17.5, 12.4], MARBLE);
  b.tri([-16, 13.4, 12.35], [8, 13.4, 12.35], [-4, 16.6, 12.35], CRIMSON);
  const doorPts = [[-3.0, 0, 13.95], [0.6, 0, 13.95]]; for (let k = 0; k <= 8; k++) { const t = k / 8 * Math.PI; doorPts.push([-1.2 + Math.cos(t) * 1.8, 5.5 + Math.sin(t) * 1.8, 13.95]); }
  b.poly([doorPts[0], doorPts[1], ...doorPts.slice(2)].reverse(), 0x2a1a14);
  b.box(-1.2, 5.6, 13.9, 4.4, 0.3, 0.3, GOLD);
  const facadeWin = new Builder(0);
  for (const x of [-12, -6.3, 3.8]) for (const y of [2.5, 7.0]) { facadeWin.quad([x - 0.8, y, 13.94], [x + 0.8, y, 13.94], [x + 0.8, y + 2.4, 13.94], [x - 0.8, y + 2.4, 13.94], 0x3a2a26); b.box(x, y - 0.1, 13.85, 2.0, 0.2, 0.35, MARBLE); }
  // east side: a low wall with a parapet and planters
  b.box(12.4, 1.3, 4, 1.0, 2.6, 18, 0xe8d6ba); b.box(12.4, 2.7, 4, 1.3, 0.3, 18.4, MARBLE);
  for (const z of [-1, 5, 11]) { b.box(11.2, 0.4, z, 1.2, 0.8, 1.2, 0x9a6a3a); }
  // statue pedestal, banner pole, small potted cypresses
  const sp = new THREE.Vector2(-2.5, balZ(-2.5) + 0.55);
  b.box(sp.x, 0.12, sp.y, 1.9, 0.24, 1.9, MARBLE); b.box(sp.x, 0.7, sp.y, 1.55, 1.0, 1.55, MARBLE2);
  b.box(sp.x, 1.0, sp.y, 1.6, 0.08, 1.6, GOLD); b.box(sp.x, 1.3, sp.y, 1.8, 0.16, 1.8, MARBLE);
  const pole = new THREE.Vector2(4.6, balZ(4.6) + 0.5);
  b.prism(pole.x, 0, pole.y, 0.09, 0.07, 6.8, 6, GOLD); b.prism(pole.x, 6.8, pole.y, 0.16, 0, 0.4, 6, GOLD);
  b.box(pole.x - 0.7, 6.55, pole.y, 1.9, 0.12, 0.12, GOLD);
  for (const [x, z] of [[11.2, -1], [11.2, 5], [11.2, 11]]) b.prism(x, 0.8, z, 0.3, 0, 2.6, 6, 0x376a3a);
  group.add(mesh(b, MAT.std));
  const fw = new THREE.Mesh(facadeWin.geometry(), new THREE.MeshStandardMaterial({ color: 0x3a2a26, emissive: 0xffa040, emissiveIntensity: 0, flatShading: true }));
  group.add(fw);
  // banners: loggia, facade, pole
  const banners = [];
  const hang = (x, y, z, yaw2, w, l) => { const m = bannerMesh(w, l); m.position.set(x, y, z); m.rotation.y = yaw2; m.castShadow = true; group.add(m); banners.push(m); };
  for (let k = 0; k < cols.length - 1; k++) { const bm = new THREE.Vector2(...cols[k]).add(new THREE.Vector2(...cols[k + 1])).multiplyScalar(0.5); hang(bm.x, 6.6, bm.y + 0.2, 0.33, 1.2, 3.4); }
  hang(-4.9, 6.5, -7.6, 0.33, 1.0, 3.2);
  for (const x of [-12, -6.3, 3.8]) hang(x, 10.2, 13.3, 0, 1.4, 4.2);
  for (let z = -6.5; z <= 9; z += 6) hang(-17.2, 6.6, z, Math.PI / 2, 1.2, 3.6);
  hang(pole.x - 1.35, 6.45, pole.y + 0.1, 0, 1.0, 3.6);
  // braziers: one by the balustrade, two flanking the doors
  const fires = [brazier(group, 3.5, balZ(3.5) + 0.95, 0.9), brazier(group, -5.2, 12.4, 0.75), brazier(group, 2.8, 12.4, 0.75)];
  // the statue: a figure in sandstone with a spear, well above human scale
  const statue = cast('thane', { headwear: 'none', prop: 'spear', cloak: 0xcdb48c, stone: true });
  statue.root.position.set(sp.x, 1.38, sp.y);
  statue.root.rotation.y = -0.5 + Math.PI;
  statue.root.scale.setScalar(1.6);
  group.add(statue.root);
  // drifting motes of dust and ash in the evening light
  const N = 260, mp = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { mp[i * 3] = rr(-18, 12); mp[i * 3 + 1] = rr(0.2, 7); mp[i * 3 + 2] = rr(-14, 12); }
  const mg = new THREE.BufferGeometry(); mg.setAttribute('position', new THREE.BufferAttribute(mp, 3));
  const motes = new THREE.Points(mg, new THREE.PointsMaterial({ color: 0xffd9a0, size: 0.05, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false }));
  group.add(motes);

  const obstacles = [...cols.map(([x, z]) => [x, z, 0.9]), [sp.x, sp.y, 1.25], [3.5, balZ(3.5) + 0.95, 0.9], [-5.2, 12.4, 0.8], [2.8, 12.4, 0.8], [pole.x, pole.y, 0.25],
    ...[-15, -9, 0.6, 7].map((x) => [x, 13.6, 1.0]), ...[-8, -5, -2, 1, 4, 7, 10].map((z) => [-18, z, 0.9])];
  return {
    group, banners, fires, motes, obstacles, facadeWin: fw,
    walkable(x, z, r = 0.35) {
      if (x < BOUNDS.x0 + r || x > BOUNDS.x1 - r || z > BOUNDS.z1 - r || z < balZ(x) + 0.75 + r) return false;
      for (const [ox, oz, orad] of obstacles) if ((x - ox) ** 2 + (z - oz) ** 2 < (orad + r) ** 2) return false;
      return true;
    },
    update(t) {
      banners.forEach((m, i) => { m.rotation.x = Math.sin(t * 1.3 + i * 1.7) * 0.06 + 0.03; m.rotation.z = Math.sin(t * 0.9 + i) * 0.02; });
      for (const f of fires) {
        f.flames.children.forEach((c) => { const s = 0.75 + 0.35 * Math.abs(Math.sin(t * 9 + c.userData.ph) * Math.sin(t * 5.3 + c.userData.ph * 2)); c.scale.set(1, s, 1); c.rotation.y = t * 1.5 + c.userData.ph; });
        f.light.intensity = f.baseI * (0.85 + 0.15 * Math.sin(t * 13) * Math.sin(t * 7.7));
      }
      const p = motes.geometry.attributes.position.array;
      for (let i = 0; i < p.length; i += 3) { p[i] += Math.sin(t * 0.3 + i) * 0.003 + 0.004; p[i + 1] += Math.sin(t * 0.5 + i * 0.7) * 0.002 + 0.0015; if (p[i + 1] > 7.5) p[i + 1] = 0.2; if (p[i] > 12) p[i] = -18; }
      motes.geometry.attributes.position.needsUpdate = true;
    },
  };
}
