#!/usr/bin/env python3
"""Content validator for game/data (PROJECT §8.5, §9.7, §10; docs/CONTRACTS.md §2-§3).

    python3 tools/validate_content.py            # validate; exit 1 on any error
    python3 tools/validate_content.py --tests    # also run the scoring oracle self-tests (tools/scoring_ref.py)

Stdlib only. Checks: JSON shape, allowed ops and their arguments (tools/schemas/ops.json), dangling IDs, text budgets,
area grids, walkability/reachability of every spawn and interactable, door round trips, case tallies and guideline vs
`expected`, fact sides, key-fact reachability within Composure with zero wrong links, >= 2 facts per side on ambiguous
cases, dialogue graph integrity, flags read but never written, and the promotion gate numbers vs config.
"""
import itertools
import json
import os
import re
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "game", "data")
sys.path.insert(0, HERE)
import scoring_ref as sr  # noqa: E402  (shared record maths; also the Engine's scoring oracle)

with open(os.path.join(HERE, "schemas", "ops.json")) as _f:
    OPS = json.load(_f)
ENUM = OPS["enums"]

BUDGET = {"card": 80, "box": 140, "objective": 40, "answer_boxes": 3, "archive_cards": 3, "choices": 4,
          "questions": 4, "epilogue_boxes": 2, "key_facts": 3, "summary": 280, "card_title_words": 3}
PROTOTYPE_CASES = ["case_s001", "case_s002", "case_s003", "case_s004", "case_s007", "case_s008"]
M2_CASES = ["case_s005", "case_s006"]

errors, warnings = [], []


def err(where, msg):
    errors.append("%s: %s" % (where, msg))


def warn(where, msg):
    warnings.append("%s: %s" % (where, msg))


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        err(os.path.relpath(path, ROOT), "invalid JSON: %s" % e)
        return None


def load_dir(sub, prefix):
    out = {}
    d = os.path.join(DATA, sub)
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".json"):
            continue
        obj = load(os.path.join(d, name))
        if obj is None:
            continue
        where = "%s/%s" % (sub, name)
        if obj.get("id") != name[:-5]:
            err(where, "id %r does not match file name" % obj.get("id"))
        if not str(obj.get("id", "")).startswith(prefix):
            err(where, "id must start with %r" % prefix)
        out[obj.get("id")] = obj
    return out


def text_len(where, s, limit, what="text"):
    if not isinstance(s, str) or not s.strip():
        err(where, "%s missing or empty" % what)
        return
    if len(s) > limit:
        err(where, "%s is %d chars (> %d): %r" % (what, len(s), limit, s))


def boxes(where, v, max_boxes, what):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list) or not v:
        err(where, "%s must be a non-empty list of boxes" % what)
        return
    if len(v) > max_boxes:
        err(where, "%s has %d boxes (> %d)" % (what, len(v), max_boxes))
    for i, b in enumerate(v):
        text_len(where, b, BUDGET["box"], "%s[%d]" % (what, i))


# ----------------------------------------------------------------------------- ops
class Refs:
    """Everything an op can point at, collected during the walk and checked at the end."""

    def __init__(self):
        self.flags_read = {}      # flag -> where
        self.flags_written = set()
        self.stats = []           # (id, where)
        self.cases = []           # (case_id, where)
        self.case_items = []      # (kind, case_id, item_id, where)
        self.objectives = []
        self.dialogues = []
        self.areas = []
        self.spawns = []
        self.days = []
        self.items = []
        self.incidents = []


REFS = Refs()


def check_args(where, op, spec, kind):
    name = op.get("op")
    for k in op:
        if k != "op" and k not in spec:
            err(where, "%s op %r: unexpected argument %r" % (kind, name, k))
    for k, t in spec.items():
        if k not in op:
            err(where, "%s op %r: missing argument %r" % (kind, name, k))
            continue
        v = op[k]
        ok = {"str": isinstance(v, str), "int": isinstance(v, int) and not isinstance(v, bool),
              "num": isinstance(v, (int, float)) and not isinstance(v, bool), "bool": isinstance(v, bool),
              "any": True, "list": isinstance(v, list), "cond": isinstance(v, dict), "conds": isinstance(v, list),
              "case": isinstance(v, str)}[t]
        if not ok:
            err(where, "%s op %r: argument %r should be %s, got %r" % (kind, name, k, t, v))


def case_ref(where, cid):
    if cid != "$active_case":
        REFS.cases.append((cid, where))


def walk_conditions(where, conds):
    if conds is None:
        return
    if not isinstance(conds, list):
        err(where, "conditions must be a list")
        return
    for c in conds:
        walk_condition(where, c)


