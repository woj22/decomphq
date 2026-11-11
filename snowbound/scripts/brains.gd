class_name Brains
extends Node
## Prompts for the AI guests. Each guest is a separate model call carrying only what that guest could know: their
## persona and secret, what they personally heard, the public record, their feelings toward the others and toward
## you, and their memory of past conversations with you. The game owns the facts; the model owns the voice.

var ai: AIClient
var story: Story


func _system(id: String) -> String:
	var g: Dictionary = Cast.GUESTS[id]
	var s: Dictionary = story.guests[id]
	var rel := []
	for other in Cast.STANCE[id]:
		var v: int = Cast.STANCE[id][other]
		rel.append("%s: %s" % [Cast.display(other), ["you despise them", "you distrust them", "you are neutral", "you like them", "you are fond of them"][v + 2]])
	var role := ""
	if id == story.culprit:
		role = "THE TRUTH ONLY YOU KNOW: you are the killer aboard this train. Never confess unless cornered by evidence you cannot explain, and even then twist it. Deflect suspicion onto others - Confucius is a convenient scapegoat - but stay plausible and in character. Keep your alibi consistent with what you said before."
	else:
		role = "You are innocent of the killings. You want to survive, see the killer locked in the baggage car, and avoid being locked up yourself. Guard your private secret, but you might reveal it to someone you trust, or under real pressure."
	return """You are %s, a passenger on a sleeper train snowbound in a mountain blizzard (an era-blended world: historical figures share this train and accept it without comment).
%s
Speak entirely in character: first person, their voice, vocabulary and knowledge. Never mention being an AI or a language model. Keep spoken replies short (1-3 sentences, under 60 words).

Your private secret: %s
%s

Your feelings toward the other guests: %s.
Your trust in Confucius (0-100): %d. Your suspicion of Confucius (0-100): %d. Let these colour how open, warm or guarded you are with him.

Always answer with ONE JSON object and nothing else.""" % [g["name"], g["persona"], g["secret"], role, "; ".join(rel), s["trust"], s["suspicion"]]


func _context(id: String) -> String:
	var s: Dictionary = story.guests[id]
	var lines := []
	lines.append("NOW: night %d of the blizzard, phase: %s." % [story.night, story.phase])
	var dead := story.victims.map(func(v): return "%s (killed night %d)" % [Cast.display(v["id"]), v["night"]])
	lines.append("Dead: %s." % (", ".join(dead) if not dead.is_empty() else "nobody yet"))
	lines.append("Locked in the baggage car: %s." % (", ".join(story.locked.map(Cast.display)) if not story.locked.is_empty() else "nobody"))
	lines.append("PUBLIC RECORD (everyone knows this):\n- " + "\n- ".join(story.public_log.slice(-14)))
	if not s["heard"].is_empty():
		lines.append("WHAT YOU PERSONALLY SAW OR HEARD (only you know this):\n- " + "\n- ".join(s["heard"]))
	if s["notes"] != "":
		lines.append("YOUR PRIVATE NOTES ABOUT EARLIER CONVERSATIONS: " + s["notes"])
	return "\n\n".join(lines)


func _ask(id: String, task: String, schema: String) -> Dictionary:
	var msgs := [{"role": "system", "content": _system(id)},
		{"role": "user", "content": _context(id) + "\n\nTASK: " + task + "\n\nReply with only this JSON: " + schema}]
	if ai.demo:
		await get_tree().create_timer(randf_range(0.4, 0.9)).timeout
		return _mock(id, task)
	while true:
		var r := await ai.chat(msgs)
		if r["ok"]:
			return AIClient.parse_json(r["text"])
		var choice: String = await get_parent().ui.ask_error(Cast.display(id), r["error"])
		if choice == "skip":
			return {"speech": "...", "vote": "", "accuse": ""}
	return {}


