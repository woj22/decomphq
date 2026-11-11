#!/usr/bin/env python3
"""Reference implementation (oracle) of the PROJECT.md §3 judgement model and §4/§6 prototype formulas.

Pure stdlib. The Engine's `judgement/scoring.gd` must produce the same numbers as this module for the same inputs.
It reads the real case data in game/data/cases, so the tests below also check the content.

    python3 tools/scoring_ref.py          # run the self-tests (§3.3 table, §10.8 playthroughs, gate, Order, pay)

Model summary (§3.2):
  Merit per case = max(0, Diligence + Verdict + Grounds)
  Diligence = floor(3 * key facts found / key facts authored)
  Verdict   = clear/contested: +4 upheld (verdict == G), -2 overturned; ambiguous (or G abstain): +4 if ground side == verdict else 0
  Grounds   = +2 if the cited (discovered) fact's side == verdict, else 0
  G         = sign of the tally of the fully corrected record (all discoveries applied); 0 -> abstain
"""
import json
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE_DIR = os.path.join(ROOT, "game", "data", "cases")
CONFIG_PATH = os.path.join(ROOT, "game", "data", "config.json")

SCORING_DEFAULTS = {"diligence_max": 3, "verdict_upheld": 4, "verdict_overturned": -2,
                    "verdict_ambiguous_ground_match": 4, "ground_match": 2, "merit_floor": 0}


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_case(case_id):
    with open(os.path.join(CASE_DIR, case_id + ".json")) as f:
        return json.load(f)


def sign_side(n):
    return "heaven" if n > 0 else "hell" if n < 0 else None


def verdict_of_tally(t):
    return "heaven" if t > 0 else "hell" if t < 0 else "abstain"


# --------------------------------------------------------------------------- record maths
def base_record(case):
    """{entry_id: weight} for visible entries; hidden entries are kept aside."""
    return {e["id"]: e["weight"] for e in case["entries"]}


def apply_ops(case, record, ops):
    """Apply discovery ops to a record dict in place. Returns the tally delta."""
    hidden = {h["id"]: h["weight"] for h in case.get("hidden", [])}
    before = sum(record.values())
    for op in ops:
        kind, entry = op["op"], op["entry"]
        if kind == "void":
            record[entry] = 0
        elif kind == "reweight":
            record[entry] = op["weight"]
        elif kind == "reveal":
            record[entry] = hidden[entry]
        else:
            raise ValueError("unknown case op %r" % kind)
    return sum(record.values()) - before


def corrected_tally(case):
    rec = base_record(case)
    for d in case.get("discoveries", []):
        apply_ops(case, rec, d["ops"])
    return sum(rec.values())


def filed_tally(case):
    return sum(base_record(case).values())


def guideline(case):
    return verdict_of_tally(corrected_tally(case))


def discovery_side(case, disc):
    """Side of a discovery's fact: sign of the tally change of its ops in isolation (authored side if no change)."""
    rec = base_record(case)
    delta = apply_ops(case, rec, disc["ops"])
    return sign_side(delta) or disc.get("fact", {}).get("side")


def key_total(case):
    n = sum(1 for d in case.get("discoveries", []) if d.get("key"))
    n += sum(1 for q in case.get("questions", []) if q.get("fact", {}).get("key"))
    return n


