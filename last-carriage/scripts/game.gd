class_name Game
extends Node
## The rules: introductions, then ROUNDS rounds of (accusations, then each passenger asks the next one a yes/no
## question), then a vote. Seat 0 is the human player. Seats 1-3 are three independent AIs: each turn is its own
## API call with its own persona, temperament and private notes. They share only the public record.

signal auto_turn  # tests: emitted when the player is asked for input (autoplay answers it)

const ROUNDS := 4

var world: World
var ui: GameUI
var ai: AIClient
var players: Array = []   # {seat, figure, temperament, notes}
var record: Array = []    # {round, kind, seat, text, target, answer}
var round_no := 0
var autoplay := false


func name_of(seat: int) -> String:
	return players[seat]["figure"]["name"]


func next_seat(seat: int) -> int:
	return (seat + 1) % 4


func others(seat: int) -> Array:
	return [0, 1, 2, 3].filter(func(s): return s != seat)


# ------------------------------------------------------------------ flow
func run() -> void:
	while true:
		await play_once()


func play_once() -> void:
	var figs: Array = Figures.ALL.duplicate()
	figs.shuffle()
	figs = figs.slice(0, 4)
	var temps: Array = Figures.TEMPERAMENTS.duplicate()
	temps.shuffle()
	players.clear()
	for seat in 4:
		players.append({"seat": seat, "figure": figs[seat], "temperament": temps[seat], "notes": ""})
	record.clear()
	round_no = 0
	world.seat_passengers(figs)
	ui.set_cast(figs)
	ui.show_hud(true)
	world.reset_view()

	system("Midnight. The train has ground to a halt in a blizzard, snowed in somewhere on the line. Introductions.")
	for s in 4:
		await intro_turn(s)
	for r in range(1, ROUNDS + 1):
		round_no = r
		var start := (r - 1) % 4  # who opens rotates each round
		system("Round %d of %d — who is the human?" % [r, ROUNDS])
		for i in 4:
			await accuse_turn((start + i) % 4)
		system("Round %d — yes-or-no questions, each to the passenger beside them" % r)
		for i in 4:
			await question_turn((start + i) % 4)
	system("The lights flicker. Final vote.")
	var votes := []
	for s in 4:
		votes.append(await vote_turn(s))
	for s in 4:
		record.append({"round": round_no, "kind": "vote", "seat": s, "target": votes[s]["target"], "text": votes[s]["reason"]})
		ui.log_line(s, "votes " + name_of(votes[s]["target"]), votes[s]["reason"])
	await results(votes)


func system(t: String) -> void:
	record.append({"round": round_no, "kind": "system", "text": t})
	ui.log_system(t)


func read_time(s: String) -> float:
	return clampf(s.length() * 0.045, 2.4, 9.0)


func speak(seat: int, entry: Dictionary, tag: String) -> void:
	record.append(entry)
	var line: String = entry["text"]
	if entry["kind"] == "answer":
		line = entry["answer"] + "." + (" " + entry["text"] if entry["text"] != "" else "")
	ui.log_line(seat, tag, line)
	world.turn_to(seat)
	if seat != 0:
		var p: Passenger = world.passengers[seat]
		p.thinking = false
		p.talking = true
		p.nod()
	ui.say(seat, line)
	await ui.wait(1.6 if seat == 0 else read_time(line))
	ui.say(seat, "")
	if seat != 0:
		world.passengers[seat].talking = false


func thinking(seat: int, look := -1) -> void:
	world.everyone_look_at(seat, look)
	world.turn_to(seat)
	if seat != 0:
		world.passengers[seat].thinking = true
		ui.say(seat, "…", true)


