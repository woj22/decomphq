// Low-poly characters for the four species, built from a spec (cast.js) and animated procedurally:
// walk cycle, idle breathing and glances, talking gestures, and a cloth cloak that swings with movement.
// A figure faces local +Z. Heights in metres.
import * as THREE from 'three';
import { Builder, MAT, rand } from './lowpoly.js';

export const SPECIES = {
  human: { ankle: 0.09, knee: 0.5, hip: 0.92, waist: 1.1, chest: 1.3, shoulder: 1.44, neck: 1.51, neckTop: 1.58, hipW: 0.16, waistW: 0.145, chestW: 0.19, shW: 0.215, depth: 0.12, leg: 0.07, arm: 0.05, armX: 0.215, legX: 0.09, neckR: 0.055, head: 1.0 },
  veyari: { ankle: 0.1, knee: 0.57, hip: 1.03, waist: 1.22, chest: 1.43, shoulder: 1.57, neck: 1.65, neckTop: 1.76, hipW: 0.14, waistW: 0.125, chestW: 0.165, shW: 0.19, depth: 0.105, leg: 0.06, arm: 0.044, armX: 0.19, legX: 0.08, neckR: 0.048, head: 0.98 },
  othari: { ankle: 0.08, knee: 0.32, hip: 0.6, waist: 0.78, chest: 0.98, shoulder: 1.14, neck: 1.2, neckTop: 1.24, hipW: 0.21, waistW: 0.21, chestW: 0.26, shW: 0.29, depth: 0.17, leg: 0.095, arm: 0.07, armX: 0.29, legX: 0.12, neckR: 0.08, head: 1.15 },
  kharad: { ankle: 0.32, knee: 0.72, hip: 1.1, waist: 1.3, chest: 1.56, shoulder: 1.74, neck: 1.8, neckTop: 1.98, hipW: 0.2, waistW: 0.18, chestW: 0.27, shW: 0.3, depth: 0.17, leg: 0.1, arm: 0.078, armX: 0.32, legX: 0.15, neckR: 0.12, head: 1.25 },
};
const C = (h) => new THREE.Color(h);
const shade = (h, k) => C(h).multiplyScalar(k).getHex();

function part(b, parent, mat = MAT.std) {
  const m = new THREE.Mesh(b.geometry(), mat);
  m.castShadow = true; m.receiveShadow = true;
  parent.add(m);
  return m;
}