# --------------------------------------------------------------------------- desk simulation
class Desk:
    """A player's state on one case: archives held, links, questions, discoveries, facts, Composure."""

    def __init__(self, case, composure=3):
        self.case = case
        self.record = base_record(case)
        self.held = set()
        self.asked = []
        self.discovered = []
        self.facts = {}          # fact_id -> {"side":, "key":}
        self.composure = composure
        self.wrong_links = 0

    # -- conditions (case-local subset used by `requires`)
    def check(self, cond):
        op = cond["op"]
        if op == "discovered":
            return cond["id"] in self.discovered
        if op == "asked":
            return cond["id"] in self.asked
        if op == "holds_archive":
            return cond["id"] in self.held
        if op == "not":
            return not self.check(cond["of"])
        if op == "any":
            return any(self.check(c) for c in cond["of"])
        raise ValueError("condition %r not evaluable on the desk" % op)

    def check_all(self, conds):
        return all(self.check(c) for c in conds or [])

    def visible(self, entry_id):
        return entry_id in self.record

    def tally(self):
        return sum(self.record.values())

    # -- discoveries
    def _discover(self, disc):
        if disc["id"] in self.discovered:
            return False
        self.discovered.append(disc["id"])
        apply_ops(self.case, self.record, disc["ops"])
        self.facts[disc["id"]] = {"side": discovery_side(self.case, disc), "key": bool(disc.get("key"))}
        return True

    def _fire(self, kind, value):
        for d in self.case.get("discoveries", []):
            for t in d["triggers"]:
                if kind in t and t[kind] == value:
                    self._discover(d)

    # -- actions
    def available_archives(self):
        return [a["id"] for a in self.case.get("archive", [])
                if a["id"] not in self.held and self.check_all(a.get("requires"))]

    def visit_pell(self):
        """give_archive{}: every available, un-held doc of this case. Returns the ids received."""
        got = self.available_archives()
        for arc in got:
            self.receive(arc)
        return got

    def receive(self, arc_id):
        """give_archive_one: no requires check (used by the correction)."""
        if arc_id in self.held:
            return
        self.held.add(arc_id)
        self._fire("archive", arc_id)

    def link(self, entry_id, arc_id):
        """True if the pair is an authored discrepancy; a wrong link costs 1 Composure."""
        if not self.visible(entry_id) or arc_id not in self.held:
            raise ValueError("cannot select %s / %s" % (entry_id, arc_id))
        for d in self.case.get("discoveries", []):
            for t in d["triggers"]:
                if t.get("link") == [entry_id, arc_id]:
                    self._discover(d)
                    return True
        self.wrong_links += 1
        self.composure = max(0, self.composure - 1)
        return False

    def can_ask(self, q):
        if q["id"] in self.asked or not self.check_all(q.get("requires")):
            return False
        if self.composure <= 0:
            return False     # at 0 the soul stops answering (ASK disabled)
        return True

    def ask(self, qid):
        q = next(q for q in self.case["questions"] if q["id"] == qid)
        if not self.can_ask(q):
            raise ValueError("cannot ask %s" % qid)
        if q["kind"] == "general":
            self.composure -= 1
        self.asked.append(qid)
        if "fact" in q:
            f = q["fact"]
            self.facts[f["id"]] = {"side": f["side"], "key": bool(f.get("key"))}
        self._fire("question", qid)

    def ask_everything(self):
        """Ask every question as it becomes available (general ones while Composure lasts)."""
        progress = True
        while progress:
            progress = False
            for q in self.case["questions"]:
                if self.can_ask(q):
                    self.ask(q["id"])
                    progress = True

    def key_found(self):
        return sum(1 for f in self.facts.values() if f["key"])

    def best_ground(self, verdict):
        """A ground whose side matches the verdict (key facts first), else None."""
        match = [fid for fid, f in self.facts.items() if f["side"] == verdict]
        match.sort(key=lambda fid: not self.facts[fid]["key"])
        return match[0] if match else None


def score(case, desk, verdict, ground=None, scoring=None):
    """Score one stamped verdict. `ground` is a discovered fact id or None ("No ground")."""
    s = dict(SCORING_DEFAULTS, **(scoring or {}))
    if verdict not in ("heaven", "hell"):
        raise ValueError(verdict)
    if ground is not None and ground not in desk.facts:
        raise ValueError("ground %r is not a discovered fact" % ground)
    total = key_total(case)
    diligence = (s["diligence_max"] * desk.key_found()) // total if total else 0
    g = guideline(case)
    ambiguous = case["type"] == "ambiguous" or g == "abstain"
    gside = desk.facts[ground]["side"] if ground else None
    if ambiguous:
        sound, label = True, "noted"
        vpts = s["verdict_ambiguous_ground_match"] if gside == verdict else 0
    else:
        sound = verdict == g
        label = "upheld" if sound else "overturned"
        vpts = s["verdict_upheld"] if sound else s["verdict_overturned"]
    gpts = s["ground_match"] if gside == verdict else 0
    merit = max(s["merit_floor"], diligence + vpts + gpts)
    return {"case": case["id"], "verdict": verdict, "guideline": g, "diligence": diligence, "verdict_pts": vpts,
            "ground_pts": gpts, "merit": merit, "sound": sound, "label": label,
            "overturned": label == "overturned", "key_found": desk.key_found(), "key_total": total,
            "known_tally": desk.tally()}