def walk_condition(where, c):
    if not isinstance(c, dict) or "op" not in c:
        err(where, "condition must be an object with 'op': %r" % (c,))
        return
    name = c["op"]
    if name not in OPS["conditions"]:
        err(where, "condition op %r is not allowed (CONTRACTS 3.1)" % name)
        return
    check_args(where, c, OPS["conditions"][name], "condition")
    if name in ("flag", "not_flag"):
        REFS.flags_read.setdefault(c.get("id"), where)
    elif name in ("stat_gte", "stat_lte"):
        REFS.stats.append((c.get("id"), where))
    elif name == "verdict":
        case_ref(where, c.get("case"))
        if c.get("value") not in ENUM["verdict"]:
            err(where, "verdict value %r" % c.get("value"))
    elif name == "case_state":
        case_ref(where, c.get("case"))
        if c.get("value") not in ENUM["case_state"]:
            err(where, "case_state value %r" % c.get("value"))
    elif name in ("discovered", "asked", "holds_archive"):
        case_ref(where, c.get("case"))
        REFS.case_items.append((name, c.get("case"), c.get("id"), where))
    elif name == "active_case_eq":
        case_ref(where, c.get("case"))
    elif name == "any":
        walk_conditions(where, c.get("of"))
    elif name == "not":
        walk_condition(where, c.get("of"))


def walk_effects(where, effs):
    if effs is None:
        return
    if not isinstance(effs, list):
        err(where, "effects must be a list")
        return
    for e in effs:
        if not isinstance(e, dict) or "op" not in e:
            err(where, "effect must be an object with 'op': %r" % (e,))
            continue
        name = e["op"]
        if name not in OPS["effects"]:
            err(where, "effect op %r is not allowed (CONTRACTS 3.2)" % name)
            continue
        check_args(where, e, OPS["effects"][name], "effect")
        if name == "set_flag":
            REFS.flags_written.add(e.get("id"))
        elif name == "set_npc_line_flag":
            REFS.flags_written.add(e.get("id"))
        elif name == "add_stat":
            REFS.stats.append((e.get("id"), where))
        elif name == "set_objective":
            REFS.objectives.append((e.get("id"), where))
        elif name == "start_dialogue":
            REFS.dialogues.append((e.get("id"), where))
        elif name in ("give_docket", "start_shift"):
            REFS.days.append((e.get("day"), where))
        elif name in ("give_archive_one",):
            case_ref(where, e.get("case"))
            REFS.case_items.append(("archive", e.get("case"), e.get("id"), where))
        elif name in ("reopen_case", "appeal_case"):
            case_ref(where, e.get("case"))
        elif name == "reset_cases":
            for cid in e.get("ids", []):
                case_ref(where, cid)
        elif name == "unlock_area":
            REFS.areas.append((e.get("id"), where))
        elif name == "teleport":
            REFS.spawns.append((e.get("area"), e.get("spawn"), where))
        elif name == "buy_item":
            REFS.items.append((e.get("id"), e.get("price"), where))
        elif name in ("start_incident", "resolve_incident"):
            REFS.incidents.append((e.get("id"), where))
        elif name == "show_card":
            text_len(where, e.get("title"), 40, "card title")
            text_len(where, e.get("text"), BUDGET["box"], "card text")
            if len(str(e.get("title", "")).split()) > BUDGET["card_title_words"]:
                err(where, "card title over %d words (blackletter budget)" % BUDGET["card_title_words"])


# ----------------------------------------------------------------------------- cases
CASE_FIELDS = ["id", "ref", "name", "age", "era", "place", "cause", "summary", "portrait", "type", "min_rank", "entries",
               "hidden", "archive", "discoveries", "questions", "expected", "epilogue", "verdicts", "ext"]


