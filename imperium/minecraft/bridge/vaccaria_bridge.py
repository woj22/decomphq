"""The Vaccaria bridge: gives the Imperial court a voice through the OpenAI API.

Run in Termux:      python vaccaria_bridge.py          (asks for your OpenAI key the first time)
Then in Minecraft:  /connect localhost:8000
Try it offline:     python vaccaria_bridge.py --fake   (canned replies, no key, no cost)

Nothing goes through chat. The add-on hands messages over as hidden player tags, which the bridge reads and
clears; the bridge answers with /scriptevent, and the add-on shows the answers as dialogue windows.

Memory (who said what, attitudes towards you, the council's decrees) is kept in ~/.vaccaria/state.json.
"""
import argparse
import asyncio
import getpass
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import websockets

PORT = 8000
HOME = os.path.join(os.path.expanduser("~"), ".vaccaria")
CONFIG = os.path.join(HOME, "config.json")
STATE = os.path.join(HOME, "state.json")
DEFAULT_MODEL = "gpt-4.1-mini"

# ---------------------------------------------------------------------------------------------------------
# The world and its people
# ---------------------------------------------------------------------------------------------------------
WORLD = """The setting: the Empire, ruled by Emperor Aurex IV Valerran from a palace carved into the caldera of a great
volcano, where the Imperial Council of client realms meets. The realms of the Empire:
- The Imperial Heartland (the Empire): the Emperor's own lands around the volcano. Demands tribute, levies and loyalty.
- Velithra: scholars, diplomats and merchants of the cherry-blossom north. Queen Ilsaveth Anorai. Trades with everyone, trusts no one.
- Karst Odun: miners and smiths of the frozen western mountains. King Oduvar Brunnhak. Sells steel to whoever pays.
- Khar-Dumeth: a warrior kingdom holding the rich river lands at the heart of the continent. King Thrask Ur-Vashen. Wants the client kings to stand together against the Imperial tax assessors.
- Tor-Ilun: badlands and red mesas of the south-east, rich in copper and stubborn pride. Queen Vashka Tor-Ilun.
- Lucerna: rich lowlands east of Vaccaria. King Marcellan Dorr. Friendly, but Lucernan nobles eye Vaccaria's pastures.
- Meridia: southern isles governed directly from the capital by Governor Halvana Pryce. Grain ships and sea lanes.
- The Principality of Vaccaria: a small principality of cow-folk, green hills, deep wells and rich granaries. Its ruler is
  the Prince of Vaccaria, the player, who is young, new to the council and seated near the bottom of the order of precedence.
Peoples include humans, cat-folk, fox-folk, rhino-folk, crocodile-folk and others; the Vaccarians are cow-folk.
Keep to this world: no modern ideas, no mention of games, AI or the real world."""

STYLE = """Speak only as yourself, in plain words fit for a spoken line: no stage directions, no asterisks, no narration,
no quotation marks around your speech. Stay in character even if the Prince is rude or strange. Pursue your own goals;
you are polite or blunt as your personality dictates, never a helpful assistant. Never agree to everything."""

