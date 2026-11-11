class_name Game
extends Node
## Runs Snowbound: phases (evening -> night -> morning -> tribunal -> day -> ... -> the snowplough), where everyone
## is, the doors, clues and the body, conversations with the AI guests and the scripted staff, and the votes.

var train: Train
var player: Player
var ui: GameUI
var ai: AIClient
var brains: Brains
var story: Story
var people := {}                  # id -> Person (guests and staff)
var doors := {}                   # compartment n -> {node, open, z}
var clue_nodes := {}              # clue id -> Node3D
var autoplay := false
var _busy := false
var _target: Dictionary = {}
var _in_baggage := false
var _tribunal_pending := false


func start() -> void:
	story = Story.new()
	story.start()
	brains = Brains.new()
	brains.ai = ai
	brains.story = story
	brains.name = "Brains"
	add_child(brains)
	ui.story = story
	ui.player = player
	ui.action_pressed.connect(_on_action)
	player.blocker = door_blocks
	for id in Cast.ids() + ["conductor", "steward"]:
		var p := Person.new()
		train.add_child(p)
		p.setup(id)
		people[id] = p
	_make_doors()
	await _say_card("Snowbound", "The night train stopped hours ago. Outside, the blizzard has buried the line; the conductor says the snowplough cannot reach you for three days.\n\nYou are Confucius, compartment 1. Dinner is over in the dining car, and your fellow passengers linger over the last of the wine: Napoleon Bonaparte, Florence Nightingale, Nikola Tesla, Cleopatra and Niccolò Machiavelli.\n\nTalk to them. Learn who they are. When you are ready, go to your compartment and sleep.")
	evening()


# ------------------------------------------------------------------ phases
func evening() -> void:
	story.phase = "evening"
	ui.set_phase("Night %d · evening" % story.night)
	_seat_guests_dining(1.0)
	_staff_positions()
	for n in doors:
		_set_door(n, true)
	if story.night == 1:
		player.position = Vector3(0, 0, Layout.DINING_Z + 0.6)
		player.yaw = PI
	_refresh_interactables()


func sleep() -> void:
	if _busy:
		return
	_busy = true
	if story.night > Story.LAST_NIGHT:   # the last day is over: the snowplough comes at dawn
		await _fade_card("The last night", "You lie down for the last time in this carriage. Toward dawn, through the wind, a deep mechanical rumble.")
		await ending()
		return
	await _fade_card("Night %d" % story.night, "You lie down in your berth. The wind leans on the carriage; the lamps tick as they cool. Somewhere a door slides.")
	var res := story.resolve_night()
	_clear_clues()
	for c in story.clues:
		if c["night"] == story.night:
			_spawn_clue(c)
	var morning := story.night
	if story.outcome() != "":
		await ending()
		return
	story.phase = "morning"
	ui.set_phase("Morning %d" % story.night)
	player.put(Vector3(0.0, 0, Layout.compartment_z(1) + 1.1), -PI / 2.0)
	for n in doors:
		_set_door(n, true)
	if res["victim"] != "":
		var v: String = res["victim"]
		var vp: Person = people[v]
		vp.status = "dead"
		vp.place(Layout.compartment_bed(Cast.compartment_of(v)), "lie")
		story.announce("Morning %d: %s was found dead in compartment %d." % [story.night, Cast.display(v), Cast.compartment_of(v)])
		await _say_card("Morning", "A scream from the corridor. Mrs Brandt, the steward, stands frozen at the door of compartment %d.\n\n%s is dead in the berth.\n\nThe conductor calls everyone to the dining car for a tribunal. You have a little time to look at the scene first." % [Cast.compartment_of(v), Cast.GUESTS[v]["name"]])
		story.journal.append("Night %d: %s was killed in compartment %d." % [morning, Cast.display(v), Cast.compartment_of(v)])
	else:
		var why: String = res["quiet_reason"]
		var line := "A quiet night. Nobody died."
		story.announce("Morning %d: a quiet night; nobody died." % story.night)
		story.journal.append("Night %d passed quietly. (%s)" % [morning, "Whoever slept by the stove was watched all night" if why == "stove" else "The baggage car's lock held"])
		await _say_card("Morning", line + "\n\nThe passengers gather in the dining car for the tribunal.")
	for id in story.free_guests():
		var p: Person = people[id]
		p.status = "aboard"
		p.walk_to(_dining_seat_for(id), "sit")
	_tribunal_pending = true
	_busy = false
	_refresh_interactables()


