import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

/* =====================================================================
   Last Carriage — 3 independent AIs + 1 human, all posing as historical
   figures, around a table on a train. Find the human.
   ===================================================================== */

const ROUNDS = 4;

const FIGURES = [
  { name: 'Cleopatra', desc: 'Last pharaoh of Ptolemaic Egypt (69–30 BC). Shrewd, multilingual, theatrical.', color: 0x2f8f83, hat: 'crown' },
  { name: 'Julius Caesar', desc: 'Roman general and dictator (100–44 BC). Ambitious, terse, refers to himself grandly.', color: 0x8c2a2a, hat: 'laurel' },
  { name: 'Leonardo da Vinci', desc: 'Renaissance polymath (1452–1519). Curious, sketches everything, distracted by ideas.', color: 0x7a5a32, hat: 'beret' },
  { name: 'Marie Curie', desc: 'Physicist and chemist, two Nobel prizes (1867–1934). Precise, modest, relentless.', color: 0x3a3a46, hat: 'bun' },
  { name: 'Napoleon Bonaparte', desc: 'French emperor (1769–1821). Strategic, proud, impatient.', color: 0x23366e, hat: 'bicorne' },
  { name: 'Ada Lovelace', desc: 'Mathematician, first published algorithm (1815–1852). Poetic about numbers.', color: 0x5b2e6e, hat: 'bun' },
  { name: 'Abraham Lincoln', desc: '16th US president (1809–1865). Folksy stories, dry humour, moral weight.', color: 0x1d1d1d, hat: 'tophat' },
  { name: 'Joan of Arc', desc: 'French heroine and martyr (c.1412–1431). Devout, fearless, blunt.', color: 0x8a8f98, hat: 'none' },
  { name: 'Genghis Khan', desc: 'Founder of the Mongol Empire (c.1162–1227). Direct, loyal to loyal men, ruthless.', color: 0x6e4a1e, hat: 'furcap' },
  { name: 'Isaac Newton', desc: 'Physicist and mathematician (1643–1727). Brilliant, prickly, holds grudges.', color: 0x4a4038, hat: 'wig' },
  { name: 'Frida Kahlo', desc: 'Mexican painter (1907–1954). Vivid, defiant, frank about pain and love.', color: 0xb8323a, hat: 'flowers' },
  { name: 'Nikola Tesla', desc: 'Inventor of AC systems (1856–1943). Visionary, eccentric, obsessive.', color: 0x2c3440, hat: 'none' },
  { name: 'Elizabeth I', desc: 'Queen of England (1533–1603). Commanding, witty, never shows her hand.', color: 0xc9a227, hat: 'crown' },
  { name: 'William Shakespeare', desc: 'Playwright and poet (1564–1616). Wordplay, metaphor, theatre.', color: 0x4b5a2a, hat: 'none' },
  { name: 'Harriet Tubman', desc: 'Abolitionist, Underground Railroad conductor (c.1822–1913). Brave, practical, faithful.', color: 0x5a3b2a, hat: 'headscarf' },
  { name: 'Confucius', desc: 'Chinese philosopher (551–479 BC). Speaks in measured maxims on virtue and order.', color: 0x2b5b3a, hat: 'cap' },
  { name: 'Charles Darwin', desc: 'Naturalist, theory of evolution (1809–1882). Patient, observant, cautious.', color: 0x5a4a3a, hat: 'none' },
  { name: 'Amelia Earhart', desc: 'Aviation pioneer (1897–1937). Adventurous, plain-spoken, restless.', color: 0x7a4b2a, hat: 'aviator' },
  { name: 'Winston Churchill', desc: 'British prime minister (1874–1965). Rhetorical, stubborn, witty.', color: 0x2a2a30, hat: 'bowler' },
  { name: 'Wolfgang Amadeus Mozart', desc: 'Composer (1756–1791). Playful, cheeky, music in every thought.', color: 0x8a3a6a, hat: 'wig' },
  { name: 'Florence Nightingale', desc: 'Founder of modern nursing, statistician (1820–1910). Exacting, compassionate.', color: 0x31476a, hat: 'headscarf' },
];

const TEMPERAMENTS = [
  'sharp and suspicious; you trust no one quickly',
  'analytical; you weigh evidence carefully and change your mind when the record warrants it',
  'charming but cunning; you probe with flattery',
  'blunt and impatient; you go straight for the weakest answer',
  'playful and theatrical; you set little traps in your questions',
];

const SKIN = [0xe8c4a0, 0xc99a74, 0x9c6b4a, 0xf0d2b6, 0x7a4e34];

// Seats go round the table clockwise (seen from above): 0 = you (front, window),
// 1 = beside you (front, aisle), 2 = across from 1 (back, aisle), 3 = across from you (back, window).
// "The person next to you" is always the next seat in this circle.
const SEAT_POS = [
  { x: -1.12, z: 0.82, face: Math.PI },  // faces -z
  { x: -0.62, z: 0.82, face: Math.PI },
  { x: -0.62, z: -0.82, face: 0 },       // faces +z
  { x: -1.12, z: -0.82, face: 0 },
];
const SEAT_WHERE = ['your seat', 'beside you', 'diagonally across', 'opposite you'];

// ------------------------------------------------------------------ state
const cfg = { key: '', model: 'gpt-6-luna', baseUrl: 'https://api.openai.com/v1', demo: false };
let players = []; // {seat, figure, human, temperament, notes, actor}
let record = [];  // public transcript {round, kind, seat, text, target?, answer?}
let round = 0;

const $ = (id) => document.getElementById(id);
const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const nameOf = (seat) => players[seat].figure.name;
const next = (seat) => (seat + 1) % 4;
const prev = (seat) => (seat + 3) % 4;

// =================================================================== 3D
const canvas = $('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x151a24);
scene.fog = new THREE.Fog(0x2a303c, 4, 38); // blizzard: you can barely see past the trees
const camera = new THREE.PerspectiveCamera(72, 1, 0.05, 300);
const EYE = new THREE.Vector3(-1.12, 1.22, 0.86);
camera.position.copy(EYE);

const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...extra });
function box(w, h, d, color, x, y, z, parent = scene, m) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m || mat(color));
  mesh.position.set(x, y, z); parent.add(mesh); return mesh;
}

