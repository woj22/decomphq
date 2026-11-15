"""The Steward's Ledger: assign cow-folk a roaming area and sleeping quarters.

Hold the ledger and use it on a cow-folk for their assignment menu. Roaming areas are boxes marked by tapping two
corner blocks; quarters are a bed. By day they wander inside their area (an invisible fence keeps them in); at
nightfall they go to their bed and lie down asleep, and at dawn they get up again. Assignments are stored on each NPC.
"""
import json
import os

from PIL import Image, ImageDraw

NS = "vaccaria"


def ledger_icon(path):
    """A small leather-bound ledger with a gold clasp and a ribbon (original 16x16 pixel art)."""
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([2, 2, 13, 14], fill=(96, 52, 30, 255))          # cover
    d.rectangle([3, 3, 12, 13], fill=(122, 68, 38, 255))
    d.rectangle([12, 3, 13, 13], fill=(236, 226, 200, 255))      # page edges
    d.line([(12, 4), (12, 12)], fill=(200, 188, 160, 255))
    d.rectangle([2, 2, 3, 14], fill=(70, 38, 22, 255))           # spine
    d.rectangle([6, 6, 9, 9], fill=(214, 170, 60, 255))          # gold crest
    d.point((7, 7), fill=(255, 230, 140, 255))
    d.rectangle([11, 7, 13, 8], fill=(214, 170, 60, 255))        # clasp
    d.line([(5, 14), (5, 15)], fill=(160, 30, 36, 255))          # ribbon
    im.save(path)


def add_assign(bp, rp):
    item = {"format_version": "1.20.80", "minecraft:item": {
        "description": {"identifier": NS + ":ledger", "menu_category": {"category": "items"}},
        "components": {"minecraft:icon": {"texture": NS + "_ledger"}, "minecraft:display_name": {"value": "Steward's Ledger"},
                       "minecraft:max_stack_size": 1}}}
    os.makedirs(os.path.join(bp, "items"), exist_ok=True)
    json.dump(item, open(os.path.join(bp, "items", "ledger.json"), "w"), indent=1)
    os.makedirs(os.path.join(rp, "textures", "items"), exist_ok=True)
    ledger_icon(os.path.join(rp, "textures", "items", NS + "_ledger.png"))
    json.dump({"resource_pack_name": "vaccaria", "texture_name": "atlas.items",
               "texture_data": {NS + "_ledger": {"textures": "textures/items/" + NS + "_ledger"}}},
              open(os.path.join(rp, "textures", "item_texture.json"), "w"), indent=1)
    lang = os.path.join(rp, "texts", "en_US.lang")
    with open(lang, "a") as f:
        f.write("item.%s:ledger=Steward's Ledger\n" % NS)
    fdir = os.path.join(bp, "functions", NS)
    os.makedirs(fdir, exist_ok=True)
    open(os.path.join(fdir, "ledger.mcfunction"), "w").write("# The Steward's Ledger: use it on a cow-folk to assign their area and quarters\ngive @s vaccaria:ledger\n")
    return ASSIGN_SCRIPT