def check_case(cid, case):
    w = "cases/%s" % cid
    for k in CASE_FIELDS:
        if k not in case:
            err(w, "missing field %r" % k)
    for k in case:
        if k not in CASE_FIELDS:
            err(w, "unknown field %r (put extras in ext)" % k)
    if any(k not in case for k in ("entries", "hidden", "archive", "discoveries", "questions", "expected")):
        return
    if case["type"] not in ENUM["case_type"]:
        err(w, "type %r" % case["type"])
    text_len(w, case["summary"], BUDGET["summary"], "summary")
    if not isinstance(case.get("portrait"), dict) or "seed" not in case["portrait"] or "tags" not in case["portrait"]:
        err(w, "portrait must be {seed, tags}")
    want_rank = 2 if cid in M2_CASES else 1
    if case["min_rank"] != want_rank:
        err(w, "min_rank %r, expected %d" % (case["min_rank"], want_rank))

    ids = set()
    entry_ids, hidden_ids = set(), set()
    for e in case["entries"]:
        ew = "%s entry %s" % (w, e.get("id"))
        if not re.fullmatch(r"r\d+", str(e.get("id"))):
            err(ew, "entry ids are r1..rn")
        entry_ids.add(e.get("id"))
        if e.get("tag") not in ENUM["entry_tag"]:
            err(ew, "tag %r" % e.get("tag"))
        if not isinstance(e.get("weight"), int) or not -3 <= e["weight"] <= 3:
            err(ew, "weight must be an int in -3..3")
        if e.get("ink") not in ENUM["ink"]:
            err(ew, "ink %r" % e.get("ink"))
        text_len(ew, e.get("text"), BUDGET["card"])
        tag_sign = {"virtue": 1, "sin": -1, "neutral": 0}.get(e.get("tag"))
        if isinstance(e.get("weight"), int) and tag_sign is not None and (e["weight"] > 0) - (e["weight"] < 0) != tag_sign:
            err(ew, "tag %s disagrees with weight %d" % (e["tag"], e["weight"]))
    for h in case["hidden"]:
        hw = "%s hidden %s" % (w, h.get("id"))
        if not re.fullmatch(r"h\d+", str(h.get("id"))):
            err(hw, "hidden ids are h1..hn")
        hidden_ids.add(h.get("id"))
        if h.get("tag") not in ENUM["entry_tag"]:
            err(hw, "tag %r" % h.get("tag"))
        if not isinstance(h.get("weight"), int) or not -3 <= h["weight"] <= 3:
            err(hw, "weight must be an int in -3..3")
        text_len(hw, h.get("text"), BUDGET["card"])
    if len(case["entries"]) > 15:
        err(w, "more than 15 record cards (3 pages x 5)")

    arc_ids = set()
    for a in case["archive"]:
        aw = "%s archive %s" % (w, a.get("id"))
        if not re.fullmatch(r"arc_%s[a-z]?" % cid[-3:], str(a.get("id"))):
            err(aw, "archive ids are arc_%s[a-z]" % cid[-3:])
        arc_ids.add(a.get("id"))
        text_len(aw, a.get("title"), 40, "title")
        cards = a.get("cards", [])
        if not cards or len(cards) > BUDGET["archive_cards"]:
            err(aw, "needs 1..%d cards" % BUDGET["archive_cards"])
        for i, c in enumerate(cards):
            text_len(aw, c, BUDGET["card"], "card %d" % i)
        walk_conditions(aw, a.get("requires", []))

    q_ids = {q.get("id") for q in case["questions"]}
    disc_ids = set()
    fact_ids = []
    for d in case["discoveries"]:
        dw = "%s discovery %s" % (w, d.get("id"))
        if not str(d.get("id", "")).startswith("d_"):
            err(dw, "discovery ids start with d_")
        disc_ids.add(d.get("id"))
        fact_ids.append(d.get("id"))
        if not d.get("triggers"):
            err(dw, "needs at least one trigger")
        for t in d.get("triggers", []):
            if len(t) != 1:
                err(dw, "trigger must have exactly one of link/archive/question: %r" % t)
            if "link" in t:
                pair = t["link"]
                if not (isinstance(pair, list) and len(pair) == 2):
                    err(dw, "link must be [entry, arc]")
                    continue
                if pair[0] not in entry_ids | hidden_ids:
                    err(dw, "link entry %r unknown" % pair[0])
                if pair[1] not in arc_ids:
                    err(dw, "link archive %r unknown" % pair[1])
            elif "archive" in t:
                if t["archive"] not in arc_ids:
                    err(dw, "archive trigger %r unknown" % t["archive"])
            elif "question" in t:
                if t["question"] not in q_ids:
                    err(dw, "question trigger %r unknown" % t["question"])
            else:
                err(dw, "unknown trigger %r" % t)
        if not d.get("ops"):
            err(dw, "needs ops")
        for op in d.get("ops", []):
            if op.get("op") not in ENUM["case_op"]:
                err(dw, "case op %r" % op.get("op"))
                continue
            if op["op"] == "reveal" and op.get("entry") not in hidden_ids:
                err(dw, "reveal of non-hidden entry %r" % op.get("entry"))
            if op["op"] in ("void", "reweight") and op.get("entry") not in entry_ids | hidden_ids:
                err(dw, "%s of unknown entry %r" % (op["op"], op.get("entry")))
            if op["op"] == "reweight" and (not isinstance(op.get("weight"), int) or not -3 <= op["weight"] <= 3):
                err(dw, "reweight needs weight -3..3")
        fact = d.get("fact") or {}
        text_len(dw, fact.get("text"), BUDGET["card"], "fact")
        computed = sr.discovery_side(case, d) if all(o.get("op") in ENUM["case_op"] for o in d.get("ops", [])) else None
        if fact.get("side") is not None and fact.get("side") not in ENUM["side"]:
            err(dw, "fact side %r" % fact.get("side"))
        if computed is None:
            err(dw, "fact has no tally change and no authored side")
        elif fact.get("side") and fact["side"] != computed:
            err(dw, "authored side %s disagrees with computed side %s" % (fact["side"], computed))
        if not isinstance(d.get("key"), bool):
            err(dw, "key must be true/false")
        if "effects" in d:
            walk_effects(dw, d["effects"])

    if len(case["questions"]) > BUDGET["questions"]:
        err(w, "more than %d questions" % BUDGET["questions"])
    for q in case["questions"]:
        qw = "%s question %s" % (w, q.get("id"))
        if not re.fullmatch(r"q\d+", str(q.get("id"))):
            err(qw, "question ids are q1..qn")
        if q.get("kind") not in ENUM["question_kind"]:
            err(qw, "kind %r" % q.get("kind"))
        if q.get("kind") == "confront" and not q.get("requires"):
            err(qw, "confrontation question needs requires (unlocked by a discovery or earlier answer)")
        text_len(qw, q.get("text"), BUDGET["box"], "question text")
        boxes(qw, q.get("answer"), BUDGET["answer_boxes"], "answer")
        text_len(qw, q.get("card"), BUDGET["card"], "card")
        walk_conditions(qw, q.get("requires", []))
        if "fact" in q:
            f = q["fact"]
            for k in ("id", "text", "side", "key"):
                if k not in f:
                    err(qw, "fact missing %r" % k)
            text_len(qw, f.get("text"), BUDGET["card"], "fact")
            if f.get("side") not in ENUM["side"]:
                err(qw, "fact side %r" % f.get("side"))
            fact_ids.append(f.get("id"))
    for a in case["archive"]:
        for c in a.get("requires", []):
            pass
    dup = {x for x in fact_ids if fact_ids.count(x) > 1}
    if dup:
        err(w, "duplicate fact ids %s" % sorted(dup))
    all_ids = list(entry_ids) + list(hidden_ids) + list(arc_ids) + list(q_ids) + fact_ids
    if len(all_ids) != len(set(all_ids)):
        err(w, "case-internal ids collide")

    # every hidden entry must be revealable
    revealed = {o["entry"] for d in case["discoveries"] for o in d.get("ops", []) if o.get("op") == "reveal"}
    for h in hidden_ids - revealed:
        err(w, "hidden entry %s is never revealed" % h)

    # key facts
    kt = sr.key_total(case)
    if not 1 <= kt <= BUDGET["key_facts"]:
        err(w, "key facts must be 1..3, found %d" % kt)

    # tallies vs expected
    exp = case["expected"]
    filed, corr, g = sr.filed_tally(case), sr.corrected_tally(case), sr.guideline(case)
    if exp.get("tally_filed") != filed:
        err(w, "expected.tally_filed %r but computed %d" % (exp.get("tally_filed"), filed))
    if exp.get("tally_corrected") != corr:
        err(w, "expected.tally_corrected %r but computed %d" % (exp.get("tally_corrected"), corr))
    if exp.get("guideline") != g:
        err(w, "expected.guideline %r but computed %s" % (exp.get("guideline"), g))
    if case["type"] == "contested" and sr.verdict_of_tally(filed) == g and not case["discoveries"]:
        warn(w, "contested case with no discoveries")

    # epilogue and verdicts
    ep = case.get("epilogue", {})
    for side in ("heaven", "hell"):
        boxes("%s epilogue.%s" % (w, side), ep.get(side), BUDGET["epilogue_boxes"], "epilogue")
        walk_effects("%s verdicts.%s" % (w, side), (case.get("verdicts", {}).get(side) or {}).get("effects"))

    # local requires refer to own case
    for kind, c, item, where in list(REFS.case_items):
        pass

    check_case_reachability(cid, case)


