// Stylised sunset sky: a gradient dome with a sun disc and glow, stars that fade in at night, and large
// angular low-poly cloud banks that are pre-shaded (gold crests, rose and lavender undersides).
import * as THREE from 'three';
import { Builder, rand, rr, setSeed } from './lowpoly.js';

const vert = /* glsl */`
varying vec3 vDir;
void main() {
  vDir = normalize(position);
  vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  gl_Position = p.xyww;
}`;
const frag = /* glsl */`
uniform vec3 uSun; uniform vec3 uZenith; uniform vec3 uMid; uniform vec3 uHorizon; uniform vec3 uSunHorizon;
uniform vec3 uGlow; uniform vec3 uGround; uniform float uNight; uniform float uSunSize;
varying vec3 vDir;
float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
void main() {
  vec3 d = normalize(vDir);
  float h = d.y;
  vec3 col = mix(uHorizon, uMid, smoothstep(0.0, 0.16, h));
  col = mix(col, uZenith, smoothstep(0.12, 0.65, h));
  // warmer, brighter horizon toward the sun's bearing
  vec3 sh = normalize(vec3(uSun.x, 0.0, uSun.z));
  float az = max(dot(normalize(vec3(d.x, 0.0, d.z)), sh), 0.0);
  col = mix(col, uSunHorizon, pow(az, 3.0) * (1.0 - smoothstep(0.0, 0.32, h)) * 0.85);
  float s = max(dot(d, uSun), 0.0);
  col += uGlow * (pow(s, 6.0) * 0.35 + pow(s, 48.0) * 0.8);
  col += vec3(1.0, 0.85, 0.55) * smoothstep(uSunSize, uSunSize + 0.0004, s) * 6.0 * (1.0 - uNight);
  col = mix(col, uGround, smoothstep(0.0, -0.06, h));
  // stars
  vec3 q = floor(d * 380.0);
  float st = step(0.9975, hash(q)) * smoothstep(0.04, 0.3, h) * uNight;
  col += vec3(0.9, 0.92, 1.0) * st * 1.6;
  gl_FragColor = vec4(col, 1.0);
}`;

export const SKY_SUNSET = { zenith: 0x4c3f8e, mid: 0xb98ab5, horizon: 0xffb27a, sunHorizon: 0xffc070, glow: 0xffa860, ground: 0xc9a08a, fog: 0xe2aa98 };
export const SKY_NIGHT = { zenith: 0x0a0f26, mid: 0x1c2148, horizon: 0x3a3060, sunHorizon: 0x6a3a58, glow: 0x402030, ground: 0x1a1830, fog: 0x2a2640 };