func player_input(kind: String, args := []) -> Variant:
	if autoplay:
		auto_turn.emit()
		await get_tree().create_timer(0.3).timeout
		match kind:
			"intro": return "Good evening. I confess the cold has got into my bones."
			"accuse": return {"target": 1 + randi() % 3, "text": "Their answers are too tidy to be honest."}
			"question": return "Have you ever seen snow like this before?"
			"answer": return {"answer": "Yes" if randf() < 0.5 else "No", "text": "Never quite like this."}
			"vote": return 1 + randi() % 3
	match kind:
		"intro": return await ui.ask_intro()
		"accuse": return await ui.ask_accuse(round_no)
		"question": return await ui.ask_question()
		"answer": return await ui.ask_answer(args[0], args[1])
		"vote": return await ui.ask_vote()
	return null


func intro_turn(seat: int) -> void:
	thinking(seat)
	ui.set_phase("Introductions · " + ("your turn" if seat == 0 else name_of(seat)))
	var text: String
	if seat == 0:
		text = await player_input("intro")
	else:
		var out := await ai_turn(seat, "Introduce yourself to the table in character (1-2 sentences). You might remark on the storm or the stopped train.", '{"speech": "...", "notes": "..."}')
		text = str(out.get("speech", "..."))
	await speak(seat, {"round": round_no, "kind": "intro", "seat": seat, "text": text}, "intro")


func accuse_turn(seat: int) -> void:
	thinking(seat)
	ui.set_phase("Round %d/%d · Accusations · %s" % [round_no, ROUNDS, "your turn" if seat == 0 else name_of(seat)])
	var target: int
	var text: String
	if seat == 0:
		var v: Dictionary = await player_input("accuse")
		target = v["target"]
		text = v["text"]
	else:
		var opts := ", ".join(others(seat).map(name_of))
		var out := await ai_turn(seat, "Round %d of %d. Say aloud who you believe is the human (one of: %s) and why. Cite specifics from the record where you can." % [round_no, ROUNDS, opts],
			'{"suspect": "<exact name>", "speech": "<what you say aloud>", "notes": "..."}')
		var m := match_seat(out.get("suspect"), seat)
		if m < 0:
			m = match_seat(out.get("speech"), seat)
		target = m if m >= 0 else others(seat).pick_random()
		text = str(out.get("speech", "I suspect %s." % name_of(target)))
		world.passengers[seat].look_target = world.head_point(target)
	await speak(seat, {"round": round_no, "kind": "accuse", "seat": seat, "target": target, "text": text}, "suspects " + name_of(target))


func question_turn(seat: int) -> void:
	var target := next_seat(seat)
	thinking(seat, target)
	ui.set_phase("Round %d/%d · Questions · %s" % [round_no, ROUNDS,
		("you ask " + name_of(target)) if seat == 0 else (name_of(seat) + " asks " + ("you" if target == 0 else name_of(target)))])
	var q: String
	if seat == 0:
		q = await player_input("question")
	else:
		var out := await ai_turn(seat, "Round %d. Ask %s (beside you) ONE yes-or-no question designed to reveal whether they are the human. Ask it in character." % [round_no, name_of(target)],
			'{"question": "<your yes/no question>", "notes": "..."}')
		q = str(out.get("question", out.get("speech", "Are you truly who you claim to be?")))
	await speak(seat, {"round": round_no, "kind": "question", "seat": seat, "text": q}, "asks " + name_of(target))

	thinking(target, seat)
	var answer: String
	var text := ""
	if target == 0:
		var v: Dictionary = await player_input("answer", [seat, q])
		answer = v["answer"]
		text = v["text"]
	else:
		var out := await ai_turn(target, '%s has just asked you: "%s". Answer Yes or No, then optionally one short in-character remark (under 25 words).' % [name_of(seat), q],
			'{"answer": "Yes" or "No", "speech": "<optional short remark>", "notes": "..."}')
		answer = "No" if str(out.get("answer", "Yes")).strip_edges().to_lower().begins_with("n") else "Yes"
		text = str(out.get("speech", ""))
		var re := RegEx.create_from_string("(?i)^(yes|no)[.,!]?\\s*")
		text = re.sub(text, "")
	await speak(target, {"round": round_no, "kind": "answer", "seat": target, "answer": answer, "text": text}, answer)