func tribunal() -> void:
	_tribunal_pending = false
	_busy = true
	story.phase = "tribunal"
	ui.set_phase("Morning %d · tribunal" % story.night)
	if not story.player_locked:
		player.sit(Layout.dining_seats()[4])
	player.frozen = true
	for id in story.free_guests():
		(people[id] as Person).place(_dining_seat_for(id), "sit_table")
	ui.tribunal_open("The tribunal — morning %d" % story.night)
	var found := story.sweep_clues()
	for c in found:
		var line := "Mr Hale, the conductor: \"I found this on my round: %s\"" % c["text"]
		ui.tribunal_line("Conductor", line)
		story.announce(line)
	await _wait(1.0)
	var choices: Array = story.free_guests().duplicate()
	if not story.player_locked:
		choices.append(Cast.PLAYER)
	for id in story.free_guests():
		_look_all(id)
		(people[id] as Person).set_talking(true)
		ui.tribunal_line(Cast.display(id), "...")
		var r := await brains.accusation(id)
		(people[id] as Person).set_talking(false)
		var line := "%s: \"%s\"" % [Cast.display(id), r["speech"]]
		ui.tribunal_line(Cast.display(id), r["speech"])
		story.announce("Tribunal %d — %s" % [story.night, line])
		if r["accuse"] != "":
			story.guests[id]["suspicion"] = story.guests[id]["suspicion"] + (8 if r["accuse"] == Cast.PLAYER else 0)
		await _wait(0.4)
	ui.tribunal_close()
	var mine := "I have nothing to add." if autoplay else await ui.ask_text("Your turn to speak", "Say who you believe the killer is, and why. Everyone will hear it.", "I believe...")
	story.announce("Tribunal %d — Confucius: \"%s\"" % [story.night, mine])
	# the lock vote
	var votes := {}
	for id in story.free_guests():
		votes[id] = await brains.lock_vote(id, choices.filter(func(c): return c != id))
	var pv: Variant = 0 if autoplay else await ui.choose("Vote: who goes in the baggage car?", choices.filter(func(c): return c != Cast.PLAYER).map(Cast.display), "", false)
	if not story.player_locked:
		votes[Cast.PLAYER] = choices.filter(func(c): return c != Cast.PLAYER)[pv]
	var locked := story.tally(votes)
	var summary := "Votes: " + ", ".join(votes.keys().map(func(k): return "%s → %s" % [Cast.display(k), Cast.display(votes[k]) if votes[k] != "" else "abstained"]))
	story.announce(summary)
	if locked == "":
		story.announce("The vote was tied. Nobody is locked up.")
		await _say_card("The vote", summary + "\n\nA tie. Nobody is locked up today.")
	else:
		story.lock_up(locked)
		story.announce("%s was locked in the baggage car." % Cast.display(locked))
		if locked == Cast.PLAYER:
			await _say_card("The vote", summary + "\n\nThe carriage has chosen you. The conductor takes your arm and leads you to the baggage car. The lock turns.\n\nYou are not finished: you can still speak through the door, and your voice still counts at the tribunal.")
			_go_to_baggage()
		else:
			(people[locked] as Person).status = "locked"
			(people[locked] as Person).visible = false
			await _say_card("The vote", summary + "\n\n%s is led to the baggage car, protesting. The padlock snaps shut." % Cast.display(locked))
	# the coal vote
	var free := story.free_guests()
	if not free.is_empty():
		var coal_choices: Array = free.duplicate()
		var cv := {}
		for id in free:
			cv[id] = await brains.coal_vote(id, coal_choices)
		if not story.player_locked:
			var pick: Variant = 0 if autoplay else await ui.choose("The coal is low", coal_choices.map(Cast.display), "One passenger must sleep in the armchair by the stove tonight, watched by the steward. Who?", false)
			cv[Cast.PLAYER] = coal_choices[pick]
		var stove := story.tally(cv)
		if stove == "":
			stove = coal_choices[story.rng.randi() % coal_choices.size()]
		story.guests[stove]["status"] = "stove"
		story.stove_tonight = stove
		story.announce("%s will sleep by the stove tonight." % Cast.display(stove))
		await _say_card("The stove", "%s will sleep by the stove tonight, under Mrs Brandt's eye." % Cast.display(stove))
	player.frozen = false
	if not story.player_locked:
		player.stand()
	_busy = false
	day()


