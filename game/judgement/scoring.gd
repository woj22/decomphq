class_name Scoring
extends RefCounted
## Pure, static scoring model (PROJECT §3.2, ruling C05). No autoload access.

const HEAVEN := "heaven"
const HELL := "hell"
const PURGATORY := "purgatory" ## DEFERRED: the soul stays in the fortress
const ABSTAIN := "abstain"


static func side_of(v: int) -> String:
	if v > 0:
		return HEAVEN
	if v < 0:
		return HELL
	return ABSTAIN


static func _entries(case_data: Dictionary) -> Array:
	return case_data.get("entries", []) as Array


static func _hidden(case_data: Dictionary) -> Array:
	return case_data.get("hidden", []) as Array


static func find_discovery(case_data: Dictionary, did: String) -> Dictionary:
	for d: Dictionary in case_data.get("discoveries", []):
		if str(d.get("id", "")) == did:
			return d
	return {}


static func find_question(case_data: Dictionary, qid: String) -> Dictionary:
	for q: Dictionary in case_data.get("questions", []):
		if str(q.get("id", "")) == qid:
			return q
	return {}


static func find_archive(case_data: Dictionary, aid: String) -> Dictionary:
	for a: Dictionary in case_data.get("archive", []):
		if str(a.get("id", "")) == aid:
			return a
	return {}


static func _base_weight(case_data: Dictionary, entry_id: String) -> int:
	for e: Dictionary in _entries(case_data):
		if str(e.get("id", "")) == entry_id:
			return int(e.get("weight", 0))
	for h: Dictionary in _hidden(case_data):
		if str(h.get("id", "")) == entry_id:
			return int(h.get("weight", 0))
	return 0


## Builds the current record: entry_id -> {id, tag, text, ink, weight, filed_weight, visible, voided, reweighted, revealed}.
## `discoveries` = ids of discoveries made (in order).
static func record(case_data: Dictionary, discoveries: Array) -> Array:
	var rows: Array = []
	var index := {}
	for e: Dictionary in _entries(case_data):
		var r := {"id": str(e.get("id", "")), "tag": str(e.get("tag", "neutral")), "text": str(e.get("text", "")),
			"ink": str(e.get("ink", "black")), "weight": int(e.get("weight", 0)), "filed_weight": int(e.get("weight", 0)),
			"visible": true, "voided": false, "reweighted": false, "revealed": false, "hidden": false}
		index[r["id"]] = rows.size()
		rows.append(r)
	for h: Dictionary in _hidden(case_data):
		var r := {"id": str(h.get("id", "")), "tag": str(h.get("tag", "neutral")), "text": str(h.get("text", "")),
			"ink": str(h.get("ink", "black")), "weight": int(h.get("weight", 0)), "filed_weight": int(h.get("weight", 0)),
			"visible": false, "voided": false, "reweighted": false, "revealed": false, "hidden": true}
		index[r["id"]] = rows.size()
		rows.append(r)
	for did: Variant in discoveries:
		var d := find_discovery(case_data, str(did))
		for op: Dictionary in d.get("ops", []):
			var eid := str(op.get("entry", ""))
			if not index.has(eid):
				continue
			var r: Dictionary = rows[index[eid]]
			match str(op.get("op", "")):
				"void":
					r["weight"] = 0
					r["voided"] = true
				"reweight":
					r["weight"] = int(op.get("weight", 0))
					r["reweighted"] = true
				"reveal":
					r["visible"] = true
					r["revealed"] = true
	return rows


static func tally_of(rows: Array) -> int:
	var t := 0
	for r: Dictionary in rows:
		if r["visible"]:
			t += int(r["weight"])
	return t


static func filed_tally(case_data: Dictionary) -> int:
	return tally_of(record(case_data, []))


static func known_tally(case_data: Dictionary, discoveries: Array) -> int:
	return tally_of(record(case_data, discoveries))


static func all_discovery_ids(case_data: Dictionary) -> Array:
	var out: Array = []
	for d: Dictionary in case_data.get("discoveries", []):
		out.append(str(d.get("id", "")))
	return out


static func corrected_tally(case_data: Dictionary) -> int:
	return tally_of(record(case_data, all_discovery_ids(case_data)))


## Guideline verdict G (Rubric on the fully corrected record).
static func guideline(case_data: Dictionary) -> String:
	return side_of(corrected_tally(case_data))


## Tally change caused by one discovery's ops, measured against filed weights.
static func discovery_delta(case_data: Dictionary, d: Dictionary) -> int:
	var delta := 0
	for op: Dictionary in d.get("ops", []):
		var eid := str(op.get("entry", ""))
		var base := _base_weight(case_data, eid)
		match str(op.get("op", "")):
			"void":
				delta -= base
			"reweight":
				delta += int(op.get("weight", 0)) - base
			"reveal":
				delta += base
	return delta


static func discovery_side(case_data: Dictionary, d: Dictionary) -> String:
	var s := side_of(discovery_delta(case_data, d))
	if s == ABSTAIN:
		var f: Dictionary = d.get("fact", {})
		var authored := str(f.get("side", ""))
		if authored == HEAVEN or authored == HELL:
			return authored
		return "none"
	return s


