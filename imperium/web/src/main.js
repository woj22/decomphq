import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { buildCity, loadMap, TERRACE, CAPITOL, HILL_H } from './city.js';
import { buildSky } from './sky.js';
import { buildPalace, balZ } from './palace.js';
import { Figure } from './figure.js';
import { CAST } from './cast.js';
import { STATS, PETITIONS, verdict } from './story.js';
import { MAT } from './lowpoly.js';

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const QUALITY = params.get('q') ? parseFloat(params.get('q')) : (matchMedia('(pointer: coarse)').matches ? 0.6 : 1);
const SHOT = params.has('shot');           // fixed camera for automated screenshots

// ------------------------------------------------------------------------------------------------ renderer
const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, QUALITY < 1 ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
$('game').appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xe2aa98, 0.00042);
const camera = new THREE.PerspectiveCamera(46, innerWidth / innerHeight, 0.1, 22000);

const rt = new THREE.WebGLRenderTarget(innerWidth, innerHeight, { type: THREE.HalfFloatType, samples: QUALITY < 1 ? 0 : 4 });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth / 2, innerHeight / 2), 0.42, 0.55, 0.92);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const grade = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uVig: { value: 0.32 }, uWarm: { value: 1.0 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uVig; uniform float uWarm; varying vec2 vUv;
    void main(){ vec4 c = texture2D(tDiffuse, vUv);
      float l = dot(c.rgb, vec3(0.299,0.587,0.114));
      vec3 shadowTint = mix(vec3(0.93,0.95,1.07), vec3(0.92,0.92,1.1), 1.0-uWarm), hiTint = mix(vec3(1.04,1.0,0.94), vec3(0.97,0.98,1.03), 1.0-uWarm);
      c.rgb *= mix(shadowTint, hiTint, smoothstep(0.15, 0.85, l));
      c.rgb = mix(vec3(l), c.rgb, 1.08);
      vec2 d = vUv - 0.5; c.rgb *= 1.0 - uVig * dot(d, d) * 1.6;
      gl_FragColor = c; }`,
});
composer.addPass(grade);

// ------------------------------------------------------------------------------------------------ world
const yawT = Math.atan2(-(CAPITOL[0] - TERRACE[0]), -(CAPITOL[1] - TERRACE[1]));   // terrace faces the capitol
const viewDir = new THREE.Vector3(-Math.sin(yawT), 0, -Math.cos(yawT));
const rightDir = new THREE.Vector3(-viewDir.z, 0, viewDir.x);
const sunAz = (a) => viewDir.clone().multiplyScalar(Math.cos(a)).addScaledVector(rightDir, Math.sin(a));

const sun = new THREE.DirectionalLight(0xffb070, 3.2);
sun.castShadow = true;
sun.shadow.mapSize.set(QUALITY < 1 ? 1024 : 2048, QUALITY < 1 ? 1024 : 2048);
Object.assign(sun.shadow.camera, { left: -24, right: 24, top: 24, bottom: -24, near: 1, far: 200 });
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.04;
scene.add(sun, sun.target);
const hemi = new THREE.HemisphereLight(0xb8a0d8, 0xc89870, 0.9);
scene.add(hemi);
const sky = buildSky(scene);
sky.clouds.rotation.y = yawT;

function cast(id, over = {}) {
  const spec = { ...CAST[id], ...over };
  if (over.stone) for (const k of ['skin', 'hair', 'primary', 'secondary', 'trim', 'cloak']) if (spec[k] !== undefined) spec[k] = 0xe6d2ae;
  const f = new Figure(spec);
  f.id = id;
  if (over.stone) f.root.traverse((o) => { if (o.isMesh) o.material = new THREE.MeshStandardMaterial({ vertexColors: true, flatShading: true, roughness: 0.75, color: 0xffffff, side: o.material.side }); });
  return f;
}

let palace, city, player, npcs = [], walkers = [];
const stats = Object.fromEntries(STATS.map((s) => [s.id, s.start]));
let step = 0, night = 0, nightTarget = 0, state = 'title', talking = null;

async function init() {
  $('loading').textContent = 'Surveying the capital…';
  await loadMap('data/citymap.json');
  await new Promise((r) => setTimeout(r, 30));
  city = buildCity(scene, { quality: QUALITY });
  $('loading').textContent = 'Lighting the braziers…';
  await new Promise((r) => setTimeout(r, 30));
  palace = buildPalace(scene, { cast });
  palace.group.position.set(TERRACE[0], HILL_H, TERRACE[1]);
  palace.group.rotation.y = yawT;
  palace.group.updateMatrixWorld(true);
  palace.group.traverse((o) => { if (o.isMesh) o.receiveShadow = true; });

  // you: the King of Seravel, in a pleated burgundy royal cloak
  player = cast('player', { cloak: 0x7a1c2a, trim: 0xc8962e, royal: true, headwear: 'crown_gold' });
  player.root.position.set(-1.09, 0.02, -6.0);
  player.root.rotation.y = Math.PI;
  palace.group.add(player.root);

  // petitioners and the court
  const spots = { aldric: [1.3, -3.2, -2.6], treasurer: [-12.5, 1.5, 0.8], thane: [6.2, 5.8, -2.2], thrask: [-13.5, -6.0, 1.9], chancellor: [-1.2, 10.4, 3.1] };
  for (const p of PETITIONS) {
    const [x, z, yaw] = spots[p.who];
    const f = cast(p.who); f.root.position.set(x, 0.02, z); f.root.rotation.y = yaw; f.home = { x, z, yaw }; f.petition = p;
    palace.group.add(f.root); npcs.push(f);
  }
  for (const [id, x, z, yaw] of [['vashka', -12.2, -7.4, 0.6], ['cassia', -3.6, 12.3, Math.PI], ['hessa', 1.4, 12.3, Math.PI], ['ilsaveth', 8.0, 0.5, -1.4], ['marcellan', 6.6, 0.9, 1.6], ['ulda', -9, 6.5, 0.4]]) {
    const f = cast(id); f.root.position.set(x, 0.02, z); f.root.rotation.y = yaw; f.home = { x, z, yaw };
    palace.group.add(f.root); npcs.push(f);
  }
  for (const [id, path] of [['empress', [[-8, 9], [6, 9], [6, 3], [-8, 3]]], ['herald', [[-6.5, 9.5], [7.5, 9.5], [7.5, 3.5], [-6.5, 3.5]]], ['korrach', [[-15, -4], [8, 2.5], [8, 8], [-15, 8]]]]) {
    const f = cast(id); f.path = path; f.wp = 0; f.root.position.set(path[0][0], 0.02, path[0][1]);
    palace.group.add(f.root); walkers.push(f);
  }
  const marker = new THREE.Mesh(new THREE.OctahedronGeometry(0.14, 0), new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 2.2, 0.6), toneMapped: false }));
  palace.group.add(marker);
  window.__marker = marker;

  buildHUD();
  setNight(0, true);
  $('loading').style.display = 'none';
  $('enter').disabled = false;
  $('enter').textContent = 'Enter the Palace';
  if (SHOT) startGame();
  window.__ready = true;
}

// ------------------------------------------------------------------------------------------------ time of day
const waterEnv = { last: -1 };
function setNight(n, force = false) {
  night = n;
  const elev = THREE.MathUtils.lerp(4.5, -14, n) * Math.PI / 180;
  const az = THREE.MathUtils.degToRad(23);
  const dir = sunAz(az).multiplyScalar(Math.cos(elev)); dir.y = Math.sin(elev);
  sky.update(n, dir.clone().normalize(), camera);
  // the lighting sun is held a little higher than the visible disc so the terrace is lit, then fades to moonlight
  const le = Math.max(14, 14 + (1 - n) * 2) * Math.PI / 180;
  const ld = sunAz(n > 0.6 ? -0.9 : az).multiplyScalar(Math.cos(le)); ld.y = Math.sin(le);
  sun.userData.dir = ld.normalize();
  const warm = new THREE.Color(0xffa860), moon = new THREE.Color(0x8aa0ff);
  sun.color.copy(warm).lerp(moon, THREE.MathUtils.smoothstep(n, 0.45, 0.85));
  sun.intensity = THREE.MathUtils.lerp(3.4, 0.55, THREE.MathUtils.smoothstep(n, 0.0, 0.8));
  hemi.intensity = THREE.MathUtils.lerp(1.0, 0.32, n);
  hemi.color.set(0xb8a0d8).lerp(new THREE.Color(0x3a4a8a), n);
  hemi.groundColor.set(0xc89870).lerp(new THREE.Color(0x2a2030), n);
  scene.fog.color.copy(sky.fogColor);
  scene.fog.density = THREE.MathUtils.lerp(0.00042, 0.00034, n);
  renderer.toneMappingExposure = THREE.MathUtils.lerp(1.0, 1.15, n);
  grade.uniforms.uWarm.value = 1 - n;
  const wa = THREE.MathUtils.smoothstep(n, 0.2, 0.55) * 2.6, wb = THREE.MathUtils.smoothstep(n, 0.45, 0.85) * 2.4;
  if (city) { city.winMatA.emissiveIntensity = wa; city.winMatB.emissiveIntensity = wb; }
  if (palace) { palace.facadeWin.material.emissiveIntensity = wa * 1.2; palace.fires.forEach((f) => { f.baseI = 18 + n * 14; }); }
  if (city && (force || Math.abs(n - waterEnv.last) > 0.12)) {
    waterEnv.last = n;
    const s2 = new THREE.Scene(); const d2 = sky.dome.clone(); d2.position.set(0, 0, 0); d2.scale.setScalar(100); s2.add(d2);
    const c2 = sky.clouds.clone(); c2.position.set(0, 0, 0); c2.scale.setScalar(0.03); s2.add(c2);
    const pm = new THREE.PMREMGenerator(renderer);
    const env = pm.fromScene(s2, 0, 0.1, 1000).texture;
    if (city.waterMat.envMap) city.waterMat.envMap.dispose();
    city.waterMat.envMap = env; city.waterMat.needsUpdate = true;
    pm.dispose();
  }
}

// ------------------------------------------------------------------------------------------------ HUD and dialogue
function buildHUD() {
  $('stats').innerHTML = STATS.map((s) => `<div class="stat" id="st-${s.id}"><span class="ic">${s.icon}</span><span class="lb">${s.label}</span><span class="bar"><i></i></span><b></b></div>`).join('');
  refreshHUD();
}
function refreshHUD(delta = {}) {
  for (const s of STATS) {
    const el = $('st-' + s.id), v = Math.max(0, Math.min(100, stats[s.id]));
    el.querySelector('i').style.width = v + '%';
    el.querySelector('b').textContent = Math.round(v);
    if (delta[s.id]) { el.classList.remove('up', 'down'); void el.offsetWidth; el.classList.add(delta[s.id] > 0 ? 'up' : 'down'); }
  }
  const hours = ['The sun touches the hills', 'The first lamps are lit', 'Dusk settles on the capital', 'The city glows in the dark', 'The second watch of the night', 'Night over the capital'];
  $('clock').textContent = hours[Math.min(step, hours.length - 1)];
  const p = PETITIONS[step];
  $('objective').innerHTML = p ? `<span>Petition</span> ${CAST[p.who].name} <em>· ${CAST[p.who].title}</em> seeks a word with you` : '<span>The evening is over</span>';
}
function openDialogue(npc) {
  const p = npc.petition;
  state = 'talk'; talking = npc; npc.talk = 1;
  $('prompt').classList.remove('show');
  const d = $('dialogue');
  d.querySelector('.who').innerHTML = `${CAST[npc.id].name}<em>${CAST[npc.id].title}</em>`;
  d.querySelector('.title').textContent = p.title;
  d.querySelector('.text').textContent = '';
  typeText(d.querySelector('.text'), p.text);
  const ch = d.querySelector('.choices');
  ch.innerHTML = '';
  p.choices.forEach((c, i) => {
    const b = document.createElement('button');
    b.innerHTML = `<span class="k">${i + 1}</span>${c.label}<span class="fx">${fxText(c.fx)}</span>`;
    b.onclick = () => choose(npc, c);
    ch.appendChild(b);
  });
  d.classList.add('show');
}
const fxText = (fx) => Object.entries(fx).map(([k, v]) => `<i class="${v > 0 ? 'p' : 'n'}">${STATS.find((s) => s.id === k).icon}${v > 0 ? '+' : ''}${v}</i>`).join('');
let typeTimer = null;
function typeText(el, text) {
  clearInterval(typeTimer);
  let i = 0;
  typeTimer = setInterval(() => { i += 2; el.textContent = text.slice(0, i); if (i >= text.length) clearInterval(typeTimer); }, 16);
}
function choose(npc, c) {
  for (const [k, v] of Object.entries(c.fx)) stats[k] += v;
  refreshHUD(c.fx);
  const d = $('dialogue');
  typeText(d.querySelector('.text'), '“' + c.reply + '”');
  d.querySelector('.choices').innerHTML = `<div class="result">${fxText(c.fx)}</div>`;
  const b = document.createElement('button');
  b.className = 'cont'; b.textContent = 'Continue';
  b.onclick = () => closeDialogue();
  d.querySelector('.choices').appendChild(b);
  npc.petition = null;
  step++;
  nightTarget = Math.min(1, step / PETITIONS.length);
}
function closeDialogue() {
  $('dialogue').classList.remove('show');
  if (talking) { talking.talk = 0; }
  talking = null;
  state = 'play';
  refreshHUD();
  if (step >= PETITIONS.length) setTimeout(showEnd, 2500);
}
function showEnd() {
  const [t, txt] = verdict(stats);
  $('end').querySelector('h2').textContent = t;
  $('end').querySelector('p').textContent = txt;
  $('end').classList.add('show');
}
$('again').onclick = () => location.reload();

function startGame() {
  $('title').classList.add('hide');
  $('hud').classList.add('show');
  state = 'play';
}
$('enter').onclick = startGame;

// ------------------------------------------------------------------------------------------------ input
const keys = new Set();
addEventListener('keydown', (e) => {
  keys.add(e.code);
  if (state === 'talk') {
    const n = parseInt(e.key, 10);
    const btns = $('dialogue').querySelectorAll('.choices button');
    if (n >= 1 && n <= btns.length) btns[n - 1].click();
    if ((e.code === 'Enter' || e.code === 'Space' || e.code === 'KeyE') && btns.length === 1) btns[0].click();
  } else if (state === 'play' && e.code === 'KeyE' && nearNPC) openDialogue(nearNPC);
});
addEventListener('keyup', (e) => keys.delete(e.code));

const cam = { yaw: 0, pitch: -0.13, dist: 6.2, tYaw: 0, tPitch: -0.13, tDist: 6.2 };
let drag = null, moveTo = null, nearNPC = null, approach = null;
const ray = new THREE.Raycaster();
renderer.domElement.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, moved: 0, id: e.pointerId }; renderer.domElement.setPointerCapture(e.pointerId); });
renderer.domElement.addEventListener('pointermove', (e) => {
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  drag.moved += Math.abs(dx) + Math.abs(dy); drag.x = e.clientX; drag.y = e.clientY;
  if (state === 'play') { cam.tYaw -= dx * 0.005; cam.tPitch = THREE.MathUtils.clamp(cam.tPitch - dy * 0.003, -0.6, 0.25); }
});
renderer.domElement.addEventListener('pointerup', (e) => {
  if (drag && drag.moved < 8 && state === 'play') click(e);
  drag = null;
});
renderer.domElement.addEventListener('wheel', (e) => { cam.tDist = THREE.MathUtils.clamp(cam.tDist + e.deltaY * 0.004, 2.5, 14); }, { passive: true });
function click(e) {
  const v = new THREE.Vector2((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(v, camera);
  const pet = npcs.filter((n) => n.petition);
  const hits = ray.intersectObjects(pet.map((n) => n.root), true);
  if (hits.length) {
    let o = hits[0].object; while (o && !pet.find((n) => n.root === o)) o = o.parent;
    const n = pet.find((q) => q.root === o);
    if (n) { approach = n; moveTo = null; return; }
  }
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -HILL_H);
  const p = new THREE.Vector3();
  if (ray.ray.intersectPlane(plane, p)) { palace.group.worldToLocal(p); moveTo = new THREE.Vector2(p.x, p.z); approach = null; }
}

// ------------------------------------------------------------------------------------------------ loop
const clock = new THREE.Clock();
const tmp = new THREE.Vector3(), tmp2 = new THREE.Vector3();
let t = 0;
function frame() {
  const dt = Math.min(0.05, clock.getDelta());
  t += dt;
  if (!palace) { requestAnimationFrame(frame); return; }
  // time of day eases toward the evening's progress
  if (Math.abs(nightTarget - night) > 0.001) setNight(night + Math.sign(nightTarget - night) * Math.min(Math.abs(nightTarget - night), dt * 0.08));
  // player movement
  let mv = new THREE.Vector2();
  if (state === 'play') {
    const f = new THREE.Vector2(-Math.sin(cam.yaw), -Math.cos(cam.yaw)), r = new THREE.Vector2(Math.cos(cam.yaw), -Math.sin(cam.yaw));
    if (keys.has('KeyW') || keys.has('ArrowUp')) mv.add(f);
    if (keys.has('KeyS') || keys.has('ArrowDown')) mv.sub(f);
    if (keys.has('KeyD') || keys.has('ArrowRight')) mv.add(r);
    if (keys.has('KeyA') || keys.has('ArrowLeft')) mv.sub(r);
    if (mv.lengthSq() > 0) { moveTo = null; approach = null; }
    const pp = new THREE.Vector2(player.root.position.x, player.root.position.z);
    if (approach) {
      const ap = new THREE.Vector2(approach.root.position.x, approach.root.position.z);
      if (pp.distanceTo(ap) < 1.9) { openDialogue(approach); approach = null; } else mv.copy(ap.sub(pp));
    } else if (moveTo) { if (pp.distanceTo(moveTo) < 0.2) moveTo = null; else mv.copy(moveTo.clone().sub(pp)); }
  }
  const run = keys.has('ShiftLeft') || keys.has('ShiftRight');
  let speed = 0;
  if (mv.lengthSq() > 0) {
    mv.normalize();
    speed = run ? 4.4 : 2.1;
    const p = player.root.position, nx = p.x + mv.x * speed * dt, nz = p.z + mv.y * speed * dt;
    const blocked = (x, z) => !palace.walkable(x, z) || npcs.concat(walkers).some((n) => (n.root.position.x - x) ** 2 + (n.root.position.z - z) ** 2 < 0.55 ** 2);
    if (!blocked(nx, nz)) { p.x = nx; p.z = nz; } else if (!blocked(nx, p.z)) p.x = nx; else if (!blocked(p.x, nz)) p.z = nz; else { speed = 0; moveTo = null; }
    const want = Math.atan2(mv.x, mv.y);
    let dy = want - player.root.rotation.y; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    player.root.rotation.y += dy * Math.min(1, dt * 10);
  }
  player.update(dt, speed);
  // NPCs
  nearNPC = null;
  for (const n of npcs) {
    const d = n.root.position.distanceTo(player.root.position);
    if (n.petition && d < 2.4 && state === 'play') nearNPC = n;
    // turn toward the king when he is close or speaking with them
    const face = (n === talking || d < 3.2) ? Math.atan2(player.root.position.x - n.root.position.x, player.root.position.z - n.root.position.z) : n.home.yaw;
    let dy = face - n.root.rotation.y; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    n.root.rotation.y += dy * Math.min(1, dt * 3);
    n.update(dt, 0);
  }
  for (const w of walkers) {
    const [tx, tz] = w.path[w.wp], p = w.root.position;
    const dx = tx - p.x, dz = tz - p.z, d = Math.hypot(dx, dz);
    if (d < 0.3) w.wp = (w.wp + 1) % w.path.length;
    const sp = 1.1;
    const nx = p.x + dx / d * sp * dt, nz = p.z + dz / d * sp * dt;
    const blocked = (player.root.position.x - nx) ** 2 + (player.root.position.z - nz) ** 2 < 0.8;
    if (!blocked) { p.x = nx; p.z = nz; }
    let dy = Math.atan2(dx, dz) - w.root.rotation.y; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    w.root.rotation.y += dy * Math.min(1, dt * 4);
    w.update(dt, blocked ? 0 : sp);
  }
  const marker = window.__marker, cur = npcs.find((n) => n.petition === PETITIONS[step]);
  marker.visible = !!cur && state !== 'talk';
  if (cur) { marker.position.set(cur.root.position.x, cur.P.neckTop + 0.75 + Math.sin(t * 2.5) * 0.08, cur.root.position.z); marker.rotation.y = t * 1.5; }
  // other petitions can be taken in any order, but the marked one is next
  const pr = $('prompt');
  if (nearNPC && state === 'play') { pr.innerHTML = `Speak with <b>${CAST[nearNPC.id].name}</b> <kbd>E</kbd>`; pr.classList.add('show'); } else pr.classList.remove('show');

  palace.update(t);
  // camera
  cam.yaw += (cam.tYaw - cam.yaw) * Math.min(1, dt * 6);
  cam.pitch += (cam.tPitch - cam.pitch) * Math.min(1, dt * 6);
  cam.dist += (cam.tDist - cam.dist) * Math.min(1, dt * 6);
  const pl = player.root.position;
  let camPos, look;
  if (state === 'talk' && talking) {
    const a = talking.root.position, b2 = pl;
    const dir = tmp.set(b2.x - a.x, 0, b2.z - a.z).normalize();
    const side = new THREE.Vector3(-dir.z, 0, dir.x);
    const headY = talking.P.neckTop * 1.0 + 0.12;
    // a two-shot from the side: the speaker's face, the king in profile
    const mid = new THREE.Vector3((a.x + b2.x) / 2, 0, (a.z + b2.z) / 2);
    camPos = mid.clone().addScaledVector(side, 3.3).addScaledVector(dir, 0.9); camPos.y = headY + 0.05;
    look = new THREE.Vector3(a.x, headY - 0.62, a.z).addScaledVector(dir, 0.5);
    let fy = Math.atan2(a.x - b2.x, a.z - b2.z) - player.root.rotation.y; fy = Math.atan2(Math.sin(fy), Math.cos(fy));
    player.root.rotation.y += fy * Math.min(1, dt * 6);
  } else {
    const f = new THREE.Vector3(-Math.sin(cam.yaw) * Math.cos(cam.pitch), Math.sin(cam.pitch), -Math.cos(cam.yaw) * Math.cos(cam.pitch));
    const r = new THREE.Vector3(Math.cos(cam.yaw), 0, -Math.sin(cam.yaw));
    camPos = new THREE.Vector3(pl.x, 1.6, pl.z).addScaledVector(new THREE.Vector3(f.x, 0, f.z).normalize(), -cam.dist).addScaledVector(r, 1.09 * cam.dist / 6.2).add(new THREE.Vector3(0, 1.26 * cam.dist / 6.2, 0));
    look = camPos.clone().add(f);
  }
  palace.group.localToWorld(camPos); palace.group.localToWorld(look);
  if (!camera.userData.init || state === 'title') { camera.position.copy(camPos); camera.userData.init = true; } else camera.position.lerp(camPos, Math.min(1, dt * 5));
  if (!camera.userData.look) camera.userData.look = look.clone(); else camera.userData.look.lerp(look, Math.min(1, dt * 5));
  if (state === 'title') camera.userData.look.copy(look);
  camera.lookAt(camera.userData.look);
  // sun shadow box follows the player
  const pw = palace.group.localToWorld(tmp2.copy(pl));
  sun.target.position.copy(pw);
  sun.position.copy(pw).addScaledVector(sun.userData.dir, 90);
  sky.update(night, sky.uniforms.uSun.value, camera);

  composer.render();
  requestAnimationFrame(frame);
}

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.fov = innerWidth < innerHeight ? 70 : 46;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});
dispatchEvent(new Event('resize'));
init().catch((e) => { $('loading').textContent = 'Failed to load: ' + e.message; console.error(e); });
requestAnimationFrame(frame);
window.__dbg = { scene, camera, renderer, setNight: (n) => { nightTarget = n; setNight(n, true); }, stats, talk: () => { const n = npcs.find((q) => q.petition === PETITIONS[step]); player.root.position.set(n.root.position.x - 1.2, 0.02, n.root.position.z - 1.0); player.root.rotation.y = Math.atan2(1.2, 1.0); n.root.rotation.y = Math.atan2(-1.2, -1.0); openDialogue(n); } };
void MAT; void balZ;
