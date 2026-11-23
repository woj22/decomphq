
// ---- Server layer: who rules each area, and how many members live there ----
// Stored in the #server-data block of the page itself. Editors save from the page,
// which republishes the artifact with the new data.
const SERVER = JSON.parse(document.getElementById("server-data").textContent);
const AREA_ORDER = ["belgium", "flanders", "wallonia", "brussels", "antwerp", "east-flanders", "west-flanders", "flemish-brabant", "limburg", "hainaut", "liege", "luxembourg", "namur", "walloon-brabant"];

const SHELL = `
<div class="wrap">
  <header>
    <div class="brand">
      <div class="flag" aria-hidden="true"><i></i><i></i><i></i></div>
      <div>
        <h1>Belgium Region Atlas</h1>
        <p class="sub" id="sub"></p>
      </div>
    </div>
    <div class="seg" role="group" aria-label="Map divisions">
      <button id="mode-prov" aria-pressed="true">Provinces</button>
      <button id="mode-reg" aria-pressed="false">Regions</button>
    </div>
  </header>
  <div class="main">
    <div class="stage" id="stage">
      <svg id="map" role="img" aria-label="Map of Belgium"></svg>
      <div class="cap" id="cap"></div>
      <div class="tip" id="tip"></div>
      <div class="legend" aria-hidden="true">
        <span><i style="background:var(--flanders)"></i>Flanders</span>
        <span><i style="background:var(--wallonia)"></i>Wallonia</span>
        <span><i style="background:var(--brussels)"></i>Brussels</span>
      </div>
    </div>
    <aside class="panel" id="panel" aria-live="polite"></aside>
  </div>
  <footer>Boundaries: Statbel / NGI open data. Population ≈ 1 Jan 2024 (Statbel), rounded.</footer>
</div>`;
document.getElementById("root").innerHTML = SHELL;

const svg = document.getElementById("map");
const tip = document.getElementById("tip");
const cap = document.getElementById("cap");
const stage = document.getElementById("stage");
const panel = document.getElementById("panel");
const NS = "http://www.w3.org/2000/svg";
let mode = "province";
let selected = null;
let editing = false;
let canEdit = false;
let artifactApi = null;

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = n => n.toLocaleString("en-US");
const fmt = n => n >= 1e6 ? (n / 1e6).toFixed(2).replace(/0$/, "") + "M" : Math.round(n / 1000) + "k";
const regionOf = key => PROVINCES[key].region;
const currentTarget = key => mode === "province" ? key : regionOf(key);
const areaName = id => id === "belgium" ? "Belgium" : (PROVINCES[id] || REGIONS[id]).name;
const areaRegion = id => id === "belgium" ? null : PROVINCES[id] ? PROVINCES[id].region : id;

function area(id) { return SERVER.areas[id] || (SERVER.areas[id] = { title: "", ruler: "", members: null }); }
// a region's or the country's count is its own number if set, else the sum of what's below it
function membersOf(id) {
  const own = area(id).members;
  if (Number.isFinite(own)) return own;
  const kids = id === "belgium" ? Object.keys(PROVINCES) : REGIONS[id] && id !== "brussels" ? Object.keys(PROVINCES).filter(k => PROVINCES[k].region === id) : [];
  const vals = kids.map(k => area(k).members).filter(Number.isFinite);
  return vals.length ? vals.reduce((a, b) => a + b, 0) : null;
}
const membersText = id => { const m = membersOf(id); return m == null ? "—" : num(m); };

svg.setAttribute("viewBox", `0 0 ${GEO.w} ${GEO.h}`);
function el(tag, attrs = {}, text) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text != null) e.textContent = text;
  return e;
}
[["NORTH SEA", 70, 80], ["NETHERLANDS", 760, 40], ["GERMANY", 945, 620], ["FRANCE", 260, 640], ["LUX.", 905, 760]]
  .forEach(([t, x, y]) => svg.append(el("text", { class: "edge", x, y, "text-anchor": "middle" }, t)));

const shapes = {};
const gShapes = el("g");
svg.append(gShapes);
const order = Object.keys(GEO.shapes).sort((a, b) => (a === "brussels") - (b === "brussels"));
for (const key of order) {
  const path = el("path", { d: GEO.shapes[key].d, class: "prov", tabindex: 0, role: "button", "aria-label": PROVINCES[key].name, "fill-rule": "evenodd" });
  path.dataset.key = key;
  shapes[key] = path;
  gShapes.append(path);
}

// lightness step per province within its region, so neighbours read apart
const STEP = { "antwerp": 0, "east-flanders": 12, "west-flanders": -6, "flemish-brabant": 20, "limburg": 7,
  "hainaut": -4, "liege": 9, "namur": 17, "luxembourg": 3, "walloon-brabant": 24, "brussels": 0 };