export function buildSky(scene) {
  const u = {
    uSun: { value: new THREE.Vector3(0, 0.05, -1).normalize() }, uZenith: { value: new THREE.Color() }, uMid: { value: new THREE.Color() },
    uHorizon: { value: new THREE.Color() }, uSunHorizon: { value: new THREE.Color() }, uGlow: { value: new THREE.Color() },
    uGround: { value: new THREE.Color() }, uNight: { value: 0 }, uSunSize: { value: 0.9994 },
  };
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 24), new THREE.ShaderMaterial({ uniforms: u, vertexShader: vert, fragmentShader: frag, side: THREE.BackSide, depthWrite: false, fog: false }));
  dome.frustumCulled = false;
  dome.renderOrder = -10;
  scene.add(dome);

  // cloud banks: wide faceted relief sheets facing the palace
  setSeed(5);
  const cb = new Builder(0.02);
  const gold = 0xffd88e, peach = 0xfdbd80, coral = 0xf2a08a, rose = 0xd898aa, lav = 0xaa8ebc;
  const banks = [[-0.55, 11.5, 1700, 260], [-0.32, 15, 1100, 180], [-0.75, 7.5, 900, 150], [-0.12, 9, 700, 110], [0.6, 10.5, 1200, 190],
    [0.8, 14.5, 900, 150], [0.42, 6.5, 700, 90], [0.95, 8, 800, 120], [-1.0, 13, 800, 160], [2.4, 9, 1400, 200], [3.0, 12, 1200, 170], [-2.2, 10, 1300, 180]];
  for (const [t, elev, L, H] of banks) {
    const d = rr(2900, 3300);
    const c = new THREE.Vector3(Math.sin(t) * d, d * Math.tan(elev * Math.PI / 180), -Math.cos(t) * d);
    const fwd = c.clone().normalize();
    const uu = new THREE.Vector3(-fwd.z, 0, fwd.x).normalize(), w = new THREE.Vector3(0, 1, 0);
    const tilt = rr(-0.12, 0.12), n = Math.max(6, Math.floor(L / 110));
    const cols = [];
    for (let i = 0; i <= n; i++) {
      const x = (i / n - 0.5) * L, prof = Math.pow(Math.sin(Math.PI * i / n), 0.7);
      const base = rr(-0.08, 0.05) * H + x * tilt, top = base + H * prof * rr(0.55, 1.15), mid = base + (top - base) * rr(0.35, 0.6), lip = base - H * 0.12 * prof * rand();
      cols.push([
        c.clone().addScaledVector(uu, x + rr(-20, 20)).addScaledVector(w, lip),
        c.clone().addScaledVector(uu, x).addScaledVector(w, mid).addScaledVector(fwd, -rr(0.3, 0.8) * H * 0.6),
        c.clone().addScaledVector(uu, x + rr(-30, 30) - H * 0.5).addScaledVector(w, top),
      ]);
    }
    for (let i = 0; i < n; i++) {
      const Aa = cols[i], Bb = cols[i + 1];
      for (const [r, keys] of [[0, [lav, rose]], [1, [coral, i < n * 0.6 ? gold : peach]]]) {
        const p00 = Aa[r], p01 = Aa[r + 1], p10 = Bb[r], p11 = Bb[r + 1];
        const tris = (i + r) % 2 ? [[p00, p10, p11], [p00, p11, p01]] : [[p00, p10, p01], [p10, p11, p01]];
        tris.forEach((tri, k) => {
          let key = keys[k];
          if (r === 1 && rand() < 0.25) key = peach;
          const nrm = new THREE.Vector3().subVectors(tri[1], tri[0]).cross(new THREE.Vector3().subVectors(tri[2], tri[0]));
          const pts = tri.map((p) => p.toArray());
          cb.tri(...(nrm.dot(fwd) < 0 ? pts : pts.reverse()), key);
        });
      }
    }
  }
  const cloudMat = new THREE.MeshBasicMaterial({ vertexColors: true, fog: false, side: THREE.DoubleSide });
  const clouds = new THREE.Mesh(cb.geometry(), cloudMat);
  clouds.frustumCulled = false;
  scene.add(clouds);

  const A = Object.fromEntries(Object.entries(SKY_SUNSET).map(([k, v]) => [k, new THREE.Color(v)]));
  const B = Object.fromEntries(Object.entries(SKY_NIGHT).map(([k, v]) => [k, new THREE.Color(v)]));
  const fog = new THREE.Color();
  return {
    dome, clouds, uniforms: u, fogColor: fog,
    update(night, sunDir, camera) {
      dome.position.copy(camera.position);
      dome.scale.setScalar(camera.far * 0.95);
      clouds.position.set(camera.position.x, 0, camera.position.z);
      u.uSun.value.copy(sunDir);
      u.uNight.value = night;
      for (const [k, un] of [['zenith', 'uZenith'], ['mid', 'uMid'], ['horizon', 'uHorizon'], ['sunHorizon', 'uSunHorizon'], ['glow', 'uGlow'], ['ground', 'uGround']]) u[un].value.copy(A[k]).lerp(B[k], night);
      fog.copy(A.fog).lerp(B.fog, night);
      cloudMat.color.setRGB(1, 1, 1).lerp(new THREE.Color(0.16, 0.15, 0.3), night);
    },
  };
}