def check_case_reachability(cid, case):
    """Every key fact reachable with 0 wrong links within Composure; ambiguous cases have >= 2 facts per side."""
    w = "cases/%s" % cid
    composure = 3
    generals = [q["id"] for q in case["questions"] if q["kind"] == "general"]
    link_pairs = [tuple(t["link"]) for d in case["discoveries"] for t in d["triggers"] if "link" in t]

    def closure(general_subset):
        desk = sr.Desk(case, composure)
        progress = True
        while progress:
            progress = False
            if desk.visit_pell():
                progress = True
            for e, a in link_pairs:
                disc = next(d for d in case["discoveries"] if {"link": [e, a]} in d["triggers"])
                if disc["id"] not in desk.discovered and desk.visible(e) and a in desk.held:
                    desk.link(e, a)
                    progress = True
            for q in case["questions"]:
                if q["kind"] == "general" and q["id"] not in general_subset:
                    continue
                if desk.can_ask(q):
                    desk.ask(q["id"])
                    progress = True
        return desk

    best = None
    for n in range(len(generals) + 1):
        for subset in itertools.combinations(generals, n):
            desk = closure(set(subset))
            if desk.key_found() == sr.key_total(case) and desk.wrong_links == 0:
                best = (n, desk)
                break
        if best:
            break
    if best is None:
        err(w, "not every key fact is reachable with 0 wrong links within %d Composure" % composure)
        return
    if best[0] > composure:
        err(w, "key facts need %d general questions (> Composure %d)" % (best[0], composure))
    # full closure: everything askable/discoverable
    desk = closure(set(generals))
    undisc = {d["id"] for d in case["discoveries"]} - set(desk.discovered)
    if undisc:
        err(w, "discoveries unreachable even with every question asked: %s" % sorted(undisc))
    if case["type"] == "ambiguous":
        facts = {}
        for d in case["discoveries"]:
            facts[d["id"]] = sr.discovery_side(case, d)
        for q in case["questions"]:
            if "fact" in q:
                facts[q["fact"]["id"]] = q["fact"]["side"]
        for side in ("heaven", "hell"):
            n = sum(1 for s in facts.values() if s == side)
            if n < 2:
                err(w, "ambiguous case has %d fact(s) on the %s side (need >= 2)" % (n, side))


# ----------------------------------------------------------------------------- areas
def legend_at(area, cell):
    for o in area.get("overrides", []):
        if o.get("cell") == list(cell):
            return o
    ch = area["grid"][cell[1]][cell[0]]
    return area["legend"].get(ch, {})


def walkable(area, cell):
    w, h = area["size"]
    x, y = cell
    if not (0 <= x < w and 0 <= y < h):
        return False
    lg = legend_at(area, cell)
    kind = lg.get("kind")
    if lg.get("h_hu", 0):
        return False
    if kind in ("floor", "decal"):
        return not lg.get("solid", False)
    if kind == "queue":
        return lg.get("walkable", True)
    if kind == "seat":
        return not lg.get("solid", False)
    return False


def bfs(area, start):
    seen = {tuple(start)}
    dq = deque([tuple(start)])
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in seen and walkable(area, n):
                seen.add(n)
                dq.append(n)
    return seen