func day() -> void:
	story.phase = "day"
	var d := story.night
	ui.set_phase("Day %d · the train is still snowbound" % d)
	story.night += 1   # the next sleep is the next night
	for id in story.free_guests():
		var p: Person = people[id]
		if story.rng.randf() < 0.55:
			p.walk_to(_dining_seat_for(id), "sit_table")
		else:
			var n := Cast.compartment_of(id)
			p.walk_to(Layout.compartment_seat(n), "sit")
			p.arrived.connect(func(): _set_door(n, false), CONNECT_ONE_SHOT)
	_staff_positions()
	_refresh_interactables()
	if story.player_locked:
		await _say_card("Day %d" % d, "From the baggage car you hear the others moving about. Speak through the door to whoever comes near. At nightfall, the train sleeps.", "Wait for night")
		await sleep()


func ending() -> void:
	story.phase = "ending"
	var won := story.culprit in story.locked
	var who: String = Cast.GUESTS[story.culprit]["name"]
	var dead := story.victims.map(func(v): return Cast.display(v["id"]))
	var body := ""
	if won:
		body = "Dawn. A rumble in the mountains: the snowplough breaks through.\n\nThe killer was %s, and they are behind the baggage-car door. %s\n\nYou found the truth. Confucius would say: the superior man is modest in his speech but exceeds in his actions." % [who, ("They took %s with them." % ", ".join(dead)) if not dead.is_empty() else "Nobody else had to die."]
	else:
		body = "Dawn. The snowplough breaks through - too late.\n\nThe killer was %s, still free among you. %s\n\nWhen the doors open, they step down into the snow and are gone." % [who, ("Dead: %s." % ", ".join(dead)) if not dead.is_empty() else ""]
	if autoplay:
		print("GAME_OVER won=%s culprit=%s locked=%s victims=%s" % [won, story.culprit, story.locked, dead])
		return
	await _say_card("You caught the killer" if won else "The killer escaped", body, "Ride again")
	get_tree().reload_current_scene()


# ------------------------------------------------------------------ positions
func _dining_seat_for(id: String) -> Dictionary:
	var seats := Layout.dining_seats()
	var order := {"napoleon": 0, "nightingale": 3, "tesla": 1, "cleopatra": 9, "machiavelli": 10}
	return seats[order.get(id, 12)]


func _seat_guests_dining(_p: float) -> void:
	for id in Cast.ids():
		var p: Person = people[id]
		if story.guests[id]["status"] in ["dead", "locked"]:
			continue
		p.place(_dining_seat_for(id), "sit_table")
		p.visible = true


func _staff_positions() -> void:
	(people["steward"] as Person).place(Layout.bar_spot(), "idle")
	(people["conductor"] as Person).place({"pos": Vector3(Layout.CORRIDOR_X, 0, 13.2), "rot": PI}, "idle")


func _look_all(at_id: String) -> void:
	var at: Vector3 = (people[at_id] as Person).head_position()
	for id in people:
		if id != at_id:
			(people[id] as Person).look_target = at