const HVAR = { flanders: "fl", wallonia: "wa", brussels: "br" };
function paint() {
  for (const [key, path] of Object.entries(shapes)) {
    const v = HVAR[regionOf(key)];
    const step = mode === "province" ? STEP[key] : 0;
    const base = `hsl(var(--${v}-h) var(--${v}-s) calc(var(--${v}-l) + ${step}%))`;
    // with a selection, everything else fades to a quiet tinted neutral instead of going translucent
    path.style.fill = selected && !path.classList.contains("sel") ? `color-mix(in srgb, ${base} 22%, var(--dim))` : base;
  }
}

function setSelected(id, push = true) {
  selected = id;
  editing = false;
  svg.classList.toggle("has-sel", !!id);
  for (const [key, path] of Object.entries(shapes)) {
    const on = !!id && (mode === "province" ? key === id : regionOf(key) === id);
    path.classList.toggle("sel", on);
    path.setAttribute("aria-pressed", on ? "true" : "false");
  }
  if (id && mode === "province" && id !== "brussels") gShapes.insertBefore(shapes[id], shapes.brussels);
  paint();
  renderCap();
  render();
  if (push) {
    const h = id ? "#" + id : "";
    if (location.hash !== h) history.replaceState(null, "", h || location.pathname + location.search);
  }
}

function renderCap() {
  if (!selected) { cap.innerHTML = `<span>${mode === "province" ? "Tap a province" : "Tap a region"}</span>`; return; }
  const r = areaRegion(selected);
  const kind = mode === "province" && selected !== "brussels" ? "Province" : "Region";
  cap.innerHTML = `<i style="background:var(--${r})"></i><b>${esc(areaName(selected))}</b><span>${kind}</span>`;
}
function renderSub() {
  const total = membersOf("belgium");
  document.getElementById("sub").innerHTML = `<b>${esc(SERVER.name || "Your server")}</b> · ${total == null ? "member counts coming soon" : num(total) + " members"} · 3 regions, 10 provinces + Brussels`;
}

const hueVars = r => r ? `--hue: var(--${r}); --soft: var(--${r}-soft);` : `--hue: var(--fg); --soft: var(--surface-2);`;
const CROWN = `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 7.5l4.5 3.5L12 4l4.5 7L21 7.5 19 18H5L3 7.5z"/><rect x="5" y="19.5" width="14" height="2" rx="1"/></svg>`;

function courtHTML(id) {
  const a = area(id);
  const editBtn = canEdit ? `<button class="ghost" id="edit">Edit</button>` : "";
  if (editing) {
    return `<div class="court" style="${hueVars(areaRegion(id))}">
      <div class="court-head"><h3>Server · ${esc(areaName(id))}</h3></div>
      <form id="court-form">
        ${id === "belgium" ? `<label>Server name<input id="f-server" value="${esc(SERVER.name)}" maxlength="60"></label>` : ""}
        <label>Title<input id="f-title" value="${esc(a.title)}" maxlength="60" placeholder="e.g. Duke of Brabant"></label>
        <label>Ruler<input id="f-ruler" value="${esc(a.ruler)}" maxlength="60" placeholder="Discord name, or leave empty"></label>
        <label>Members${id === "belgium" || REGIONS[id] && id !== "brussels" ? " (leave empty to add up the provinces)" : ""}<input id="f-members" type="number" min="0" step="1" inputmode="numeric" value="${Number.isFinite(a.members) ? a.members : ""}"></label>
        <div class="row"><button type="button" class="btn" id="cancel">Cancel</button><button type="submit" class="btn primary" id="save">Save to map</button></div>
        <p class="note" id="save-note">Saving publishes a new version of this page for everyone.</p>
      </form></div>`;
  }
  return `<div class="court" style="${hueVars(areaRegion(id))}">
    <div class="court-head"><h3>On the server</h3>${editBtn}</div>
    <div class="court-row">
      <div class="crest">${CROWN}</div>
      <div style="min-width:0"><div class="ruler-title">${esc(a.title || "Ruler")}</div>
        <div class="ruler-name ${a.ruler ? "" : "empty"}">${a.ruler ? esc(a.ruler) : "Unclaimed"}</div></div>
      <div class="members"><b class="${membersOf(id) == null ? "empty" : ""}">${membersText(id)}</b><span>members</span></div>
    </div></div>`;
}