def in_bounds(area, cell):
    return (isinstance(cell, list) and len(cell) == 2 and 0 <= cell[0] < area["size"][0] and 0 <= cell[1] < area["size"][1])


def check_area(aid, area, npcs, dialogues, areas):
    w = "areas/%s" % aid
    for k in ("id", "name", "size", "ambience", "backdrop", "grid", "legend", "floor", "windows", "decor", "objects", "spawns", "zones"):
        if k not in area:
            err(w, "missing %r" % k)
    if "grid" not in area or "size" not in area:
        return
    W, H = area["size"]
    if len(area["grid"]) != H:
        err(w, "grid has %d rows, size says %d" % (len(area["grid"]), H))
        return
    for i, row in enumerate(area["grid"]):
        if len(row) != W:
            err(w, "grid row %d has %d chars, size says %d" % (i, len(row), W))
            return
        for ch in row:
            if ch not in area["legend"]:
                err(w, "grid char %r (row %d) not in legend" % (ch, i))
    for ch, lg in area["legend"].items():
        if lg.get("kind") not in ENUM["legend_kind"]:
            err(w, "legend %r kind %r" % (ch, lg.get("kind")))
    # far walls / kerbs
    for x in range(W):
        if legend_at(area, (x, H - 1)).get("kind") not in ("kerb", "door", "wall"):
            err(w, "last row must be kerb/door at column %d" % x)
    for y in range(H - 1):
        if legend_at(area, (W - 1, y)).get("kind") not in ("kerb", "door", "wall"):
            err(w, "last column must be kerb/door/wall at row %d" % y)
    if area.get("backdrop") not in ENUM["backdrop"]:
        err(w, "backdrop %r" % area.get("backdrop"))
    for win in area.get("windows", []):
        if not in_bounds(area, win.get("cell")) or legend_at(area, win["cell"]).get("kind") != "wall":
            err(w, "window %r not on a wall cell" % win)
        if win.get("glass") not in ENUM["glass"]:
            err(w, "window glass %r" % win.get("glass"))
    for d in area.get("decor", []):
        if not in_bounds(area, d.get("cell")) or not d.get("sprite"):
            err(w, "bad decor %r" % d)
    spawns = area.get("spawns", {})
    if "default" not in spawns:
        err(w, "needs a default spawn")
    start = spawns.get("default")
    reach = bfs(area, start) if start and walkable(area, start) else set()
    for name, cell in spawns.items():
        if not in_bounds(area, cell) or not walkable(area, cell):
            err(w, "spawn %s %r is not walkable" % (name, cell))
        elif tuple(cell) not in reach:
            err(w, "spawn %s %r unreachable from default" % (name, cell))
    obj_ids = set()
    for o in area.get("objects", []):
        ow = "%s object %s" % (w, o.get("id"))
        if o.get("id") in obj_ids:
            err(ow, "duplicate object id")
        obj_ids.add(o.get("id"))
        if o.get("type") not in ENUM["object_type"]:
            err(ow, "type %r" % o.get("type"))
        if not in_bounds(area, o.get("cell")):
            err(ow, "cell out of bounds")
            continue
        walk_conditions(ow, o.get("conditions"))
        uc = o.get("use_cell")
        if uc is not None and o.get("via"):
            pass  # reached through another object (e.g. the stair climb); that object's use_cell is checked
        elif uc is not None:
            if not in_bounds(area, uc) or not walkable(area, uc):
                err(ow, "use_cell %r not walkable" % uc)
            elif tuple(uc) not in reach and o.get("type") != "soul_door":
                err(ow, "use_cell %r unreachable from the default spawn" % uc)
        else:
            err(ow, "needs a use_cell")
        if "facing" in o and o["facing"] not in ENUM["facing"]:
            err(ow, "facing %r" % o["facing"])
        t = o.get("type")
        if t in ("door", "soul_door"):
            if legend_at(area, o["cell"]).get("kind") != "door":
                err(ow, "door object not on a 'D' cell")
            if o.get("style") not in ENUM["door_style"]:
                err(ow, "style %r" % o.get("style"))
        if t in ("door", "stair"):
            to = o.get("to") or {}
            if to.get("area") not in areas:
                err(ow, "door target area %r unknown" % to.get("area"))
            elif to.get("spawn") not in areas[to["area"]].get("spawns", {}):
                err(ow, "door target spawn %r missing in %s" % (to.get("spawn"), to.get("area")))
        if t == "soul_door" and o.get("verdict") not in ENUM["verdict"]:
            err(ow, "soul_door needs verdict heaven/hell")
        if t in ("npc", "hatch"):
            if o.get("npc") not in npcs:
                err(ow, "npc %r unknown" % o.get("npc"))
        if t == "inspect":
            if o.get("dialogue") not in dialogues and o.get("npc") not in npcs:
                err(ow, "inspect needs a known dialogue (or npc)")
        if "locked_dialogue" in o and o["locked_dialogue"] not in dialogues:
            err(ow, "locked_dialogue %r unknown" % o["locked_dialogue"])
        if t == "stair":
            for c in o.get("cells", []) + o.get("climb", []):
                if not in_bounds(area, c):
                    err(ow, "stair cell %r out of bounds" % c)
            for c in o.get("cells", []):
                if legend_at(area, c).get("kind") != "stair":
                    err(ow, "stair cell %r is not 's'" % c)
            if len(o.get("climb", [])) != len(o.get("climb_h_hu", [])):
                err(ow, "climb and climb_h_hu lengths differ")
    # every D cell has a door object
    door_cells = {tuple(o["cell"]) for o in area.get("objects", []) if o.get("type") in ("door", "soul_door")}
    for y, row in enumerate(area["grid"]):
        for x, ch in enumerate(row):
            if area["legend"].get(ch, {}).get("kind") == "door" and (x, y) not in door_cells:
                err(w, "door cell (%d,%d) has no door object" % (x, y))
    for zid, z in area.get("zones", {}).items():
        for c in z.get("cells", []):
            if not in_bounds(area, c):
                err(w, "zone %s cell %r out of bounds" % (zid, c))
        if "head" in z and z["head"] not in z.get("cells", []):
            err(w, "zone %s head not in its cells" % zid)
    return obj_ids


