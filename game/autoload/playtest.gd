extends Node
## Scripted playthrough driver (04 §8.3): --playtest=res://tests/playthroughs/<name>.json [--shots=<dir>]
## Issues high-level actions and asserts outcomes. Real UI is driven where it matters (desk, verdict view, modals).

var active := false
var script_path := ""
var shots_dir := ""
var main: Node
var steps: Array = []
var failures: PackedStringArray = []
var log_lines: PackedStringArray = []
var _driving := false
var quit_when_done := true


func _ready() -> void:
	for a: String in OS.get_cmdline_user_args() + OS.get_cmdline_args():
		if a.begins_with("--playtest="):
			script_path = a.substr(11)
			active = true
		elif a.begins_with("--shots="):
			shots_dir = a.substr(8)


func driving_input() -> bool:
	return _driving


func attach(m: Node) -> void:
	main = m
	if active:
		_run.call_deferred()


func _log(s: String) -> void:
	log_lines.append(s)
	print("[playtest] " + s)


func fail(s: String) -> void:
	failures.append(s)
	print("[playtest] FAIL " + s)


func _run() -> void:
	var d: Variant = JsonUtil.load_file(script_path)
	if not (d is Dictionary):
		fail("cannot read " + script_path)
		_finish()
		return
	var spec: Dictionary = d
	SaveGame.path = "user://playtest_%s.json" % script_path.get_file().get_basename()
	SaveGame.delete_save()
	if spec.has("settings"):
		var st: Dictionary = spec["settings"]
		Settings.text_speed = int(st.get("text_speed", 2))
		Settings.tap_stamp = bool(st.get("tap_stamp", true))
	else:
		Settings.text_speed = 2
		Settings.tap_stamp = true
	var t0 := Time.get_ticks_msec()
	await get_tree().process_frame
	var i := 0
	for step: Variant in spec.get("steps", []):
		i += 1
		if not (step is Dictionary):
			continue
		var ok: bool = await run_step(step)
		if not ok:
			fail("step %d failed: %s" % [i, JSON.stringify(step)])
			if bool(spec.get("stop_on_fail", true)):
				break
	_log("done in %.1f s, %d failures" % [(Time.get_ticks_msec() - t0) / 1000.0, failures.size()])
	_finish()


func _finish() -> void:
	print("PLAYTEST %s: %s" % [script_path.get_file(), "PASS" if failures.is_empty() else "FAIL (%d)" % failures.size()])
	if quit_when_done:
		get_tree().quit(0 if failures.is_empty() else 1)


func frames(n: int = 1) -> void:
	for i in n:
		await get_tree().process_frame


func wait_s(s: float) -> void:
	await get_tree().create_timer(s).timeout


# ---------------------------------------------------------------- dialogue helpers
## Runs queued dialogues/modals to completion. `prefer` picks choices by text substring; `effect` by an effect op.
func drain(prefer: Array = [], effect: String = "", max_steps: int = 400) -> void:
	for n in max_steps:
		await frames(1)
		if World.fading:
			continue
		if Dialogue.current_kind == "":
			if Dialogue.queue.is_empty():
				return
			Dialogue._pump()
			continue
		if Dialogue.current_kind == "dialogue":
			if Dialogue.has_choices():
				Dialogue.choose(_pick(prefer, effect))
			else:
				Dialogue.advance()
		elif Dialogue.current_kind == "summary":
			return  # end-of-prototype summary: leave it on screen for the script to assert/dismiss
		elif Dialogue.current_kind == "card":
			# Dismiss title cards with a real tap through the input pipeline, as a player would.
			await tap_screen(get_viewport().get_visible_rect().size * 0.5)
			await frames(2)
			if Dialogue.current_kind == "card":
				fail("title card did not respond to a tap")
				main.dismiss_modal()
		else:
			main.dismiss_modal()
			if Dialogue.current_kind != "" and Dialogue.current_kind != "dialogue":
				Dialogue.modal_done()


func _pick(prefer: Array, effect: String) -> int:
	var vc := Dialogue.visible_choices
	if effect != "":
		for j in vc.size():
			for e: Variant in Dialogue.choice_effects(j):
				if e is Dictionary and str((e as Dictionary).get("op", "")) == effect:
					return j
	for p: Variant in prefer:
		for j in vc.size():
			if str(vc[j]["text"]).to_lower().find(str(p).to_lower()) >= 0:
				return j
	return 0


# ---------------------------------------------------------------- navigation
## Finds the area holding an object id.
func area_of(oid: String) -> String:
	for aid: Variant in Content.area_ids():
		var m := AreaModel.from_id(str(aid))
		if not m.object_by_id(oid).is_empty():
			return str(aid)
	return ""