function head(spec, P) {
  const b = new Builder(0.03);
  const sp = spec.species, skin = spec.skin;
  const wx = sp === 'othari' ? 1.22 : sp === 'kharad' ? 1.1 : sp === 'veyari' ? 0.92 : 1;
  const top = sp === 'veyari' ? 1.25 : 1;
  const secs = [[0, 0.05, 0.06, 0.02], [0.05, 0.075, 0.085, 0.015], [0.11, 0.088, 0.1, 0.005], [0.17, 0.092, 0.102, 0], [0.22 * top, 0.077, 0.09, -0.01 * top], [0.255 * top, 0.042, 0.055, -0.025 * top]]
    .map(([y, rx, rz, cz]) => [y, rx * wx, rz, 0, cz]);
  b.loft(secs, 8, skin, true, true, Math.PI / 8);
  const fz = 0.1 * 0.93;                     // the front facet plane
  const eyeY = 0.135, ex = 0.036 * wx;
  const eyeCol = sp === 'kharad' ? 0xe0b030 : sp === 'veyari' ? 0x9fd6ff : 0xf4efe6;
  for (const s of [-1, 1]) {
    b.quad([s * ex - 0.017, eyeY - 0.008, fz + 0.004], [s * ex + 0.017, eyeY - 0.008, fz + 0.004], [s * ex + 0.017, eyeY + 0.009, fz + 0.004], [s * ex - 0.017, eyeY + 0.009, fz + 0.004].map((v) => v), eyeCol);
    b.quad([s * ex - 0.007, eyeY - 0.008, fz + 0.007], [s * ex + 0.007, eyeY - 0.008, fz + 0.007], [s * ex + 0.007, eyeY + 0.008, fz + 0.007], [s * ex - 0.007, eyeY + 0.008, fz + 0.007], sp === 'kharad' ? 0x201000 : 0x2a1c14);
    b.box(s * ex, eyeY + 0.024, fz + 0.004, 0.04, 0.011, 0.014, spec.hair || shade(skin, 0.6));
    // ears
    if (sp === 'veyari') b.tri([s * 0.082 * wx, 0.12, 0.0], [s * 0.082 * wx, 0.16, -0.02], [s * 0.15, 0.2, -0.06], shade(skin, 0.92));
    else if (sp !== 'kharad') b.box(s * 0.09 * wx, 0.12, -0.005, 0.02, 0.05, 0.035, shade(skin, 0.95));
  }
  if (sp === 'kharad') {
    b.box(0, 0.07, fz + 0.035, 0.11, 0.075, 0.09, shade(skin, 1.05));          // muzzle
    b.box(0, 0.04, fz + 0.045, 0.1, 0.012, 0.07, 0x2a1810);                    // mouth line
    b.box(0, 0.16, fz + 0.01, 0.17, 0.025, 0.04, shade(skin, 0.85));           // brow ridge
    for (const s of [-1, 1]) b.tube([[s * 0.07, 0.2, -0.03], [s * 0.12, 0.25, -0.1], [s * 0.13, 0.27, -0.2], [s * 0.11, 0.25, -0.27]], [0.025, 0.02, 0.014, 0.006], 5, 0xd8c8a8);
  } else {
    b.tri([0, 0.09, fz + 0.035], [-0.017, 0.088, fz], [0.017, 0.088, fz], shade(skin, 0.9));      // nose
    b.tri([0, 0.09, fz + 0.035], [0, 0.135, fz + 0.005], [-0.017, 0.088, fz], shade(skin, 1.0));
    b.tri([0, 0.09, fz + 0.035], [0.017, 0.088, fz], [0, 0.135, fz + 0.005], shade(skin, 0.95));
    b.quad([-0.022, 0.058, fz - 0.004], [0.022, 0.058, fz - 0.004], [0.022, 0.066, fz - 0.004], [-0.022, 0.066, fz - 0.004], shade(skin, 0.55));
  }
  // hair
  const hc = spec.hair;
  if (hc && spec.headwear !== 'helmet') {
    const st = spec.hairStyle || 'short';
    b.loft([[0.15 * top, 0.097 * wx, 0.107, 0, -0.012], [0.21 * top, 0.088 * wx, 0.1, 0, -0.016], [0.265 * top, 0.05, 0.065, 0, -0.03]], 8, hc, true, false, Math.PI / 8);
    b.box(0, 0.12, -0.085, 0.17 * wx, 0.09, 0.05, hc);
    if (st === 'long') b.box(0, 0.0, -0.08, 0.18 * wx, 0.26, 0.05, hc);
    if (st === 'bun') b.prism(0, 0.2, -0.12, 0.045, 0.04, 0.06, 6, hc, true, true);
    if (st === 'braids') for (const s of [-1, 1]) b.tube([[s * 0.08, 0.12, -0.04], [s * 0.09, 0.0, -0.03], [s * 0.085, -0.12, 0.0]], [0.022, 0.02, 0.016], 5, hc);
  }
  if (spec.beard === 'full' || spec.beard === 'short') {
    const L = spec.beard === 'full' ? 0.07 : 0.035;
    b.loft([[-L, 0.03, 0.03, 0, 0.07], [0.02, 0.07 * wx, 0.07, 0, 0.04], [0.075, 0.088 * wx, 0.08, 0, 0.02]], 8, hc || 0x3a2618, false, true, Math.PI / 8);
  }
  if (spec.beard === 'plates') for (let k = 0; k < 3; k++) b.box((k - 1) * 0.045, -0.01, fz - 0.01, 0.04, 0.07, 0.04, 0x8a8a80);
  // headwear
  const hw = spec.headwear;
  const metal = hw && hw.includes('silver') ? 0xc7cdd8 : hw && hw.includes('iron') ? 0x5a5a5e : 0xd8a23a;
  if (hw && (hw.startsWith('crown') || hw === 'kharad_crown')) {
    b.prism(0, 0.2 * top, -0.01, 0.1 * wx, 0.105 * wx, 0.035, 8, metal, false, false, Math.PI / 8, 0.112, 0.117);
    for (let k = 0; k < 8; k++) { const a = (k / 8) * Math.PI * 2 + Math.PI / 8; b.prism(Math.cos(a) * 0.1 * wx, 0.235 * top, Math.sin(a) * 0.115 - 0.01, 0.018, 0, 0.05, 4, metal); }
  }
  if (hw === 'laurel_gold' || hw === 'circlet' || hw === 'circlet_gold' || hw === 'diadem' || hw === 'diadem_silver') {
    b.prism(0, 0.19 * top, -0.012, 0.098 * wx, 0.098 * wx, 0.02, 8, hw === 'circlet' || hw === 'diadem_silver' ? 0xc7cdd8 : 0xd8a23a, false, false, Math.PI / 8, 0.11, 0.11);
    if (hw.startsWith('diadem')) b.prism(0, 0.2, 0.1, 0.02, 0, 0.05, 4, 0xd8a23a);
  }
  if (hw === 'helmet') {
    b.loft([[0.1, 0.1 * wx, 0.112, 0, -0.01], [0.2, 0.098 * wx, 0.11, 0, -0.012], [0.27, 0.06, 0.07, 0, -0.025], [0.29, 0.01, 0.01, 0, -0.03]], 8, 0xb8893a, true, false, Math.PI / 8);
    b.box(0, 0.33, -0.02, 0.025, 0.08, 0.24, spec.secondary || 0x9b2226);
    for (const s of [-1, 1]) b.box(s * 0.095 * wx, 0.07, 0.03, 0.015, 0.08, 0.06, 0xb8893a);
  }
  return b;
}

export class Figure {
  constructor(spec) {
    this.spec = spec;
    const P = SPECIES[spec.species] || SPECIES.human;
    const k = spec.build || 1;
    this.P = P;
    this.root = new THREE.Group();
    this.body = new THREE.Group();
    this.root.add(this.body);
    const prim = spec.primary, sec = spec.secondary || prim, trim = spec.trim || 0xc8962e, skin = spec.skin;
    const outfit = spec.outfit || 'tunic';
    const robe = ['toga', 'robe', 'stola'].includes(outfit);
    // torso
    const tb = new Builder();
    tb.loft([[P.hip, P.hipW * k, P.depth * k], [P.waist, P.waistW * k, P.depth * 0.95 * k], [P.chest, P.chestW * k, P.depth * 1.1 * k], [P.shoulder, P.shW * k * 0.95, P.depth * k], [P.neck, P.neckR * 1.6, P.neckR * 1.4]], 8, outfit === 'armour' || outfit === 'scale' ? prim : prim, true, true, Math.PI / 8);
    tb.box(0, P.waist - 0.02, 0, P.waistW * 2.15 * k, 0.05, P.depth * 2.05 * k, trim);
    if (outfit === 'toga') tb.tube([[P.shW * 0.9, P.shoulder, 0.02], [0.02, P.chest, P.depth * 1.15], [-P.waistW, P.waist - 0.05, 0.03]], [0.035, 0.04, 0.035], 5, sec);
    if (outfit === 'armour' || outfit === 'scale') {
      tb.box(0, P.chest, P.depth * 0.75 * k, P.chestW * 1.6 * k, 0.16, 0.06, shade(prim, 1.1));
      for (const s of [-1, 1]) tb.box(s * P.shW * 0.95 * k, P.shoulder - 0.03, 0, 0.12, 0.06, P.depth * 2.2 * k, shade(prim, 0.9));
    }
    // skirt: robes to the ankle, tunics to the knee, armour to mid-thigh with strips
    const hemY = robe ? P.ankle + 0.04 : outfit === 'tunic' ? P.knee - 0.04 : (P.hip + P.knee) / 2;
    const flare = robe ? 1.45 : 1.15;
    tb.loft([[P.hip + 0.02, P.hipW * 1.06 * k, P.depth * 1.08 * k], [hemY + (P.hip - hemY) * 0.4, P.hipW * (1 + (flare - 1) * 0.6) * k, P.depth * 1.15 * k], [hemY, P.hipW * flare * k, P.depth * 1.3 * k]].reverse(), 10, robe ? (outfit === 'toga' ? prim : prim) : sec, true, true);
    tb.loft([[hemY - 0.0, P.hipW * flare * k * 1.01, P.depth * 1.31 * k], [hemY + 0.04, P.hipW * flare * k * 0.98, P.depth * 1.27 * k]], 10, trim, false, false);
    if (outfit === 'armour' || outfit === 'scale') for (let i = 0; i < 8; i++) { const a = (i / 8) * Math.PI * 2; tb.box(Math.cos(a) * P.hipW * 1.15 * k, hemY - 0.06, Math.sin(a) * P.depth * 1.3 * k, 0.06, 0.12, 0.02, sec, -a); }
    tb.prism(0, P.neck - 0.02, 0, P.neckR, P.neckR * 0.95, P.neckTop - P.neck + 0.03, 6, skin);
    if (spec.species === 'kharad') tb.prism(0, P.neckTop - 0.06, 0.02, P.neckR * 1.1, P.neckR * 0.9, 0.08, 6, skin);
    this.torso = part(tb, this.body);
    // head
    this.head = new THREE.Group();
    this.head.position.set(0, P.neckTop - 0.02, 0.0);
    this.head.scale.setScalar(P.head * (spec.species === 'othari' ? 1.15 : 1));
    this.body.add(this.head);
    part(head(spec, P), this.head);
    // legs
    this.legs = [];
    for (const s of [-1, 1]) {
      const g = new THREE.Group(); g.position.set(s * P.legX * k, P.hip, 0); this.body.add(g);
      const lb = new Builder();
      const L = P.hip - P.ankle;
      lb.tube([[0, 0, 0], [0, -L * 0.48, 0.01], [0, -L, 0]], [P.leg * k, P.leg * 0.78 * k, P.leg * 0.6 * k], 6, robe ? shade(prim, 0.8) : outfit === 'tunic' ? skin : shade(sec, 0.9));
      lb.box(0, -L - P.ankle / 2 + 0.01, 0.04, P.leg * 1.6 * k, Math.max(0.06, P.ankle), 0.22 * (spec.species === 'kharad' ? 1.4 : 1), spec.species === 'kharad' ? skin : 0x5b3a28);
      part(lb, g);
      this.legs.push(g);
    }
    // arms
    this.arms = [];
    const armL = (P.shoulder - P.hip) * 1.05;
    for (const s of [-1, 1]) {
      const g = new THREE.Group(); g.position.set(s * P.armX * k, P.shoulder - 0.04, 0); g.rotation.z = s * 0.08; this.body.add(g);
      const ab = new Builder();
      const sleeve = outfit === 'armour' || outfit === 'tunic' ? skin : robe ? prim : skin;
      ab.tube([[0, 0.02, 0], [0, -armL * 0.5, 0.01]], [P.arm * 1.15 * k, P.arm * k], 6, outfit === 'scale' ? prim : robe ? prim : sec);
      ab.tube([[0, -armL * 0.48, 0.01], [0, -armL * 0.95, 0.04]], [P.arm * 0.9 * k, P.arm * 0.72 * k], 6, sleeve);
      ab.box(0, -armL - 0.03, 0.045, P.arm * 1.6 * k, 0.09, P.arm * 1.2 * k, skin);
      part(ab, g);
      this.arms.push(g);
    }
    this.handY = -armL - 0.04;
    // prop in the right hand
    if (spec.prop && spec.prop !== 'none') {
      const pb = new Builder();
      const hy = this.handY;
      if (spec.prop === 'spear' || spec.prop === 'staff' || spec.prop === 'staff_gold') {
        pb.prism(0, hy - 0.9, 0.06, 0.022, 0.02, 2.4, 5, spec.prop === 'staff_gold' ? 0xd8a23a : 0x6b4a2e, true, true);
        if (spec.prop === 'spear') pb.prism(0, hy + 1.5, 0.06, 0.045, 0, 0.26, 4, 0xc7cdd8);
        else pb.prism(0, hy + 1.5, 0.06, 0.06, 0.03, 0.1, 6, 0xd8a23a);
      } else if (spec.prop === 'scroll') pb.tube([[-0.1, hy, 0.08], [0.1, hy, 0.08]], [0.03, 0.03], 6, 0xe8dcc0);
      else if (spec.prop === 'tablet') pb.box(0, hy + 0.02, 0.1, 0.18, 0.24, 0.025, 0x8a6a48);
      else if (spec.prop === 'sword') pb.box(-0.02, hy + 0.12, 0.05, 0.04, 0.6, 0.015, 0xd0d4dc);
      part(pb, this.arms[1]);
    }
    // cloak: a cloth grid hanging from the shoulders, rebuilt every frame
    if (spec.cloak) {
      this.cloak = { cols: spec.royal ? 11 : 8, rows: 8, top: P.shoulder + 0.01, len: P.shoulder - P.ankle - 0.08, w: P.shW * 1.15 * k, d: P.depth * k, colour: C(spec.cloak), trim: C(trim), royal: !!spec.royal };
      const n = (this.cloak.cols - 1) * (this.cloak.rows - 1) * 6;
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
      const col = new Float32Array(n * 3);
      let q = 0;
      for (let r = 0; r < this.cloak.rows - 1; r++) for (let c = 0; c < this.cloak.cols - 1; c++) for (let t = 0; t < 6; t++) {
        const edge = this.cloak.royal && (c === 0 || c === this.cloak.cols - 2 || r === this.cloak.rows - 2);
        const cc = edge ? this.cloak.trim : this.cloak.colour;
        const j = 1 + ((r * 7 + c * 3) % 5 - 2) * 0.02;
        col[q++] = cc.r * j; col[q++] = cc.g * j; col[q++] = cc.b * j;
      }
      geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
      this.cloakMesh = new THREE.Mesh(geo, MAT.cloth);
      this.cloakMesh.castShadow = true;
      this.cloakMesh.frustumCulled = false;
      this.body.add(this.cloakMesh);
      if (spec.royal) {   // gold V on the back
        const vb = new Builder();
        for (const s of [-1, 1]) vb.tube([[s * P.shW * 0.9 * k, P.shoulder + 0.01, -P.depth * k - 0.03], [0, P.shoulder - 0.45, -P.depth * k - 0.09]], [0.022, 0.022], 4, trim);
        this.vmesh = part(vb, this.body);
      }
    }
    // animation state
    this.phase = rand() * 6.28; this.speed = 0; this.time = rand() * 10; this.talk = 0; this.look = 0; this.lookT = 0;
    this.updateCloak(0);
  }

