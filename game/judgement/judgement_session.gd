class_name JudgementSession
extends RefCounted
## Logic for one case at the desk (composure, questions, links, discoveries, archive, facts, verdict).
## All state lives in GameState.cases[case_id] so it persists when the player leaves the desk.

var case_id: String
var data: Dictionary


func _init(cid: String) -> void:
	case_id = cid
	data = Content.case(cid)


func rec() -> Dictionary:
	return GameState.case_rec(case_id)


func ctx() -> Dictionary:
	return {"case": case_id}


func composure() -> int:
	return int(rec().get("composure", 0))


func discoveries() -> Array:
	return rec()["discoveries"]


func asked() -> Array:
	return rec()["asked"]


func held_archive() -> Array:
	return rec()["archive"]


func record_rows() -> Array:
	return Scoring.record(data, discoveries())


func visible_rows() -> Array:
	var out: Array = []
	for r: Dictionary in record_rows():
		if r["visible"]:
			out.append(r)
	return out


func known_tally() -> int:
	return Scoring.known_tally(data, discoveries())


func facts() -> Array:
	return Scoring.facts(data, discoveries(), asked())


# ---------------------------------------------------------------- questions
func question_available(q: Dictionary) -> bool:
	return Conditions.check(q.get("requires", []), ctx())


## Unasked questions whose requirements pass (max 4 visible).
func open_questions() -> Array:
	var out: Array = []
	for q: Dictionary in data.get("questions", []):
		if asked().has(str(q.get("id", ""))):
			continue
		if question_available(q):
			out.append(q)
		if out.size() >= 4:
			break
	return out


func can_ask() -> bool:
	return composure() > 0


## Asks a question; returns {ok, answer:Array[String], discovery:Array} .
func ask(qid: String) -> Dictionary:
	var q := Scoring.find_question(data, qid)
	if q.is_empty() or asked().has(qid):
		return {"ok": false, "reason": "unknown"}
	if not question_available(q):
		return {"ok": false, "reason": "locked"}
	if composure() <= 0:
		return {"ok": false, "reason": "composure"}
	var general := str(q.get("kind", "general")) != "confront"
	if general:
		_set_composure(composure() - 1)
	asked().append(qid)
	var answer: Array = []
	var a: Variant = q.get("answer", [])
	if a is Array:
		for s: Variant in a:
			answer.append(str(s))
	elif a is String:
		answer.append(a)
	(rec()["answers"] as Dictionary)[qid] = answer
	Clock.advance(Content.clock_cost("question_general" if general else "question_confront"), "question")
	EventBus.question_asked.emit(case_id, qid)
	var found: Array = []
	for d: Dictionary in data.get("discoveries", []):
		for t: Variant in d.get("triggers", []):
			if t is Dictionary and str((t as Dictionary).get("question", "")) == qid:
				if discover(str(d.get("id", ""))):
					found.append(str(d.get("id", "")))
	Effects.apply(q.get("effects", []), ctx())
	return {"ok": true, "answer": answer, "discoveries": found, "general": general}


func _set_composure(v: int) -> void:
	rec()["composure"] = maxi(0, v)
	EventBus.composure_changed.emit(case_id, int(rec()["composure"]))


# ---------------------------------------------------------------- links
func entry_visible(eid: String) -> bool:
	for r: Dictionary in record_rows():
		if r["id"] == eid:
			return r["visible"]
	return false


## Links one record entry with one held archive document. Returns {ok, discovery, already}.
func link(entry_id: String, arc_id: String) -> Dictionary:
	if not entry_visible(entry_id) or not held_archive().has(arc_id):
		return {"ok": false, "invalid": true}
	(rec()["links"] as Array).append([entry_id, arc_id])
	for d: Dictionary in data.get("discoveries", []):
		for t: Variant in d.get("triggers", []):
			if not (t is Dictionary) or not (t as Dictionary).has("link"):
				continue
			var pair: Array = (t as Dictionary)["link"]
			if pair.size() >= 2 and str(pair[0]) == entry_id and str(pair[1]) == arc_id:
				var did := str(d.get("id", ""))
				var already := discoveries().has(did)
				if not already:
					discover(did)
				EventBus.link_attempted.emit(case_id, entry_id, arc_id, true)
				return {"ok": true, "discovery": did, "already": already}
	if composure() > 0:
		_set_composure(composure() - 1)
	EventBus.link_attempted.emit(case_id, entry_id, arc_id, false)
	return {"ok": false, "invalid": false}