func vote_turn(seat: int) -> Dictionary:
	thinking(seat)
	ui.set_phase("Final vote · " + ("your vote" if seat == 0 else name_of(seat)))
	if seat == 0:
		return {"target": await player_input("vote"), "reason": ""}
	var opts := ", ".join(others(seat).map(name_of))
	var out := await ai_turn(seat, "All %d rounds are over. Cast your final, secret vote for who is the human (one of: %s). Votes are revealed together afterwards." % [ROUNDS, opts],
		'{"vote": "<exact name>", "reason": "<one sentence, in character>", "notes": "..."}')
	ui.say(seat, "")
	world.passengers[seat].thinking = false
	var m := match_seat(out.get("vote"), seat)
	if m < 0:
		m = match_seat(out.get("reason"), seat)
	return {"target": m if m >= 0 else others(seat).pick_random(), "reason": str(out.get("reason", ""))}


func results(votes: Array) -> void:
	var tally := [0, 0, 0, 0]
	for v in votes:
		tally[v["target"]] += 1
	var top: int = tally.max()
	var leaders := [0, 1, 2, 3].filter(func(s): return tally[s] == top)
	var caught: bool = leaders.size() == 1 and leaders[0] == 0
	for s in range(1, 4):  # the AIs reveal their votes one by one
		var p: Passenger = world.passengers[s]
		p.look_target = world.head_point(votes[s]["target"])
		world.turn_to(s)
		p.talking = true
		var line := "I vote %s.%s" % [name_of(votes[s]["target"]), (" " + votes[s]["reason"]) if votes[s]["reason"] != "" else ""]
		ui.say(s, line)
		await ui.wait(read_time(line) + 0.5)
		ui.say(s, "")
		p.talking = false
	for s in range(1, 4):
		world.passengers[s].look_target = world.head_point(0) if caught else null
	world.reset_view()
	ui.set_phase("Caught!" if caught else "You got away with it")
	var verdict: String
	if caught:
		verdict = "The carriage turns to you. You were unmasked as the human with %d of 4 votes." % tally[0]
	elif 0 in leaders:
		verdict = "A tie at the top: nobody can agree, and you slip away into the night."
	else:
		verdict = "You blended in. The table settled on %s, an AI." % " and ".join(leaders.map(name_of))
	var rows := []
	for s in 4:
		rows.append([name_of(s) + (" (you)" if s == 0 else " (AI)"), name_of(votes[s]["target"]), str(tally[s])])
	var notes := []
	for s in range(1, 4):
		notes.append("%s: %s" % [name_of(s), players[s]["notes"] if players[s]["notes"] != "" else "(none)"])
	if autoplay:
		auto_turn.emit()
		print("GAME_OVER caught=%s tally=%s" % [caught, tally])
		await get_tree().create_timer(0.5).timeout
		return
	await ui.show_results(caught, verdict, rows, notes)


# ------------------------------------------------------------------ AI
func match_seat(v: Variant, self_seat: int) -> int:
	if v == null:
		return -1
	var n := str(v).to_lower()
	for s in others(self_seat):
		if name_of(s).to_lower() == n:
			return s
	for s in others(self_seat):
		for part in name_of(s).to_lower().split(" "):
			if part.length() > 2 and n.contains(part):
				return s
	return -1


func system_prompt(seat: int) -> String:
	var p: Dictionary = players[seat]
	var circle := "\n".join([0, 1, 2, 3].map(func(s): return "- " + name_of(s) + (" (YOU)" if s == seat else "")))
	return """You are an AI playing a social-deduction game set in a night-train carriage. It is midnight; the train has stopped, snowed in by a blizzard, and the wind howls at the frosted windows. Four passengers sit around one table. Each is playing a historical figure.

You are playing %s: %s
Stay fully in character at all times: first person, the voice, vocabulary, era and knowledge of %s. Never say you are an AI or a language model out loud.
Your personality as a player: %s.

The passengers, in seating order round the table (each one's "next" is the one below them; the last wraps to the first):
%s

THE SECRET: exactly one of the other three is a real human pretending to be their figure. The other two are AIs like you. You are definitely an AI, so you are not the human. You have no private channel with anyone; nobody can see your private notes.

YOUR GOALS: (1) work out which passenger is the human and (2) avoid being mistaken for the human yourself. Look for human tells: typos, casual or modern phrasing, very short or very long answers, dodging, inconsistent character knowledge, emotional reactions, answers an AI would phrase differently. Everyone else is trying the same, so form your own opinion; do not just follow the crowd.

Rules: the game lasts %d rounds. Each round everyone says aloud who they believe is the human and why, then each passenger asks the passenger next to them one yes-or-no question, which must be answered Yes or No (a short remark may follow). After round %d everyone votes. Spoken lines are short: 1-3 sentences, under 60 words.

Always reply with ONE JSON object only, no other text.""" % [p["figure"]["name"], p["figure"]["desc"], p["figure"]["name"], p["temperament"], circle, ROUNDS, ROUNDS]