## Door path between areas (BFS over door objects).
func route(from: String, to: String) -> Array:
	if from == to:
		return []
	var prev := {from: ""}
	var via := {}
	var q := [from]
	while not q.is_empty():
		var a: String = q.pop_front()
		var m := AreaModel.from_id(a)
		for o: Dictionary in m.doors():
			if o.has("via") or (o.has("conditions") and not Conditions.check(o["conditions"])):
				continue
			var b := str((o.get("to", {}) as Dictionary).get("area", ""))
			if b == "" or prev.has(b):
				continue
			prev[b] = a
			via[b] = str(o["id"])
			q.append(b)
	if not prev.has(to):
		return []
	var out: Array = []
	var cur := to
	while cur != from:
		out.push_front(via[cur])
		cur = prev[cur]
	return out


## Moves the player next to an object (walking or fast travel) without interacting.
func go_to(oid: String, walk: bool) -> bool:
	var target_area := area_of(oid)
	if target_area == "":
		fail("no object " + oid)
		return false
	for door_id: Variant in route(World.area_id, target_area):
		var door := World.model.object_by_id(str(door_id))
		if walk:
			if not await walk_to(World.model.use_cell(door)):
				return false
		else:
			World.player.set_gpos(Vector2(World.model.use_cell(door)))
		var to: Dictionary = door.get("to", {})
		World._do_transition(str(to.get("area", "")), str(to.get("spawn", "default")), true)
		await frames(2)
		await drain()
	if World.area_id != target_area:
		fail("could not reach " + target_area)
		return false
	var o := World.model.object_by_id(oid)
	var uc := World.model.use_cell(o)
	if walk:
		return await walk_to(uc)
	World.player.set_gpos(Vector2(uc))
	if World.soul != null and World.soul.mode == "follow":
		World.soul.set_gpos(Vector2(World.model.nearest_walkable(uc + Vector2i(0, 1), uc)))
	return true


func walk_to(c: Vector2i) -> bool:
	var p := World.model.path(World.player.cell(), c)
	if p.is_empty() and World.player.cell() != c:
		fail("no path to %s in %s" % [str(c), World.area_id])
		return false
	_driving = true
	World.player.walk_path(p)
	var t := 0.0
	while World.player.moving() and t < 30.0:
		await frames(1)
		t += get_process_delta_time()
	_driving = false
	return World.player.cell() == c


func interact(oid: String, walk: bool = false) -> bool:
	if not await go_to(oid, walk):
		return false
	World.interact(World.model.object_by_id(oid))
	await frames(2)
	return true


# ---------------------------------------------------------------- steps
func run_step(s: Dictionary) -> bool:
	var op := str(s.get("do", ""))
	var walk := bool(s.get("walk", false))
	match op:
		"new_game":
			main.start_new_game()
			await frames(2)
			await drain()
		"continue":
			main.continue_game()
			await frames(2)
		"go_to":
			return await go_to(str(s["object"]), walk)
		"talk", "interact":
			if not await interact(str(s["object"]), walk):
				return false
			await drain(s.get("prefer", []), str(s.get("effect", "")))
		"call_soul":
			if not await interact("obj_registrar", walk):
				return false
			await drain(["call next"], "call_soul")
			if GameState.active_case_id() == "":
				return false
		"pell":
			if not await interact("obj_pell", walk):
				return false
			await drain([], "give_archive")
		"sit":
			if not await interact("obj_player_desk", walk):
				return false
			await frames(2)
			if main.desk == null:
				return false
		"tab":
			main.desk.set_tab(str(s["tab"]))
			await frames(1)
		"ask":
			main.desk.ask(str(s["q"]))
			await frames(1)
			main.desk.dismiss_overlays()
		"ask_all":
			var sess: JudgementSession = main.desk.session
			var progress := true
			while progress:
				progress = false
				for q: Dictionary in sess.data.get("questions", []):
					var qid := str(q["id"])
					if sess.asked().has(qid) or not sess.question_available(q) or sess.composure() <= 0:
						continue
					main.desk.ask(qid)
					main.desk.dismiss_overlays()
					progress = true
			await frames(1)
		"link":
			main.desk.sel_entry = str(s["entry"])
			main.desk.sel_arc = str(s["arc"])
			main.desk.do_link()
			await frames(1)
		"leave_desk":
			main.desk.leave_desk()
			await frames(2)
		"stamp":
			return await stamp(str(s.get("verdict", "guideline")), str(s.get("ground", "auto")))
		"drain":
			await drain(s.get("prefer", []), str(s.get("effect", "")))
		"advance_clock":
			Clock.advance(int(s.get("minutes", 0)), "playtest")
		"save_load":
			return await save_load()
		"assert":
			return check(s)
		"screenshot":
			await screenshot(str(s.get("name", "shot")))
		"debug_promote":
			# Presses the real Pause-menu button, as the player would.
			var ps := PauseScreen.new()
			main.add_child(ps)
			await frames(2)
			var btn: Button = null
			for b: Node in ps.find_children("*", "Button", true, false):
				if (b as Button).text == "DEBUG: Promote":
					btn = b
			if btn == null:
				fail("no DEBUG: Promote button in Pause")
				ps.queue_free()
				return false
			btn.pressed.emit()
			await frames(2)
		"wait":
			await wait_s(float(s.get("seconds", 0.5)))
		"buy_lamp":
			if not await interact("obj_works_hatch", walk):
				return false
			await drain(["buy"], "buy_item")
		"open":
			match str(s.get("screen", "")):
				"map":
					main.hud.open_map.emit()
				"journal":
					main.hud.open_journal.emit()
				"pause":
					main.hud.open_pause.emit()
			await frames(2)
		"close_menus":
			main._clear_layer(main.menu_layer)
			await frames(1)
		"verdict_view":
			main.desk.open_verdict()
			if s.has("verdict"):
				main.desk.verdict_view.choose(str(s["verdict"]))
			if s.has("ground"):
				main.desk.verdict_view.set_ground(_resolve_ground(str(s["ground"]), str(s.get("verdict", "heaven"))))
			await frames(2)
		"tap_cell":
			World.tap_cell(JsonUtil.to_vec2i(s["cell"]))
			_driving = true
			var t := 0.0
			while World.player.moving() and t < 30.0:
				await frames(1)
				t += get_process_delta_time()
			_driving = false
		_:
			fail("unknown step " + op)
			return false
	return true