## All facts the player holds: discovery facts + question facts. Each {id, text, side, key, source}.
static func facts(case_data: Dictionary, discoveries: Array, asked: Array) -> Array:
	var out: Array = []
	var seen := {}
	for did: Variant in discoveries:
		var d := find_discovery(case_data, str(did))
		if d.is_empty():
			continue
		var f: Dictionary = d.get("fact", {})
		var fid := str(d.get("id", ""))
		if seen.has(fid):
			continue
		seen[fid] = true
		out.append({"id": fid, "text": str(f.get("text", fid)), "side": discovery_side(case_data, d),
			"key": bool(d.get("key", false)), "source": "discovery"})
	for qid: Variant in asked:
		var q := find_question(case_data, str(qid))
		if not q.has("fact") or not (q["fact"] is Dictionary):
			continue
		var f: Dictionary = q["fact"]
		var fid := str(f.get("id", "f_" + str(qid)))
		if seen.has(fid):
			continue
		seen[fid] = true
		var side := str(f.get("side", "none"))
		if side != HEAVEN and side != HELL:
			side = "none"
		out.append({"id": fid, "text": str(f.get("text", fid)), "side": side, "key": bool(f.get("key", false)), "source": "question"})
	return out


static func key_total(case_data: Dictionary) -> int:
	var n := 0
	for d: Dictionary in case_data.get("discoveries", []):
		if bool(d.get("key", false)):
			n += 1
	for q: Dictionary in case_data.get("questions", []):
		if q.get("fact") is Dictionary and bool((q["fact"] as Dictionary).get("key", false)):
			n += 1
	return n


static func fact_side(case_data: Dictionary, discoveries: Array, asked: Array, fact_id: String) -> String:
	for f: Dictionary in facts(case_data, discoveries, asked):
		if f["id"] == fact_id:
			return f["side"]
	return "none"


## Full scoring of a stamped verdict. `ground` = fact id or "" for "No ground".
static func score(case_data: Dictionary, discoveries: Array, asked: Array, verdict: String, ground: String) -> Dictionary:
	var g := guideline(case_data)
	var ctype := str(case_data.get("type", "clear"))
	var ambiguous := ctype == "ambiguous" or g == ABSTAIN
	var held := facts(case_data, discoveries, asked)
	var key_found := 0
	var ground_side := "none"
	for f: Dictionary in held:
		if f["key"]:
			key_found += 1
		if ground != "" and f["id"] == ground:
			ground_side = f["side"]
	var kt := key_total(case_data)
	var diligence := 0
	if kt > 0:
		diligence = int(floor(3.0 * key_found / kt))
	var verdict_pts := 0
	var sound := true
	var audit := "noted"
	var deferred := verdict == PURGATORY
	if deferred:
		# Not wrong, never Overturned - but it dodges the call: +2 on an ambiguous case, -1 on a clear/contested one.
		verdict_pts = 2 if ambiguous else -1
		audit = "deferred"
	elif ambiguous:
		verdict_pts = 4 if ground_side == verdict else 0
	else:
		if verdict == g:
			verdict_pts = 4
			audit = "upheld"
		else:
			verdict_pts = -2
			audit = "overturned"
			sound = false
	var ground_pts := 2 if (ground != "" and ground_side == verdict and not deferred) else 0
	var ground_label := "none"
	if ground != "" and not deferred:
		ground_label = "sound" if ground_side == verdict else "unsound"
	var merit := maxi(0, diligence + verdict_pts + ground_pts)
	var conscience := 0
	if deferred:
		conscience = 0
	elif ambiguous:
		conscience = 1 if verdict == HEAVEN else -1
	elif verdict != g:
		conscience = 1 if verdict == HEAVEN else -1
	return {"guideline": g, "type": ctype, "ambiguous": ambiguous, "key_found": key_found, "key_total": kt,
		"diligence": diligence, "verdict_pts": verdict_pts, "ground_pts": ground_pts, "merit": merit, "sound": sound,
		"audit": audit, "ground": ground, "ground_side": ground_side, "ground_label": ground_label, "verdict": verdict,
		"overturned": audit == "overturned", "deferred": deferred, "favour_gilt": 1 if verdict == HEAVEN else 0,
		"favour_ember": 1 if verdict == HELL else 0, "conscience": conscience}


## PROJECT §6 Order formula.
static func order_value(start: int, sound: int, unsound: int, queue: int, resolved: int, unresolved: int, queue_free: int = 30,
		adj: int = 0) -> int:
	return clampi(start + 2 * sound - 5 * unsound - maxi(0, queue - queue_free) + 4 * resolved - 4 * unresolved + adj, 0, 100)


## PROJECT §6 pay formula (per shift).
static func pay_value(base: int, processed: int, sound: int, unsound: int, accuracy_bonus: int = 3, accuracy_threshold: float = 0.8) -> int:
	var pay := base + processed + sound - 2 * unsound
	if processed > 0 and float(sound) / float(processed) >= accuracy_threshold:
		pay += accuracy_bonus
	return pay