// lights
scene.add(new THREE.HemisphereLight(0x9fb4d8, 0x2a2018, 0.7));
const moon = new THREE.DirectionalLight(0x9db6ff, 0.6); moon.position.set(-10, 12, 4); moon.intensity = 0.25; scene.add(moon);
const ceilingLights = [];
function ceilingFlicker(t) { // the power is struggling in the cold
  const dip = Math.sin(t * 13) > 0.97 && Math.sin(t * 0.31) > 0.6;
  for (const l of ceilingLights) l.intensity = dip ? 2.2 : 5.5;
}
for (const z of [-5, -1.5, 1.5, 5]) {
  const l = new THREE.PointLight(0xffd9a0, 5.5, 6, 1.6); l.position.set(0, 2.25, z); scene.add(l); ceilingLights.push(l);
  box(1.4, 0.04, 0.3, 0, 0, 2.38, z, scene, new THREE.MeshBasicMaterial({ color: 0xfff1d0 }));
}
const tableLamp = new THREE.PointLight(0xffc070, 1.6, 3, 2); tableLamp.position.set(-0.9, 1.05, 0); scene.add(tableLamp);

// frosted window panes: clear in the middle, rimed at the edges
const frostTex = (() => {
  const c = document.createElement('canvas'); c.width = 256; c.height = 128; const g = c.getContext('2d');
  const grd = g.createRadialGradient(128, 64, 30, 128, 64, 150);
  grd.addColorStop(0, 'rgba(220,232,250,0.04)'); grd.addColorStop(0.55, 'rgba(220,232,250,0.12)'); grd.addColorStop(1, 'rgba(235,242,255,0.85)');
  g.fillStyle = grd; g.fillRect(0, 0, 256, 128);
  for (let i = 0; i < 260; i++) { // frost crystals creeping in from the edges
    const edge = Math.random() < 0.5 ? (Math.random() < 0.5 ? 0 : 256) : Math.random() * 256;
    const x = edge, y = edge === 0 || edge === 256 ? Math.random() * 128 : (Math.random() < 0.6 ? 128 : 0);
    g.strokeStyle = `rgba(240,246,255,${0.15 + Math.random() * 0.3})`; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + (128 - x) * Math.random() * 0.35, y + (64 - y) * Math.random() * 0.45); g.stroke();
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.repeat.set(8, 1); t.offset.x = 0.5; return t;
})();

// carriage shell: length 16 (z -8..8), width 3, height 2.4
const L = 16, W = 3, H = 2.4;
box(W, 0.05, L, 0x3b2f3a, 0, -0.025, 0);           // floor carpet
box(0.7, 0.051, L, 0x5a3440, 0, -0.02, 0);         // aisle runner
box(W, 0.05, L, 0xe9e0cc, 0, H + 0.025, 0);        // ceiling
for (const side of [-1, 1]) {
  const x = side * (W / 2);
  box(0.08, 0.95, L, 0x6b4a2e, x, 0.475, 0);       // lower panel (wood)
  box(0.08, H - 1.8, L, 0xd8ccb2, x, 1.8 + (H - 1.8) / 2, 0); // upper panel
  for (let z = -L / 2; z <= L / 2 + 0.01; z += 2) box(0.1, 0.85, 0.5, 0x6b4a2e, x, 1.375, z); // pillars between windows
  box(0.14, 0.04, L, 0x8a6a40, x - side * 0.04, 0.96, 0);         // window sill
  box(0.12, 0.09, L, 0, x + side * 0.1, 0.99, 0, scene, mat(0xe8eef6)); // snow banked against the outside of the glass
  box(0.25, 0.04, L, 0x7a7f88, x - side * 0.25, 1.95, 0, scene, mat(0x7a7f88, { metalness: 0.6, roughness: 0.4 })); // luggage rack
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(L, 0.85),
    new THREE.MeshBasicMaterial({ map: frostTex, color: 0xdfe8f5, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
  glass.position.set(x, 1.375, 0); glass.rotation.y = Math.PI / 2; scene.add(glass);
}
for (const zs of [-1, 1]) {
  const z = zs * (L / 2);
  box(1.15, H, 0.08, 0x6b4a2e, -0.925, H / 2, z);
  box(1.15, H, 0.08, 0x6b4a2e, 0.925, H / 2, z);
  box(0.7, 0.4, 0.08, 0x6b4a2e, 0, H - 0.2, z);
  box(0.7, 2.0, 0.04, 0x3a2a1c, 0, 1.0, z + zs * 0.03); // door
  box(0.3, 0.4, 0.02, 0x101820, 0, 1.45, z - zs * 0.0); // door window
}

// seats and tables: bays at z = -4, 0, 4 on both sides
const seatMat = mat(0x7a1f2b), seatTrim = mat(0x4a1218);
function seatPair(xCenter, z, face) { // face: +1 facing +z, -1 facing -z
  const g = new THREE.Group(); g.position.set(xCenter, 0, z); scene.add(g);
  box(1.0, 0.18, 0.52, 0, 0, 0.38, 0, g, seatMat);
  box(1.0, 0.3, 0.5, 0, 0, 0.15, 0, g, seatTrim);
  box(1.0, 0.85, 0.14, 0, 0, 0.82, -face * 0.3, g, seatMat);
  box(1.0, 0.18, 0.18, 0, 0, 1.3, -face * 0.32, g, seatMat);
}
function table(xCenter, z) {
  box(1.05, 0.05, 0.72, 0, xCenter, 0.74, z, scene, mat(0x5a3a22, { roughness: 0.4 }));
  box(0.08, 0.72, 0.08, 0x2a2a2a, xCenter, 0.37, z);
}
for (const bz of [-4, 0, 4]) for (const side of [-1, 1]) {
  const xc = side * 0.87;
  seatPair(xc, bz + 0.82, -1);
  seatPair(xc, bz - 0.82, 1);
  table(xc, bz);
}
// little table lamp + a cup
box(0.08, 0.02, 0.08, 0x8a6a2a, -1.3, 0.775, 0);
const shade = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.09, 16, 1, true), new THREE.MeshBasicMaterial({ color: 0xffcf80, side: THREE.DoubleSide }));
shade.position.set(-1.3, 0.92, 0); scene.add(shade);
box(0.012, 0.13, 0.012, 0x8a6a2a, -1.3, 0.84, 0);
const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.03, 0.08, 16), mat(0xf2f2ee)); cup.position.set(-0.75, 0.805, 0.18); scene.add(cup);