function namesHTML(local) {
  return `<p class="names"><em>NL</em>${local.nl} &nbsp; <em>FR</em>${local.fr} &nbsp; <em>DE</em>${local.de}</p>`;
}
function rosterHTML() {
  const ids = mode === "province" ? Object.keys(PROVINCES) : Object.keys(REGIONS);
  return `<div class="sec"><h3>${mode === "province" ? "Provinces & rulers" : "Regions & rulers"}</h3><div class="roster">${ids.map(k => {
    const a = area(k);
    return `<button data-go="${k}" aria-current="${k === selected}"><i style="background:var(--${areaRegion(k)})"></i>
      <span class="who"><b>${esc(areaName(k))}</b><span>${esc(a.title || "Ruler")} · ${a.ruler ? esc(a.ruler) : "Unclaimed"}</span></span>
      <span class="n">${membersText(k)}</span></button>`;
  }).join("")}</div></div>`;
}

function render() {
  let html;
  if (!selected) {
    html = `
      <div><span class="badge" style="${hueVars(null)}"><i></i>Kingdom of Belgium</span>
      <h2>Pick a ${mode === "province" ? "province" : "region"}</h2>
      ${namesHTML({ nl: "België", fr: "Belgique", de: "Belgien" })}</div>
      ${courtHTML("belgium")}
      <p class="lede">Belgium is split two ways: three <b>regions</b> (Flanders, Wallonia, Brussels) and three language <b>communities</b> (Flemish, French, German-speaking). Flanders and Wallonia each have five provinces.</p>
      ${rosterHTML()}`;
  } else if (mode === "province") {
    const p = PROVINCES[selected], R = REGIONS[p.region];
    html = `
      <div class="panel-top"><div><span class="badge" style="${hueVars(p.region)}"><i></i>${p.region === "brussels" ? "Capital region" : "Province · " + R.name}</span>
      <h2>${p.name}</h2>${namesHTML(p.local)}</div>
      <button class="ghost" id="copy">Copy link</button></div>
      ${courtHTML(selected)}
      <dl class="stats">
        <div class="stat"><dt>Capital</dt><dd>${p.capital}</dd></div>
        <div class="stat"><dt>Largest city</dt><dd>${p.city}</dd></div>
        <div class="stat"><dt>Population</dt><dd>≈ ${fmt(p.pop)}</dd></div>
        <div class="stat"><dt>Area</dt><dd>${num(p.area)} <small>km²</small></dd></div>
        <div class="stat"><dt>Density</dt><dd>${num(Math.round(p.pop / p.area))} <small>/km²</small></dd></div>
        <div class="stat"><dt>Language</dt><dd>${p.lang}</dd></div>
      </dl>
      <p class="lede">${p.lede}</p>
      <div class="sec" style="${hueVars(p.region)}"><h3>Highlights</h3><ul>${p.highlights.map(h => `<li>${h}</li>`).join("")}</ul></div>
      <div class="fact" style="${hueVars(p.region)}"><b>Did you know?</b> ${p.fact}</div>
      ${rosterHTML()}`;
  } else {
    const R = REGIONS[selected];
    html = `
      <div class="panel-top"><div><span class="badge" style="${hueVars(selected)}"><i></i>${R.kind}</span>
      <h2>${R.name}</h2>${namesHTML(R.local)}</div>
      <button class="ghost" id="copy">Copy link</button></div>
      ${courtHTML(selected)}
      <dl class="stats">${R.stats.map(([k, v]) => `<div class="stat"><dt>${k}</dt><dd>${v}</dd></div>`).join("")}</dl>
      <p class="lede">${R.lede}</p>
      <div class="sec" style="${hueVars(selected)}"><h3>Highlights</h3><ul>${R.highlights.map(h => `<li>${h}</li>`).join("")}</ul></div>
      <div class="fact" style="${hueVars(selected)}"><b>${R.fact[0]}</b> ${R.fact[1]}</div>
      ${rosterHTML()}`;
  }
  panel.innerHTML = html;
  panel.classList.remove("swap"); void panel.offsetWidth; panel.classList.add("swap");
  renderSub();
  wirePanel();
}

function wirePanel() {
  panel.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => setSelected(b.dataset.go === selected ? null : b.dataset.go)));
  const copy = panel.querySelector("#copy");
  if (copy) copy.addEventListener("click", () => {
    const url = location.href.split("#")[0] + "#" + selected;
    const done = () => { copy.textContent = "Copied"; setTimeout(() => copy.textContent = "Copy link", 1400); };
    try { navigator.clipboard.writeText(url).then(done, () => { copy.textContent = url; }); } catch { copy.textContent = url; }
  });
  const edit = panel.querySelector("#edit");
  if (edit) edit.addEventListener("click", () => { editing = true; render(); panel.querySelector("#f-title")?.focus(); });
  const cancel = panel.querySelector("#cancel");
  if (cancel) cancel.addEventListener("click", () => { editing = false; render(); });
  const form = panel.querySelector("#court-form");
  if (form) form.addEventListener("submit", e => { e.preventDefault(); save(); });
}