# --------------------------------------------------------------------------- gate, Order, pay
def promotion_gate(merit, overturned, processed, found_violet_ink, promo=None):
    """PROJECT §4: 'correction' if the violet ink was missed, else 'pass' or 'reissue'."""
    p = promo or {"cases_processed": 6, "merit_min": 30, "overturned_max": 2}
    if not found_violet_ink:
        return "correction"
    if processed >= p["cases_processed"] and merit >= p["merit_min"] and overturned <= p["overturned_max"]:
        return "pass"
    return "reissue"


def order_value(sound, unsound, queue, resolved, unresolved, o=None):
    o = o or {"start": 68, "per_sound": 2, "per_unsound": -5, "queue_threshold": 30, "per_queue_over": -1,
              "per_resolved": 4, "per_unresolved": -4, "min": 0, "max": 100}
    v = (o["start"] + o["per_sound"] * sound + o["per_unsound"] * unsound
         + o["per_queue_over"] * max(0, queue - o["queue_threshold"])
         + o["per_resolved"] * resolved + o["per_unresolved"] * unresolved)
    return max(o["min"], min(o["max"], v))


def shift_pay(processed, sound, unsound, base=8, p=None):
    p = p or {"per_processed": 1, "per_sound": 1, "per_unsound": -2, "accuracy_bonus": 3, "accuracy_threshold": 0.8}
    accuracy = (sound / processed) if processed else 0.0
    bonus = p["accuracy_bonus"] if accuracy >= p["accuracy_threshold"] else 0
    return base + p["per_processed"] * processed + p["per_sound"] * sound + p["per_unsound"] * unsound + bonus


# --------------------------------------------------------------------------- playthrough profiles (§10.8)
def play(case_id, script, verdict, ground="auto"):
    """script: list of ('pell',) | ('link', entry, arc) | ('ask', q) | ('ask_all',).
    verdict: 'heaven' | 'hell' | 'tally' (Rubric on the known record).
    ground: 'auto' (best matching fact) | None | fact id."""
    case = load_case(case_id)
    desk = Desk(case)
    for step in script:
        if step[0] == "pell":
            desk.visit_pell()
        elif step[0] == "link":
            desk.link(step[1], step[2])
        elif step[0] == "ask":
            desk.ask(step[1])
        elif step[0] == "ask_all":
            desk.ask_everything()
        else:
            raise ValueError(step)
    if verdict == "tally":
        verdict = verdict_of_tally(desk.tally())
        assert verdict != "abstain"
    if ground == "auto":
        ground = desk.best_ground(verdict)
    return score(case, desk, verdict, ground), desk


FULL = {
    "case_s001": [("pell",), ("ask_all",)],
    "case_s002": [("pell",), ("link", "r1", "arc_002a"), ("ask_all",)],
    "case_s003": [("pell",), ("ask_all",)],
    "case_s004": [("pell",), ("link", "r2", "arc_004a"), ("ask_all",)],
    "case_s007": [("pell",), ("link", "r4", "arc_007a"), ("ask_all",), ("pell",)],
    "case_s008": [("pell",), ("link", "r2", "arc_008a"), ("link", "r1", "arc_008b"), ("ask_all",)],
}
ORDER = ["case_s001", "case_s002", "case_s003", "case_s004", "case_s007", "case_s008"]

PROFILES = {
    "perfect": {c: (FULL[c], "guideline", "auto") for c in ORDER},
    "attentive": {
        "case_s001": ([], "heaven", None),
        "case_s002": (FULL["case_s002"], "hell", "auto"),
        "case_s003": ([("pell",)], "heaven", "auto"),
        "case_s004": ([("ask", "q2")], "heaven", "auto"),
        "case_s007": ([("pell",), ("link", "r4", "arc_007a")], "hell", "auto"),
        "case_s008": (FULL["case_s008"], "heaven", "auto"),
    },
    "half_diligent": {
        "case_s001": ([], "heaven", None),
        "case_s002": (FULL["case_s002"], "hell", "auto"),
        "case_s003": ([("pell",), ("ask", "q3")], "heaven", "auto"),
        "case_s004": ([], "tally", None),
        "case_s007": ([], "tally", None),
        "case_s008": (FULL["case_s008"], "heaven", "auto"),
    },
    "rubric_only": {c: ([("ask_all",)], "tally", "auto") for c in ORDER},
    "careless": {c: ([], "tally", None) for c in ORDER},
}