# ------------------------------------------------------------------ doors
func _make_doors() -> void:
	var wood := StandardMaterial3D.new()
	wood.albedo_texture = load("res://assets/textures/rosewood_veneer1_albedo.jpg")
	wood.normal_enabled = true
	wood.normal_texture = load("res://assets/textures/rosewood_veneer1_normal.jpg")
	wood.albedo_color = Color(0.46, 0.3, 0.24)
	wood.roughness = 0.32
	wood.uv1_scale = Vector3(1.2, 1.2, 1.2)
	var brass := StandardMaterial3D.new()
	brass.albedo_color = Color("c9a050")
	brass.metallic = 0.8
	brass.roughness = 0.3
	for n in range(1, 7):
		var d := Node3D.new()
		train.add_child(d)
		var z := Layout.compartment_z(n)
		d.position = Vector3(0.405, 0, z + 0.575)
		var panel := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.035, 1.97, 0.74)
		panel.mesh = bm
		panel.material_override = wood
		panel.position = Vector3(0, 0.985, 0)
		d.add_child(panel)
		var win := MeshInstance3D.new()
		var wm := BoxMesh.new()
		wm.size = Vector3(0.04, 0.36, 0.34)
		win.mesh = wm
		var glass := StandardMaterial3D.new()
		glass.albedo_color = Color(0.15, 0.1, 0.06, 0.85)
		glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		glass.roughness = 0.1
		win.material_override = glass
		win.position = Vector3(0, 1.5, 0)
		d.add_child(win)
		var handle := MeshInstance3D.new()
		var hm := BoxMesh.new()
		hm.size = Vector3(0.06, 0.16, 0.025)
		handle.mesh = hm
		handle.material_override = brass
		handle.position = Vector3(0.0, 1.0, -0.3)
		d.add_child(handle)
		var num := Label3D.new()
		num.text = str(n)
		num.font = load("res://assets/fonts/LibreBaskerville-Bold.ttf")
		num.font_size = 64
		num.pixel_size = 0.0012
		num.modulate = Color(0.08, 0.05, 0.02)
		num.position = Vector3(0.452, 1.75, z + 1.08)
		num.rotation.y = PI / 2.0
		train.add_child(num)
		doors[n] = {"node": d, "open": false, "z": z}


func _set_door(n: int, open: bool) -> void:
	var d: Dictionary = doors[n]
	d["open"] = open
	var node: Node3D = d["node"]
	var tw := create_tween()
	tw.tween_property(node, "position:z", d["z"] + (1.33 if open else 0.575), 0.6).set_trans(Tween.TRANS_SINE)


func door_blocks(p: Vector3) -> bool:
	if p.z > 14.4 or p.x < 0.15 or p.x > 0.66:
		return false
	var n := int(floor(p.z / Layout.BAY)) + 1
	if not doors.has(n):
		return false
	var lz := p.z - Layout.compartment_z(n)
	return not doors[n]["open"] and lz > 0.2 and lz < 0.95


# ------------------------------------------------------------------ clues
func _clear_clues() -> void:
	for k in clue_nodes:
		(clue_nodes[k] as Node3D).queue_free()
	clue_nodes.clear()


func _spawn_clue(c: Dictionary) -> void:
	var n := Node3D.new()
	var m := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.07, 0.015, 0.05)
	m.mesh = bm
	var mt := StandardMaterial3D.new()
	mt.albedo_color = Color(0.95, 0.85, 0.55)
	mt.emission_enabled = true
	mt.emission = Color(1.0, 0.8, 0.4)
	mt.emission_energy_multiplier = 0.6
	mt.metallic = 0.6
	mt.roughness = 0.3
	m.material_override = mt
	n.add_child(m)
	n.position = c["pos"]
	train.add_child(n)
	clue_nodes[c["id"]] = n


# ------------------------------------------------------------------ interaction
func _refresh_interactables() -> void:
	pass


func _seat_free(seat: Dictionary) -> bool:
	for id in people:
		var p: Person = people[id]
		if p.visible and p.position.distance_to(seat["pos"]) < 0.25:
			return false
	return true