ASSIGN_SCRIPT = r'''
// ---- the Steward's Ledger: roaming areas, quarters, and the daily round ----------------------------------
import { world as aw, system as asys } from "@minecraft/server";
import { ActionFormData as AF } from "@minecraft/server-ui";

const COW = "vaccaria:cow_folk";
const LEDGER = "vaccaria:ledger";
const pending = new Map();      // player id -> { mode: "cornerA" | "cornerB" | "bed", target, a }
const lastClick = new Map();

const getJSON = (e, k) => { try { const v = e.getDynamicProperty(k); return v ? JSON.parse(v) : null; } catch (x) { return null; } };
const setJSON = (e, k, v) => e.setDynamicProperty(k, v === null ? undefined : JSON.stringify(v));
const label = (e) => e.nameTag || "this cow-folk";

function menu(p, e) {
  const area = getJSON(e, "vaccaria:area"), bed = getJSON(e, "vaccaria:bed");
  const now = `Roaming area: ${area ? `${area.x1 - area.x0 + 1} x ${area.z1 - area.z0 + 1} blocks` : "§7none (roams freely)§r"}\nQuarters: ${bed ? `bed at ${bed.foot.x} ${bed.foot.y} ${bed.foot.z}` : "§7none§r"}`;
  new AF().title(`Assign ${label(e)}`).body(now)
    .button("Set roaming area").button("Set sleeping quarters").button("Copy roaming area to cow-folk nearby")
    .button("Show assignment").button("§cClear assignment").button("Done")
    .show(p).then((r) => {
      if (r.canceled) return;
      if (r.selection === 0) { pending.set(p.id, { mode: "cornerA", target: e.id }); p.sendMessage("§6Ledger: tap the first corner block of the roaming area."); }
      if (r.selection === 1) { pending.set(p.id, { mode: "bed", target: e.id }); p.sendMessage("§6Ledger: tap the bed that will be their quarters."); }
      if (r.selection === 2) copyArea(p, e);
      if (r.selection === 3) show(e);
      if (r.selection === 4) { setJSON(e, "vaccaria:area", null); setJSON(e, "vaccaria:bed", null); p.sendMessage(`§6${label(e)} may roam freely again.`); }
    });
}

function copyArea(p, e) {
  const area = getJSON(e, "vaccaria:area");
  if (!area) { p.sendMessage("§eSet a roaming area for this one first."); return; }
  let n = 0;
  for (const o of e.dimension.getEntities({ type: COW, location: e.location, maxDistance: 12 })) {
    if (o.id === e.id) continue;
    setJSON(o, "vaccaria:area", area); n++;
  }
  p.sendMessage(`§6Copied the roaming area to ${n} cow-folk nearby.`);
}

function show(e) {
  const area = getJSON(e, "vaccaria:area"), bed = getJSON(e, "vaccaria:bed");
  let ticks = 0;
  const id = asys.runInterval(() => {
    if (++ticks > 12) return asys.clearRun(id);
    const d = e.dimension;
    if (area) {
      const y = area.y0 + 1.2;
      for (let x = area.x0; x <= area.x1 + 1; x++) for (const z of [area.z0, area.z1 + 1]) d.spawnParticle("minecraft:villager_happy", { x, y, z });
      for (let z = area.z0; z <= area.z1 + 1; z++) for (const x of [area.x0, area.x1 + 1]) d.spawnParticle("minecraft:villager_happy", { x, y, z });
    }
    if (bed) for (let k = 0; k < 6; k++) d.spawnParticle("minecraft:heart_particle", { x: bed.foot.x + 0.5, y: bed.foot.y + 1 + k * 0.25, z: bed.foot.z + 0.5 });
  }, 10);
}

function bedAt(block) {
  if (!block || block.typeId !== "minecraft:bed") return null;
  const isHead = !!block.permutation.getState("head_piece_bit");
  for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    const o = block.dimension.getBlock({ x: block.location.x + dx, y: block.location.y, z: block.location.z + dz });
    if (o?.typeId === "minecraft:bed" && !!o.permutation.getState("head_piece_bit") !== isHead) {
      const foot = isHead ? o.location : block.location, head = isHead ? block.location : o.location;
      return { foot: { x: foot.x, y: foot.y, z: foot.z }, dir: [head.x - foot.x, head.z - foot.z] };
    }
  }
  return null;
}

aw.afterEvents.playerInteractWithEntity.subscribe((ev) => {
  if (ev.target?.typeId === COW && ev.itemStack?.typeId === LEDGER) menu(ev.player, ev.target);
});

aw.afterEvents.playerInteractWithBlock.subscribe((ev) => {
  const p = ev.player, job = pending.get(p.id);
  if (!job || ev.itemStack?.typeId !== LEDGER) return;
  if (asys.currentTick - (lastClick.get(p.id) ?? -99) < 6) return;
  lastClick.set(p.id, asys.currentTick);
  const e = aw.getEntity(job.target);
  if (!e) { pending.delete(p.id); p.sendMessage("§eThat cow-folk is no longer nearby."); return; }
  const b = ev.block.location;
  if (job.mode === "cornerA") {
    pending.set(p.id, { mode: "cornerB", target: job.target, a: { x: b.x, y: b.y, z: b.z } });
    p.sendMessage("§6Ledger: now tap the opposite corner.");
  } else if (job.mode === "cornerB") {
    const a = job.a;
    const area = { x0: Math.min(a.x, b.x), x1: Math.max(a.x, b.x), y0: Math.min(a.y, b.y), y1: Math.max(a.y, b.y), z0: Math.min(a.z, b.z), z1: Math.max(a.z, b.z) };
    setJSON(e, "vaccaria:area", area);
    pending.delete(p.id);
    const l = e.location;
    if (l.x < area.x0 || l.x > area.x1 + 1 || l.z < area.z0 || l.z > area.z1 + 1)
      e.teleport({ x: (area.x0 + area.x1 + 1) / 2, y: area.y0 + 1, z: (area.z0 + area.z1 + 1) / 2 });
    p.sendMessage(`§6${label(e)} will roam within ${area.x1 - area.x0 + 1} x ${area.z1 - area.z0 + 1} blocks.`);
    show(e);
  } else if (job.mode === "bed") {
    const bed = bedAt(ev.block);
    if (!bed) { p.sendMessage("§eThat isn't a bed. Tap one of the two halves of a bed."); return; }
    setJSON(e, "vaccaria:bed", bed);
    pending.delete(p.id);
    p.sendMessage(`§6${label(e)} will sleep there at night.`);
    show(e);
  }
});

aw.afterEvents.itemUse.subscribe((ev) => {
  if (ev.itemStack?.typeId !== LEDGER) return;
  const p = ev.source;
  new AF().title("Steward's Ledger")
    .body("Use the ledger on a cow-folk to give them a roaming area (two corner blocks) and sleeping quarters (a bed).\n\nBy day they wander inside their area. At nightfall they go to bed, and at dawn they rise.")
    .button("Show assignments near me").button("Close")
    .show(p).then((r) => {
      if (r.canceled || r.selection !== 0) return;
      const near = p.dimension.getEntities({ type: COW, location: p.location, maxDistance: 32 });
      near.forEach(show);
      p.sendMessage(`§6Showing ${near.length} cow-folk within 32 blocks.`);
    });
});

// following: they walk after their player, catch up if left far behind, and hop up single steps
function startFollowing(e, p) {
  e.setDynamicProperty("vaccaria:follow", p.id);
  if (e.getProperty("vaccaria:sleeping")) e.setProperty("vaccaria:sleeping", false);
  e.triggerEvent("vaccaria:follow");
}
function stopFollowing(e) {
  e.setDynamicProperty("vaccaria:follow", undefined);
  e.triggerEvent("vaccaria:wake");
}
asys.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity;
  if (!p || p.typeId !== "minecraft:player") return;
  if (ev.id === "vaccaria:follow") {
    const near = p.dimension.getEntities({ type: COW, location: p.location, maxDistance: 10 });
    near.forEach((e) => startFollowing(e, p));
    p.sendMessage(`§6${near.length} cow-folk fall in behind you.`);
  } else if (ev.id === "vaccaria:stay") {
    let n = 0;
    for (const e of p.dimension.getEntities({ type: COW })) if (e.getDynamicProperty("vaccaria:follow") === p.id) { stopFollowing(e); n++; }
    p.sendMessage(`§6${n} cow-folk return to their posts.`);
  }
});
function steer(e, p) {
  const l = e.location, t = p.location;
  const dx = t.x - l.x, dz = t.z - l.z, dist = Math.hypot(dx, dz);
  if (dist > 24 || e.dimension.id !== p.dimension.id) {
    e.teleport({ x: t.x - (dx / (dist || 1)) * 2, y: t.y, z: t.z - (dz / (dist || 1)) * 2 }, { dimension: p.dimension });
    return;
  }
  try { e.setRotation({ x: 0, y: Math.atan2(-dx, dz) * 180 / Math.PI }); } catch (x) { }
  if (dist < 2.6) return;
  const v = e.getVelocity();
  const speed = dist > 8 ? 0.26 : 0.19;
  let vy = v.y;
  const ahead = e.dimension.getBlock({ x: Math.floor(l.x + dx / dist * 0.8), y: Math.floor(l.y), z: Math.floor(l.z + dz / dist * 0.8) });
  if (ahead && ahead.isSolid && e.isOnGround) vy = 0.42;
  e.clearVelocity();
  e.applyImpulse({ x: dx / dist * speed, y: vy, z: dz / dist * speed });
}
asys.runInterval(() => {
  for (const p of aw.getAllPlayers()) {
    for (const e of p.dimension.getEntities({ type: COW, location: p.location, maxDistance: 64 })) {
      if (e.getDynamicProperty("vaccaria:follow") === p.id) { try { steer(e, p); } catch (x) { } }
    }
  }
}, 1);

// the daily round: every half second keep each cow-folk inside its area, put it to bed at night, wake it at dawn
function tend(e, night) {
  if (e.getDynamicProperty("vaccaria:follow")) {          // followers keep company with their player, not their routine
    const owner = aw.getAllPlayers().find((q) => q.id === e.getDynamicProperty("vaccaria:follow"));
    if (owner) return;
  }
  if (!e.getDynamicProperty("vaccaria:v14")) {          // cow-folk summoned before this version need their walking legs back
    try { e.triggerEvent("vaccaria:wake"); } catch (x) { }
    e.setDynamicProperty("vaccaria:v14", true);
  }
  const bed = getJSON(e, "vaccaria:bed"), area = getJSON(e, "vaccaria:area");
  const sleeping = !!e.getProperty("vaccaria:sleeping");
  if (night && bed) {
    const pos = { x: bed.foot.x + 0.5 - bed.dir[0] * 0.45, y: bed.foot.y + 0.62, z: bed.foot.z + 0.5 - bed.dir[1] * 0.45 };
    const yaw = Math.atan2(bed.dir[0], -bed.dir[1]) * 180 / Math.PI;     // feet at the foot of the bed, lying toward the head
    if (!sleeping) { e.triggerEvent("vaccaria:sleep"); e.setProperty("vaccaria:sleeping", true); }
    const l = e.location;
    if (Math.abs(l.x - pos.x) + Math.abs(l.y - pos.y) + Math.abs(l.z - pos.z) > 0.25) e.teleport(pos, { rotation: { x: 0, y: yaw } });
    return;
  }
  if (sleeping) {
    e.setProperty("vaccaria:sleeping", false);
    e.triggerEvent("vaccaria:wake");
    if (bed) e.teleport({ x: bed.foot.x + 0.5, y: bed.foot.y + 0.6, z: bed.foot.z + 0.5 });
    return;
  }
  if (area) {
    const l = e.location;
    const x = Math.min(Math.max(l.x, area.x0 + 0.3), area.x1 + 0.7), z = Math.min(Math.max(l.z, area.z0 + 0.3), area.z1 + 0.7);
    if (x !== l.x || z !== l.z) e.teleport({ x, y: l.y, z });
  }
}

asys.runInterval(() => {
  const t = aw.getTimeOfDay();
  const night = t >= 12600 && t < 23400;
  for (const id of ["overworld", "nether", "the_end"]) {
    let d;
    try { d = aw.getDimension(id); } catch (x) { continue; }
    for (const e of d.getEntities({ type: COW })) {
      try { tend(e, night); } catch (x) { }
    }
  }
}, 10);
'''
