class_name CaseGen
extends RefCounted
## Procedural soul cases (owner request: "randomly generated from hundreds of different possibilities").
## Output is a case Dictionary in exactly the authored format (PROJECT §8.5), so the desk, scoring, appeals and
## DEFERRED all work unchanged. Deterministic from the case id, so saves only need ids.
##
## Every generated soul has 1-2 "twists" - a discrepancy between the file and the truth that the player can find:
##   inflated      a virtue that wasn't   (LINK entry <-> archive: reweight to 0)
##   hidden_sin    the archive reveals a buried sin
##   slander       a sin on the file that is false   (LINK: void)
##   hidden_virtue the archive reveals a hidden good deed
##   violet        a Room 0 forgery in violet ink (LINK to the original register: void) - story evidence for Pell

const PARTS_PATH := "res://data/procgen/case_parts.json"
const BUSTS := ["case_s001", "case_s002", "case_s003", "case_s004", "case_s007", "case_s008"]

static var _parts: Dictionary = {}


static func parts() -> Dictionary:
	if _parts.is_empty():
		var d: Variant = JsonUtil.load_file(PARTS_PATH)
		_parts = d if d is Dictionary else {}
	return _parts


static func _pick(rng: RandomNumberGenerator, a: Array) -> Variant:
	return a[rng.randi_range(0, a.size() - 1)]


static func _fmt(s: String, ctx: Dictionary) -> String:
	var out := s
	for k: String in ctx:
		out = out.replace("{" + k + "}", str(ctx[k]))
	return out


static func _card(t: String) -> String:
	var c := "\"" + t + "\""
	return c if c.length() <= 80 else c.substr(0, 78) + "\""


