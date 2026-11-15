"""Council sessions and free conversation, driven by the Vaccaria bridge (bridge/vaccaria_bridge.py in Termux).

No chat is used. The add-on and the bridge talk invisibly:
  game -> bridge: the add-on puts the message on the player as tags "vq.<seq>.<i>.<n>.<chunk>" (URI-encoded JSON);
                  the bridge reads them with "tag @a list" and acknowledges with "scriptevent vaccaria:ack <seq>".
  bridge -> game: "scriptevent vaccaria:msg <id>|<i>|<n>|<chunk>", reassembled here and shown as dialogue windows.
"""
import json
import os

import court_addon

NS = "vaccaria"

# motions the player can put before the council, and the realm that would naturally propose each
MOTIONS = [
    ("Raise the Imperial tribute by a tenth", "the Empire"),
    ("Cut the tribute paid by the client kingdoms", "Khar-Dumeth"),
    ("Raise new auxiliary levies for the Khar border", "the Empire"),
    ("Build a road from Lucerna to Vaccaria at the Treasury's expense", "Lucerna"),
    ("Guarantee open sea lanes to the southern isles", "Meridia"),
    ("Fix the price of copper across the Empire", "Tor-Ilun"),
    ("Grant Karst Odun the sole contract to arm the Legions", "Karst Odun"),
    ("Open Velithra's harbours to every realm free of duty", "Velithra"),
]


def add_council(bp):
    fdir = os.path.join(bp, "functions", NS)
    os.makedirs(fdir, exist_ok=True)
    files = {
        "convene.mcfunction": "# Convene the Imperial council (the Vaccaria bridge must be connected)\nscriptevent vaccaria:convene me\n",
        "adjourn.mcfunction": "# End a council session and let everyone rise\nscriptevent vaccaria:adjourn me\n",
        "bridge_test.mcfunction": "# Check the Vaccaria bridge can hear you\nscriptevent vaccaria:ping me\n",
    }
    for name, text in files.items():
        open(os.path.join(fdir, name), "w").write(text)
    realms = {i: c[3] for i, c in enumerate(court_addon.CHARS, 1)}
    tags = {i: c[0] for i, c in enumerate(court_addon.CHARS, 1)}
    return (SCRIPT.replace("__REALMS__", json.dumps(realms)).replace("__TAGS__", json.dumps(tags))
            .replace("__MOTIONS__", json.dumps(MOTIONS)))