def run_profile(name):
    results = []
    for c in ORDER:
        script, verdict, ground = PROFILES[name][c]
        if verdict == "guideline":
            verdict = guideline(load_case(c))
        res, desk = play(c, script, verdict, ground)
        res["desk"] = desk
        results.append(res)
    return results


# --------------------------------------------------------------------------- tests
class Section33(unittest.TestCase):
    """Every row of the PROJECT §3.3 table."""

    def test_tallies(self):
        want = {"case_s001": (3, 3), "case_s002": (2, -4), "case_s003": (-2, 1), "case_s004": (-5, 1),
                "case_s005": (0, -1), "case_s006": (1, -1), "case_s007": (5, 1), "case_s008": (-4, 3)}
        for cid, (filed, corr) in want.items():
            case = load_case(cid)
            self.assertEqual(filed_tally(case), filed, cid)
            self.assertEqual(corrected_tally(case), corr, cid)

    def row(self, cid, script, verdict, ground, merit, label, key=None, known=None):
        res, desk = play(cid, script, verdict, ground)
        self.assertEqual(res["merit"], merit, (cid, script, res))
        self.assertEqual(res["label"], label, (cid, script, res))
        if key is not None:
            self.assertEqual((res["key_found"], res["key_total"]), key)
        if known is not None:
            self.assertEqual(res["known_tally"], known)
        self.assertEqual(desk.wrong_links, 0)
        return res

    def test_s002(self):
        r = self.row("case_s002", [("pell",), ("link", "r1", "arc_002a")], "hell", "d_two_ledgers", 9, "upheld", (2, 2))
        self.assertEqual((r["diligence"], r["verdict_pts"], r["ground_pts"]), (3, 4, 2))
        r = self.row("case_s002", [("pell",)], "hell", "d_two_ledgers", 7, "upheld", (1, 2), known=-1)
        self.assertEqual((r["diligence"], r["verdict_pts"], r["ground_pts"]), (1, 4, 2))
        r = self.row("case_s002", [], "heaven", None, 0, "overturned", (0, 2), known=2)
        self.assertEqual((r["diligence"], r["verdict_pts"], r["ground_pts"]), (0, -2, 0))

    def test_s004(self):
        self.row("case_s004", [("pell",), ("link", "r2", "arc_004a")], "heaven", "d_enemy_boy", 9, "upheld", (2, 2))
        r = self.row("case_s004", [("ask", "q2")], "hell", "d_enemy_boy", 0, "overturned", (1, 2), known=-2)
        self.assertEqual((r["diligence"], r["verdict_pts"], r["ground_pts"]), (1, -2, 0))
        self.row("case_s004", [("ask", "q2")], "heaven", "d_enemy_boy", 7, "upheld", (1, 2), known=-2)

    def test_s007(self):
        full = FULL["case_s007"]
        self.row("case_s007", full, "heaven", "d_widows", 9, "noted", (3, 3))
        self.row("case_s007", full, "hell", "d_kell", 9, "noted", (3, 3))
        r = self.row("case_s007", full, "heaven", "d_kell", 3, "noted", (3, 3))
        self.assertEqual((r["diligence"], r["verdict_pts"], r["ground_pts"]), (3, 0, 0))
        self.row("case_s007", [], "heaven", None, 0, "noted", (0, 3))

    def test_s008(self):
        self.row("case_s008", [("pell",), ("link", "r2", "arc_008a"), ("link", "r1", "arc_008b")],
                 "heaven", "d_violet_ink", 9, "upheld", (3, 3))
        r = self.row("case_s008", [("pell",)], "hell", None, 0, "overturned", (1, 3), known=-1)
        self.assertEqual((r["diligence"], r["verdict_pts"], r["ground_pts"]), (1, -2, 0))

    def test_guidelines_and_sides(self):
        self.assertEqual([guideline(load_case(c)) for c in ORDER], ["heaven", "hell", "heaven", "heaven", "heaven", "heaven"])
        c7 = load_case("case_s007")
        sides = {d["id"]: discovery_side(c7, d) for d in c7["discoveries"]}
        self.assertEqual(sides, {"d_false_name": "hell", "d_kell": "hell", "d_widows": "heaven"})

    def test_wrong_link_costs_composure(self):
        desk = Desk(load_case("case_s002"))
        desk.visit_pell()
        self.assertFalse(desk.link("r2", "arc_002a"))
        self.assertEqual((desk.composure, desk.wrong_links), (2, 1))

    def test_composure_zero_disables_ask(self):
        desk = Desk(load_case("case_s001"))
        for q in ("q1", "q2", "q3"):
            desk.ask(q)
        self.assertEqual(desk.composure, 0)