# ---------------------------------------------------------------- archive
func available_archive() -> Array:
	var out: Array = []
	for a: Dictionary in data.get("archive", []):
		var aid := str(a.get("id", ""))
		if held_archive().has(aid):
			continue
		if Conditions.check(a.get("requires", []), ctx()):
			out.append(aid)
	return out


## Pell's "give_archive": every available document; +15 min if any. Returns ids received.
func request_archive() -> Array:
	var ids := available_archive()
	if ids.is_empty():
		return ids
	Clock.advance(Content.clock_cost("archive"), "archive")
	receive_archive(ids)
	return ids


func receive_archive(ids: Array) -> void:
	var got: Array = []
	for aid: Variant in ids:
		if Scoring.find_archive(data, str(aid)).is_empty() or held_archive().has(str(aid)):
			continue
		held_archive().append(str(aid))
		got.append(str(aid))
	if got.is_empty():
		return
	EventBus.archive_received.emit(case_id, got)
	for aid: Variant in got:
		for d: Dictionary in data.get("discoveries", []):
			for t: Variant in d.get("triggers", []):
				if t is Dictionary and str((t as Dictionary).get("archive", "")) == str(aid):
					discover(str(d.get("id", "")))


# ---------------------------------------------------------------- discoveries
func discover(did: String) -> bool:
	if did == "" or discoveries().has(did):
		return false
	var d := Scoring.find_discovery(data, did)
	if d.is_empty():
		return false
	discoveries().append(did)
	Effects.apply(d.get("effects", []), ctx())
	EventBus.discovery_made.emit(case_id, did)
	return true


## Lamp: the first file entry of a not-yet-found link pair (PROJECT §6 sink).
func lamp_entry() -> String:
	if not GameState.items.has("item_desk_lamp") and not GameState.items.has("item_lamp"):
		return ""
	for d: Dictionary in data.get("discoveries", []):
		if discoveries().has(str(d.get("id", ""))):
			continue
		for t: Variant in d.get("triggers", []):
			if t is Dictionary and (t as Dictionary).has("link"):
				return str(((t as Dictionary)["link"] as Array)[0])
	return ""


# ---------------------------------------------------------------- verdict
func stamp(verdict: String, ground: String) -> Dictionary:
	var result := Scoring.score(data, discoveries(), asked(), verdict, ground)
	result["case_id"] = case_id
	result["order_before"] = GameState.get_stat_i("order")
	GameState.record_verdict(case_id, result)
	Clock.advance(Content.clock_cost("verdict"), "verdict")
	var v: Variant = data.get("verdicts", {})
	if v is Dictionary and (v as Dictionary).get(verdict) is Dictionary:
		Effects.apply(((v as Dictionary)[verdict] as Dictionary).get("effects", []), ctx())
	GameState.recompute_derived()
	result["order_after"] = GameState.get_stat_i("order")
	result["order_delta"] = int(result["order_after"]) - int(result["order_before"])
	(rec()["result"] as Dictionary)["order_delta"] = result["order_delta"]
	SaveGame.autosave("verdict")
	return result


func epilogue(verdict: String) -> Array:
	if verdict == "purgatory" and not ((data.get("epilogue", {}) as Dictionary).has("purgatory")):
		var nm := str(data.get("name", "The soul"))
		return ["%s is issued a desk, a pen, and a file stamped DEFERRED." % nm,
			"Neither Gate will have them now. The Chancery always has room."]
	var e: Variant = data.get("epilogue", {})
	if not (e is Dictionary):
		return []
	var t: Variant = (e as Dictionary).get(verdict, "")
	if t is Array:
		return t
	if str(t) == "":
		return []
	return [str(t)]
