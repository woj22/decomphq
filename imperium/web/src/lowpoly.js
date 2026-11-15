// Low-poly mesh builder: accumulates flat-shaded, vertex-coloured triangles under a transform stack.
// Every face gets a tiny brightness jitter so large surfaces read as hand-faceted rather than flat.
import * as THREE from 'three';

const _v = new THREE.Vector3();
let seed = 1;
export function rand() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }
export function setSeed(s) { seed = Math.max(1, Math.floor(s) % 2147483647); }
export const rr = (a, b) => a + (b - a) * rand();
export const pick = (arr) => arr[Math.floor(rand() * arr.length)];

export class Builder {
  constructor(jitter = 0.035) {
    this.pos = []; this.col = []; this.jitter = jitter;
    this.stack = [new THREE.Matrix4()];
  }
  get m() { return this.stack[this.stack.length - 1]; }
  push(mat) { this.stack.push(this.m.clone().multiply(mat)); return this; }
  pushT(x, y, z, ry = 0, s = 1) {
    const mat = new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), ry), new THREE.Vector3(s, s, s));
    return this.push(mat);
  }
  pop() { this.stack.pop(); return this; }
  _p(p) { _v.set(p[0], p[1], p[2]).applyMatrix4(this.m); this.pos.push(_v.x, _v.y, _v.z); }
  tri(a, b, c, color) {
    const col = new THREE.Color(color);
    const j = 1 + (rand() - 0.5) * 2 * this.jitter;
    this._p(a); this._p(b); this._p(c);
    for (let i = 0; i < 3; i++) this.col.push(col.r * j, col.g * j, col.b * j);
  }
  quad(a, b, c, d, color) { this.tri(a, b, c, color); this.tri(a, c, d, color); }
  poly(pts, color) { for (let i = 1; i < pts.length - 1; i++) this.tri(pts[0], pts[i], pts[i + 1], color); }
  // axis-aligned box (in the current frame), optional rotation about Y and top taper
  box(cx, cy, cz, sx, sy, sz, color, ry = 0, taper = 1) {
    const c = Math.cos(ry), s = Math.sin(ry);
    const P = (x, y, z) => { const t = y > 0 ? taper : 1; x *= t; z *= t; return [cx + c * x + s * z, cy + y, cz - s * x + c * z]; };
    const hx = sx / 2, hy = sy / 2, hz = sz / 2;
    const v = [P(-hx, -hy, -hz), P(hx, -hy, -hz), P(hx, -hy, hz), P(-hx, -hy, hz), P(-hx, hy, -hz), P(hx, hy, -hz), P(hx, hy, hz), P(-hx, hy, hz)];
    const f = (a, b, cc, d, k = 1) => this.quad(v[a], v[b], v[cc], v[d], k === 1 ? color : new THREE.Color(color).multiplyScalar(k));
    f(4, 7, 6, 5, 1.0); f(0, 1, 2, 3, 0.8); f(3, 2, 6, 7); f(1, 0, 4, 5); f(2, 1, 5, 6); f(0, 3, 7, 4);
  }
  // a frustum / prism / cone along Y with n sides
  prism(cx, cy, cz, r0, r1, h, n, color, capTop = true, capBot = true, rot = 0, ry0 = null, ry1 = null) {
    const a0 = [], a1 = [];
    for (let i = 0; i < n; i++) {
      const t = rot + (i / n) * Math.PI * 2;
      a0.push([cx + Math.cos(t) * r0, cy, cz + Math.sin(t) * (ry0 ?? r0)]);
      a1.push([cx + Math.cos(t) * r1, cy + h, cz + Math.sin(t) * (ry1 ?? r1)]);
    }
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      if (r1 > 1e-4) this.quad(a0[j], a0[i], a1[i], a1[j], color);
      else this.tri(a0[j], a0[i], a1[i], color);
    }
    if (capTop && r1 > 1e-4) this.poly([...a1].reverse(), color);
    if (capBot) this.poly(a0, color);
  }
  // a loft through rings: sections = [[y, rx, rz, cx, cz]], n sides
  loft(sections, n, color, capTop = true, capBot = true, rot = 0) {
    const rings = sections.map(([y, rx, rz, cx = 0, cz = 0]) => {
      const r = [];
      for (let i = 0; i < n; i++) { const t = rot + (i / n) * Math.PI * 2; r.push([cx + Math.cos(t) * rx, y, cz + Math.sin(t) * rz]); }
      return r;
    });
    for (let k = 0; k < rings.length - 1; k++) {
      for (let i = 0; i < n; i++) { const j = (i + 1) % n; this.quad(rings[k][j], rings[k][i], rings[k + 1][i], rings[k + 1][j], color); }
    }
    if (capTop) this.poly([...rings[rings.length - 1]].reverse(), color);
    if (capBot) this.poly(rings[0], color);
  }
  // a tube along a path of points with radii
  tube(path, radii, n, color) {
    const rings = [];
    for (let k = 0; k < path.length; k++) {
      const p = new THREE.Vector3(...path[k]);
      const q = new THREE.Vector3(...path[Math.min(k + 1, path.length - 1)]);
      const o = new THREE.Vector3(...path[Math.max(k - 1, 0)]);
      const d = q.sub(o).normalize();
      const up = Math.abs(d.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
      const u = new THREE.Vector3().crossVectors(d, up).normalize();
      const w = new THREE.Vector3().crossVectors(u, d).normalize();
      const r = [];
      for (let i = 0; i < n; i++) {
        const t = (i / n) * Math.PI * 2;
        r.push(p.clone().addScaledVector(u, Math.cos(t) * radii[k]).addScaledVector(w, Math.sin(t) * radii[k]).toArray());
      }
      rings.push(r);
    }
    for (let k = 0; k < rings.length - 1; k++) {
      for (let i = 0; i < n; i++) { const j = (i + 1) % n; this.quad(rings[k][j], rings[k][i], rings[k + 1][i], rings[k + 1][j], color); }
    }
    this.poly(rings[0], color);
    this.poly([...rings[rings.length - 1]].reverse(), color);
  }
  // copy another builder's triangles in, transformed by `mat` (default: this builder's current frame)
  append(o, mat = this.m) {
    const v = new THREE.Vector3();
    for (let i = 0; i < o.pos.length; i += 3) { v.set(o.pos[i], o.pos[i + 1], o.pos[i + 2]).applyMatrix4(mat); this.pos.push(v.x, v.y, v.z); }
    for (let i = 0; i < o.col.length; i++) this.col.push(o.col[i]);
  }
  get count() { return this.pos.length / 9; }
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.col, 3));
    g.computeVertexNormals();
    g.computeBoundingSphere();
    return g;
  }
}

export const MAT = {
  std: new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.82, metalness: 0.0 }),
  metal: new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.38, metalness: 0.75 }),
  basic: new THREE.MeshBasicMaterial({ vertexColors: true, fog: false }),
  cloth: new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.9, side: THREE.DoubleSide }),
};

export function mesh(builder, material = MAT.std, { cast = true, receive = true } = {}) {
  const m = new THREE.Mesh(builder.geometry(), material);
  m.castShadow = cast; m.receiveShadow = receive;
  return m;
}