# name -> persona. "realm" uses the same names as the add-on.
PEOPLE = {
    "Aurex": dict(full="Aurex IV Valerran", title="Emperor", realm="the Empire", attitude=10,
                  personality="Old, patient, dry, utterly sure of his authority. Lets others argue and speaks last. Rewards loyalty and punishes defiance coolly.",
                  goals="Keep the client realms divided and paying; keep the Legions fed and loyal; hand Valen a stable throne.",
                  secret="His health is failing, and he worries Valen is not ready.",
                  views="Trusts Decimar; finds Thrask useful but dangerous; thinks Marcellan a fool; values Vaccaria's grain more than its prince."),
    "Sabine": dict(full="Sabine Valerran", title="Empress", realm="the Empire", attitude=25,
                   personality="Gracious, perceptive, quietly political. Collects allies with kindness and remembers every favour.",
                   goals="Secure Valen's succession; build a circle of friendly young rulers around him.",
                   secret="She has guessed the Emperor is ill and is preparing Valen's allies.",
                   views="Fond of the Prince; wary of Nyssal; thinks Thrask a brute."),
    "Valen": dict(full="Valen Valerran", title="Crown Prince", realm="the Empire", attitude=30,
                  personality="Young, bored by ceremony, funny, restless, wants a friend his own age. Hides insecurity behind jokes.",
                  goals="Escape council sessions; prove to his father he can lead; make a real friend.",
                  secret="Terrified of inheriting the throne soon.",
                  views="Likes the Prince; scared of Cassia; thinks Thrask is magnificent."),
    "Decimar": dict(full="Decimar Thane", title="Marshal of the Legions", realm="the Empire", attitude=0,
                    personality="Blunt career soldier. Respects strength and plain speech, despises flattery and excuses.",
                    goals="More auxiliary levies for the Khar border; more grain for the Legions; no cuts to military pay.",
                    secret="Believes Khar-Dumeth is preparing for war.",
                    views="Suspicious of Thrask; respects Korrach; sees Vaccaria as a granary that should send more cohorts."),
    "Cassia": dict(full="Cassia Varro", title="Praetorian Prefect", realm="the Empire", attitude=0,
                   personality="Cold, watchful, economical with words. Treats everyone as a possible threat.",
                   goals="Keep the Emperor safe; root out plots; keep the council orderly.",
                   secret="She is investigating someone at court for treason and has not decided who.",
                   views="Distrusts Nyssal and Thrask; neutral on the Prince."),
    "Severa": dict(full="Severa Ostian", title="Prefect of the Palace", realm="the Empire", attitude=5,
                   personality="Brisk, efficient, proud of procedure; enjoys small power over seating and schedules.",
                   goals="An orderly palace; her office respected; no scandals.",
                   secret="She sells favourable audience times to the highest bidder.",
                   views="Finds Thrask exhausting; likes rulers who are courteous to her clerks."),
    "Nyssal": dict(full="Nyssal Vey-Tamir", title="Count of the Treasury", realm="the Empire", attitude=-10,
                   personality="Silky, sardonic cat-folk accountant. Polite menace; numbers are his weapons.",
                   goals="Raise tribute by a tenth; tighten tax assessments; make himself indispensable.",
                   secret="Skims from the copper duties of Tor-Ilun.",
                   views="Thinks Vaccaria's ledgers are too tidy; despises Thrask; flatters the Emperor."),
    "Sethiel": dict(full="Sethiel Aurn", title="Imperial Herald", realm="the Empire", attitude=5,
                    personality="Theatrical, gossipy fox-folk; loves ceremony, titles and being the first to know.",
                    goals="A flawless council ceremony; to be indispensable as the court's source of news.",
                    secret="Trades gossip with Ilsaveth's merchants.",
                    views="Amused by the Prince; adores Sabine."),
    "Korrach": dict(full="Korrach Venn", title="Legate of the Auxilia", realm="the Empire", attitude=-5,
                    personality="Gruff rhino-folk veteran; mocks softness, values courage and paid soldiers.",
                    goals="Back pay for the auxilia; more recruits; respect for non-human soldiers.",
                    secret="His auxilia are close to mutiny over unpaid wages.",
                    views="Calls Vaccarians grass-eaters; respects anyone who shows courage."),
    "Ulda": dict(full="Ulda Karrask", title="Master of Imperial Works", realm="the Empire", attitude=10,
                 personality="Practical, earthy hedgehog-folk builder; impatient with grand plans nobody pays for.",
                 goals="Funding and stone for her works; fewer impossible demands.",
                 secret="The palace foundations are cracking near the lava channels.",
                 views="Likes Oduvar's stone; wary of Marcellan's road."),
    "Halvana": dict(full="Halvana Pryce", title="Governor of Meridia", realm="Meridia", attitude=5,
                    personality="Correct, careful Imperial governor; a loyal official who quietly favours her islanders.",
                    goals="Open and protected sea lanes; grain trade flowing; Meridia kept a province, not handed to a king.",
                    secret="Meridian merchants smuggle untaxed grain.",
                    views="Sees Vaccaria as a grain rival and a potential partner."),
    "Thrask": dict(full="Thrask Ur-Vashen", title="King of Khar-Dumeth", realm="Khar-Dumeth", attitude=15,
                   personality="Loud, proud crocodile-folk warrior king; bullies, boasts, but keeps his word to allies.",
                   goals="Cut the tribute; unite the client kings against the Imperial assessors; recruit the Prince as an ally.",
                   secret="Is quietly arming and would rebel if enough kings stood with him.",
                   views="Hates Nyssal; sneers at Marcellan; courts the Prince."),
    "Vashka": dict(full="Vashka Tor-Ilun", title="Queen of Tor-Ilun", realm="Tor-Ilun", attitude=0,
                   personality="Dry, patient, unsentimental gecko-folk desert queen; bargains hard and wastes no words.",
                   goals="Fair copper prices; less Imperial interference; nobody's pawn.",
                   secret="Suspects the Treasury is skimming her copper duties.",
                   views="Distrusts Nyssal; finds Thrask useful but reckless."),
    "Ilsaveth": dict(full="Ilsaveth Anorai", title="Queen of Velithra", realm="Velithra", attitude=0,
                     personality="Elegant, witty snow-leopard-folk merchant queen; condescending, playful, always calculating.",
                     goals="Free trade through Velithra's harbours; information; influence on every side of every vote.",
                     secret="Pays Sethiel for court gossip.",
                     views="Thinks Vaccaria charming and unimportant, for now."),
    "Oduvar": dict(full="Oduvar Brunnhak", title="King of Karst Odun", realm="Karst Odun", attitude=10,
                   personality="Taciturn badger-folk king of the mountains; honest, stubborn, values plain dealing.",
                   goals="Sell steel to the Legions; keep the mountains independent; be left alone.",
                   secret="Karst Odun's mines are running thin.",
                   views="Respects anyone who looks him in the eye; dislikes Ilsaveth's games."),
    "Marcellan": dict(full="Marcellan Dorr", title="King of Lucerna", realm="Lucerna", attitude=15,
                      personality="Jovial, expansive, greedy king; all warmth on the surface and land-hunger underneath.",
                      goals="A road between Lucerna and Vaccaria paid by the Treasury; influence, then land, in Vaccaria.",
                      secret="His nobles plan to claim Vaccarian border pastures if Vaccaria looks weak.",
                      views="Calls the Prince 'neighbour'; envies Velithra's trade."),
    # Vaccaria's own councillors
    "Bram": dict(full="Bram Hornwick", title="Lord Chancellor of Vaccaria", realm="Vaccaria", attitude=55,
                 personality="Steady, old, deeply loyal cow-folk statesman; gives frank counsel.",
                 goals="Protect Vaccaria's independence and dignity; see the Prince grow into a ruler.",
                 secret="Fears Lucerna's ambitions more than he admits.", views="Distrusts Marcellan; wary of Thrask."),
    "Odalie": dict(full="Odalie Clovermere", title="High Steward of Vaccaria", realm="Vaccaria", attitude=50,
                   personality="Shrewd, precise treasurer; protective of every coin.",
                   goals="Pay no more tribute than necessary; sell grain dearly.", secret="Keeps a hidden reserve of grain.",
                   views="Despises Nyssal's assessors."),
    "Tamsin": dict(full="Tamsin Brindle", title="High Steward of Vaccaria", realm="Vaccaria", attitude=50,
                   personality="Warm, organised, socially sharp; manages the household and the guest lists.",
                   goals="Make Vaccaria welcome and well-liked at court.", secret="Is friends with Sabine's ladies.",
                   views="Thinks Valen would be a good friend for the Prince."),
    "Fennick": dict(full="Fennick Moorlow", title="Envoy to the Imperial Council", realm="Vaccaria", attitude=50,
                    personality="Sly, observant diplomat; enjoys secrets and quiet deals.",
                    goals="Make Vaccaria the kingmaker in close votes.", secret="Knows Nyssal taps the table before he lies.",
                    views="Thinks Ilsaveth is the most dangerous person at court."),
    "Hesper": dict(full="Hesper Dunhorn", title="Envoy to the Imperial Council", realm="Vaccaria", attitude=50,
                   personality="Earnest, military-minded envoy; knows the Legions.",
                   goals="Keep Vaccaria on the right side of the Legions.", secret="Served with Korrach's auxilia once.",
                   views="Respects Decimar."),
}
RANK_TITLES = {4: "Magistrate", 5: "Knight-Warden", 6: "Captain of the Herd Guard", 7: "Archivist", 8: "Guildmaster",
               9: "Sergeant of the Guard", 10: "Herald", 11: "Yeoman", 12: "Herdhand"}