func _interactables() -> Array:
	var out := []
	if story == null or _busy:
		return out
	var phase := story.phase
	if player.lying:   # in your berth: sleep (when it's time) or get up
		var fwd := player.camera.global_position + player.forward()
		if phase in ["evening", "day"]:
			out.append({"pos": fwd, "label": "Sleep", "fn": sleep})
		else:
			out.append({"pos": fwd, "label": "Get up", "fn": player.stand})
		return out
	if _in_baggage:
		out.append({"pos": Layout.baggage_door() + Vector3(0, 1.5, 0.1), "label": "Speak through the door", "fn": _talk_through_door})
		return out
	for id in Cast.ids():
		var p: Person = people[id]
		if p.status == "dead":
			out.append({"pos": p.global_position + Vector3(0, 0.7, 0), "label": "Examine %s" % Cast.display(id), "fn": func(): _examine_body(id)})
		elif p.visible and story.guests[id]["status"] in ["aboard", "stove"] and not p.is_walking():
			var n := Cast.compartment_of(id)
			var inside := p.position.z < 14.4 and p.position.x < 0.4
			if inside and not doors[n]["open"]:
				out.append({"pos": Vector3(0.45, 1.4, Layout.compartment_z(n) + 0.6), "label": "Knock on %d" % n, "fn": func(): _knock(n, id)})
			else:
				out.append({"pos": p.head_position(), "label": "Talk to %s" % Cast.display(id), "fn": func(): _talk(id)})
	for staff in ["conductor", "steward"]:
		out.append({"pos": (people[staff] as Person).head_position(), "label": "Talk to %s" % Cast.STAFF[staff]["name"], "fn": func(): _talk_staff(staff)})
	for c in story.clues:
		if not c["found"] and clue_nodes.has(c["id"]):
			out.append({"pos": (clue_nodes[c["id"]] as Node3D).global_position, "label": "Inspect", "fn": func(): _inspect(c)})
	var own_z := Layout.compartment_z(Cast.compartment_of(Cast.PLAYER))
	if not player.lying and phase in ["evening", "day", "morning"]:
		out.append({"pos": Vector3(-0.5, 0.6, own_z + 1.95), "label": "Lie down", "fn": func(): player.lie(Vector3(-1.08, 0, own_z + 1.98), -PI / 2.0)})
	if not player.seated and not player.lying:
		out.append({"pos": Vector3(-0.85, 0.55, own_z + 0.35), "label": "Sit", "fn": func(): player.sit(Layout.compartment_seat(Cast.compartment_of(Cast.PLAYER)))})
		for seat in Layout.dining_seats():
			if _seat_free(seat):
				out.append({"pos": (seat["pos"] as Vector3) + Vector3(0, 0.55, 0), "label": "Sit", "fn": func(): player.sit(seat)})
	if phase == "morning" and _tribunal_pending:
		out.append({"pos": Vector3(0, 1.2, Layout.DINING_Z + 1.0), "label": "Join the tribunal", "fn": tribunal})
	if not story.locked.is_empty():
		out.append({"pos": Layout.baggage_door() + Vector3(0, 1.5, -0.1), "label": "Speak through the baggage door", "fn": _talk_through_door})
	if not _in_baggage and story.phase != "tribunal":
		var own := 1
		if doors.has(own) and player.position.x > 0.4 and absf(player.position.z - (Layout.compartment_z(own) + 0.6)) < 1.0:
			out.append({"pos": Vector3(0.45, 1.3, Layout.compartment_z(own) + 0.6), "label": "Close door" if doors[own]["open"] else "Open door", "fn": func(): _set_door(own, not doors[own]["open"])})
	return out


func _process(_d: float) -> void:
	if ui == null or player == null or story == null:
		return
	if ui.blocking_ui() or player.frozen:
		ui.set_action("")
		_target = {}
		return
	var cam := player.camera
	var best := {}
	var best_score := 1e9
	for it in _interactables():
		var to: Vector3 = (it["pos"] as Vector3) - cam.global_position
		var dist := to.length()
		if dist > 2.2:
			continue
		var ang := player.forward().angle_to(to)
		if ang > 0.6:
			continue
		var score := ang * 2.0 + dist * 0.3
		if score < best_score:
			best_score = score
			best = it
	if best.is_empty() and player.seated and story.phase != "tribunal":
		best = {"label": "Stand up", "fn": player.stand}
	_target = best
	ui.set_action(str(best.get("label", "")))
	if _tribunal_pending and player.position.z > Layout.DINING_Z + 0.3 and not _busy:
		tribunal()