// ---- Saving: rebuild the page from its own source with the new data, then publish ----
function pageSource() {
  const json = JSON.stringify(SERVER, null, 1).replace(/</g, "\\u003c");
  return SKEL + HEAD + `\n<style id="app-style">` + document.getElementById("app-style").textContent + `</style>\n<div id="root"></div>\n<script type="application/json" id="server-data">` + json + `</` + `script>\n<script id="app">` + document.getElementById("app").textContent + `</` + `script>\n</body></html>\n`;
}

async function save() {
  const id = selected || "belgium";
  const a = area(id);
  const note = panel.querySelector("#save-note");
  const btn = panel.querySelector("#save");
  const before = JSON.stringify(SERVER);
  const raw = panel.querySelector("#f-members").value.trim();
  const n = raw === "" ? null : Math.max(0, Math.round(Number(raw)));
  a.title = panel.querySelector("#f-title").value.trim();
  a.ruler = panel.querySelector("#f-ruler").value.trim();
  a.members = Number.isFinite(n) ? n : null;
  const srv = panel.querySelector("#f-server");
  if (srv) SERVER.name = srv.value.trim();
  if (JSON.stringify(SERVER) === before) { editing = false; render(); return; }
  btn.disabled = true; note.textContent = "Saving…";
  try { sessionStorage.setItem("atlas-view", JSON.stringify({ mode, selected })); } catch {}
  try {
    await artifactApi.publish(pageSource());
    note.textContent = "Saved. Reloading…";
  } catch (err) {
    const code = err && err.code;
    if (code === "conflict") { note.textContent = "Someone saved first. Loading their version…"; return; }
    if (["not_writer", "not_granted", "consent_required", "capability_disabled", "capability_removed", "not_declared"].includes(code)) {
      canEdit = false; note.textContent = "This view is read-only, so changes can't be saved here.";
    } else if (code === "rate_limited") {
      note.textContent = "Saving too often. Wait a minute and press Save again.";
    } else {
      note.textContent = "Couldn't save just now. Press Save to try again.";
    }
    btn.disabled = false;
  }
}

async function enableEditing() {
  if (!window.claude?.use) return;
  try {
    const [art, user] = await Promise.all([claude.use("artifact"), claude.use("user")]);
    if (!art) return;
    artifactApi = art;
    canEdit = (await user?.canEdit()) ?? false;
    if (canEdit) render();
  } catch {}
}

// ---- Modes and interaction ----
function setMode(m, keep) {
  mode = m;
  document.getElementById("mode-prov").setAttribute("aria-pressed", m === "province");
  document.getElementById("mode-reg").setAttribute("aria-pressed", m === "region");
  svg.classList.toggle("regions", m === "region");
  paint();
  setSelected(keep ?? null);
}
document.getElementById("mode-prov").addEventListener("click", () => setMode("province", mode === "region" ? null : selected));
document.getElementById("mode-reg").addEventListener("click", () => setMode("region", selected && mode === "province" ? regionOf(selected) : selected));

svg.addEventListener("click", e => {
  const k = e.target.dataset?.key;
  if (!k) { setSelected(null); return; }
  const t = currentTarget(k);
  setSelected(selected === t ? null : t);
});
svg.addEventListener("keydown", e => {
  const k = e.target.dataset?.key;
  if (k && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); const t = currentTarget(k); setSelected(selected === t ? null : t); }
  if (e.key === "Escape") setSelected(null);
});
svg.addEventListener("pointermove", e => {
  const k = e.target.dataset?.key;
  if (!k || e.pointerType === "touch") { tip.classList.remove("on"); return; }
  const id = currentTarget(k);
  const a = area(id);
  const r = stage.getBoundingClientRect();
  tip.innerHTML = `<b>${esc(areaName(id))}</b><span>${esc(a.title || "Ruler")}: ${a.ruler ? esc(a.ruler) : "Unclaimed"}</span><span>${membersText(id)} members</span>`;
  tip.style.left = Math.min(Math.max(e.clientX - r.left, 90), r.width - 90) + "px";
  tip.style.top = (e.clientY - r.top) + "px";
  tip.classList.add("on");
});
svg.addEventListener("pointerleave", () => tip.classList.remove("on"));

function fromHash() {
  const h = location.hash.slice(1);
  if (PROVINCES[h] && !(h === "brussels" && mode === "region")) { if (mode !== "province") setMode("province", h); else setSelected(h, false); return true; }
  if (REGIONS[h]) { if (mode !== "region") setMode("region", h); else setSelected(h, false); return true; }
  return false;
}
window.addEventListener("hashchange", fromHash);

paint();
setSelected(null, false);
if (!fromHash()) {
  try {
    const v = JSON.parse(sessionStorage.getItem("atlas-view") || "null");
    sessionStorage.removeItem("atlas-view");
    if (v) setMode(v.mode === "region" ? "region" : "province", v.selected);
  } catch {}
}
enableEditing();