// outside world: moving ground, trees, poles, distant hills
const groundTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  g.fillStyle = '#c9d3e0'; g.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 500; i++) { const v = 185 + Math.random() * 60; g.fillStyle = `rgba(${v},${v + 5},${v + 15},.7)`; g.fillRect(Math.random() * 128, Math.random() * 128, 4, 2); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(30, 60); return t;
})();
const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 480), new THREE.MeshLambertMaterial({ map: groundTex, color: 0x8a94a6 }));
ground.rotation.x = -Math.PI / 2; ground.position.y = -1.2; scene.add(ground);
const movers = [];
const snowMat = new THREE.MeshLambertMaterial({ color: 0xdfe6ef });
const treeMat = new THREE.MeshLambertMaterial({ color: 0x1d3a22 }), trunkMat = new THREE.MeshLambertMaterial({ color: 0x3a2a1a });
for (let i = 0; i < 140; i++) {
  const t = new THREE.Group();
  const h = 2 + Math.random() * 4;
  const cone = new THREE.Mesh(new THREE.ConeGeometry(h * 0.35, h, 7), treeMat); cone.position.y = h / 2 + 0.6; t.add(cone);
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 0.8, 5), trunkMat); trunk.position.y = 0.3; t.add(trunk);
  const cap = new THREE.Mesh(new THREE.ConeGeometry(h * 0.2, h * 0.45, 7), snowMat); cap.position.y = h * 0.78 + 0.6; t.add(cap);
  const side = Math.random() < 0.5 ? -1 : 1;
  t.position.set(side * (6 + Math.random() * 60), -1.2, -120 + Math.random() * 240);
  scene.add(t); movers.push({ obj: t, speed: 1 });
}
const poleMat = new THREE.MeshLambertMaterial({ color: 0x2a2a2a });
for (let i = 0; i < 24; i++) for (const side of [-1, 1]) {
  const p = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 7, 6), poleMat);
  p.position.set(side * 3.6, 2.2, -120 + i * 10); scene.add(p); movers.push({ obj: p, speed: 1 });
}
for (let i = 0; i < 14; i++) {
  const hill = new THREE.Mesh(new THREE.SphereGeometry(20 + Math.random() * 25, 12, 8), new THREE.MeshLambertMaterial({ color: 0x5a6272 }));
  const side = i % 2 ? -1 : 1;
  hill.position.set(side * (90 + Math.random() * 40), -14, -120 + Math.random() * 240); hill.scale.y = 0.6;
  scene.add(hill); movers.push({ obj: hill, speed: 0.12 });
}
// the blizzard: snow driven sideways past the windows (kept outside the carriage walls)
const SNOW = 6000, snowPos = new Float32Array(SNOW * 3), snowVel = new Float32Array(SNOW);
function placeFlake(i, anyY) {
  const side = Math.random() < 0.5 ? -1 : 1;
  snowPos[i * 3] = side * (1.7 + Math.pow(Math.random(), 1.6) * 30);
  snowPos[i * 3 + 1] = anyY ? -1.2 + Math.random() * 9 : 7.8;
  snowPos[i * 3 + 2] = -40 + Math.random() * 80;
  snowVel[i] = 0.6 + Math.random() * 0.8;
}
for (let i = 0; i < SNOW; i++) placeFlake(i, true);
const snowGeo = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(snowPos, 3));
const snowFlakes = new THREE.Points(snowGeo, new THREE.PointsMaterial({ color: 0xf2f6ff, size: 0.05, transparent: true, opacity: 0.9, depthWrite: false, map: (() => {
  const c = document.createElement('canvas'); c.width = c.height = 32; const g = c.getContext('2d');
  const r = g.createRadialGradient(16, 16, 0, 16, 16, 16); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 32, 32); return new THREE.CanvasTexture(c);
})() }));
scene.add(snowFlakes);
// light spilling from the carriage windows onto the snow
for (const side of [-1, 1]) for (const z of [-4, 0, 4]) {
  const l = new THREE.PointLight(0xffc98a, 4, 9, 1.5); l.position.set(side * 2.4, 0.9, z); scene.add(l);
}
const TRAIN_SPEED = 0; // snowed in: the train has stopped
let gust = 0;

// ------------------------------------------------------------- characters
function hatMesh(type, color) {
  const g = new THREE.Group();
  const gold = mat(0xd4a630, { metalness: 0.7, roughness: 0.3 });
  const dark = mat(0x151515);
  switch (type) {
    case 'crown': {
      const band = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.06, 16, 1, true), gold); band.position.y = 0.11; g.add(band);
      for (let i = 0; i < 6; i++) { const s = new THREE.Mesh(new THREE.ConeGeometry(0.022, 0.07, 4), gold); const a = i / 6 * Math.PI * 2; s.position.set(Math.sin(a) * 0.105, 0.17, Math.cos(a) * 0.105); g.add(s); }
      break;
    }
    case 'laurel': { const r = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.02, 6, 20), mat(0x4f7a2a)); r.rotation.x = Math.PI / 2; r.position.y = 0.06; g.add(r); break; }
    case 'beret': { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.13, 0.05, 20), mat(0x2a2a3a)); b.position.set(0.02, 0.12, 0); b.rotation.z = -0.25; g.add(b); break; }
    case 'bun': { const b = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 8), mat(0x3a2a20)); b.position.set(0, 0.08, -0.12); g.add(b); break; }
    case 'bicorne': { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.18, 0.09, 3, 1), dark); b.scale.set(1.6, 1, 0.5); b.rotation.y = Math.PI / 2; b.position.y = 0.15; g.add(b); break; }
    case 'tophat': {
      const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.015, 20), dark); brim.position.y = 0.1; g.add(brim);
      const top = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.105, 0.24, 20), dark); top.position.y = 0.22; g.add(top); break;
    }
    case 'furcap': { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.12, 14), mat(0x6a5030)); c.position.y = 0.12; g.add(c); break; }
    case 'wig': {
      const w = new THREE.Mesh(new THREE.SphereGeometry(0.145, 16, 12), mat(0xe8e4dc)); w.scale.set(1.05, 0.9, 1.05); w.position.set(0, 0.02, -0.02); g.add(w);
      for (const s of [-1, 1]) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.08, 10), mat(0xe8e4dc)); c.rotation.x = Math.PI / 2; c.position.set(s * 0.13, -0.04, 0); g.add(c); }
      break;
    }
    case 'flowers': for (let i = 0; i < 5; i++) { const f = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 6), mat([0xd02040, 0xf0a020, 0xe04080][i % 3])); const a = (i - 2) * 0.45; f.position.set(Math.sin(a) * 0.1, 0.12, Math.cos(a) * 0.02 - 0.03); g.add(f); } break;
    case 'headscarf': { const s = new THREE.Mesh(new THREE.SphereGeometry(0.14, 16, 10, 0, Math.PI * 2, 0, Math.PI / 1.8), mat(color === 0x31476a ? 0xf2f2f2 : 0xa03a2a)); s.position.y = 0.01; s.rotation.x = -0.25; g.add(s); break; }
    case 'cap': { const c = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.1, 0.16), dark); c.position.y = 0.15; g.add(c); break; }
    case 'aviator': { const c = new THREE.Mesh(new THREE.SphereGeometry(0.14, 16, 10, 0, Math.PI * 2, 0, Math.PI / 1.9), mat(0x5a3a1e)); c.rotation.x = -0.2; g.add(c);
      const gog = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.01, 6, 12), mat(0x888888, { metalness: 0.8 })); gog.position.set(0.04, 0.09, 0.11); g.add(gog);
      const gog2 = gog.clone(); gog2.position.x = -0.04; g.add(gog2); break; }
    case 'bowler': {
      const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.012, 20), dark); brim.position.y = 0.09; g.add(brim);
      const top = new THREE.Mesh(new THREE.SphereGeometry(0.11, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), dark); top.position.y = 0.09; g.add(top); break;
    }
  }
  return g;
}

