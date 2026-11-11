extends Node
## Owns the current area (model + view), the player, docket soul, camera, transitions and world input.

signal area_loaded(area_id: String)
signal joystick_changed(active: bool, base: Vector2, knob: Vector2)
signal focus_changed(object_id: String, verb: String)
signal desk_requested(case_id: String)
signal tap_marker(world_pos: Vector2)

var root: Node2D # world container supplied by the main scene
var view: AreaView
var model: AreaModel
var player: Player
var soul: SoulActor
var escort: SoulActor # a Hell-bound soul being led to the Ember Gate (combat area)
var camera: Camera2D
var backdrop: Backdrop
var area_id := ""
var fading := false
var desk_open := false
var ui_blocking := 0 # menus/overlays open
var focused: Dictionary = {}
var _fade_layer: CanvasLayer
var _fade: ColorRect
var _touch_start := Vector2.ZERO
var _touch_time := 0
var _touch_index := -1
var _joy_active := false
var _key_vec := Vector2.ZERO
var _focus_t := 0.0
var touch_blockers: Array = [] # Controls whose rects swallow world touches


func _ready() -> void:
	_fade_layer = CanvasLayer.new()
	_fade_layer.layer = 90
	add_child(_fade_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0.05, 0.04, 0.07, 1)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.modulate.a = 0.0
	_fade_layer.add_child(_fade)
	_setup_input_map()
	EventBus.case_called.connect(_on_case_called)
	Clock.night_changed.connect(_on_night_changed)