# ----------------------------------------------------------------------------- dialogue / npcs
SPECIAL_SPEAKERS = {"player", "narrator", "$soul"}


def check_dialogue(did, d, npcs):
    w = "dialogue/%s" % did
    nodes = d.get("nodes", {})
    if d.get("start") not in nodes:
        err(w, "start %r is not a node" % d.get("start"))
        return
    for nid, n in nodes.items():
        nw = "%s node %s" % (w, nid)
        sp = n.get("speaker")
        if sp not in SPECIAL_SPEAKERS and sp not in npcs:
            err(nw, "speaker %r unknown" % sp)
        walk_conditions(nw, n.get("conditions"))
        walk_effects(nw, n.get("effects"))
        if "choices" in n:
            ch = n["choices"]
            if not ch or len(ch) > BUDGET["choices"]:
                err(nw, "1..%d choices" % BUDGET["choices"])
            for c in ch:
                text_len(nw, c.get("text"), 60, "choice text")
                if c.get("next") != "end" and c.get("next") not in nodes:
                    err(nw, "choice next %r missing" % c.get("next"))
                walk_conditions(nw, c.get("conditions"))
                walk_effects(nw, c.get("effects"))
            if all(c.get("conditions") for c in ch):
                warn(nw, "every choice is conditional; the menu may be empty")
            if "text" in n:
                text_len(nw, n["text"], BUDGET["box"])
        else:
            text_len(nw, n.get("text"), BUDGET["box"])
            if n.get("next") != "end" and n.get("next") not in nodes:
                err(nw, "next %r missing" % n.get("next"))
        if "conditions" in n and n.get("else") != "end" and n.get("else") not in nodes:
            err(nw, "conditional node needs else (node id or 'end')")
    # reachability
    seen, dq = {d["start"]}, deque([d["start"]])
    while dq:
        n = nodes[dq.popleft()]
        nxt = [n.get("next"), n.get("else")] + [c.get("next") for c in n.get("choices", [])]
        for t in nxt:
            if t in nodes and t not in seen:
                seen.add(t)
                dq.append(t)
    for nid in set(nodes) - seen:
        err(w, "node %s unreachable" % nid)


def check_npc(nid, n, dialogues, areas):
    w = "npcs/%s" % nid
    for k in ("id", "name", "title", "sprite", "portrait", "dialogue"):
        if k not in n:
            err(w, "missing %r" % k)
    for i, entry in enumerate(n.get("dialogue", [])):
        if entry.get("id") not in dialogues:
            err(w, "dialogue %r unknown" % entry.get("id"))
        walk_conditions("%s dialogue[%d]" % (w, i), entry.get("conditions", []))
    lst = n.get("dialogue", [])
    if lst and lst[-1].get("conditions"):
        warn(w, "last dialogue entry is conditional; NPC may have nothing to say")
    home = n.get("home")
    if home and home.get("area") not in areas:
        err(w, "home area %r unknown" % home.get("area"))