func _resolve_ground(g: String, verdict: String) -> String:
	if g != "auto":
		return g
	return DeskDriver.best_ground(main.desk.session, verdict)


## Stamps through the real verdict view: choose, ground, seal (tap mode), epilogue, slip.
func stamp(verdict: String, ground: String) -> bool:
	if main.desk == null:
		fail("stamp: desk not open")
		return false
	var sess: JudgementSession = main.desk.session
	if verdict == "guideline":
		verdict = Scoring.guideline(sess.data)
	elif verdict == "tally":
		verdict = Scoring.side_of(sess.known_tally())
		if verdict == "abstain":
			verdict = "heaven"
	main.desk.open_verdict()
	var vv: VerdictView = main.desk.verdict_view
	vv.choose(verdict)
	vv.set_ground(_resolve_ground(ground, verdict))
	await frames(1)
	vv.seal()
	var t := 0.0
	while vv.stage == "sealed" and t < 5.0:
		await frames(1)
		t += get_process_delta_time()
	var guard := 0
	while is_instance_valid(vv) and vv.stage != "done" and guard < 10:
		if vv.stage == "slip" and shots_dir != "" and not _slip_shot:
			_slip_shot = true
			await screenshot("audit_slip")
		vv.advance()
		guard += 1
		await frames(1)
	await frames(2)
	await drain()
	return true


var _slip_shot := false


func save_load() -> bool:
	SaveGame.autosave("playtest")
	var before := JSON.stringify(SaveGame.snapshot()["state"])
	var before_player := JSON.stringify(World.to_dict())
	if not SaveGame.continue_game():
		fail("continue failed")
		return false
	await frames(2)
	var after := JSON.stringify(SaveGame.snapshot()["state"])
	var after_player := JSON.stringify(World.to_dict())
	if before != after:
		fail("save/load state differs")
		return false
	if before_player != after_player:
		fail("save/load player differs %s vs %s" % [before_player, after_player])
		return false
	return true


func check(s: Dictionary) -> bool:
	var ok := true
	if s.has("conditions") and not Conditions.check(s["conditions"]):
		fail("conditions false: " + JSON.stringify(s["conditions"]))
		ok = false
	for k: String in (s.get("stats", {}) as Dictionary):
		var want: Variant = s["stats"][k]
		if GameState.get_stat_i(k) != int(want):
			fail("stat %s = %d, want %s" % [k, GameState.get_stat_i(k), str(want)])
			ok = false
	if s.has("area") and World.area_id != str(s["area"]):
		fail("area %s, want %s" % [World.area_id, str(s["area"])])
		ok = false
	if s.has("rank") and GameState.rank != int(s["rank"]):
		fail("rank %d, want %s" % [GameState.rank, str(s["rank"])])
		ok = false
	if s.has("merits"):
		var got: Array = []
		for cid: String in DeskDriver.ORDER:
			got.append(int((GameState.cases.get(cid, {}) as Dictionary).get("merit", -1)))
		if JSON.stringify(got) != JSON.stringify(GameState.normalize(s["merits"])):
			fail("merits %s, want %s" % [str(got), str(s["merits"])])
			ok = false
	if s.has("modal") and Dialogue.current_kind != str(s["modal"]):
		fail("modal %s, want %s" % [Dialogue.current_kind, str(s["modal"])])
		ok = false
	return ok


func screenshot(name: String) -> void:
	if shots_dir == "" or DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	await frames(2)
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	DirAccess.make_dir_recursive_absolute(shots_dir)
	var p := shots_dir.path_join(name + ".png")
	img.save_png(p)
	_log("screenshot %s (%dx%d) draw_calls=%d" % [p, img.get_width(), img.get_height(),
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)])


## Simulates a finger tap at a viewport position through Input (mouse press/release; touch emulation on devices).
func tap_screen(pos: Vector2) -> void:
	var vp := get_viewport()
	var screen_pos: Vector2 = vp.get_final_transform() * pos
	for pressed: bool in [true, false]:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = pressed
		e.position = screen_pos
		e.global_position = screen_pos
		Input.parse_input_event(e)
		await frames(1)