# ------------------------------------------------------------------ conversation with you
func reply(id: String, player_line: String, shown_clue := "") -> Dictionary:
	var s: Dictionary = story.guests[id]
	var convo: Array = s["convo"]
	var said := player_line
	if shown_clue != "":
		said += " [Confucius shows you something he found: %s]" % shown_clue
	convo.append("Confucius: " + said)
	var task := "Confucius is talking with you privately.\nThis conversation so far:\n%s\n\nReply to him in character." % "\n".join(convo.slice(-12))
	var out := await _ask(id, task, '{"speech": "<what you say>", "trust_change": <-10..10>, "suspicion_change": <-10..10>, "notes": "<your updated private notes on Confucius and what you have told him, under 70 words>"}')
	var speech := str(out.get("speech", "...")).strip_edges()
	convo.append("%s: %s" % [Cast.display(id), speech])
	s["trust"] = clampi(int(s["trust"]) + int(clampf(float(out.get("trust_change", 0)), -10, 10)), 0, 100)
	s["suspicion"] = clampi(int(s["suspicion"]) + int(clampf(float(out.get("suspicion_change", 0)), -10, 10)), 0, 100)
	if out.has("notes"):
		s["notes"] = str(out["notes"]).left(600)
	return {"speech": speech}


func end_conversation(id: String) -> void:
	var s: Dictionary = story.guests[id]
	s["convo"] = (s["convo"] as Array).slice(-6)   # remember the gist; the notes carry the rest


# ------------------------------------------------------------------ the tribunal
func accusation(id: String) -> Dictionary:
	var names := story.free_guests().filter(func(i): return i != id).map(Cast.display)
	if not story.player_locked:
		names.append("Confucius")
	var task := "MORNING TRIBUNAL in the dining car. Everyone must say aloud who they think the killer is and why, before a vote to lock one passenger in the freezing baggage car. Possible names: %s. Speak to the room (2-3 sentences)." % ", ".join(names)
	var out := await _ask(id, task, '{"speech": "<what you say to the room>", "accuse": "<one name from the list>"}')
	return {"speech": str(out.get("speech", "...")), "accuse": _match(str(out.get("accuse", "")), id)}


func lock_vote(id: String, choices: Array) -> String:
	var task := "Everyone has spoken (see the public record). Cast your vote: who should be locked in the baggage car? Choices: %s." % ", ".join(choices.map(Cast.display))
	var out := await _ask(id, task, '{"vote": "<one name>", "reason": "<a few words>"}')
	return _match(str(out.get("vote", "")), id, choices)


func coal_vote(id: String, choices: Array) -> String:
	var task := "The coal will only heat the compartments of all but one passenger tonight. One must sleep in the armchair by the dining-car stove, under the steward's eye (warm, watched, and so with an alibi). Vote for who should sleep by the stove. Choices: %s." % ", ".join(choices.map(Cast.display))
	var out := await _ask(id, task, '{"vote": "<one name>"}')
	return _match(str(out.get("vote", "")), id, choices)


func _match(text: String, self_id: String, choices := []) -> String:
	var t := text.to_lower()
	var pool: Array = choices if not choices.is_empty() else (Cast.ids() + [Cast.PLAYER])
	for c in pool:
		if c == self_id and choices.is_empty():
			continue
		var nm := Cast.display(c).to_lower()
		if t != "" and (t.contains(nm) or nm.contains(t) or t.contains(c)):
			return c
	return ""


func _mock(id: String, task: String) -> Dictionary:
	var others := (Cast.ids() + [Cast.PLAYER]).filter(func(i): return i != id and story.status(i) in ["aboard", "stove"])
	var pick: String = others[randi() % others.size()] if not others.is_empty() else ""
	var lines := ["The snow has made liars of us all.", "I slept poorly; this train has thin walls.", "Ask yourself who gains from a death tonight.",
		"I have nothing to hide that concerns this matter.", "You are a careful man, Confucius. So am I."]
	return {"speech": lines[randi() % lines.size()] + " (demo)", "accuse": Cast.display(pick), "vote": Cast.display(pick),
		"trust_change": randi_range(-3, 5), "suspicion_change": randi_range(-3, 3), "notes": "demo"}