func public_record() -> String:
	if record.is_empty():
		return "(nothing has been said yet)"
	var lines := []
	for r in record:
		match r["kind"]:
			"system": lines.append("--- %s ---" % r["text"])
			"intro": lines.append('%s: "%s"' % [name_of(r["seat"]), r["text"]])
			"accuse": lines.append('%s (believes %s is the human): "%s"' % [name_of(r["seat"]), name_of(r["target"]), r["text"]])
			"question": lines.append('%s asks %s: "%s"' % [name_of(r["seat"]), name_of(next_seat(r["seat"])), r["text"]])
			"answer": lines.append("%s answers: %s%s" % [name_of(r["seat"]), r["answer"], (' — "%s"' % r["text"]) if r["text"] != "" else ""])
			"vote": lines.append("%s votes for %s" % [name_of(r["seat"]), name_of(r["target"])])
	return "\n".join(lines)


func ai_turn(seat: int, task: String, schema: String) -> Dictionary:
	var p: Dictionary = players[seat]
	var user := """PUBLIC RECORD OF EVERYTHING SAID IN THE CARRIAGE SO FAR:
%s

YOUR PRIVATE NOTES FROM EARLIER (only you can see these):
%s

YOUR TASK NOW: %s

Reply with only this JSON: %s
"notes" = your updated private notes: current suspicion of each other passenger (0-100) and the evidence, under 80 words.""" % [public_record(), p["notes"] if p["notes"] != "" else "(none yet)", task, schema]
	var messages := [{"role": "system", "content": system_prompt(seat)}, {"role": "user", "content": user}]
	while true:
		var out: Dictionary
		if ai.demo:
			out = await _mock(seat)
		else:
			var r := await ai.chat(messages)
			if not r["ok"]:
				if autoplay:
					push_error("AI call failed: " + r["error"])
					print("AI_ERROR " + r["error"])
				var choice: String = "skip" if autoplay else await ui.ask_error(name_of(seat), r["error"])
				if choice == "skip":
					return {"speech": "Hmm. I shall keep my thoughts to myself for now.", "question": "Are you who you claim to be?", "answer": "Yes"}
				continue
			out = AIClient.parse_json(r["text"])
		if out.has("notes"):
			p["notes"] = str(out["notes"]).left(800)
		return out
	return {}


func _mock(seat: int) -> Dictionary:  # canned lines so the game can be tried without a key
	await get_tree().create_timer(randf_range(0.5, 1.2)).timeout
	var sus: int = others(seat).pick_random()
	var lines := ["Your phrasing betrays you.", "You answered too quickly for one of us.", "There is something unpractised in your manner.", "You hesitated where a machine would not."]
	return {"speech": "%s, %s (demo line)" % [["By my word", "Mark me", "Hear this", "I confess"].pick_random(), lines.pick_random()],
		"suspect": name_of(sus), "vote": name_of(sus), "reason": lines.pick_random(),
		"question": ["Have you ever seen the sea?", "Do you fear death?", "Did you write your own speeches?", "Is tonight colder than you expected?"].pick_random() + " (demo)",
		"answer": ["Yes", "No"].pick_random(), "notes": "Suspect %s (demo)." % name_of(sus)}