PRECEDENCE = ["the Empire", "Lucerna", "Velithra", "Karst Odun", "Khar-Dumeth", "Tor-Ilun", "Meridia", "Vaccaria"]
REALM_TITLE = {"the Empire": "the Empire", "Vaccaria": "the Principality of Vaccaria"}


def persona(who, kind=None, rank=None):
    if who in PEOPLE:
        return PEOPLE[who]
    title = RANK_TITLES.get(rank or 12, "Herdhand")
    return dict(full=who, title=title, realm="Vaccaria", attitude=40,
                personality="An ordinary cow-folk subject of Vaccaria: plain-spoken, a little in awe of the Prince, with everyday worries.",
                goals="A good harvest, fair treatment, a safe home.", secret="", views="Loyal to the Prince.")


# ---------------------------------------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------------------------------------
def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"people": {}, "decrees": []}


def save_state():
    os.makedirs(HOME, exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(state, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, STATE)


def mem(who, p=None):
    p = p or persona(who)
    return state["people"].setdefault(who, {"attitude": p["attitude"], "memories": []})


def remember(who, note, delta=0):
    m = mem(who)
    m["memories"] = (m["memories"] + [note])[-30:]
    m["attitude"] = max(-100, min(100, m["attitude"] + delta))


def feeling(a):
    if a >= 60: return "devoted to the Prince"
    if a >= 30: return "warm towards the Prince"
    if a >= 10: return "cordial towards the Prince"
    if a > -10: return "neutral towards the Prince"
    if a > -30: return "cool towards the Prince"
    if a > -60: return "hostile towards the Prince"
    return "an enemy of the Prince"


def system_prompt(who, kind=None, rank=None, extra=""):
    p = persona(who, kind, rank)
    m = mem(who, p)
    lines = [WORLD, "",
             f"You are {p['full']}, {p['title']} ({REALM_TITLE.get(p['realm'], p['realm'])}).",
             f"Personality: {p['personality']}", f"Goals: {p['goals']}"]
    if p.get("secret"):
        lines.append(f"Secret (never reveal it outright; it may colour what you say): {p['secret']}")
    lines.append(f"Opinions: {p['views']}")
    lines.append(f"You are {feeling(m['attitude'])} (attitude {m['attitude']} on a scale of -100 to 100).")
    if m["memories"]:
        lines.append("What you remember of your dealings with the Prince, oldest first:\n- " + "\n- ".join(m["memories"][-12:]))
    if state["decrees"]:
        lines.append("Recent council decisions:\n- " + "\n- ".join(
            f"{d['motion']}: {d['outcome']} ({d['tally']}); Vaccaria voted {d['prince']}" for d in state["decrees"][-6:]))
    lines += ["", STYLE]
    if extra:
        lines += ["", extra]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------------------------------------
cfg = {}
FAKE = False


def _call(messages, as_json, max_tokens):
    body = {"model": cfg.get("model", DEFAULT_MODEL), "messages": messages, "max_completion_tokens": max_tokens}
    if as_json:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + cfg["key"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def _fake(messages, as_json):
    last = messages[-1]["content"]
    if as_json:
        if '"vote"' in last:
            return json.dumps({"vote": random.choice(["aye", "nay", "abstain"]), "reason": "My realm's interest decides it."})
        if '"speakers"' in last:
            return json.dumps({"speakers": []})
        if '"outcome"' in last:
            return json.dumps({"outcome": "passed", "speech": "The council has spoken. So it shall be."})
        return json.dumps({"memory": "Spoke with the Prince.", "attitude_change": 1})
    return "(offline test) Words fit for the council, Highness. " + last[-60:].replace("\n", " ")


async def ask(messages, as_json=False, max_tokens=350):
    if FAKE:
        await asyncio.sleep(0.5)
        text = _fake(messages, as_json)
    else:
        try:
            text = await asyncio.to_thread(_call, messages, as_json, max_tokens)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"OpenAI said {e.code}: {detail}")
        except Exception as e:
            raise RuntimeError(f"Couldn't reach OpenAI: {e}")
    if as_json:
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.S)
            return json.loads(m.group(0)) if m else {}
    return text.strip().strip('"')