func _on_action() -> void:
	if _target.is_empty() or _busy:
		return
	var fn: Callable = _target["fn"]
	fn.call()


func _knock(n: int, id: String) -> void:
	_set_door(n, true)
	var p: Person = people[id]
	p.look_target = player.camera.global_position
	await _wait(0.6)
	_talk(id)


func _examine_body(id: String) -> void:
	await _say_card(Cast.display(id), "%s lies in the berth as if asleep, but cold. No blood. A faint bruise at the throat; the pillow is pressed out of shape. Whoever did this came close, and was let in - or had a way in." % Cast.GUESTS[id]["name"])
	if not story.journal.has("%s: smothered, no struggle - let in, or a key?" % Cast.display(id)):
		story.journal.append("%s: smothered, no struggle - let in, or a key?" % Cast.display(id))


func _inspect(c: Dictionary) -> void:
	c["found"] = true
	if clue_nodes.has(c["id"]):
		(clue_nodes[c["id"]] as Node3D).queue_free()
		clue_nodes.erase(c["id"])
	var mine: bool = c["owner"] == Cast.PLAYER
	await _say_card("You found something", str(c["text"]) + ("\n\nIt is yours. Someone wants you blamed - and now nobody else will see it." if mine else ""))


func _talk(id: String) -> void:
	if _busy:
		return
	_busy = true
	var p: Person = people[id]
	p.look_target = player.camera.global_position
	player.face(p.head_position())
	player.frozen = true
	ui.open_talk(id, story.guests[id]["trust"])
	ui.talk_line(Cast.display(id), _greeting(id))
	while true:
		var line: String = await ui.send_line
		if line == "__leave__":
			break
		var shown := ""
		if line.begins_with("__clue__"):
			shown = line.substr(8)
			line = "Look at this."
			ui.talk_line("Confucius", "(shows: %s)" % shown, true)
		else:
			ui.talk_line("Confucius", line, true)
		ui.set_busy(true)
		p.set_talking(true)
		var r := await brains.reply(id, line, shown)
		ui.talk_line(Cast.display(id), r["speech"])
		ui.set_trust(story.guests[id]["trust"])
		ui.set_busy(false)
		await _wait(minf(4.0, 1.0 + str(r["speech"]).length() * 0.03))
		p.set_talking(false)
	brains.end_conversation(id)
	ui.close_talk()
	p.look_target = null
	player.face_clear()
	player.frozen = false
	_busy = false


func _greeting(id: String) -> String:
	var t: int = story.guests[id]["trust"]
	if t > 65:
		return "(%s looks relieved to see you.)" % Cast.display(id)
	if t < 25:
		return "(%s watches you warily.)" % Cast.display(id)
	return "(%s turns to you.)" % Cast.display(id)