SCRIPT = r'''
// ---- the bridge: free conversation and the Imperial council ---------------------------------------------
import { world as bw, system as bs } from "@minecraft/server";
import { ActionFormData as BF, ModalFormData as BM } from "@minecraft/server-ui";

const CHAR_REALM = __REALMS__;
const CHAR_TAG = __TAGS__;
const MOTIONS = __MOTIONS__;

function realmOf(e) {
  if (e.typeId === "vaccaria:courtier") return CHAR_REALM[e.getComponent("minecraft:variant")?.value ?? 1] ?? "the Empire";
  return "Vaccaria";
}
function whoOf(e) {
  if (e.typeId === "vaccaria:courtier") return CHAR_TAG[e.getComponent("minecraft:variant")?.value ?? 1];
  return e.nameTag || "Cow-folk";
}

// -- the link ----------------------------------------------------------------------------------------------
let bridgeSeen = 0;
const bridgeUp = () => Date.now() - bridgeSeen < 30000;
let outSeq = Math.floor(Date.now() / 1000) % 1000000 * 100;
const inbox = new Map();

function chunks(text, size) {
  const enc = encodeURIComponent(text), out = [];
  let i = 0;
  while (i < enc.length) {
    let j = Math.min(i + size, enc.length);
    if (j < enc.length) { if (enc[j - 1] === "%") j -= 1; else if (enc[j - 2] === "%") j -= 2; }
    out.push(enc.slice(i, j)); i = j;
  }
  return out;
}
function bridgeDown(p) {
  new BF().title("The bridge isn't connected")
    .body("Free conversation and the council need the Vaccaria bridge.\n\n1. In Termux run:\n   python vaccaria_bridge.py\n2. Back here type:\n   /connect localhost:8000\n\nThen try again.")
    .button("OK").show(p);
}
function toBridge(p, msg) {
  if (!bridgeUp()) { bridgeDown(p); return false; }
  msg.p = p.name;
  const seq = ++outSeq, parts = chunks(JSON.stringify(msg), 100);
  parts.forEach((c, i) => p.addTag(`vq.${seq}.${i}.${parts.length}.${c}`));
  return true;
}
bw.afterEvents.playerSpawn.subscribe((ev) => {
  if (ev.initialSpawn) for (const t of ev.player.getTags()) if (t.startsWith("vq.")) ev.player.removeTag(t);
});

bs.afterEvents.scriptEventReceive.subscribe((ev) => {
  const p = ev.sourceEntity?.typeId === "minecraft:player" ? ev.sourceEntity : undefined;
  switch (ev.id) {
    case "vaccaria:hello": bridgeSeen = Date.now(); return;
    case "vaccaria:ack": {
      const pre = `vq.${ev.message.trim()}.`;
      for (const q of bw.getAllPlayers()) for (const t of q.getTags()) if (t.startsWith(pre)) q.removeTag(t);
      return;
    }
    case "vaccaria:convene": if (p) convene(p); return;
    case "vaccaria:adjourn": if (session) { if (p) toBridge(p, { t: "council", action: "adjourn" }); endSession(); } return;
    case "vaccaria:ping":
      if (!p) return;
      if (toBridge(p, { t: "ping" })) notify(p, "§7Pinging the bridge...");
      return;
    case "vaccaria:msg": break;
    default: return;
  }
  bridgeSeen = Date.now();
  const [id, i, n, chunk] = ev.message.trim().split("|");
  const box = inbox.get(id) ?? { n: Number(n), parts: [] };
  box.parts[Number(i)] = chunk ?? "";
  inbox.set(id, box);
  if (box.parts.filter((x) => x !== undefined).length < box.n) return;
  inbox.delete(id);
  let msg;
  try { msg = JSON.parse(decodeURIComponent(box.parts.join(""))); } catch (x) { return; }
  const targets = bw.getAllPlayers().filter((q) => !msg.p || q.name === msg.p);
  for (const q of targets) { try { handle(q, msg); } catch (x) { } }
});

// shows a form, waiting politely if the player is busy in another screen
function present(p, form, then) {
  form.show(p).then((r) => {
    if (r.canceled && r.cancelationReason === "UserBusy") { bs.runTimeout(() => present(p, form, then), 20); return; }
    then(r);
  });
}

function handle(p, m) {
  switch (m.t) {
    case "wait": try { p.onScreenDisplay.setActionBar(`§7${m.text}`); } catch (x) { } return;
    case "notice": notify(p, m.text); return;
    case "reply": return showReply(p, m);
    case "speech": return showSpeech(p, m);
    case "floor": return showFloor(p, m);
    case "vote_call": return showVote(p, m);
    case "result": return showResult(p, m);
  }
}

// -- one-on-one ----------------------------------------------------------------------------------------------
const talking = new Map();          // player id -> who they are talking to
function speakFreely(p, info) {
  if (!bridgeUp()) return bridgeDown(p);
  talking.set(p.id, info);
  new BM().title(info.who).textField(`What do you say to ${info.who}?`, "Speak your mind...").show(p).then((r) => {
    const text = String(r.formValues?.[0] ?? "").trim();
    if (r.canceled || !text) { toBridge(p, { t: "bye", who: info.who }); talking.delete(p.id); return; }
    if (toBridge(p, { t: "talk", ...info, text })) try { p.onScreenDisplay.setActionBar(`§7${info.who} considers your words...`); } catch (x) { }
  });
}
function showReply(p, m) {
  const info = talking.get(p.id) ?? { who: m.who };
  present(p, new BF().title(m.who).body(m.text).button("Reply").button("Farewell"), (r) => {
    if (!r.canceled && r.selection === 0) speakFreely(p, info);
    else { toBridge(p, { t: "bye", who: m.who }); talking.delete(p.id); }
  });
}

// -- the council --------------------------------------------------------------------------------------------
let session = null;                 // { realms: [...], centre: {x, z} } while the council sits
bs.run(() => { try { session = JSON.parse(bw.getDynamicProperty("vaccaria:session") ?? "null"); } catch (x) { session = null; } });
function saveSession() { bw.setDynamicProperty("vaccaria:session", session ? JSON.stringify(session) : undefined); }
function endSession() { session = null; saveSession(); }

function faceCentre(c) { return Math.atan2(-(session.centre.x - (c.x + 0.5)), session.centre.z - (c.z + 0.5)) * 180 / Math.PI; }
function councilSeat(e) {
  if (!session) return null;
  const c = getJSON(e, "vaccaria:cushion");
  if (!c || !session.realms.includes(realmOf(e))) return null;
  return { pos: { x: c.x + 0.5, y: c.top, z: c.z + 0.5 }, yaw: faceCentre(c) };
}

function convene(p) {
  if (!bridgeUp()) return bridgeDown(p);
  if (session) {
    present(p, new BF().title("The Council").body("The council is already in session.").button("§cAdjourn it").button("Close"), (r) => {
      if (!r.canceled && r.selection === 0) { toBridge(p, { t: "council", action: "adjourn" }); endSession(); }
    });
    return;
  }
  const reps = allNpcs().filter((e) => getJSON(e, "vaccaria:cushion") && realmOf(e) !== "Vaccaria");
  if (!reps.length) { notify(p, "§eNo one has a council cushion yet. Use the Ledger on a courtier and choose Set council cushion."); return; }
  const form = new BF().title("Convene the Council")
    .body(`Present: ${reps.map((e) => `${whoOf(e)} (${realmOf(e)})`).join(", ")}${getJSON(p, "vaccaria:cushion") ? ", and you for Vaccaria" : "\n\n§eYou have no cushion yet: you will speak from where you stand.§r"}\n\nWhat motion is put before the council?`);
  for (const [motion, by] of MOTIONS) form.button(`${motion}\n§8proposed by ${by}`);
  form.button("§6Propose a motion of your own");
  present(p, form, (r) => {
    if (r.canceled) return;
    if (r.selection < MOTIONS.length) return openSession(p, reps, MOTIONS[r.selection][0], MOTIONS[r.selection][1]);
    new BM().title("Your motion").textField("Vaccaria moves that the council...", "e.g. lower the levies on small realms").show(p).then((m) => {
      const text = String(m.formValues?.[0] ?? "").trim();
      if (!m.canceled && text) openSession(p, reps, text, "Vaccaria");
    });
  });
}

function openSession(p, reps, motion, proposer) {
  const cushions = reps.map((e) => getJSON(e, "vaccaria:cushion"));
  const mine = getJSON(p, "vaccaria:cushion");
  if (mine) cushions.push(mine);
  session = { realms: reps.map(realmOf), motion,
              centre: { x: cushions.reduce((a, c) => a + c.x + 0.5, 0) / cushions.length, z: cushions.reduce((a, c) => a + c.z + 0.5, 0) / cushions.length } };
  saveSession();
  if (mine) { try { p.teleport({ x: mine.x + 0.5, y: mine.top, z: mine.z + 0.5 }, { dimension: bw.getDimension(mine.dim ?? "overworld"), rotation: { x: 0, y: faceCentre(mine) } }); } catch (x) { } }
  const seats = reps.map((e) => ({ who: whoOf(e), realm: realmOf(e), kind: e.typeId === "vaccaria:courtier" ? "courtier" : "cow_folk" }));
  toBridge(p, { t: "convene", motion, proposer, seats });
  notify(p, "§6The council takes its seats.");
}

function highlight(who) {
  for (const e of allNpcs()) {
    if (whoOf(e) !== who || !councilSeat(e)) continue;
    const l = e.location;
    for (let k = 0; k < 5; k++) e.dimension.spawnParticle("minecraft:villager_happy", { x: l.x + (Math.random() - 0.5) * 0.6, y: l.y + 1.6 + Math.random() * 0.5, z: l.z + (Math.random() - 0.5) * 0.6 });
  }
}
function askSpeech(p) {
  new BM().title("Address the council").textField("What do you say?", "My lords and ladies...").show(p).then((r) => {
    const text = String(r.formValues?.[0] ?? "").trim();
    toBridge(p, r.canceled || !text ? { t: "council", action: "continue" } : { t: "council", action: "speak", text });
  });
}
function showSpeech(p, m) {
  if (m.who) highlight(m.who);
  present(p, new BF().title("The Council").body(`${m.who ? `§6${m.who}§r${m.title ? ` §7(${m.title})` : ""}§r\n\n` : ""}${m.text}`)
    .button("Continue").button("Speak").button("§cAdjourn"), (r) => {
    if (r.canceled || r.selection === 0) return toBridge(p, { t: "council", action: "continue" });
    if (r.selection === 1) return askSpeech(p);
    toBridge(p, { t: "council", action: "adjourn" }); endSession();
  });
}
function showFloor(p, m) {
  present(p, new BF().title("The Council").body(m.text).button("Speak").button("Yield the floor"), (r) => {
    if (!r.canceled && r.selection === 0) askSpeech(p);
    else toBridge(p, { t: "council", action: "continue" });
  });
}
function showVote(p, m) {
  present(p, new BF().title("The Vote").body(m.text).button("§2Aye").button("§4Nay").button("Abstain"), (r) => {
    toBridge(p, { t: "council", action: "vote", vote: r.canceled ? "abstain" : ["aye", "nay", "abstain"][r.selection] });
  });
}
function showResult(p, m) {
  endSession();
  present(p, new BF().title(m.title ?? "The Council").body(m.text).button("Rise"), () => { });
}
'''
