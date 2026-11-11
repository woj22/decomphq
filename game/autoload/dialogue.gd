extends Node
## Dialogue runner + single presentation queue for dialogues and modal screens (card, ledger, ceremony, summary).
## UI listens to the signals below; logic never references UI nodes.

signal line(speaker_id: String, speaker_name: String, text: String, portrait: String)
signal choices(items: Array)
signal closed(dlg_id: String)
signal modal_opened(kind: String, data: Dictionary)
signal modal_closed(kind: String, data: Dictionary)

var queue: Array = []
var current_kind := ""
var current_data: Dictionary = {}
var dlg_id := ""
var dlg: Dictionary = {}
var node_id := ""
var node: Dictionary = {}
var visible_choices: Array = []
var npc_context := ""
var _guard := 0


func busy() -> bool:
	return current_kind != "" or not queue.is_empty()


func in_dialogue() -> bool:
	return current_kind == "dialogue"


func clear() -> void:
	queue.clear()
	current_kind = ""
	current_data = {}
	dlg_id = ""
	dlg = {}
	node = {}
	node_id = ""
	visible_choices = []


## Start (or queue) a dialogue by id.
func request(id: String, npc_id: String = "") -> void:
	if id == "" or Content.dialogue(id).is_empty():
		push_warning("Dialogue '%s' not found" % id)
		return
	queue.append({"kind": "dialogue", "id": id, "npc": npc_id})
	_pump()


func request_modal(kind: String, data: Dictionary) -> void:
	queue.append({"kind": kind, "data": data})
	_pump()


## Picks the first dialogue of an NPC whose conditions pass.
func dialogue_for_npc(npc_id: String) -> String:
	var n := Content.npc(npc_id)
	for d: Variant in n.get("dialogue", []):
		if d is String:
			return d
		if d is Dictionary and Conditions.check((d as Dictionary).get("conditions", [])):
			return str((d as Dictionary).get("id", ""))
	return ""


func talk_to(npc_id: String) -> bool:
	var id := dialogue_for_npc(npc_id)
	if id == "":
		return false
	request(id, npc_id)
	return true


func _pump() -> void:
	if current_kind != "" or queue.is_empty():
		return
	var item: Dictionary = queue.pop_front()
	if item["kind"] == "dialogue":
		_begin(str(item["id"]), str(item.get("npc", "")))
	else:
		current_kind = str(item["kind"])
		current_data = item.get("data", {})
		modal_opened.emit(current_kind, current_data)


func modal_done() -> void:
	if current_kind == "" or current_kind == "dialogue":
		return
	var kind := current_kind
	var data := current_data
	current_kind = ""
	current_data = {}
	if kind == "ledger":
		GameState.sign_ledger()
	modal_closed.emit(kind, data)
	_pump()


func _begin(id: String, npc_id: String) -> void:
	current_kind = "dialogue"
	dlg_id = id
	dlg = Content.dialogue(id)
	npc_context = npc_id
	EventBus.dialogue_started.emit(id)
	var start := str(dlg.get("start", ""))
	var nodes: Dictionary = dlg.get("nodes", {})
	if start == "" or not nodes.has(start):
		start = "start" if nodes.has("start") else ("n1" if nodes.has("n1") else (str(nodes.keys()[0]) if nodes.size() > 0 else "end"))
	_guard = 0
	_goto(start)


func _goto(nid: String) -> void:
	_guard += 1
	if _guard > 500:
		push_error("Dialogue loop in " + dlg_id)
		_end()
		return
	var nodes: Dictionary = dlg.get("nodes", {})
	if nid == "" or nid == "end" or not nodes.has(nid):
		_end()
		return
	node_id = nid
	node = nodes[nid]
	if node.has("conditions") and not Conditions.check(node["conditions"]):
		_goto(str(node.get("else", "end")))
		return
	Effects.apply(node.get("effects", []))
	if current_kind != "dialogue":
		return
	visible_choices = []
	for i in (node.get("choices", []) as Array).size():
		var c: Dictionary = node["choices"][i]
		if Conditions.check(c.get("conditions", [])):
			visible_choices.append({"text": _subst(str(c.get("text", "..."))), "index": i})
	var text := _subst(str(node.get("text", "")))
	if text != "":
		var spk := str(node.get("speaker", "narrator"))
		var info := speaker_info(spk)
		EventBus.line_shown.emit(info["name"], text)
		line.emit(spk, info["name"], text, info["portrait"])
	if not visible_choices.is_empty():
		choices.emit(visible_choices)
	elif text == "":
		_goto(str(node.get("next", "end")))


func has_choices() -> bool:
	return current_kind == "dialogue" and not visible_choices.is_empty()


## Advance past a text node (no-op while choices are shown).
func advance() -> void:
	if current_kind != "dialogue" or not visible_choices.is_empty():
		return
	_goto(str(node.get("next", "end")))


## Choose among visible choices (index into the visible list).
func choose(i: int) -> void:
	if current_kind != "dialogue" or i < 0 or i >= visible_choices.size():
		return
	var c: Dictionary = node["choices"][int(visible_choices[i]["index"])]
	GameState.choices_log.append({"dlg": dlg_id, "node": node_id, "text": str(c.get("text", ""))})
	visible_choices = []
	Effects.apply(c.get("effects", []))
	if current_kind != "dialogue":
		return
	_goto(str(c.get("next", "end")))


func choice_effects(i: int) -> Array:
	if i < 0 or i >= visible_choices.size():
		return []
	var c: Dictionary = node["choices"][int(visible_choices[i]["index"])]
	return c.get("effects", [])


func _end() -> void:
	var id := dlg_id
	current_kind = ""
	dlg = {}
	node = {}
	node_id = ""
	visible_choices = []
	dlg_id = ""
	closed.emit(id)
	EventBus.dialogue_ended.emit(id)
	_pump()


func _subst(t: String) -> String:
	if t.find("$") < 0:
		return t
	var cid := GameState.active_case_id()
	if cid != "":
		t = t.replace("$soul", str(Content.case(cid).get("name", "the soul")))
	t = t.replace("$merit", str(GameState.get_stat_i("merit")))
	t = t.replace("$purse", str(GameState.get_stat_i("purse")))
	return t


func speaker_info(spk: String) -> Dictionary:
	if spk == "player":
		return {"name": "You", "portrait": ""}
	if spk == "narrator" or spk == "":
		return {"name": "", "portrait": ""}
	if spk == "$soul":
		var cid := GameState.active_case_id()
		var c := Content.case(cid)
		return {"name": str(c.get("name", "Soul")), "portrait": "bust_%s_neutral" % cid if cid != "" else "por_soul"}
	var n := Content.npc(spk)
	if n.is_empty():
		return {"name": spk.trim_prefix("npc_").capitalize(), "portrait": ""}
	return {"name": str(n.get("name", spk)), "portrait": str(n.get("portrait", ""))}