# ----------------------------------------------------------------------------- main
def main():
    run_tests = "--tests" in sys.argv
    cases = load_dir("cases", "case_")
    areas = load_dir("areas", "area_")
    npcs = load_dir("npcs", "npc_")
    dialogues = load_dir("dialogue", "dlg_")
    config = load(os.path.join(DATA, "config.json")) or {}
    ranks = load(os.path.join(DATA, "ranks.json")) or {}
    triggers = load(os.path.join(DATA, "triggers.json")) or []
    objectives = load(os.path.join(DATA, "objectives.json")) or {}

    for cid in PROTOTYPE_CASES + M2_CASES:
        if cid not in cases:
            err("cases", "missing %s" % cid)
    for cid, c in cases.items():
        check_case(cid, c)

    for nid, n in npcs.items():
        check_npc(nid, n, dialogues, areas)
    for did, d in dialogues.items():
        check_dialogue(did, d, npcs)
    area_objects = {}
    for aid, a in areas.items():
        area_objects[aid] = check_area(aid, a, npcs, dialogues, areas) or set()
    for aid in ("area_clerks_court", "area_arrival_hall", "area_records_annexe", "area_booths", "area_adjudicator_chamber"):
        if aid not in areas:
            err("areas", "missing %s" % aid)
    if "area_clerks_court" in areas and areas["area_clerks_court"].get("backdrop") != "court":
        err("areas/area_clerks_court", "backdrop must be 'court'")
    # door round trips
    for aid, a in areas.items():
        for o in a.get("objects", []):
            if o.get("type") == "door" and (o.get("to") or {}).get("area") in areas:
                back = [b for b in areas[o["to"]["area"]].get("objects", [])
                        if b.get("type") in ("door", "stair") and (b.get("to") or {}).get("area") == aid]
                if not back:
                    err("areas/%s" % aid, "door %s has no way back from %s" % (o["id"], o["to"]["area"]))
    # every npc placed somewhere
    placed = {o.get("npc") for a in areas.values() for o in a.get("objects", [])}
    for nid in npcs:
        if nid not in placed:
            err("npcs/%s" % nid, "not placed in any area")
    # dialogues used
    used = {e.get("id") for n in npcs.values() for e in n.get("dialogue", [])}
    used |= {o.get("dialogue") for a in areas.values() for o in a.get("objects", [])}
    used |= {o.get("locked_dialogue") for a in areas.values() for o in a.get("objects", [])}
    used |= {d for d, _ in REFS.dialogues}
    # (start_dialogue refs inside triggers are walked below; recompute after)

    # triggers
    sig = ENUM["trigger_signals"]
    tids = set()
    if not isinstance(triggers, list):
        err("triggers.json", "must be a list")
        triggers = []
    for t in triggers:
        tw = "triggers/%s" % t.get("id")
        if t.get("id") in tids:
            err(tw, "duplicate id")
        tids.add(t.get("id"))
        if t.get("on") not in sig:
            err(tw, "signal %r not usable in triggers" % t.get("on"))
            continue
        for k, v in (t.get("match") or {}).items():
            if k not in sig[t["on"]]:
                err(tw, "match key %r not an argument of %s" % (k, t["on"]))
            if k == "case_id" and v not in cases:
                err(tw, "match case %r unknown" % v)
            if k == "area_id" and v not in areas:
                err(tw, "match area %r unknown" % v)
            if k == "dlg_id" and v not in dialogues:
                err(tw, "match dialogue %r unknown" % v)
            if k == "discovery_id":
                c = cases.get((t.get("match") or {}).get("case_id"), {})
                if v not in {d["id"] for d in c.get("discoveries", [])}:
                    err(tw, "match discovery %r unknown in its case" % v)
        if not isinstance(t.get("once"), bool):
            err(tw, "once must be true/false")
        walk_conditions(tw, t.get("conditions", []))
        walk_effects(tw, t.get("effects", []))
    used |= {d for d, _ in REFS.dialogues}
    for did in dialogues:
        if did not in used:
            err("dialogue/%s" % did, "never used (no NPC, object, trigger or start_dialogue refers to it)")

    # objectives
    for oid, o in objectives.items():
        ow = "objectives/%s" % oid
        if not oid.startswith("obj_"):
            err(ow, "ids start with obj_")
        text_len(ow, o.get("text"), BUDGET["objective"])
        tg = o.get("target") or {}
        if tg.get("area") not in areas:
            err(ow, "target area %r unknown" % tg.get("area"))
        elif tg.get("object") not in area_objects.get(tg["area"], set()):
            err(ow, "target object %r not in %s" % (tg.get("object"), tg.get("area")))

    # config / ranks
    for k in ("dockets", "promotion", "clock", "judgement", "scoring", "queue", "order", "pay", "items", "player", "incidents"):
        if k not in config:
            err("config.json", "missing %r" % k)
    dockets = config.get("dockets", {})
    for day, ids in dockets.items():
        for cid in ids:
            if cid not in cases:
                err("config.json", "docket %s case %r unknown" % (day, cid))
            elif int(day) <= 2 and cases[cid]["min_rank"] != 1:
                err("config.json", "docket %s case %r has min_rank > 1" % (day, cid))
    # Days 1-2 are the rank-1 prototype and must hold exactly its six cases; later days are rank 2+ content.
    if sorted(c for d, ids in dockets.items() if int(d) <= 2 for c in ids) != sorted(PROTOTYPE_CASES):
        err("config.json", "dockets for days 1-2 must hold exactly the six prototype cases")
    want = {("clock", "costs"): {"door": 5, "question_general": 10, "question_confront": 5, "archive": 15, "link": 0, "verdict": 20}}
    costs = config.get("clock", {}).get("costs", {})
    for k, v in want[("clock", "costs")].items():
        if costs.get(k) != v:
            err("config.json", "clock cost %s = %r, PROJECT §2 says %d" % (k, costs.get(k), v))
    exact = [("judgement", "composure", 3), ("queue", "arrival_start", 16), ("queue", "bench_start", 8), ("queue", "bench_cap", 12),
             ("order", "start", 68), ("pay", "purse_start", 12), ("promotion", "merit_min", 30), ("promotion", "overturned_max", 2),
             ("promotion", "cases_processed", 6), ("player", "speed_cells_per_s", 3.0), ("player", "interaction_radius_cells", 1.5)]
    for sec, key, v in exact:
        if config.get(sec, {}).get(key) != v:
            err("config.json", "%s.%s = %r, spec says %r" % (sec, key, config.get(sec, {}).get(key), v))
    if config.get("items", {}).get("item_desk_lamp", {}).get("price") != 20:
        err("config.json", "desk lamp must cost 20")
    for day, notes in (config.get("ledger_notes") or {}).items():
        for i, n in enumerate(notes):
            text_len("config.json ledger_notes.%s[%d]" % (day, i), n.get("text"), BUDGET["box"])
            walk_conditions("config.json ledger_notes.%s[%d]" % (day, i), n.get("conditions", []))
    for iid, inc in (config.get("incidents") or {}).items():
        iw = "config.json incidents.%s" % iid
        if inc.get("npc") not in npcs:
            err(iw, "npc unknown")
        if inc.get("area") not in areas:
            err(iw, "area unknown")
        elif inc.get("object") not in area_objects.get(inc["area"], set()):
            err(iw, "object unknown")
    stat_ids = {s.get("id") for s in ranks.get("stats", [])}
    for sid in ("merit", "order", "purse", "queue", "overturned", "cases_processed", "favour_gilt", "favour_ember", "conscience"):
        if sid not in stat_ids:
            err("ranks.json", "missing stat %r" % sid)
    for r in ranks.get("ranks", []):
        walk_conditions("ranks.json rank %s" % r.get("rank"), r.get("requires", []))
        walk_effects("ranks.json rank %s" % r.get("rank"), r.get("on_reach", []))

    # promotion gate in triggers must equal config
    promo = config.get("promotion", {})
    gate = next((t for t in triggers if t.get("id") == "trg_gate_pass"), None)
    if not gate:
        err("triggers.json", "missing trg_gate_pass")
    else:
        c = {(x["op"], x.get("id")): x.get("value") for x in gate["conditions"]}
        if c.get(("stat_gte", "merit")) != promo.get("merit_min"):
            err("triggers/trg_gate_pass", "merit threshold differs from config.promotion")
        if c.get(("stat_lte", "overturned")) != promo.get("overturned_max"):
            err("triggers/trg_gate_pass", "overturned threshold differs from config.promotion")
        if c.get(("stat_gte", "cases_processed")) != promo.get("cases_processed"):
            err("triggers/trg_gate_pass", "processed threshold differs from config.promotion")
        if ("flag", promo.get("flag")) not in c:
            err("triggers/trg_gate_pass", "gate does not check %s" % promo.get("flag"))
    if not any(e.get("op") == "set_flag" and e.get("id") == promo.get("flag")
               for e in (next((d for d in cases.get("case_s008", {}).get("discoveries", []) if d["id"] == "d_violet_ink"), {}) or {}).get("effects", [])):
        err("cases/case_s008", "d_violet_ink must set %s in its effects" % promo.get("flag"))

    # resolve collected references
    for cid, where in REFS.cases:
        if cid not in cases:
            err(where, "case %r unknown" % cid)
    for kind, cid, item, where in REFS.case_items:
        c = cases.get(cid)
        if not c:
            continue
        pool = {"discovered": {d["id"] for d in c["discoveries"]}, "asked": {q["id"] for q in c["questions"]},
                "holds_archive": {a["id"] for a in c["archive"]}, "archive": {a["id"] for a in c["archive"]}}[kind]
        if item not in pool:
            err(where, "%s %r not in %s" % (kind, item, cid))
    for oid, where in REFS.objectives:
        if oid not in objectives:
            err(where, "objective %r unknown" % oid)
    for did, where in REFS.dialogues:
        if did not in dialogues:
            err(where, "dialogue %r unknown" % did)
    for aid, where in REFS.areas:
        if aid not in areas:
            err(where, "area %r unknown" % aid)
    for aid, sp, where in REFS.spawns:
        if aid not in areas:
            err(where, "teleport area %r unknown" % aid)
        elif sp not in areas[aid].get("spawns", {}):
            err(where, "teleport spawn %r missing in %s" % (sp, aid))
    for day, where in REFS.days:
        if str(day) not in dockets:
            err(where, "day %r has no docket" % day)
    for sid, where in REFS.stats:
        if sid not in stat_ids:
            err(where, "stat %r not defined in ranks.json" % sid)
    for iid, price, where in REFS.items:
        item = config.get("items", {}).get(iid)
        if not item:
            err(where, "item %r not in config.items" % iid)
        elif item.get("price") != price:
            err(where, "price %r differs from config (%r)" % (price, item.get("price")))
    for iid, where in REFS.incidents:
        if iid not in (config.get("incidents") or {}):
            err(where, "incident %r not in config.incidents" % iid)
    for fl, where in REFS.flags_read.items():
        if fl not in REFS.flags_written:
            err(where, "flag %r is read but never set" % fl)

    # scoring oracle
    if run_tests:
        import unittest
        suite = unittest.defaultTestLoader.loadTestsFromModule(sr)
        res = unittest.TextTestRunner(verbosity=0, stream=sys.stdout).run(suite)
        if not res.wasSuccessful():
            err("tools/scoring_ref.py", "oracle tests failed")

    for wmsg in warnings:
        print("WARN  " + wmsg)
    for e in errors:
        print("ERROR " + e)
    print("validate_content: %d case(s), %d area(s), %d npc(s), %d dialogue(s), %d trigger(s), %d objective(s): %s"
          % (len(cases), len(areas), len(npcs), len(dialogues), len(triggers), len(objectives),
             "FAIL (%d errors)" % len(errors) if errors else "OK"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