class Section108(unittest.TestCase):
    """The five reference playthroughs (PROJECT §10.8)."""

    WANT = {
        "perfect": ([9, 9, 9, 9, 9, 9], 54, 0, "pass"),
        "attentive": ([4, 9, 7, 7, 7, 9], 43, 0, "pass"),
        "half_diligent": ([4, 9, 9, 0, 0, 9], 31, 1, "pass"),
        "rubric_only": ([9, 0, 0, 0, 0, 0], 9, 4, "correction"),
        "careless": ([4, 0, 0, 0, 0, 0], 4, 4, "correction"),
    }

    def test_profiles(self):
        for name, (per_case, total, overturned, outcome) in self.WANT.items():
            res = run_profile(name)
            self.assertEqual([r["merit"] for r in res], per_case, name)
            self.assertEqual(sum(r["merit"] for r in res), total, name)
            self.assertEqual(sum(r["overturned"] for r in res), overturned, name)
            found_ink = "d_violet_ink" in res[-1]["desk"].discovered
            self.assertEqual(promotion_gate(total, overturned, 6, found_ink), outcome, name)
            for r in res:
                self.assertEqual(r["desk"].wrong_links, 0, name)
                self.assertGreaterEqual(r["desk"].composure, 0, name)

    def test_correction_then_reissue(self):
        """rubric-only and careless: Pell's correction (arc_008a given, S-008 re-stamped), then the gate reissues."""
        for name in ("rubric_only", "careless"):
            res = run_profile(name)
            desk = res[-1]["desk"]
            first = res[-1]
            desk.receive("arc_008a")                       # give_archive_one{case_s008, arc_008a}
            self.assertTrue(desk.link("r2", "arc_008a"))   # the correction
            verdict = verdict_of_tally(desk.tally())
            ground = desk.best_ground(verdict) if name == "rubric_only" else None
            again = score(load_case("case_s008"), desk, verdict, ground)
            merit = sum(r["merit"] for r in res) - first["merit"] + again["merit"]
            overturned = sum(r["overturned"] for r in res) - first["overturned"] + again["overturned"]
            self.assertEqual(promotion_gate(merit, overturned, 6, True), "reissue", (name, merit, overturned))

    def test_gate_thresholds(self):
        self.assertEqual(promotion_gate(30, 2, 6, True), "pass")
        self.assertEqual(promotion_gate(29, 0, 6, True), "reissue")
        self.assertEqual(promotion_gate(54, 3, 6, True), "reissue")
        self.assertEqual(promotion_gate(54, 0, 5, True), "reissue")
        self.assertEqual(promotion_gate(54, 0, 6, False), "correction")

    def test_gate_matches_config(self):
        p = load_config()["promotion"]
        self.assertEqual((p["cases_processed"], p["merit_min"], p["overturned_max"]), (6, 30, 2))


class Section6(unittest.TestCase):
    def test_order_example(self):
        # attentive player, shift 1, 3 sound, incident resolved: 68 + 6 + 4 = 78 before queue penalty
        self.assertEqual(order_value(3, 0, 24, 1, 0), 78)
        self.assertEqual(order_value(0, 0, 24, 0, 0), 68)
        self.assertEqual(order_value(0, 2, 35, 0, 1), 68 - 10 - 5 - 4)
        self.assertEqual(order_value(0, 20, 24, 0, 0), 0)

    def test_pay_example(self):
        self.assertEqual(shift_pay(3, 3, 0), 17)          # 8 + 3 + 3 + 3
        self.assertEqual(12 + shift_pay(3, 3, 0), 29)
        self.assertEqual(shift_pay(3, 2, 1), 8 + 3 + 2 - 2)  # accuracy 67 % < 80 %: no bonus
        self.assertEqual(shift_pay(3, 3, 0, base=12), 21)


if __name__ == "__main__":
    unittest.main(verbosity=1)