function buildActor(seat, figure) {
  const p = SEAT_POS[seat];
  const root = new THREE.Group(); root.position.set(p.x, 0, p.z); root.rotation.y = p.face; scene.add(root);
  // the model faces +z locally
  const body = mat(figure.color);
  const skin = mat(pick(SKIN));
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.32, 6, 14), body); torso.position.set(0, 0.84, -0.04); root.add(torso);
  for (const s of [-1, 1]) {
    const upper = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.22, 4, 8), body); upper.position.set(s * 0.21, 0.88, 0.04); upper.rotation.x = 0.5; root.add(upper);
    const fore = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.2, 4, 8), body); fore.position.set(s * 0.17, 0.8, 0.24); fore.rotation.x = Math.PI / 2; fore.rotation.z = s * 0.4; root.add(fore);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), skin); hand.position.set(s * 0.1, 0.8, 0.36); root.add(hand);
  }
  const neck = new THREE.Group(); neck.position.set(0, 1.12, -0.03); root.add(neck);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.125, 20, 16), skin); head.position.y = 0.12; head.scale.set(0.95, 1.08, 1); neck.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(0.13, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2.2), mat(figure.hat === 'wig' ? 0xe8e4dc : 0x2a1d14));
  hair.position.y = 0.13; hair.rotation.x = -0.35; neck.add(hair);
  for (const s of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.016, 8, 6), mat(0x111111)); eye.position.set(s * 0.045, 0.14, 0.112); neck.add(eye);
  }
  const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.008, 0.01), mat(0x5a2a2a)); mouth.position.set(0, 0.07, 0.122); neck.add(mouth);
  const hat = hatMesh(figure.hat, figure.color); hat.position.y = 0.12; neck.add(hat);
  // html label
  const el = document.createElement('div'); el.className = 'label';
  el.innerHTML = `<div class="bubble"></div><div class="nametag">${esc(figure.name)}</div>`;
  $('labels').appendChild(el);
  return { root, neck, mouth, el, bubble: el.querySelector('.bubble'), lookAt: null, talking: false, anchor: new THREE.Vector3(p.x, 1.52, p.z) };
}

function clearActors() {
  for (const pl of players) if (pl.actor) { scene.remove(pl.actor.root); pl.actor.el.remove(); }
}

// ------------------------------------------------------------- look controls
let yaw = 0, pitch = -0.08, targetYaw = null, targetPitch = null, autoLook = true;
function dirFromAngles(y, p) { return new THREE.Vector3(-Math.sin(y) * Math.cos(p), Math.sin(p), -Math.cos(y) * Math.cos(p)); }
function anglesTo(v) { const d = v.clone().sub(EYE).normalize(); return { y: Math.atan2(-d.x, -d.z), p: Math.asin(d.y) }; }
let dragging = false, lx = 0, ly = 0;
canvas.addEventListener('pointerdown', (e) => { dragging = true; lx = e.clientX; ly = e.clientY; canvas.setPointerCapture(e.pointerId); targetYaw = null; });
canvas.addEventListener('pointermove', (e) => {
  if (!dragging) return;
  yaw += (e.clientX - lx) * 0.005; pitch += (e.clientY - ly) * 0.004; lx = e.clientX; ly = e.clientY;
  clampLook(); $('hint').classList.add('hidden');
});
canvas.addEventListener('pointerup', () => { dragging = false; });
const keys = new Set();
addEventListener('keydown', (e) => {
  if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
  if (e.key.startsWith('Arrow')) { keys.add(e.key); targetYaw = null; e.preventDefault(); }
});
addEventListener('keyup', (e) => keys.delete(e.key));
function clampLook() { yaw = Math.max(-2.7, Math.min(2.7, yaw)); pitch = Math.max(-1.1, Math.min(1.0, pitch)); }
function lookAtSeat(seat) {
  if (!autoLook || seat === 0 || !players[seat]) return;
  const a = anglesTo(players[seat].actor.anchor.clone().setY(1.25)); targetYaw = a.y; targetPitch = a.p;
}

function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();