  updateCloak(dt) {
    if (!this.cloakMesh) return;
    const c = this.cloak, pos = this.cloakMesh.geometry.attributes.position.array;
    const grid = [];
    const swing = 0.05 + Math.min(this.speed, 2.5) * 0.12;
    for (let r = 0; r < c.rows; r++) {
      const t = r / (c.rows - 1), y = c.top - c.len * t;
      grid.push([]);
      for (let k = 0; k < c.cols; k++) {
        const u = k / (c.cols - 1);
        const a = Math.PI * (0.08 + 0.84 * u);
        const fold = c.royal ? (k % 2 ? 0.025 : -0.015) * t : 0;
        const flare = 1 + t * 0.35;
        const wave = Math.sin(this.time * 2.2 + u * 5 + t * 3) * 0.025 * t + Math.sin(this.phase * 2) * 0.02 * t * Math.min(1, this.speed);
        const x = -Math.cos(a) * c.w * flare;
        const z = -Math.sin(a) * (c.d + 0.03) * flare - 0.02 - t * t * swing - fold - wave;
        grid[r].push([x, y + Math.abs(wave) * 0.3, z]);
      }
    }
    let q = 0;
    const P = (p) => { pos[q++] = p[0]; pos[q++] = p[1]; pos[q++] = p[2]; };
    for (let r = 0; r < c.rows - 1; r++) for (let k = 0; k < c.cols - 1; k++) {
      const a = grid[r][k], b = grid[r][k + 1], d = grid[r + 1][k], e = grid[r + 1][k + 1];
      P(a); P(d); P(e); P(a); P(e); P(b);
    }
    this.cloakMesh.geometry.attributes.position.needsUpdate = true;
    this.cloakMesh.geometry.computeVertexNormals();
  }