func _talk_staff(staff: String) -> void:
	if _busy:
		return
	_busy = true
	var p: Person = people[staff]
	p.look_target = player.camera.global_position
	var n := story.night
	var opts: Array
	if staff == "conductor":
		opts = ["What did you see on your rounds last night?", "Who has keys to the compartments?", "When will the snowplough come?", "Nothing, thank you."]
	else:
		opts = ["Who was up late last night?", "What do you make of the passengers?", "Is there enough coal?", "Nothing, thank you."]
	while true:
		var c: Variant = await ui.choose(Cast.STAFF[staff]["name"], opts, "The %s." % Cast.STAFF[staff]["role"], false)
		var ans := ""
		if c == opts.size() - 1:
			break
		if staff == "conductor":
			match c:
				0: ans = story.patrol_note if story.patrol_note != "" else "Nothing yet, sir. It is early in our troubles."
				1: ans = "Only me, sir - the master key never leaves my waistcoat. Though the locks on these old doors are nothing a hairpin couldn't manage."
				2: ans = "If the line clears, after the third night. %d more night%s, God willing." % [maxi(0, Story.LAST_NIGHT - n + 1), "" if Story.LAST_NIGHT - n + 1 == 1 else "s"]
		else:
			match c:
				0: ans = story.steward_note if story.steward_note != "" else "Everyone went to bed at a respectable hour, sir. So far."
				1: ans = ["The Emperor counts the doors. The nurse counts the people. The inventor counts everything in threes.", "The lady from Egypt tips very generously. Too generously, if you ask me.", "The Florentine writes in a little book whenever anyone speaks."][story.rng.randi() % 3]
				2: ans = "Enough for all but one compartment each night, sir. Someone will have to sleep by my stove."
		if not story.journal.has("%s: %s" % [Cast.STAFF[staff]["name"], ans]):
			story.journal.append("%s: %s" % [Cast.STAFF[staff]["name"], ans])
		await _say_card(Cast.STAFF[staff]["name"], ans)
	p.look_target = null
	_busy = false


func _talk_through_door() -> void:
	var choices: Array
	if _in_baggage:
		choices = story.free_guests()
	else:
		choices = story.locked.filter(func(i): return i != Cast.PLAYER)
	if choices.is_empty():
		await _say_card("The baggage door", "There is nobody to speak to.")
		return
	var c: Variant = await ui.choose("Speak to whom?", choices.map(Cast.display))
	if c != null:
		_talk(choices[c])


func _go_to_baggage() -> void:
	_in_baggage = true
	var z0 := Layout.baggage_door().z
	player.extra_rects = [[-1.2, 1.2, z0 + 0.3, z0 + 3.7]]
	player.put(Layout.baggage_door() + Vector3(0, 0, 1.2), 0.0)
	if not train.has_node("Baggage"):
		_build_baggage()


func _build_baggage() -> void:
	## The baggage car: cold, dark, crates and mailbags, one lantern.
	var b := Node3D.new()
	b.name = "Baggage"
	train.add_child(b)
	var z0 := Layout.baggage_door().z + 0.05
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(0.16, 0.13, 0.11)
	dark.roughness = 0.9
	for spec in [[Vector3(2.9, 0.05, 4.0), Vector3(0, -0.025, z0 + 2.0)], [Vector3(2.9, 0.05, 4.0), Vector3(0, 2.3, z0 + 2.0)],
			[Vector3(0.05, 2.3, 4.0), Vector3(-1.45, 1.15, z0 + 2.0)], [Vector3(0.05, 2.3, 4.0), Vector3(1.45, 1.15, z0 + 2.0)],
			[Vector3(2.9, 2.3, 0.05), Vector3(0, 1.15, z0 + 4.0)]]:
		var m := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = spec[0]
		m.mesh = bm
		m.material_override = dark
		m.position = spec[1]
		b.add_child(m)
	var crate := StandardMaterial3D.new()
	crate.albedo_texture = load("res://assets/textures/wood_table_001_albedo.jpg")
	crate.albedo_color = Color(0.8, 0.65, 0.5)
	for i in 6:
		var m := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.6, 0.5 + (i % 3) * 0.15, 0.6)
		m.mesh = bm
		m.material_override = crate
		m.position = Vector3(-1.0 + (i % 2) * 2.0, bm.size.y / 2, z0 + 1.0 + (i / 2) * 1.0)
		b.add_child(m)
	var l := OmniLight3D.new()
	l.light_color = Color(1.0, 0.7, 0.4)
	l.light_energy = 0.8
	l.omni_range = 3.5
	l.position = Vector3(0.8, 1.8, z0 + 2.0)
	b.add_child(l)


# ------------------------------------------------------------------ helpers
func _say_card(title: String, body: String, btn := "Continue") -> void:
	if autoplay:
		print("CARD ", title, ": ", body.left(90).replace("\n", " "))
		await get_tree().process_frame
		return
	await ui.card(title, body, btn)


func _fade_card(title: String, body: String) -> void:
	await _say_card(title, body)


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout
