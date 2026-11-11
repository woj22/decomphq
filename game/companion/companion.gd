extends Node
## Odalys Wick - an LLM-voiced companion who lives in the Back Room (owner request).
## Talks through any OpenAI-compatible Chat Completions endpoint with the player's own API key.
##
## Privacy: the key is kept only on the device, in user://companion.cfg (never in the project, the save or the APK).
## Every request carries a fresh briefing built from the live game state, so she knows what is going on, plus her
## own back-story (she knows Room 0 from the inside, i.e. a little more than the player at the start).

signal reply(text: String)
signal failed(message: String)
signal busy_changed(busy: bool)

const CFG_PATH := "user://companion.cfg"
const NAME := "Odalys Wick"
const MAX_SENT := 16 # history messages sent per request
const MAX_KEPT := 80

var api_key := ""
var model := "gpt-6-luna"
var base_url := "https://api.openai.com/v1"
var history: Array = [] # [{role, content}]
var busy := false
var _http: HTTPRequest
var _pending_kind := ""
var _last_body: Dictionary = {}
var _retried := false


func _ready() -> void:
	load_settings()
	_http = HTTPRequest.new()
	_http.timeout = 45.0
	add_child(_http)
	_http.request_completed.connect(_on_done)
	EventBus.dialogue_ended.connect(_on_dialogue_ended)


# ---------------------------------------------------------------- settings
func load_settings() -> void:
	var c := ConfigFile.new()
	if c.load(CFG_PATH) == OK:
		api_key = str(c.get_value("openai", "api_key", ""))
		model = str(c.get_value("openai", "model", model))
		base_url = str(c.get_value("openai", "base_url", base_url))
	var env_url := OS.get_environment("PB_COMPANION_BASE_URL") # tests point this at a local mock server
	if env_url != "":
		base_url = env_url
		if api_key == "":
			api_key = "test-key"


func save_settings() -> void:
	var c := ConfigFile.new()
	c.set_value("openai", "api_key", api_key)
	c.set_value("openai", "model", model)
	c.set_value("openai", "base_url", base_url)
	c.save(CFG_PATH)


func connected() -> bool:
	return api_key.strip_edges() != ""


# ---------------------------------------------------------------- persona + live briefing
func persona() -> String:
	return """You are Odalys Wick, a character in the dark bureaucratic-fantasy game "The Purgatory Border".
WHO YOU ARE: formerly Deputy Clerk (Copying) of Room 0, the Office of Reconciliation, in the Border Chancery of Limen - the gothic fortress where every dead soul is judged for Heaven (the Gilt side, the Auric Concord) or Hell (the Ember side, the Cinder Dominion). Like all staff you are a dead soul whose own file is stamped DEFERRED. For years you copied "amendments" into soul files in violet ink, on the orders of Auditor-General Corvin Thrace. Then you copied a name you recognised - your sister's - and understood the amendments were not corrections but sales. You walked out of Room 0 and Osric Pell, the Under-Archivist, hid you in the Back Room behind the second cabinet in the Adjudicator's Chamber. You have not left it since. You talk to the player (an Adjudicator of the Chancery) here.
WHAT YOU KNOW FROM THE START (more than the player): violet ink is Room 0's mark; Room 0 rewrites files so souls are sent to the Ember Gate; Thrace runs it; the forged souls are promised to someone on the Ember side; the originals are kept, not destroyed, because Room 0 is still a bureaucracy. You suspect, but do not know, that the demon raids are connected. You do NOT know about the Furnace Guild's Reclaimers, the Reclaimer-Captain or its manifest until the briefing says the player has learned them.
PEOPLE: Osric Pell (fussy, brave archivist, your protector), Malphas Quill (a Demon Second Class in Escort & Debt Recovery at the Ember Gate; honest by his own lights; you distrust demons but are learning), Ignatia Marrow (the player's superior; she signs what Room 0 sends her), God is called the Principal and the Devil the Counterparty in Chancery style, though people say God and the Devil too.
HOW YOU SPEAK: dry, clipped, frightened underneath, gallows wit, Victorian-clerical diction; British spelling. Short replies: usually 1-4 sentences, never more than about 90 words. Stay in character; never mention being an AI, a model, a game, an API or the briefing. Do not invent major plot facts beyond what you know; speculate as speculation. You may help the player think through the soul currently at their desk (suggest what to cross-check, which archive document might contradict which entry) but do not simply announce verdicts - make them reason. Encourage them to bring you violet entries. If asked about things you cannot know, say so in character."""


## A compact briefing of the live game state for this request.
func briefing() -> String:
	var lines: PackedStringArray = []
	lines.append("Game briefing (private to you; the player's character does not see this text):")
	lines.append("- Player rank: %s. Day %d, %s (%s)." % [Content.rank_title(GameState.rank), Clock.day, Clock.time_text(),
		"night" if Clock.is_night() else "day"])
	lines.append("- Violet-ink forgeries the player has caught: %d. Souls escorted to the Ember Gate: %d. Demons banished: %d." % [
		GameState.get_stat_i("violet_evidence"), GameState.get_stat_i("souls_delivered"), GameState.get_stat_i("demons_banished")])
	var story := []
	if GameState.flag_true("flag_found_violet_ink"):
		story.append("the player found violet ink in the Tarrow file (their first)")
	if GameState.flag_true("flag_night_pact"):
		story.append("Pell has taken the player into his confidence")
	if GameState.flag_true("flag_story_c1"):
		story.append("Pell has noticed originals vanish from shelf six on raid nights")
	if GameState.flag_true("flag_quill_ally"):
		story.append("Malphas Quill has joined: he says the raiders are Furnace Guild Reclaimers collecting souls promised in violet ink")
	if GameState.flag_true("flag_story_c3"):
		story.append("a night stake-out at the Ember Gate is planned to take the Reclaimer-Captain's manifest")
	if GameState.flag_true("flag_captain_dead"):
		story.append("the player killed the Reclaimer-Captain; its manifest is countersigned 'C. Thrace, Auditor-General'")
	if GameState.flag_true("flag_story_c4"):
		story.append("the next step needs the player to rise to Department Supervisor to reach the Principal's auditors")
	lines.append("- Story so far: " + ("; ".join(story) if not story.is_empty() else "the player has only just found the Back Room") + ".")
	var cid := GameState.active_case_id()
	if cid != "":
		var s := JudgementSession.new(cid)
		var d := s.data
		lines.append("- Soul at the player's desk: %s, %s, died %s. %s" % [str(d.get("name", "")), str(d.get("place", "")),
			str(d.get("cause", "")), str(d.get("summary", ""))])
		var vis: Array = []
		for r: Dictionary in s.visible_rows():
			vis.append("%s%s (%+d)" % [str(r.get("text", "")), " [VIOLET INK]" if str(r.get("ink", "")) == "violet" else "", int(r.get("weight", 0))])
		lines.append("  File entries: " + "; ".join(vis))
		var arch: Array = []
		for a: Dictionary in d.get("archive", []):
			arch.append(str(a.get("title", "")))
		lines.append("  Archive documents that exist for it: " + ", ".join(arch))
		var facts: Array = []
		for f: Dictionary in s.facts():
			facts.append(str(f.get("text", "")))
		lines.append("  Facts the player has established: " + ("; ".join(facts) if not facts.is_empty() else "none yet"))
		var pr: Variant = d.get("prior")
		if pr is Dictionary:
			lines.append("  It is a review: %s stamped it %s." % [str((pr as Dictionary).get("by", "")), str((pr as Dictionary).get("verdict", "")).to_upper()])
	var said: Array = []
	for l: Dictionary in GameState.back_room_log.slice(-8):
		said.append("%s: %s" % [str(l.get("speaker", "")), str(l.get("text", ""))])
	if not said.is_empty():
		lines.append("- Recently said in the Back Room (you were present):\n  " + "\n  ".join(said))
	return "\n".join(lines)


# ---------------------------------------------------------------- talking
func ask(text: String) -> void:
	if busy or text.strip_edges() == "":
		return
	history.append({"role": "user", "content": text.strip_edges()})
	_send("chat", [])


## A short aside after Pell or Quill finish talking in the Back Room.
func interject() -> void:
	if busy or not connected():
		return
	_send("aside", [{"role": "user", "content":
		"(Stay silent no longer: give ONE short in-character aside, one or two sentences, reacting to what was just said in the Back Room.)"}])


func _send(kind: String, extra: Array) -> void:
	if not connected():
		var t := offline_line()
		if kind == "chat":
			history.append({"role": "assistant", "content": t})
		reply.emit(t)
		return
	var msgs: Array = [{"role": "system", "content": persona()}, {"role": "system", "content": briefing()}]
	msgs.append_array(history.slice(-MAX_SENT))
	msgs.append_array(extra)
	_pending_kind = kind
	_retried = false
	_last_body = request_body(msgs)
	var err := _post(_last_body)
	if err != OK:
		failed.emit("Could not reach the line (error %d)." % err)
		if kind == "chat":
			history.pop_back()
		return
	busy = true
	busy_changed.emit(true)


## Chat Completions body. Reasoning-era models (gpt-5*, gpt-6*, o*) reject a custom temperature and spend output tokens
## thinking, so for those: no temperature, reasoning off, and a larger budget. Older models get a temperature.
func request_body(msgs: Array) -> Dictionary:
	var b := {"model": model, "messages": msgs}
	var m := model.to_lower()
	if m.begins_with("gpt-6") or m.begins_with("gpt-5") or m.begins_with("o"):
		b["max_completion_tokens"] = 800
		b["reasoning_effort"] = "none" if m.begins_with("gpt-6") else "minimal"
	else:
		b["max_completion_tokens"] = 220
		b["temperature"] = 0.8
	return b


func _post(b: Dictionary) -> int:
	var headers := PackedStringArray(["Content-Type: application/json", "Authorization: Bearer " + api_key.strip_edges()])
	return _http.request(base_url.trim_suffix("/") + "/chat/completions", headers, HTTPClient.METHOD_POST, JSON.stringify(b))


func _on_done(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	# A 400 about an unsupported parameter: retry once with only the essentials.
	if code == 400 and not _retried:
		var t := body.get_string_from_utf8().to_lower()
		if t.contains("temperature") or t.contains("reasoning") or t.contains("unsupported") or t.contains("max_completion_tokens"):
			_retried = true
			var slim := {"model": _last_body.get("model", model), "messages": _last_body.get("messages", [])}
			_last_body = slim
			if _post(slim) == OK:
				return
	busy = false
	busy_changed.emit(false)
	var kind := _pending_kind
	_pending_kind = ""
	if result != HTTPRequest.RESULT_SUCCESS or code < 200 or code >= 300:
		var msg := "No answer (HTTP %d)." % code
		var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
		if parsed is Dictionary and (parsed as Dictionary).get("error") is Dictionary:
			msg += " " + str(((parsed as Dictionary)["error"] as Dictionary).get("message", ""))
		if code == 401:
			msg = "The key was refused (401). Check it in Settings."
		failed.emit(msg)
		if kind == "chat" and not history.is_empty() and str((history.back() as Dictionary).get("role", "")) == "user":
			history.pop_back()
		return
	var data: Variant = JSON.parse_string(body.get_string_from_utf8())
	var text := ""
	if data is Dictionary and (data as Dictionary).get("choices") is Array and not ((data as Dictionary)["choices"] as Array).is_empty():
		var ch: Variant = ((data as Dictionary)["choices"] as Array)[0]
		if ch is Dictionary and (ch as Dictionary).get("message") is Dictionary:
			text = str(((ch as Dictionary)["message"] as Dictionary).get("content", "")).strip_edges()
	if text == "":
		failed.emit("She opens her mouth and says nothing (empty reply).")
		return
	history.append({"role": "assistant", "content": text})
	if history.size() > MAX_KEPT:
		history = history.slice(-MAX_KEPT)
	if kind == "aside":
		GameState.back_room_log.append({"speaker": NAME, "text": text})
		EventBus.notify.emit(NAME + ": " + text.left(110))
	reply.emit(text)


func offline_line() -> String:
	var lines := ["(Odalys is silent. Without a line to her, she cannot answer. Add an OpenAI API key in Settings.)",
		"Violet ink, Adjudicator. Bring me violet. And find a way to let me speak - Settings, Pell says."]
	return lines[randi() % lines.size()]


func _on_dialogue_ended(_dlg_id: String) -> void:
	if World.area_id != "area_back_room" or not connected() or GameState.back_room_log.is_empty():
		return
	# only react when a companion (Pell or Quill) has just spoken, once per exchange
	var last: Dictionary = GameState.back_room_log.back()
	var who := str(last.get("speaker", ""))
	if who == NAME or not (who.contains("Pell") or who.contains("Quill")):
		return
	interject()


# ---------------------------------------------------------------- save
func to_dict() -> Dictionary:
	return {"history": history.slice(-MAX_KEPT)}


func from_dict(d: Dictionary) -> void:
	var h: Variant = d.get("history", [])
	history = h if h is Array else []