  update(dt, speed) {
    this.time += dt;
    this.speed += (speed - this.speed) * Math.min(1, dt * 8);
    const s = this.speed, P = this.P;
    this.phase += dt * (1.6 + s * 2.6);
    const sw = Math.min(1, s / 1.4);
    const ph = this.phase;
    this.legs[0].rotation.x = Math.sin(ph) * 0.55 * sw;
    this.legs[1].rotation.x = -Math.sin(ph) * 0.55 * sw;
    this.arms[0].rotation.x = -Math.sin(ph) * 0.4 * sw;
    this.arms[1].rotation.x = Math.sin(ph) * 0.4 * sw - (this.spec.prop === 'spear' || this.spec.prop?.startsWith('staff') ? 0.25 : 0);
    this.body.position.y = Math.abs(Math.sin(ph)) * 0.035 * sw + Math.sin(this.time * 1.7) * 0.004;
    this.torso.scale.set(1 + Math.sin(this.time * 1.7) * 0.008, 1, 1 + Math.sin(this.time * 1.7) * 0.012);
    // talking: gesture with the free hand and nod
    if (this.talk > 0) {
      this.arms[0].rotation.x = -0.5 - Math.sin(this.time * 3.1) * 0.25;
      this.arms[0].rotation.z = -0.25 + Math.sin(this.time * 2.3) * 0.1;
      this.head.rotation.x = Math.sin(this.time * 4.3) * 0.05;
    } else { this.arms[0].rotation.z = -0.08; this.head.rotation.x *= 0.9; }
    // idle glances
    this.lookT -= dt;
    if (this.lookT < 0) { this.look = s > 0.2 ? 0 : (rand() - 0.5) * 1.0; this.lookT = 2 + rand() * 4; }
    this.head.rotation.y += (this.look - this.head.rotation.y) * Math.min(1, dt * 2);
    this.updateCloak(dt);
    void P;
  }
}