## `violet_chance`: probability that one twist is a Room 0 forgery (story evidence).
static func generate(id: String, violet_chance: float = 0.3) -> Dictionary:
	var p := parts()
	if p.is_empty():
		return {}
	var rng := RandomNumberGenerator.new()
	rng.seed = absi(id.hash()) + 7919
	var region: String = _pick(rng, (p["first"] as Dictionary).keys())
	var first: String = _pick(rng, p["first"][region])
	var last: String = _pick(rng, p["surname"][region])
	var town: String = _pick(rng, p["towns"][region])
	var trade: String = _pick(rng, p["trades"])
	var age := rng.randi_range(19, 89)
	var year := rng.randi_range(1640, 1990)
	var ctx := {"name": first + " " + last, "name_s": last, "town": town, "year": year, "age": age, "count": rng.randi_range(6, 40)}

	# -- twists
	var kinds := ["inflated", "hidden_sin", "slander", "hidden_virtue"]
	var chosen: Array = [_pick(rng, kinds)]
	if rng.randf() < 0.45:
		var second: String = _pick(rng, kinds)
		if second != chosen[0]:
			chosen.append(second)
	if rng.randf() < violet_chance:
		chosen[chosen.size() - 1] = "violet"

	var entries: Array = []
	var hidden: Array = []
	var archive: Array = []
	var discoveries: Array = []
	var questions: Array = []
	var used := {}
	var n := 0

	for spec: Array in [[p["virtues"], "virtue", 2], [p["sins"], "sin", 2]]:
		var got := 0
		var tries := 0
		while got < int(spec[2]) and tries < 20:
			tries += 1
			var item: Dictionary = _pick(rng, spec[0])
			var t := _fmt(str(item["text"]), ctx)
			if used.has(t):
				continue
			used[t] = true
			got += 1
			n += 1
			entries.append({"id": "r%d" % n, "tag": str(spec[1]), "weight": int(item["w"]), "ink": "black", "text": t})
	if rng.randf() < 0.6:
		n += 1
		entries.append({"id": "r%d" % n, "tag": "neutral", "weight": 0, "ink": "black", "text": _fmt(str(_pick(rng, p["neutral"])), ctx)})

	questions.append({"id": "q1", "kind": "general", "requires": [], "text": "Tell me about your life as a %s." % trade,
		"answer": [_fmt(str(_pick(rng, ["I worked. I paid my dues, mostly. Ask anyone in {town}.",
			"It was honest work, whatever they've written down there.", "Forty years of it. My hands still ache, if hands can.",
			"I did what the day needed. Nobody thanked me for it."])), ctx)], "card": "Describes a working life; defensive about the file."})

	var hn := 0
	for i in chosen.size():
		var kind: String = chosen[i]
		var t: Dictionary = _pick(rng, p["twists"][kind])
		var arc_id := "arc_g%d" % (i + 1)
		archive.append({"id": arc_id, "title": _fmt(str(t["title"]), ctx), "requires": [],
			"cards": (t["cards"] as Array).map(func(c: Variant) -> String: return _fmt(str(c), ctx))})
		var d := {"id": "d_%s" % kind, "key": true, "fact": {"text": _fmt(str(t["fact"]), ctx)}}
		if t.has("entry"):
			n += 1
			var eid := "r%d" % n
			var tag := "virtue" if int(t["w"]) > 0 else "sin"
			entries.append({"id": eid, "tag": tag, "weight": int(t["w"]), "ink": "violet" if kind == "violet" else "black",
				"text": _fmt(str(t["entry"]), ctx)})
			d["triggers"] = [{"link": [eid, arc_id]}]
			if kind == "inflated":
				d["ops"] = [{"op": "reweight", "entry": eid, "weight": 0}]
			else:
				d["ops"] = [{"op": "void", "entry": eid}]
		else:
			hn += 1
			var hid := "h%d" % hn
			hidden.append({"id": hid, "tag": "sin" if int(t["w"]) < 0 else "virtue", "weight": int(t["w"]), "text": _fmt(str(t["hidden"]), ctx)})
			d["triggers"] = [{"archive": arc_id}]
			d["ops"] = [{"op": "reveal", "entry": hid}]
		if kind == "violet":
			d["effects"] = [{"op": "add_stat", "id": "violet_evidence", "value": 1}, {"op": "set_flag", "id": "flag_found_violet_ink", "value": true}]
		discoveries.append(d)
		var qn := questions.size() + 1
		if i == 0:
			questions.append({"id": "q%d" % qn, "kind": "general", "requires": [], "text": _fmt(str(t["q"]), ctx),
				"answer": [_fmt(str(t["a"]), ctx)], "card": _card(_fmt(str(t["a"]), ctx))})
			qn += 1
		questions.append({"id": "q%d" % qn, "kind": "confront", "text": "About the %s." % _fmt(str(t["title"]), ctx).to_lower(),
			"requires": [{"op": "discovered", "case": id, "id": str(d["id"])}],
			"answer": [_fmt(str(t["conf"]), ctx)], "card": _card(_fmt(str(t["conf"]), ctx))})

	var data := {
		"id": id, "ref": "G-%04d" % (absi(id.hash()) % 10000), "name": ctx["name"], "age": age, "era": str(year),
		"place": "%s, %s" % [town, region.capitalize()], "cause": str(_pick(rng, p["causes"])),
		"summary": "%s of %s. %s" % [trade.capitalize(), town, str(_pick(rng, p["traits"]))],
		"portrait": {"seed": absi(id.hash()) % 100000, "tags": []}, "bust": BUSTS[absi(id.hash()) % BUSTS.size()],
		"type": "clear", "min_rank": 1, "generated": true,
		"entries": entries, "hidden": hidden, "archive": archive, "discoveries": discoveries, "questions": questions,
		"epilogue": {"heaven": [_fmt(str(_pick(rng, p["epilogue"]["heaven"])), ctx)],
			"hell": [_fmt(str(_pick(rng, p["epilogue"]["hell"])), ctx)]},
		"verdicts": {"heaven": {"effects": [{"op": "add_stat", "id": "favour_gilt", "value": 1}]},
			"hell": {"effects": [{"op": "add_stat", "id": "favour_ember", "value": 1}]}},
		"ext": {"twists": chosen}}
	var filed := Scoring.filed_tally(data)
	var corrected := Scoring.corrected_tally(data)
	var g := Scoring.guideline(data)
	data["type"] = "ambiguous" if corrected == 0 else ("contested" if Scoring.side_of(filed) != g else "clear")
	data["expected"] = {"tally_filed": filed, "tally_corrected": corrected, "guideline": g}
	# Rank 2 review: a junior clerk has already stamped it. Right ~55%, wrong ~30%, deferred ~15%.
	var juniors := ["Hob Tanner", "Edwina Pratt", "Lemuel Oakes", "Peg Dalloway", "Cyril Mott", "Agatha Quail", "Wilf Bramble",
		"Tamsin Reeve", "Ezekiel Gaunt", "Molly Crane", "Ned Pocock", "Ursula Fane"]
	var roll := rng.randf()
	var gv := g if g != "abstain" else ("heaven" if rng.randf() < 0.5 else "hell")
	var pv := gv if roll < 0.55 else ("purgatory" if roll >= 0.85 else ("hell" if gv == "heaven" else "heaven"))
	data["prior"] = {"verdict": pv, "by": "Junior clerk " + str(_pick(rng, juniors))}
	return data