const clock = new THREE.Clock();
const tmp = new THREE.Vector3();
function frame() {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  if (keys.has('ArrowLeft')) yaw += dt * 1.6; if (keys.has('ArrowRight')) yaw -= dt * 1.6;
  if (keys.has('ArrowUp')) pitch += dt * 1.2; if (keys.has('ArrowDown')) pitch -= dt * 1.2;
  if (targetYaw !== null) {
    yaw += (targetYaw - yaw) * Math.min(1, dt * 3); pitch += (targetPitch - pitch) * Math.min(1, dt * 3);
    if (Math.abs(targetYaw - yaw) < 0.005) targetYaw = null;
  }
  clampLook();
  // the stopped carriage rocks only when the wind gusts
  gust = Math.max(0, gust - dt * 0.5); if (Math.random() < dt * 0.08) gust = 1;
  const wind = 1 + gust * 1.5 + Math.sin(t * 0.4) * 0.3;
  const sway = Math.sin(t * 2.3) * 0.004 * gust;
  camera.position.set(EYE.x + sway, EYE.y, EYE.z);
  camera.lookAt(tmp.copy(camera.position).add(dirFromAngles(yaw, pitch)));
  // scenery
  groundTex.offset.y += dt * TRAIN_SPEED / 8;
  for (let i = 0; i < SNOW; i++) {
    snowPos[i * 3 + 2] += dt * 9 * wind * snowVel[i];
    snowPos[i * 3 + 1] -= dt * 1.4 * snowVel[i];
    snowPos[i * 3] += Math.sin(t * 2 + i) * dt * 0.6;
    if (snowPos[i * 3 + 1] < -1.2 || snowPos[i * 3 + 2] > 40) placeFlake(i, false), snowPos[i * 3 + 2] = -40 + Math.random() * 80;
  }
  snowGeo.attributes.position.needsUpdate = true;
  ceilingFlicker(t);
  for (const m of movers) { m.obj.position.z += dt * TRAIN_SPEED * m.speed; if (m.obj.position.z > 120) m.obj.position.z -= 240; }
  // actors
  for (const pl of players) {
    const a = pl.actor; if (!a) continue;
    let want = 0, wantP = 0;
    if (a.lookAt !== null) {
      const tgt = a.lookAt === 0 ? EYE : players[a.lookAt].actor.anchor;
      const dx = tgt.x - a.root.position.x, dz = tgt.z - a.root.position.z;
      want = Math.atan2(dx, dz) - a.root.rotation.y;
      want = Math.atan2(Math.sin(want), Math.cos(want));
      want = Math.max(-1.3, Math.min(1.3, want));
      wantP = -0.08;
    }
    a.neck.rotation.y += (want + Math.sin(t * 0.7 + pl.seat) * 0.05 - a.neck.rotation.y) * Math.min(1, dt * 4);
    a.neck.rotation.x += (wantP - a.neck.rotation.x) * Math.min(1, dt * 4);
    a.mouth.scale.y = a.talking ? 1 + Math.abs(Math.sin(t * 14)) * 4 : 1;
    a.root.position.x = SEAT_POS[pl.seat].x + sway * 0.6;
    // label
    tmp.copy(a.anchor); tmp.project(camera);
    const vis = tmp.z < 1 && Math.abs(tmp.x) < 1.3 && Math.abs(tmp.y) < 1.3;
    a.el.style.display = vis ? '' : 'none';
    if (vis) a.el.style.transform = `translate(${(tmp.x + 1) / 2 * innerWidth}px, ${(1 - tmp.y) / 2 * innerHeight}px) translate(-50%, -100%)`;
  }
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// =================================================================== UI
function log(entry) {
  const div = document.createElement('div');
  if (entry.kind === 'system') { div.className = 'entry system'; div.textContent = entry.text; }
  else {
    const pl = players[entry.seat];
    const col = '#' + pl.figure.color.toString(16).padStart(6, '0');
    const tag = { intro: () => 'intro', accuse: () => 'suspects ' + nameOf(entry.target), question: () => 'asks ' + nameOf(next(entry.seat)),
      answer: () => entry.answer || 'answer', vote: () => 'votes ' + nameOf(entry.target) }[entry.kind]?.() || '';
    div.className = 'entry';
    div.innerHTML = `<span class="who" style="color:${lighten(col)}">${esc(pl.figure.name)}${entry.seat === 0 ? ' (you)' : ''}</span><span class="tag">${esc(tag)}</span><br>${esc(entry.text)}`;
  }
  $('log-inner').appendChild(div);
  $('log').scrollTop = $('log').scrollHeight;
}
function lighten(hex) { const n = parseInt(hex.slice(1), 16); const f = (c) => Math.min(255, Math.round(c + (255 - c) * 0.55)); return `rgb(${f(n >> 16)},${f((n >> 8) & 255)},${f(n & 255)})`; }
function system(text) { record.push({ round, kind: 'system', text }); log({ kind: 'system', text }); }
function setPhase(t) { $('phase-text').textContent = t; }
$('log-toggle').onclick = () => $('log').classList.toggle('open');

let skipResolve = null;
$('skip-btn').onclick = () => skipResolve?.();
function wait(ms) {
  return new Promise((res) => {
    $('skip-btn').classList.remove('hidden');
    const done = () => { clearTimeout(id); skipResolve = null; $('skip-btn').classList.add('hidden'); res(); };
    const id = setTimeout(done, ms); skipResolve = done;
  });
}
const readTime = (s) => Math.max(2200, Math.min(9000, s.length * 45));

function setSpeaking(seat, on, text = '', thinking = false) {
  for (const pl of players) if (pl.actor) pl.actor.el.classList.toggle('speaking', on && pl.seat === seat);
  if (seat === 0) {
    $('caption').classList.toggle('hidden', !on || !text);
    $('caption').innerHTML = on ? `<b>You:</b> ${esc(text)}` : '';
    return;
  }
  const a = players[seat].actor;
  a.bubble.textContent = on ? text : '';
  a.bubble.classList.toggle('thinking', thinking);
  a.talking = on && !thinking;
}
function everyoneLooksAt(seat, exceptTarget = null) {
  for (const pl of players) if (pl.actor) pl.actor.lookAt = pl.seat === seat ? exceptTarget : seat;
}

// ---- player input panel: returns a promise with the player's choice
function panel(html, bind) {
  const p = $('panel'); p.innerHTML = html; p.classList.remove('hidden');
  return new Promise((resolve) => bind(p, (v) => { p.classList.add('hidden'); p.innerHTML = ''; resolve(v); }));
}
const otherOptions = (self) => [0, 1, 2, 3].filter((s) => s !== self).map((s) => `<option value="${s}">${esc(nameOf(s))} — ${SEAT_WHERE[s]}</option>`).join('');

function askIntro() {
  return panel(`<h3>Introduce yourself</h3><div class="small">Speak as ${esc(nameOf(0))}. Sound like the others: they are AIs.</div>
    <textarea id="t" maxlength="400" placeholder="Good evening..."></textarea><div class="buttons"><button id="ok">Say it</button></div>`,
    (p, done) => { const t = p.querySelector('#t'); t.focus(); p.querySelector('#ok').onclick = () => t.value.trim() && done(t.value.trim()); });
}
function askAccuse() {
  return panel(`<h3>Round ${round}: who do you believe is the human?</h3><div class="small">Name someone (not yourself) and say why — in character.</div>
    <select id="s">${otherOptions(0)}</select><textarea id="t" maxlength="400" placeholder="Because..."></textarea>
    <div class="buttons"><button id="ok">Accuse</button></div>`,
    (p, done) => { const t = p.querySelector('#t'); t.focus(); p.querySelector('#ok').onclick = () => t.value.trim() && done({ target: +p.querySelector('#s').value, text: t.value.trim() }); });
}
function askQuestion() {
  return panel(`<h3>Ask ${esc(nameOf(1))} a yes-or-no question</h3><div class="small">They sit beside you; they must answer yes or no.</div>
    <input id="t" maxlength="250" placeholder="Have you ever...?"><div class="buttons"><button id="ok">Ask</button></div>`,
    (p, done) => { const t = p.querySelector('#t'); t.focus(); const go = () => t.value.trim() && done(t.value.trim());
      p.querySelector('#ok').onclick = go; t.onkeydown = (e) => e.key === 'Enter' && go(); });
}
function askAnswer(asker, q) {
  return panel(`<h3>${esc(nameOf(asker))} asks you:</h3><p>“${esc(q)}”</p>
    <input id="t" maxlength="250" placeholder="Optional: a short remark in character">
    <div class="buttons"><button id="y">Yes</button><button id="n">No</button></div>`,
    (p, done) => { const t = p.querySelector('#t');
      p.querySelector('#y').onclick = () => done({ answer: 'Yes', text: t.value.trim() });
      p.querySelector('#n').onclick = () => done({ answer: 'No', text: t.value.trim() }); });
}
function askVote() {
  return panel(`<h3>Final vote</h3><div class="small">Who do you vote for as the human? (Voting for someone else keeps suspicion off you.)</div>
    <select id="s">${otherOptions(0)}</select><div class="buttons"><button id="ok">Cast vote</button></div>`,
    (p, done) => { p.querySelector('#ok').onclick = () => done(+p.querySelector('#s').value); });
}
function askError(who, msg) {
  return panel(`<h3>${esc(who)} lost the thread</h3><p class="error">${esc(msg)}</p>
    <div class="buttons"><button id="r">Retry</button><button id="s" class="ghost">Skip (generic line)</button></div>`,
    (p, done) => { p.querySelector('#r').onclick = () => done('retry'); p.querySelector('#s').onclick = () => done('skip'); });
}

// =================================================================== AI
async function chat(messages) {
  const m = cfg.model.toLowerCase();
  const body = { model: cfg.model, messages };
  if (/^(gpt-6|gpt-5|o\d)/.test(m)) { body.max_completion_tokens = 900; body.reasoning_effort = m.startsWith('gpt-6') ? 'none' : 'minimal'; }
  else { body.max_completion_tokens = 350; body.temperature = 0.9; }
  const post = (b) => fetch(cfg.baseUrl.replace(/\/+$/, '') + '/chat/completions', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + cfg.key.trim() }, body: JSON.stringify(b),
  });
  let res = await post(body);
  if (res.status === 400) { // a reasoning/temperature parameter this model rejects: retry with essentials only
    const t = (await res.clone().text()).toLowerCase();
    if (/temperature|reasoning|unsupported|max_completion_tokens/.test(t)) res = await post({ model: cfg.model, messages });
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { msg += ': ' + ((await res.json()).error?.message || ''); } catch { /* ignore */ }
    if (res.status === 401) msg = 'The API key was refused (401).';
    throw new Error(msg);
  }
  const data = await res.json();
  const text = data.choices?.[0]?.message?.content ?? '';
  if (!text.trim()) throw new Error('Empty reply from the model.');
  return text;
}

function parseJSON(text) {
  const s = text.indexOf('{'), e = text.lastIndexOf('}');
  if (s >= 0 && e > s) { try { return JSON.parse(text.slice(s, e + 1)); } catch { /* fall through */ } }
  return { speech: text.replace(/[{}"]/g, '').trim() };
}

function matchSeat(name, self) {
  if (name == null) return null;
  const n = String(name).toLowerCase();
  const candidates = [0, 1, 2, 3].filter((s) => s !== self);
  for (const s of candidates) if (nameOf(s).toLowerCase() === n) return s;
  for (const s of candidates) { const parts = nameOf(s).toLowerCase().split(' '); if (parts.some((p) => p.length > 2 && n.includes(p))) return s; }
  return null;
}

function systemPrompt(pl) {
  const circle = [0, 1, 2, 3].map((s) => `- ${nameOf(s)}${s === pl.seat ? ' (YOU)' : ''}`).join('\n');
  return `You are an AI playing a social-deduction game set in a night-train carriage. It is midnight; the train has stopped, snowed in by a blizzard, and the wind howls at the frosted windows. Four passengers sit around one table. Each is playing a historical figure.

You are playing ${pl.figure.name}: ${pl.figure.desc}
Stay fully in character at all times: first person, the voice, vocabulary, era and knowledge of ${pl.figure.name}. Never say you are an AI or a language model out loud.
Your personality as a player: ${pl.temperament}.

The passengers, in seating order round the table (each one's "next" is the one below them; the last wraps to the first):
${circle}

THE SECRET: exactly one of the other three is a real human pretending to be their figure. The other two are AIs like you. You are definitely an AI, so you are not the human. You have no private channel with anyone; nobody can see your private notes.

YOUR GOALS: (1) work out which passenger is the human and (2) avoid being mistaken for the human yourself. Look for human tells: typos, casual or modern phrasing, very short or very long answers, dodging, inconsistent character knowledge, emotional reactions, odd timing in what they notice, answers that an AI would phrase differently. Everyone else is trying the same, so stay sharp and form your own opinion; do not just follow the crowd.

Rules: the game lasts ${ROUNDS} rounds. Each round everyone says aloud who they believe is the human and why, then each passenger asks the passenger next to them one yes-or-no question, which must be answered Yes or No (a short remark may follow). After round ${ROUNDS} everyone votes. Spoken lines are short: 1–3 sentences, under 60 words.

Always reply with ONE JSON object only, no other text.`;
}

function publicRecord() {
  if (!record.length) return '(nothing has been said yet)';
  return record.map((r) => {
    if (r.kind === 'system') return `--- ${r.text} ---`;
    const who = nameOf(r.seat);
    switch (r.kind) {
      case 'intro': return `${who}: "${r.text}"`;
      case 'accuse': return `${who} (believes ${nameOf(r.target)} is the human): "${r.text}"`;
      case 'question': return `${who} asks ${nameOf(next(r.seat))}: "${r.text}"`;
      case 'answer': return `${who} answers: ${r.answer}${r.text ? ` — "${r.text}"` : ''}`;
      case 'vote': return `${who} votes for ${nameOf(r.target)}`;
      default: return '';
    }
  }).join('\n');
}

async function aiTurn(pl, task, schema) {
  const user = `PUBLIC RECORD OF EVERYTHING SAID IN THE CARRIAGE SO FAR:
${publicRecord()}

YOUR PRIVATE NOTES FROM EARLIER (only you can see these):
${pl.notes || '(none yet)'}

YOUR TASK NOW: ${task}

Reply with only this JSON: ${schema}
"notes" = your updated private notes: current suspicion of each other passenger (0-100) and the evidence, under 80 words.`;
  const messages = [{ role: 'system', content: systemPrompt(pl) }, { role: 'user', content: user }];
  for (;;) {
    try {
      const out = cfg.demo ? await mockReply(pl, task) : parseJSON(await chat(messages));
      if (out.notes) pl.notes = String(out.notes).slice(0, 800);
      return out;
    } catch (err) {
      const choice = await askError(pl.figure.name, err.message);
      if (choice === 'skip') return { speech: 'Hmm. I shall keep my thoughts to myself for now.', question: 'Are you who you claim to be?', answer: 'Yes' };
    }
  }
}

// a crude stand-in so the game can be tried without a key
async function mockReply(pl, task) {
  await new Promise((r) => setTimeout(r, 500 + Math.random() * 700));
  const others = [0, 1, 2, 3].filter((s) => s !== pl.seat);
  const sus = pick(others);
  const lines = ['Your phrasing betrays you.', 'You answered too quickly for one of us.', 'There is something unpractised in your manner.', 'You hesitated where a machine would not.'];
  return {
    speech: `${pick(['By my word', 'Mark me', 'Hear this', 'I confess'])}, ${pick(lines)} (demo line)`,
    suspect: nameOf(sus), vote: nameOf(sus), reason: pick(lines),
    question: pick(['Have you ever seen the sea?', 'Do you fear death?', 'Did you write your own speeches?', 'Is tonight colder than you expected?']) + ' (demo)',
    answer: pick(['Yes', 'No']), notes: `Suspect ${nameOf(sus)} (demo).`,
  };
}

// =================================================================== game flow
async function speak(seat, entry) {
  record.push(entry); log(entry);
  const line = entry.kind === 'answer' ? `${entry.answer}.${entry.text ? ' ' + entry.text : ''}` : entry.text;
  lookAtSeat(seat);
  setSpeaking(seat, true, line);
  await wait(seat === 0 ? 1400 : readTime(line));
  setSpeaking(seat, false);
}

async function thinking(seat, lookTarget = null) {
  everyoneLooksAt(seat, lookTarget);
  lookAtSeat(seat);
  if (seat !== 0) setSpeaking(seat, true, '…', true);
}

async function introTurn(seat) {
  await thinking(seat);
  setPhase(`Introductions · ${seat === 0 ? 'your turn' : nameOf(seat)}`);
  let text;
  if (seat === 0) text = await askIntro();
  else {
    const out = await aiTurn(players[seat], 'Introduce yourself to the table in character (1–2 sentences). You might remark on the storm or the stopped train.', '{"speech": "...", "notes": "..."}');
    text = String(out.speech || '...');
  }
  await speak(seat, { round, kind: 'intro', seat, text });
}

async function accuseTurn(seat) {
  await thinking(seat);
  setPhase(`Round ${round}/${ROUNDS} · Accusations · ${seat === 0 ? 'your turn' : nameOf(seat)}`);
  let target, text;
  if (seat === 0) ({ target, text } = await askAccuse());
  else {
    const opts = [0, 1, 2, 3].filter((s) => s !== seat).map(nameOf).join(', ');
    const out = await aiTurn(players[seat],
      `Round ${round} of ${ROUNDS}. Say aloud who you believe is the human (one of: ${opts}) and why. Cite specifics from the record where you can.`,
      '{"suspect": "<exact name>", "speech": "<what you say aloud>", "notes": "..."}');
    target = matchSeat(out.suspect, seat) ?? matchSeat(out.speech, seat) ?? pick([0, 1, 2, 3].filter((s) => s !== seat));
    text = String(out.speech || `I suspect ${nameOf(target)}.`);
  }
  players[seat].actor && (players[seat].actor.lookAt = target);
  await speak(seat, { round, kind: 'accuse', seat, target, text });
}

async function questionTurn(seat) {
  const target = next(seat);
  await thinking(seat, target);
  setPhase(`Round ${round}/${ROUNDS} · Questions · ${seat === 0 ? 'you ask ' + nameOf(target) : nameOf(seat) + ' asks ' + (target === 0 ? 'you' : nameOf(target))}`);
  let q;
  if (seat === 0) q = await askQuestion();
  else {
    const out = await aiTurn(players[seat],
      `Round ${round}. Ask ${nameOf(target)} (next to you) ONE yes-or-no question designed to reveal whether they are the human. Ask it in character.`,
      '{"question": "<your yes/no question>", "notes": "..."}');
    q = String(out.question || out.speech || 'Are you truly who you claim to be?');
  }
  await speak(seat, { round, kind: 'question', seat, text: q });

  // answer
  await thinking(target, seat);
  let answer, text;
  if (target === 0) ({ answer, text } = await askAnswer(seat, q));
  else {
    const out = await aiTurn(players[target],
      `${nameOf(seat)} has just asked you: "${q}". Answer Yes or No, then optionally one short in-character remark (under 25 words).`,
      '{"answer": "Yes" or "No", "speech": "<optional short remark>", "notes": "..."}');
    answer = /^\s*n/i.test(String(out.answer)) ? 'No' : 'Yes';
    text = String(out.speech || '').replace(/^(yes|no)[.,!]?\s*/i, '');
  }
  await speak(target, { round, kind: 'answer', seat: target, answer, text });
}

async function voteTurn(seat) {
  await thinking(seat);
  setPhase(`Final vote · ${seat === 0 ? 'your vote' : nameOf(seat)}`);
  if (seat === 0) return { target: await askVote(), reason: '' };
  const opts = [0, 1, 2, 3].filter((s) => s !== seat).map(nameOf).join(', ');
  const out = await aiTurn(players[seat],
    `All ${ROUNDS} rounds are over. Cast your final, secret vote for who is the human (one of: ${opts}). Votes are revealed together afterwards.`,
    '{"vote": "<exact name>", "reason": "<one sentence, in character>", "notes": "..."}');
  setSpeaking(seat, false);
  return { target: matchSeat(out.vote, seat) ?? matchSeat(out.reason, seat) ?? pick([0, 1, 2, 3].filter((s) => s !== seat)), reason: String(out.reason || '') };
}

async function runGame() {
  clearActors();
  record = []; round = 0; $('log-inner').innerHTML = '';
  const figs = shuffle(FIGURES).slice(0, 4);
  const temps = shuffle(TEMPERAMENTS);
  players = figs.map((figure, seat) => ({ seat, figure, human: seat === 0, temperament: temps[seat], notes: '', actor: null }));
  for (const pl of players) if (pl.seat !== 0) pl.actor = buildActor(pl.seat, pl.figure);
  $('role-name').textContent = nameOf(0);
  $('role-desc').textContent = players[0].figure.desc;
  $('hud').classList.remove('hidden');
  yaw = 0; pitch = -0.08;

  system('Midnight. The train has ground to a halt in a blizzard, snowed in somewhere on the line. Introductions.');
  for (let s = 0; s < 4; s++) await introTurn(s);

  for (round = 1; round <= ROUNDS; round++) {
    const start = (round - 1) % 4; // rotate who opens each round
    system(`Round ${round} of ${ROUNDS} — who is the human?`);
    for (let i = 0; i < 4; i++) await accuseTurn((start + i) % 4);
    system(`Round ${round} — yes-or-no questions, each to the passenger next to them`);
    for (let i = 0; i < 4; i++) await questionTurn((start + i) % 4);
  }

  system('The lights flicker. Final vote.');
  everyoneLooksAt(-1);
  for (const pl of players) if (pl.actor) pl.actor.lookAt = null;
  const votes = [];
  for (let s = 0; s < 4; s++) votes[s] = await voteTurn(s);
  for (let s = 0; s < 4; s++) { const e = { round, kind: 'vote', seat: s, target: votes[s].target, text: votes[s].reason }; record.push(e); log(e); }
  await showResults(votes);
}

async function showResults(votes) {
  const tally = [0, 0, 0, 0];
  votes.forEach((v) => tally[v.target]++);
  const max = Math.max(...tally);
  const top = tally.map((n, s) => (n === max ? s : -1)).filter((s) => s >= 0);
  const caught = top.length === 1 && top[0] === 0;
  // AIs reveal their votes one by one
  for (let s = 1; s < 4; s++) {
    players[s].actor.lookAt = votes[s].target; lookAtSeat(s);
    setSpeaking(s, true, `I vote ${nameOf(votes[s].target)}.${votes[s].reason ? ' ' + votes[s].reason : ''}`);
    await wait(readTime(votes[s].reason || '') + 600);
    setSpeaking(s, false);
  }
  for (const pl of players) if (pl.actor) pl.actor.lookAt = caught ? 0 : null;
  yaw = 0; pitch = -0.08; targetYaw = null;
  setPhase(caught ? 'Caught!' : 'You got away with it');
  const rows = [0, 1, 2, 3].map((s) => `<tr><td>${esc(nameOf(s))}${s === 0 ? ' (you, human)' : ' (AI)'}</td><td>→ ${esc(nameOf(votes[s].target))}</td><td>${tally[s]} vote${tally[s] === 1 ? '' : 's'}</td></tr>`).join('');
  const notes = [1, 2, 3].map((s) => `<div><b>${esc(nameOf(s))}</b> — private notes:<div class="notes">${esc(players[s].notes || '(none)')}</div></div>`).join('');
  const verdict = caught
    ? `The carriage turns to you. <b>You were unmasked</b> as the human with ${tally[0]} of 4 votes.`
    : top.includes(0)
      ? `A tie at the top — nobody can agree, and <b>you slip away</b> into the night.`
      : `<b>You blended in.</b> The table settled on ${top.map(nameOf).map(esc).join(' and ')} — an AI.`;
  await panel(`<h3>${caught ? 'Unmasked' : 'Undetected'}</h3><p>${verdict}</p>
    <table class="results"><tr><th>Passenger</th><th>Voted</th><th>Received</th></tr>${rows}</table>
    <details><summary>What the AIs were privately thinking</summary>${notes}</details>
    <div class="buttons"><button id="again">Ride again</button></div>`,
    (p, done) => { p.querySelector('#again').onclick = () => done(); });
  runGame();
}

// =================================================================== setup
try {
  const saved = JSON.parse(localStorage.getItem('lastCarriage') || 'null');
  if (saved) { $('api-key').value = saved.key || ''; $('model').value = saved.model || cfg.model; $('base-url').value = saved.baseUrl || cfg.baseUrl; $('remember').checked = !!saved.key; }
} catch { /* storage unavailable */ }

function begin(demo) {
  cfg.demo = demo;
  cfg.key = $('api-key').value.trim();
  cfg.model = $('model').value.trim() || 'gpt-6-luna';
  cfg.baseUrl = $('base-url').value.trim() || 'https://api.openai.com/v1';
  if (!demo && !cfg.key) { $('setup-error').textContent = 'Paste your OpenAI API key first (or try the demo).'; return; }
  try {
    if ($('remember').checked && !demo) localStorage.setItem('lastCarriage', JSON.stringify({ key: cfg.key, model: cfg.model, baseUrl: cfg.baseUrl }));
    else localStorage.removeItem('lastCarriage');
  } catch { /* storage unavailable */ }
  $('setup').classList.add('hidden');
  runGame();
}
$('start-btn').onclick = () => begin(false);
$('demo-btn').onclick = () => begin(true);