func _setup_input_map() -> void:
	var keys := {"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN], "move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT], "interact": [KEY_E, KEY_ENTER], "cancel": [KEY_ESCAPE],
		"jump": [KEY_SPACE], "spell_triangle": [KEY_Q], "spell_circle": [KEY_R]}
	for action: String in keys:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for k: int in keys[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = k as Key
			InputMap.action_add_event(action, ev)


func set_root(r: Node2D) -> void:
	root = r


func clear() -> void:
	if view != null:
		view.queue_free()
	view = null
	player = null
	soul = null
	camera = null
	model = null
	area_id = ""
	desk_open = false
	if backdrop != null:
		backdrop.queue_free()
		backdrop = null


# ---------------------------------------------------------------- loading
func load_area(id: String, spawn: String = "default", cell_override: Vector2i = Vector2i(-1, -1), facing: String = "s") -> void:
	if Content.area(id).is_empty():
		push_error("Unknown area " + id)
		return
	if view != null:
		view.free()
		view = null
	area_id = id
	model = AreaModel.from_id(id)
	view = AreaView.new()
	if root != null:
		root.add_child(view)
	view.build(model)
	var c := cell_override if cell_override.x >= 0 else model.spawn_cell(spawn)
	player = Player.new()
	player.actor_id = "player"
	view.sorted.add_child(player)
	player.setup(_player_sprite(), model, Vector2(c), facing)
	player.speed = Content.cfg_f("player_speed", 3.0)
	player.reached_target.connect(_on_reached_target)
	_spawn_case_soul()
	camera = Camera2D.new()
	camera.name = "Camera"
	view.add_child(camera)
	camera.make_current()
	_update_camera(true)
	if backdrop == null:
		backdrop = Backdrop.new()
		add_child(backdrop)
	backdrop.build(str(model.data.get("backdrop", "none")))
	Audio.set_ambience(str(model.data.get("ambience", "")))
	area_loaded.emit(id)


func _player_sprite() -> String:
	if GameState.rank >= 2 and Assets.has("chr_player_r2"):
		return "chr_player_r2"
	return "chr_player"


func refresh_player_sprite() -> void:
	if player != null:
		player.sprite_id = _player_sprite()
		player._refresh()


func _desk_object() -> Dictionary:
	if model == null:
		return {}
	for o: Variant in model.objects:
		if o is Dictionary and str((o as Dictionary).get("type", "")) == "desk_player":
			return o
	return {}


func _spawn_case_soul() -> void:
	soul = null
	var cid := GameState.active_case_id()
	if cid == "" or model == null:
		return
	var st := GameState.case_state(cid)
	if bool(GameState.case_rec(cid).get("correction", false)):
		return
	if st == "called":
		var at := player.cell()
		var behind := model.nearest_walkable(at + Vector2i(0, 1), at)
		if behind == at:
			behind = model.nearest_walkable(at + Vector2i(1, 0), at)
		_make_soul(cid, behind, "follow")
	elif st == "seated":
		var desk := _desk_object()
		if desk.is_empty():
			return
		_make_soul(cid, JsonUtil.to_vec2i(desk.get("soul_seat", desk.get("cell"))), "seated")


func _make_soul(cid: String, c: Vector2i, mode: String) -> void:
	soul = SoulActor.new()
	soul.case_id = cid
	soul.actor_id = cid
	soul.mode = mode
	soul.follow = player
	view.sorted.add_child(soul)
	soul.setup(_soul_sprite(cid), model, Vector2(c), "ne")


func _soul_sprite(cid: String) -> String:
	var c := Content.case(cid)
	var s := str(c.get("sprite", ""))
	if s != "":
		return s
	var seed_v := int((c.get("portrait", {}) as Dictionary).get("seed", cid.hash()))
	return "chr_soul_%d" % (absi(seed_v) % 4)


func _on_case_called(cid: String) -> void:
	if model == null or player == null:
		return
	var at := player.cell()
	var spawn := at
	if model.spawns.has("soul_call"):
		spawn = model.spawn_cell("soul_call")
	else:
		spawn = model.nearest_walkable(at + Vector2i(0, 1), at)
	_make_soul(cid, spawn, "follow")


# ---------------------------------------------------------------- transitions
func request_teleport(id: String, spawn: String) -> void:
	if root == null:
		area_id = id
		return
	transition_to(id, spawn, false)


func transition_to(id: String, spawn: String, charge_clock: bool = true) -> void:
	if fading:
		return
	fading = true
	if player != null:
		player.locked = true
	var tw := create_tween()
	tw.tween_property(_fade, "modulate:a", 1.0, 0.125)
	await tw.finished
	_do_transition(id, spawn, charge_clock)
	var tw2 := create_tween()
	tw2.tween_property(_fade, "modulate:a", 0.0, 0.125)
	await tw2.finished
	fading = false


## Synchronous part of a transition (also used by the playtest driver).
func _do_transition(id: String, spawn: String, charge_clock: bool) -> void:
	if charge_clock:
		Clock.advance(Content.clock_cost("door"), "door")
	escort_lost()
	load_area(id, spawn)
	EventBus.area_entered.emit(id)
	SaveGame.autosave("area")


func door_allowed(o: Dictionary) -> bool:
	if o.has("conditions") and not Conditions.check(o["conditions"]):
		return false
	var to: Dictionary = o.get("to", {})
	var target := Content.area(str(to.get("area", "")))
	if bool(target.get("locked", false)) and not GameState.unlocked_areas.has(str(to.get("area", ""))):
		return false
	return true


# ---------------------------------------------------------------- interaction
func verb_for(o: Dictionary) -> String:
	if o.has("verb"):
		return str(o["verb"])
	match str(o.get("type", "")):
		"npc", "hatch":
			return "Talk"
		"door":
			return "Enter"
		"desk_player":
			return "Sit"
		"inspect":
			return "Talk" if o.has("npc") and not o.has("dialogue") else "Read"
		"stair":
			return "Climb"
	return ""


func interactable(o: Dictionary) -> bool:
	var t := str(o.get("type", ""))
	return t in ["npc", "hatch", "door", "desk_player", "inspect", "stair"] and model.object_visible(o)


func input_locked() -> bool:
	return fading or desk_open or ui_blocking > 0 or Dialogue.busy() or player == null or Playtest.driving_input()


## Tap on an object: walk to its use cell, then interact.
func approach(o: Dictionary) -> void:
	if player == null or model == null:
		return
	var uc := model.use_cell(o)
	var oid := str(o.get("id", ""))
	if player.cell() == uc or _in_reach(o):
		player.stop()
		interact(o)
		return
	var p := model.path(player.cell(), uc)
	if p.is_empty():
		var alt := model.nearest_walkable(uc, player.cell())
		p = model.path(player.cell(), alt)
	if p.is_empty():
		EventBus.notify.emit("You can't reach that from here.")
		return
	player.target_object = oid
	player.walk_path(p)


func _in_reach(o: Dictionary) -> bool:
	var uc := model.use_cell(o)
	if Vector2(uc).distance_to(player.gpos) < 0.35:
		return true
	var t := str(o.get("type", ""))
	if t == "door" or t == "stair":
		return false
	return Vector2(model.object_cell(o)).distance_to(player.gpos) <= Content.cfg_f("interaction_radius", 1.5) and \
		Vector2(uc).distance_to(player.gpos) <= 1.5


func _on_reached_target(oid: String) -> void:
	var o := model.object_by_id(oid)
	if not o.is_empty():
		interact(o)


func interact(o: Dictionary) -> void:
	if o.is_empty() or model == null:
		return
	var oid := str(o.get("id", ""))
	EventBus.interaction_started.emit(oid)
	Audio.sfx("sfx_tap")
	if player != null:
		player.face_towards(Vector2(model.object_cell(o)))
	match str(o.get("type", "")):
		"npc", "hatch":
			var npc_id := str(o.get("npc", ""))
			if npc_id != "":
				var a: NpcActor = view.npcs.get(oid) if view != null else null
				if a != null:
					a.face_towards(player.gpos)
				if not Dialogue.talk_to(npc_id) and o.has("dialogue"):
					Dialogue.request(str(o["dialogue"]))
			elif o.has("dialogue"):
				Dialogue.request(str(o["dialogue"]))
		"inspect":
			if o.has("dialogue"):
				Dialogue.request(str(o["dialogue"]))
			elif o.has("npc"):
				Dialogue.talk_to(str(o["npc"]))
		"door":
			if door_allowed(o):
				Audio.sfx("sfx_door")
				var to: Dictionary = o.get("to", {})
				transition_to(str(to.get("area", "")), str(to.get("spawn", "default")))
			else:
				_locked(o)
		"stair":
			if door_allowed(o):
				climb(o)
			else:
				_locked(o)
		"desk_player":
			sit(o)
		"soul_door":
			EventBus.notify.emit("That gate is for souls.")


func _locked(o: Dictionary) -> void:
	if o.has("locked_dialogue"):
		Dialogue.request(str(o["locked_dialogue"]))
	elif o.has("via"):
		var v := model.object_by_id(str(o["via"]))
		if v.has("locked_dialogue"):
			Dialogue.request(str(v["locked_dialogue"]))
			return
		EventBus.notify.emit(str(o.get("locked_text", "Locked.")))
	else:
		EventBus.notify.emit(str(o.get("locked_text", "Locked.")))


## Scripted 3-cell stair climb with height offsets, then fade to the target.
func climb(o: Dictionary) -> void:
	var cells: Array = o.get("climb", [])
	var hs: Array = o.get("climb_h_hu", [0, 2, 4])
	var to: Dictionary = o.get("to", {})
	if cells.is_empty():
		transition_to(str(to.get("area", "")), str(to.get("spawn", "default")))
		return
	player.locked = true
	fading = true
	var tw := create_tween()
	for i in cells.size():
		var c := Vector2(JsonUtil.to_vec2i(cells[i]))
		var h := float(hs[mini(i, hs.size() - 1)]) if not hs.is_empty() else 0.0
		tw.tween_method(func(g: Vector2) -> void:
			player.set_gpos(g)
			player.height_hu = h
			player.body.position = Iso.height_offset(h), player.gpos if i == 0 else Vector2(JsonUtil.to_vec2i(cells[i - 1])), c, 0.35)
	await tw.finished
	fading = false
	transition_to(str(to.get("area", "")), str(to.get("spawn", "default")))


## Sit at the player's desk: the docket soul takes the stool and the desk screen opens.
func sit(o: Dictionary) -> void:
	var cid := GameState.active_case_id()
	if cid == "":
		EventBus.notify.emit("No soul at your desk. Call one at the Registrar.")
		return
	var seat := JsonUtil.to_vec2i(o.get("seat", o.get("use_cell", model.use_cell(o))))
	player.stop()
	player.set_gpos(Vector2(seat))
	player.facing = str(o.get("facing", "sw"))
	player._refresh()
	if GameState.case_state(cid) == "called":
		GameState.seat_case(cid)
		if soul != null:
			var ss := JsonUtil.to_vec2i(o.get("soul_seat", o.get("cell")))
			soul.mode = "seated"
			soul.path.clear()
			soul.set_gpos(Vector2(ss))
			soul.facing = "ne"
			soul._refresh()
	open_desk(cid)


func open_desk(cid: String) -> void:
	desk_open = true
	EventBus.player_sat.emit(cid)
	EventBus.case_opened.emit(cid)
	desk_requested.emit(cid)


func close_desk() -> void:
	desk_open = false
	EventBus.player_stood.emit()


## After a verdict: the seated soul walks out by its gate.
func soul_exit(cid: String, verdict: String) -> void:
	if soul == null or soul.case_id != cid or model == null:
		return
	var door := Vector2i(-1, -1)
	for o: Variant in model.objects:
		if o is Dictionary and str((o as Dictionary).get("type", "")) == "soul_door":
			var od: Dictionary = o
			var v := str(od.get("verdict", "heaven" if str(od.get("style", "")) == "gilt" else "hell"))
			if v == verdict:
				door = JsonUtil.to_vec2i(od.get("cell"))
	if verdict == "purgatory":
		for o: Variant in model.objects:
			if o is Dictionary and str((o as Dictionary).get("type", "")) == "door":
				door = JsonUtil.to_vec2i((o as Dictionary).get("cell"))
				break
	var s := soul
	soul = null
	s.mode = "exit"
	if door.x < 0:
		s.queue_free()
		return
	var p := model.soul_path(s.cell(), door)
	if p.is_empty():
		s.queue_free()
		return
	s.arrived.connect(func() -> void: s.queue_free())
	s.walk_path(p)


func remove_soul() -> void:
	if soul != null:
		soul.queue_free()
		soul = null


# ---------------------------------------------------------------- per-frame
func _process(delta: float) -> void:
	if player == null or model == null:
		return
	if not input_locked():
		var kv := Input.get_vector("move_left", "move_right", "move_up", "move_down")
		if kv.length() > 0.1:
			player.move_vec = _snap_grid(kv)
		elif not _joy_active:
			player.move_vec = Vector2.ZERO
		_check_push_door()
	else:
		player.move_vec = Vector2.ZERO
	player.locked = input_locked() and not Playtest.driving_input()
	_update_camera(false)
	_focus_t -= delta
	if _focus_t <= 0.0:
		_focus_t = 0.1
		_update_focus()


func _check_push_door() -> void:
	var c := player.pushing_into()
	if c.x < -100:
		return
	var o := model.object_at(c)
	if not o.is_empty() and str(o.get("type", "")) == "door" and Vector2(model.use_cell(o)).distance_to(player.gpos) < 0.6:
		player.move_vec = Vector2.ZERO
		_joy_active = false
		joystick_changed.emit(false, Vector2.ZERO, Vector2.ZERO)
		interact(o)


func _snap_grid(screen_v: Vector2) -> Vector2:
	var best := Vector2.ZERO
	var best_dot := -2.0
	var n := screen_v.normalized()
	for g: Vector2 in [Vector2(1, 0), Vector2(0, 1), Vector2(-1, 0), Vector2(0, -1), Vector2(1, 1), Vector2(-1, -1), Vector2(1, -1), Vector2(-1, 1)]:
		var s := Iso.grid_delta_to_screen(g).normalized()
		var d := s.dot(n)
		if d > best_dot:
			best_dot = d
			best = g
	return best.normalized()


func _update_camera(snap: bool) -> void:
	if camera == null or player == null:
		return
	var vs := camera.get_viewport_rect().size
	var b := model.pixel_bounds().grow(24)
	var target := player.position + Vector2(0, -24)
	var half := vs / 2.0
	if b.size.x <= vs.x:
		target.x = b.get_center().x
	else:
		target.x = clampf(target.x, b.position.x + half.x, b.end.x - half.x)
	if b.size.y <= vs.y:
		target.y = b.get_center().y
	else:
		target.y = clampf(target.y, b.position.y + half.y, b.end.y - half.y)
	if snap:
		camera.position = target
	else:
		camera.position = camera.position.lerp(target, 0.2)
	camera.position = camera.position.round()


func _update_focus() -> void:
	var best: Dictionary = {}
	var best_d := 1.0e9
	if not input_locked():
		for o: Variant in model.objects:
			if not (o is Dictionary) or not interactable(o):
				continue
			var od: Dictionary = o
			var uc := model.use_cell(od)
			var d := Vector2(uc).distance_to(player.gpos)
			var t := str(od.get("type", ""))
			var reach := 0.6 if t == "door" or t == "stair" else 1.5
			var oc := Vector2(model.object_cell(od)).distance_to(player.gpos)
			if d <= reach or (t != "door" and t != "stair" and oc <= Content.cfg_f("interaction_radius", 1.5)):
				var score := minf(d, oc)
				if score < best_d:
					best_d = score
					best = od
	var oid := str(best.get("id", ""))
	if oid != str(focused.get("id", "")):
		focused = best
		focus_changed.emit(oid, verb_for(best) if not best.is_empty() else "")
		if view != null:
			for k: String in view.npcs:
				(view.npcs[k] as NpcActor).set_selected(k == oid)


func interact_focused() -> void:
	if not focused.is_empty() and not input_locked():
		interact(focused)


# ---------------------------------------------------------------- input
func _unhandled_input(event: InputEvent) -> void:
	if player == null:
		return
	if event.is_action_pressed("interact") and not input_locked():
		interact_focused()
		return
	if event.is_action_pressed("jump"):
		Combat.press("cross")
		return
	for pair: Array in [["spell_triangle", "triangle"], ["spell_circle", "circle"]]:
		if event.is_action_pressed(str(pair[0])) and not event.is_echo():
			Combat.press(str(pair[1]))
			return
		if event.is_action_released(str(pair[0])):
			Combat.release(str(pair[1]))
			return
	if event is InputEventScreenTouch:
		var t: InputEventScreenTouch = event
		if t.pressed:
			if input_locked() or _over_blocker(t.position):
				return
			_touch_index = t.index
			_touch_start = t.position
			_touch_time = Time.get_ticks_msec()
			_joy_active = false
		elif t.index == _touch_index:
			_touch_index = -1
			var dt := Time.get_ticks_msec() - _touch_time
			if _joy_active:
				_joy_active = false
				player.move_vec = Vector2.ZERO
				joystick_changed.emit(false, Vector2.ZERO, Vector2.ZERO)
			elif dt >= 0 and t.position.distance_to(_touch_start) < 12.0 and not input_locked():
				handle_tap(t.position)
	elif event is InputEventScreenDrag:
		var d: InputEventScreenDrag = event
		if d.index != _touch_index or input_locked():
			return
		var off := d.position - _touch_start
		if not _joy_active and off.length() >= 12.0 and Settings.joystick:
			_joy_active = true
		if _joy_active:
			var knob := off.limit_length(28.0)
			joystick_changed.emit(true, _touch_start, _touch_start + knob)
			if off.length() > 10.0:
				player.move_vec = _snap_grid(off)
			else:
				player.move_vec = Vector2.ZERO


func _over_blocker(p: Vector2) -> bool:
	for c: Variant in touch_blockers:
		if c is Control and is_instance_valid(c):
			var ctl: Control = c
			if ctl.is_visible_in_tree() and ctl.get_global_rect().has_point(p):
				return true
	return false


func screen_to_world(p: Vector2) -> Vector2:
	if view == null:
		return p
	return view.get_viewport().get_canvas_transform().affine_inverse() * p


func handle_tap(screen_pos: Vector2) -> void:
	var wp := screen_to_world(screen_pos)
	tap_world(wp)


func tap_world(wp: Vector2) -> void:
	if model == null or player == null:
		return
	var o := view.object_at_point(wp)
	if not o.is_empty() and (interactable(o) or str(o.get("type", "")) == "soul_door"):
		approach(o)
		return
	var c := Iso.local_to_cell_i(wp)
	if not model.in_bounds(c):
		return
	var dest := model.nearest_walkable(c, player.cell())
	var p := model.path(player.cell(), dest)
	if p.is_empty():
		return
	player.target_object = ""
	player.walk_path(p)
	tap_marker.emit(Iso.cellv(dest))


func tap_cell(c: Vector2i) -> void:
	tap_world(Iso.cellv(c))


func to_dict() -> Dictionary:
	var c := player.cell() if player != null else Vector2i.ZERO
	return {"area": area_id, "cell": [c.x, c.y], "facing": player.facing if player != null else "s"}


# ---------------------------------------------------------------- escort duty (Ember Gate)
func start_escort() -> void:
	if escort != null or player == null or GameState.get_stat_i("escort_pending") <= 0:
		return
	GameState.add_stat("escort_pending", -1)
	var at := model.nearest_walkable(player.cell() + Vector2i(0, 1), player.cell())
	escort = SoulActor.new()
	escort.case_id = ""
	escort.actor_id = "escort"
	escort.mode = "follow"
	escort.follow = player
	view.sorted.add_child(escort)
	escort.setup("chr_soul_%d" % randi_range(0, 3), model, Vector2(at), "ne")
	escort.modulate = Color(1.0, 0.75, 0.7, 0.9)
	EventBus.notify.emit("A Hell-bound soul follows you. Take it to the Gate.")


func escort_near(cell_c: Vector2i, radius: float = 3.0) -> bool:
	return escort != null and escort.gpos.distance_to(Vector2(cell_c)) <= radius


## Hand the soul to the Gate: it walks into the maw. Pays the escort fee.
func deliver_escort(gate: Vector2i) -> void:
	if escort == null:
		return
	var e := escort
	escort = null
	e.mode = "exit"
	e.follow = null
	var p := model.soul_path(e.cell(), gate)
	var finish := func() -> void:
		var tw := e.create_tween()
		tw.tween_property(e, "modulate", Color(1, 0.3, 0.1, 0), 0.6)
		tw.tween_callback(e.queue_free)
	if p.is_empty():
		finish.call()
	else:
		e.arrived.connect(finish, CONNECT_ONE_SHOT)
		e.walk_path(p)
	GameState.add_stat("purse", Content.cfg_i("escort_fee", 4))
	GameState.add_stat("souls_delivered", 1)
	Audio.sfx("sfx_door")


## The soul slips back to the pen (player fell or left the hall).
func escort_lost() -> void:
	if escort != null:
		escort.queue_free()
		escort = null
		GameState.add_stat("escort_pending", 1)


# ---------------------------------------------------------------- night
func _on_night_changed(night: bool) -> void:
	if player == null or model == null or not GameState.in_game:
		return
	Audio.sfx("sfx_night_bell")
	Dialogue.request_modal("card", {"title": "Night Falls" if night else "Morning", "text":
		"The night bell. Desks close, the Arrival Hall is barred, and the Watch takes the Ember Gate." if night else
		"The morning bell. Desks open and the queue begins to move again."})
	reload_area()


## Rebuilds the current area in place (keeps the player's cell), e.g. when night falls.
func reload_area() -> void:
	if model == null or player == null:
		return
	var c := player.cell()
	var f := player.facing
	escort_lost()
	load_area(area_id, "default", c, f)