# ---------------------------------------------------------------------------------------------------------
# Talking to Minecraft
# ---------------------------------------------------------------------------------------------------------
class Game:
    def __init__(self, ws):
        self.ws = ws
        self.waiting = {}
        self.parts = {}
        self.done = set()

    async def command(self, line, wait=False):
        rid = str(uuid.uuid4())
        fut = None
        if wait:
            fut = asyncio.get_running_loop().create_future()
            self.waiting[rid] = fut
        await self.ws.send(json.dumps({"header": {"version": 1, "requestId": rid, "messagePurpose": "commandRequest",
                                                  "messageType": "commandRequest"},
                                       "body": {"version": 1, "commandLine": line, "origin": {"type": "player"}}}))
        if fut:
            try:
                return await asyncio.wait_for(fut, 5)
            finally:
                self.waiting.pop(rid, None)

    async def send(self, player, **msg):
        if player:
            msg["p"] = player
        enc = urllib.parse.quote(json.dumps(msg, ensure_ascii=False), safe="")
        pieces, i = [], 0
        while i < len(enc):
            j = min(i + 900, len(enc))
            if j < len(enc):
                if enc[j - 1] == "%": j -= 1
                elif enc[j - 2] == "%": j -= 2
            pieces.append(enc[i:j]); i = j
        mid = uuid.uuid4().hex[:8]
        for k, piece in enumerate(pieces):
            await self.command(f"scriptevent vaccaria:msg {mid}|{k}|{len(pieces)}|{piece}")

    def on_response(self, msg):
        fut = self.waiting.get(msg.get("header", {}).get("requestId"))
        if fut and not fut.done():
            fut.set_result(msg.get("body", {}))

    async def poll(self):
        """Read the add-on's outgoing messages from the players' tags."""
        try:
            body = await self.command("tag @a list", wait=True)
        except asyncio.TimeoutError:
            return []
        text = (body or {}).get("statusMessage", "")
        out = []
        for seq, i, n, chunk in re.findall(r"vq\.(\d+)\.(\d+)\.(\d+)\.([^\s,§]+)", text):
            if seq in self.done:
                continue
            box = self.parts.setdefault(seq, {})
            box[int(i)] = chunk
            if len(box) == int(n):
                self.done.add(seq)
                del self.parts[seq]
                await self.command(f"scriptevent vaccaria:ack {seq}")
                try:
                    out.append(json.loads(urllib.parse.unquote("".join(box[k] for k in range(int(n))))))
                except Exception as e:
                    print("couldn't read a message:", e)
        return out


# ---------------------------------------------------------------------------------------------------------
# One-on-one conversations
# ---------------------------------------------------------------------------------------------------------
talks = {}      # (player, who) -> {"history": [...], "last": time, "kind", "rank"}


async def on_talk(game, m):
    key = (m["p"], m["who"])
    t = talks.setdefault(key, {"history": [], "last": time.time(), "kind": m.get("kind"), "rank": m.get("rank")})
    t["last"] = time.time()
    t["history"].append({"role": "user", "content": m["text"]})
    await game.send(m["p"], t="wait", text=f"{m['who']} considers your words...")
    sysp = system_prompt(m["who"], t["kind"], t["rank"],
                         "You are speaking privately with the Prince of Vaccaria at the Imperial palace. Answer in 1 to 4 sentences.")
    try:
        reply = await ask([{"role": "system", "content": sysp}] + t["history"][-16:])
    except RuntimeError as e:
        t["history"].pop()
        await game.send(m["p"], t="reply", who=m["who"], text=f"§c{e}§r\n\nTry again in a moment.")
        return
    t["history"].append({"role": "assistant", "content": reply})
    print(f"[{m['who']}] {reply}")
    await game.send(m["p"], t="reply", who=m["who"], text=reply)


async def end_talk(key):
    t = talks.pop(key, None)
    if not t or not t["history"]:
        return
    who = key[1]
    transcript = "\n".join(("Prince: " if h["role"] == "user" else f"{who}: ") + h["content"] for h in t["history"])
    try:
        r = await ask([{"role": "system", "content": system_prompt(who, t["kind"], t["rank"])},
                       {"role": "user", "content": f"This private conversation has just ended:\n{transcript}\n\n"
                        "From your own point of view, write what you will remember of it and how it changed your opinion of "
                        "the Prince. Reply as JSON: {\"memory\": \"one or two sentences, mention any promise either of you made\", "
                        "\"attitude_change\": integer from -10 to 10}"}], as_json=True, max_tokens=200)
        remember(who, r.get("memory", "Spoke privately with the Prince."), int(r.get("attitude_change", 0)))
    except Exception as e:
        remember(who, "Spoke privately with the Prince.")
        print("memory:", e)
    save_state()
    print(f"[memory] {who}: attitude {mem(who)['attitude']}")


# ---------------------------------------------------------------------------------------------------------
# The council
# ---------------------------------------------------------------------------------------------------------
class Council:
    def __init__(self, game, player, motion, proposer, seats):
        self.game, self.player, self.motion, self.proposer = game, player, motion, proposer
        self.seats = sorted(seats, key=lambda s: PRECEDENCE.index(s["realm"]) if s["realm"] in PRECEDENCE else 99)
        self.chair = next((s["who"] for s in self.seats if s["realm"] == "the Empire"), None)
        self.transcript = []
        self.prince_said = []
        order = [s["who"] for s in self.seats if s["who"] != self.chair]
        first = next((s["who"] for s in self.seats if s["realm"] == proposer and s["who"] != self.chair), None)
        if first:
            order.remove(first); order.insert(0, first)
        self.queue = order[:]
        # Vaccaria takes the floor in its place in the order of precedence (or first, if it proposed the motion)
        if proposer == "Vaccaria":
            self.queue.insert(0, "@prince")
        else:
            self.queue.append("@prince")
        if self.chair:
            self.queue.append(self.chair)       # the chair gives a view before the vote
        self.stage = "debate"
        self.rebuttals = 0
        self.busy = False

    def title_of(self, who):
        p = persona(who)
        return f"{p['title']}, {REALM_TITLE.get(p['realm'], p['realm'])}"

    def context(self):
        present = ", ".join(f"{s['who']} for {s['realm']}" for s in self.seats) + ", and the Prince of Vaccaria"
        lines = [f"THE IMPERIAL COUNCIL IS IN SESSION. Present: {present}. Chair: {self.chair or 'the Herald, Sethiel'}.",
                 f"Motion before the council: \"{self.motion}\" (proposed by {self.proposer})."]
        if self.transcript:
            lines.append("What has been said so far:\n" + "\n".join(self.transcript[-14:]))
        return "\n".join(lines)

    async def speak(self, who, instruction):
        await self.game.send(self.player, t="wait", text=f"{who} rises to speak...")
        text = await ask([{"role": "system", "content": system_prompt(who)},
                          {"role": "user", "content": self.context() + "\n\n" + instruction}], max_tokens=300)
        self.transcript.append(f"{who}: {text}")
        print(f"[council] {who}: {text}")
        await self.game.send(self.player, t="speech", who=who, title=self.title_of(who), text=text)

    async def open(self):
        if self.chair:
            await self.speak(self.chair, "You chair this session. Open it in 2 or 3 sentences: put the motion before the "
                                         "council and invite the proposer to speak. Do not yet say how you will vote.")
        else:
            line = f"Sethiel the Herald strikes his staff. \"The council is in session. The motion: {self.motion}.\""
            self.transcript.append(line)
            await self.game.send(self.player, t="speech", who="", text=line)

    async def step(self):
        """Advance to the next speech, the Prince's turn, or the vote."""
        while self.queue:
            who = self.queue.pop(0)
            if who == "@prince":
                await self.game.send(self.player, t="floor",
                                     text=f"{self.chair or 'The Herald'} turns to you.\n\n\"The council recognises the Prince of Vaccaria.\"")
                return
            if who == self.chair and self.stage == "debate":
                await self.speak(who, "The debate is ending. As chair, give the Empire's view of the motion in 2 or 3 "
                                      "sentences, then say the council will now vote.")
                self.stage = "voting"
                return
            await self.speak(who, "It is your turn to speak to the motion. In 2 to 4 sentences, argue for what serves your "
                                  "realm and your goals. You may answer or name others who spoke before you.")
            return
        if self.stage == "debate":
            self.stage = "voting"
        await self.game.send(self.player, t="vote_call",
                             text=f"The motion:\n§6{self.motion}§r\n\nThe council votes. How does Vaccaria vote?")

    async def prince_speaks(self, text):
        self.transcript.append(f"The Prince of Vaccaria: {text}")
        self.prince_said.append(text)
        if self.rebuttals >= 4 or self.stage != "debate":
            return
        # someone may want to answer the Prince directly
        names = [s["who"] for s in self.seats]
        r = await ask([{"role": "system", "content": WORLD},
                       {"role": "user", "content": self.context() + "\n\nThe Prince has just spoken. Which ONE member "
                        f"of the council ({', '.join(names)}) would most want to answer him straight away, if anyone? Consider their "
                        "goals and temper. Reply as JSON: {\"speakers\": [name]} or {\"speakers\": []}"}], as_json=True, max_tokens=60)
        for who in r.get("speakers", [])[:1]:
            if who in names:
                self.rebuttals += 1
                if who in self.queue:
                    self.queue.remove(who)
                await self.speak(who, "Answer what the Prince of Vaccaria just said, in 1 to 3 sentences, as yourself.")
                return True

    async def vote(self, prince_vote):
        await self.game.send(self.player, t="wait", text="The council votes...")
        voters = [s["who"] for s in self.seats]

        async def one(who):
            try:
                r = await ask([{"role": "system", "content": system_prompt(who)},
                               {"role": "user", "content": self.context() + "\n\nThe council now votes on the motion. Vote as "
                                "your goals and alliances dictate. Reply as JSON: {\"vote\": \"aye\" or \"nay\" or \"abstain\", "
                                "\"reason\": \"one short sentence in your own voice\"}"}], as_json=True, max_tokens=120)
                v = str(r.get("vote", "abstain")).lower()
                return who, (v if v in ("aye", "nay", "abstain") else "abstain"), r.get("reason", "")
            except Exception:
                return who, "abstain", ""

        votes = list(await asyncio.gather(*(one(w) for w in voters)))
        votes.append(("Vaccaria", prince_vote, ""))
        ayes = sum(v == "aye" for _, v, _ in votes)
        nays = sum(v == "nay" for _, v, _ in votes)
        tally = f"{ayes} aye, {nays} nay, {len(votes) - ayes - nays} abstaining"
        if self.chair:
            r = await ask([{"role": "system", "content": system_prompt(self.chair)},
                           {"role": "user", "content": self.context() + f"\n\nThe votes: " +
                            "; ".join(f"{w}: {v}" for w, v, _ in votes) + f" ({tally}). As chair, declare the result. "
                            "Normally the majority decides; the Emperor (or his representative) may overrule only when the "
                            "motion threatens Imperial authority or the Treasury, and must say so. Reply as JSON: "
                            "{\"outcome\": \"passed\" or \"rejected\", \"speech\": \"2 or 3 sentences declaring it\"}"}],
                          as_json=True, max_tokens=200)
            outcome = "passed" if str(r.get("outcome", "")).lower().startswith("pass") else "rejected"
            closing = r.get("speech", "")
        else:
            outcome = "passed" if ayes > nays else "rejected"
            closing = f"Sethiel the Herald announces: \"The motion is {outcome}.\""
        lines = [f"§6{self.motion}§r", ""]
        for w, v, reason in votes:
            colour = {"aye": "§2", "nay": "§4"}.get(v, "§7")
            lines.append(f"{colour}{v.upper()}§r  {w if w != 'Vaccaria' else 'You, for Vaccaria'}" + (f" §7- {reason}§r" if reason else ""))
        lines += ["", f"{tally}.", "", closing, "", f"§lThe motion is {outcome.upper()}.§r"]
        await self.game.send(self.player, t="result", title="The Council Decides", text="\n".join(lines))
        print(f"[council] {self.motion}: {outcome} ({tally})")
        await self.record(votes, outcome, tally, prince_vote)

    async def record(self, votes, outcome, tally, prince_vote):
        state["decrees"] = (state["decrees"] + [{"motion": self.motion, "outcome": outcome, "tally": tally,
                                                 "prince": prince_vote, "time": int(time.time())}])[-40:]
        said = ""
        if self.prince_said:
            try:
                said = await ask([{"role": "system", "content": WORLD},
                                  {"role": "user", "content": "Summarise in one sentence what the Prince of Vaccaria argued at "
                                   "council:\n" + "\n".join(self.prince_said)}], max_tokens=80)
            except Exception:
                said = ""
        for who, v, _ in votes:
            if who == "Vaccaria":
                continue
            delta = 0
            if prince_vote != "abstain" and v != "abstain":
                delta = 4 if v == prince_vote else -4
            if persona(who)["realm"] == self.proposer:
                delta *= 2
            remember(who, f"At council on \"{self.motion}\" ({outcome}), I voted {v} and the Prince voted {prince_vote}."
                          + (f" He argued: {said}" if said else ""), delta)
        save_state()

    async def adjourn(self):
        if self.prince_said:
            for s in self.seats:
                remember(s["who"], f"The council on \"{self.motion}\" was adjourned without a vote.")
            save_state()


councils = {}


async def on_council(game, m):
    c = councils.get(m["p"])
    if not c:
        await game.send(m["p"], t="notice", text="§eThe bridge has no council in session. Convene it again from the Ledger.")
        return
    if c.busy:
        return
    c.busy = True
    try:
        act = m.get("action")
        if act == "adjourn":
            await c.adjourn()
            councils.pop(m["p"], None)
            await game.send(m["p"], t="notice", text="§6The council is adjourned.")
        elif act == "speak":
            answered = await c.prince_speaks(m.get("text", ""))
            if not answered:
                await c.step()
        elif act == "vote":
            councils.pop(m["p"], None)
            await c.vote(m.get("vote", "abstain"))
        else:
            await c.step()
    except RuntimeError as e:
        await game.send(m["p"], t="speech", who="", text=f"§c{e}§r\n\nPress Continue to try again.")
    finally:
        c.busy = False


async def on_convene(game, m):
    c = Council(game, m["p"], m["motion"], m.get("proposer", "Vaccaria"), m.get("seats", []))
    councils[m["p"]] = c
    c.busy = True
    try:
        await c.open()
    except RuntimeError as e:
        await game.send(m["p"], t="speech", who="", text=f"§c{e}§r\n\nPress Continue to try again.")
    finally:
        c.busy = False


# ---------------------------------------------------------------------------------------------------------
# The connection
# ---------------------------------------------------------------------------------------------------------
async def dispatch(game, m):
    kind = m.get("t")
    try:
        if kind == "ping":
            await game.send(m["p"], t="notice", text="§aThe bridge hears you. The court is ready to talk.")
        elif kind == "talk":
            await on_talk(game, m)
        elif kind == "bye":
            await end_talk((m["p"], m["who"]))
        elif kind == "convene":
            await on_convene(game, m)
        elif kind == "council":
            await on_council(game, m)
    except Exception as e:
        print("error handling", kind, ":", e)


async def handler(ws, *_):
    game = Game(ws)
    print("Minecraft connected.")

    async def reader():
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("header", {}).get("messagePurpose") == "commandResponse":
                game.on_response(msg)

    async def loop():
        last_hello = 0
        while True:
            if time.time() - last_hello > 8:
                await game.command("scriptevent vaccaria:hello up")
                last_hello = time.time()
            for m in await game.poll():
                asyncio.create_task(dispatch(game, m))
            for key in [k for k, t in talks.items() if time.time() - t["last"] > 300]:
                asyncio.create_task(end_talk(key))      # conversations left hanging for five minutes are remembered
            await asyncio.sleep(0.4)

    tasks = [asyncio.create_task(reader()), asyncio.create_task(loop())]
    await game.command("scriptevent vaccaria:hello up")
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        for key in list(talks):
            await end_talk(key)
        print("Minecraft disconnected. Waiting for /connect again...")


def setup(args):
    global cfg, FAKE
    os.makedirs(HOME, exist_ok=True)
    try:
        cfg = json.load(open(CONFIG))
    except Exception:
        cfg = {}
    FAKE = args.fake
    if args.model:
        cfg["model"] = args.model
    if args.new_key or (not FAKE and not cfg.get("key")):
        key = getpass.getpass("Paste your OpenAI API key (it won't show) and press Enter: ").strip()
        if not key:
            sys.exit("No key given. Run with --fake to try it without one.")
        cfg["key"] = key
    json.dump(cfg, open(CONFIG, "w"))
    try:
        os.chmod(CONFIG, 0o600)
    except OSError:
        pass


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Vaccaria bridge running ({'offline test mode' if FAKE else cfg.get('model', DEFAULT_MODEL)}).")
        print(f"In Minecraft type:  /connect localhost:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fake", action="store_true", help="canned replies, no API key needed")
    ap.add_argument("--model", help=f"OpenAI model to use (default {DEFAULT_MODEL}; remembered)")
    ap.add_argument("--new-key", action="store_true", help="enter a different API key")
    args = ap.parse_args()
    setup(args)
    state = load_state()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        save_state()
        print("Bridge stopped.")
