extends Node3D
## Imperium — palace prototype. Builds the Palatium Ardens, populates it with the court, and runs
## exploration: walk, cut away walls, approach and speak with characters, overhear the court.
##
## Command-line (after `--`):
##   --shots=DIR   capture the screenshot tour into DIR and quit
##   --smoke       simulate for a few seconds, print a report and quit (exit code 1 on failure)

const CAM_OFFSET := Vector3(0, 12.5, 10.5)
const TALK_RANGE := 2.6

var palace: Palace
var player: PlayerController
var cam: Camera3D
var hud: HUD
var npcs: Array = []
var by_id: Dictionary = {}

var zoom := 0.78
var cam_yaw := 0.0
var _cam_yaw_target := 0.0
var _cam_focus := Vector3.ZERO
var _room_id := ""
var _talking_to: NPC
var _bark_t := 2.0
var _last_barker: NPC
var _cutaway := true
var _args := {}


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		_args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	palace = Palace.new()
	palace.name = "Palace"
	add_child(palace)
	palace.build()
	player = PlayerController.new()
	player.name = "Player"
	add_child(player)
	player.position = palace.spawn
	player.arrived.connect(_on_arrived)
	cam = Camera3D.new()
	cam.fov = 46
	cam.far = 400
	add_child(cam)
	hud = HUD.new()
	hud.main = self
	add_child(hud)
	hud.dialogue_closed.connect(_end_dialogue)
	_spawn_cast()
	player.npcs = npcs
	_cam_focus = player.position
	_update_camera(1.0)
	if _args.has("shots"):
		_shot_tour.call_deferred(_args["shots"])
	elif _args.has("smoke"):
		_smoke.call_deferred()


# ------------------------------------------------------------------ population

func _yaw_from(face: String) -> float:
	match face:
		"N": return 0.0
		"W": return PI / 2
		"S": return PI
		"E": return -PI / 2
	return 0.0


func _add_npc(id: String, info: Dictionary, look: Dictionary, notable: bool, seed_: int) -> NPC:
	var n := NPC.new()
	add_child(n)
	n.setup(palace, id, info, look, notable, seed_)
	npcs.append(n)
	if notable:
		by_id[id] = n
	return n


func _spawn_cast() -> void:
	var seed_ := 11
	for id in Cast.characters:
		if id == "player":
			continue
		var c: Dictionary = Cast.characters[id]
		var place: Dictionary = c.get("place", {})
		var n := _add_npc(id, c, Cast.look_for(id), true, seed_)
		seed_ += 1
		if place.has("seat") and palace.seats.has(place["seat"]):
			n.sit_at(palace.seats[place["seat"]])
		elif place.has("stand"):
			n.place_at(Vector3(place["stand"][0], 0, place["stand"][1]), _yaw_from(str(place.get("face", "S"))))
		elif place.has("routine"):
			n.follow_routine(place["routine"])
		else:
			push_warning("No place for %s" % id)
	var ex: Dictionary = Cast.extras
	var rng := RandomNumberGenerator.new()
	rng.seed = 1234
	var make_extra := func(tname: String) -> NPC:
		var t: Dictionary = ex["templates"][tname]
		var sp_list: Array = t["species"]
		var sp: String = sp_list[rng.randi() % sp_list.size()]
		var sex := "f" if rng.randf() < 0.4 else "m"
		if tname in ["praetorian", "auxiliary", "seravel_guard"] and rng.randf() < 0.5:
			sex = "m"
		var look := Cast.resolve_look(sp, t["look"], sex, rng)
		return _add_npc(tname, t, look, false, rng.randi())
	for p in ex.get("posts", []):
		var n: NPC = make_extra.call(p["t"])
		n.place_at(Vector3(p["at"][0], 0, p["at"][1]), _yaw_from(p.get("face", "S")))
	for p in ex.get("chatters", []):
		var n2: NPC = make_extra.call(p["t"])
		if p.has("seat") and palace.seats.has(p["seat"]):
			n2.sit_at(palace.seats[p["seat"]])
		else:
			n2.place_at(Vector3(p["at"][0], 0, p["at"][1]), _yaw_from(p.get("face", "S")))
	for s in ex.get("seated", []):
		var names: Array = []
		for k in palace.seats:
			if str(k).begins_with(s["seats"]):
				names.append(k)
		names.shuffle()
		for i in mini(int(s["count"]), names.size()):
			var n3: NPC = make_extra.call(s["t"])
			n3.sit_at(palace.seats[names[i]])
	for w in ex.get("walkers", []):
		for i in int(w["count"]):
			var n4: NPC = make_extra.call(w["t"])
			n4.wander()


func whereabouts(id: String) -> String:
	var n: NPC = by_id.get(id)
	if n == null:
		return "Not at court."
	var r := palace.room_at(n.global_position)
	var place: Dictionary = n.info.get("place", {})
	var where := str(r.get("name", "Somewhere in the palace"))
	if place.has("routine"):
		return "Moves about the palace; last seen in %s." % where
	if place.has("seat"):
		return "Seated in %s." % where
	return "Usually found in %s." % where


# ------------------------------------------------------------------ frame

func _process(delta: float) -> void:
	_update_camera(delta)
	if _cutaway:
		_update_cutaway()
	var r := palace.room_at(player.global_position)
	if r.get("id", "") != _room_id and r.get("id", "") != "":
		_room_id = r["id"]
		_cam_yaw_target = r.get("cam_yaw", 0.0)
		hud.show_location(r)
	cam_yaw = lerp_angle(cam_yaw, _cam_yaw_target, minf(1.0, delta * 2.5))
	player.input_dir = hud.joystick
	player.view_yaw = cam_yaw
	if _talking_to == null and not hud.roster_open():
		hud.set_speak_target(_nearest_npc(TALK_RANGE))
		_ambient_barks(delta)
	else:
		hud.set_speak_target(null)


func _update_camera(delta: float) -> void:
	var focus := player.global_position + Vector3(0, 1.0, 0)
	var yb := Basis(Vector3.UP, cam_yaw)
	var off := yb * (CAM_OFFSET * zoom)
	if _talking_to != null:
		focus = (player.global_position + _talking_to.global_position) * 0.5 + Vector3(0, 1.4, 0)
		off = yb * Vector3(2.5, 4.2, 7.0)
		if hud.dialogue_open():
			focus.y -= 1.3   # leave room for the dialogue panel at the bottom of the screen
	_cam_focus = _cam_focus.lerp(focus, minf(1.0, delta * 5.0))
	var want := _cam_focus + off
	cam.position = cam.position.lerp(want, minf(1.0, delta * 4.0)) if delta < 0.99 else want
	cam.look_at(_cam_focus)


func _update_cutaway() -> void:
	var eye := cam.global_position
	var a := player.global_position + Vector3(0, 0.4, 0)
	var b := player.global_position + Vector3(0, 1.7, 0)
	var extra: Array = []
	if _talking_to != null:
		extra.append(_talking_to.global_position + Vector3(0, 1.2, 0))
	var pp := player.global_position
	var back := Basis(Vector3.UP, cam_yaw) * Vector3.BACK     # toward the camera, horizontal
	var right := Basis(Vector3.UP, cam_yaw) * Vector3.RIGHT
	for o in palace.occluders:
		var mi := o as MeshInstance3D
		var raw: AABB = mi.get_meta("aabb")
		var box := raw.grow(0.35)
		var hit := box.intersects_segment(a, eye) != null or box.intersects_segment(b, eye) != null
		for p in extra:
			hit = hit or box.intersects_segment(p, eye) != null
		# a cutaway window: tall pieces between the player and the camera (which looks north)
		if not hit and raw.end.y > 2.5:
			var cdel := raw.get_center() - pp
			var ex := raw.size * 0.5
			var eb := absf(ex.x * back.x) + absf(ex.z * back.z)
			var er := absf(ex.x * right.x) + absf(ex.z * right.z)
			var db := cdel.x * back.x + cdel.z * back.z
			var dr := cdel.x * right.x + cdel.z * right.z
			if db + eb > 0.2 and db - eb < 11.0 and absf(dr) - er < 6.5:
				hit = true
		mi.visible = not hit


func _nearest_npc(r: float) -> NPC:
	var best: NPC = null
	var bd := r
	for n in npcs:
		var npc := n as NPC
		var d := npc.global_position - player.global_position
		d.y = 0.0
		var l := d.length()
		if l < bd and npc.is_available():
			bd = l
			best = npc
	return best


func _ambient_barks(delta: float) -> void:
	_bark_t -= delta
	if _bark_t > 0.0:
		return
	_bark_t = randf_range(2.5, 4.5)
	var near: Array = []
	for n in npcs:
		var npc := n as NPC
		if npc == _last_barker or not npc.is_available() or npc.barks().is_empty():
			continue
		var l := npc.global_position.distance_to(player.global_position)
		if l < 10.0:
			near.append(npc)
	if near.is_empty():
		return
	var pick: NPC = near[randi() % near.size()]
	var b := pick.barks()
	pick.say(b[randi() % b.size()], 4.0)
	_last_barker = pick


# ------------------------------------------------------------------ input & dialogue

func _unhandled_input(ev: InputEvent) -> void:
	if hud.joystick_input(ev):
		get_viewport().set_input_as_handled()
		return
	if ev is InputEventKey and ev.pressed and not ev.echo:
		match (ev as InputEventKey).physical_keycode:
			KEY_E, KEY_SPACE, KEY_ENTER:
				if hud.dialogue_open():
					hud.skip_typing()
				else:
					var n := _nearest_npc(TALK_RANGE)
					if n:
						begin_dialogue(n)
			KEY_C, KEY_TAB:
				hud.toggle_roster()
			KEY_ESCAPE:
				if hud.dialogue_open():
					hud.close_dialogue()
				elif hud.roster_open():
					hud.toggle_roster()
			KEY_EQUAL, KEY_KP_ADD:
				zoom = clampf(zoom - 0.1, 0.55, 1.5)
			KEY_MINUS, KEY_KP_SUBTRACT:
				zoom = clampf(zoom + 0.1, 0.55, 1.5)
	if ev is InputEventMouseButton and ev.pressed:
		var mb := ev as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom = clampf(zoom - 0.06, 0.55, 1.5)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom = clampf(zoom + 0.06, 0.55, 1.5)
	if ev is InputEventMagnifyGesture:
		zoom = clampf(zoom / (ev as InputEventMagnifyGesture).factor, 0.55, 1.5)
	if ev is InputEventScreenTouch and not ev.pressed and _talking_to == null and not hud.roster_open():
		var n2 := _pick_npc((ev as InputEventScreenTouch).position)
		if n2:
			if n2.global_position.distance_to(player.global_position) < TALK_RANGE:
				begin_dialogue(n2)
			else:
				player.walk_to(n2)


func _pick_npc(screen: Vector2) -> NPC:
	var best: NPC = null
	var bd := 70.0
	for n in npcs:
		var npc := n as NPC
		var p := npc.global_position + Vector3(0, npc.rig.height * 0.6, 0)
		if cam.is_position_behind(p):
			continue
		var d := cam.unproject_position(p).distance_to(screen)
		if d < bd and npc.global_position.distance_to(player.global_position) < 22.0:
			bd = d
			best = npc
	return best


func _on_arrived(target: Node3D) -> void:
	if target is NPC and _talking_to == null:
		begin_dialogue(target)


func begin_dialogue(npc: NPC) -> void:
	if _talking_to != null:
		return
	_talking_to = npc
	player.cancel_walk()
	player.frozen = true
	player.face(npc.global_position)
	npc.engage(player.global_position)
	hud.open_dialogue(npc)


func _end_dialogue() -> void:
	if _talking_to:
		_talking_to.disengage()
	_talking_to = null
	player.frozen = false


# ------------------------------------------------------------------ automation

func _wait(frames: int) -> void:
	for i in frames:
		await get_tree().process_frame


func _snap(dir: String, nm: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(dir.path_join(nm + ".png"))
	print("screenshot ", nm)


func _teleport(p: Vector3, face_to := Vector3.INF) -> void:
	player.global_position = p
	player.velocity = Vector3.ZERO
	if face_to != Vector3.INF:
		player.face(face_to)
	_cam_focus = p + Vector3(0, 1.0, 0)
	var r := palace.room_at(p)
	cam_yaw = r.get("cam_yaw", 0.0)
	_cam_yaw_target = cam_yaw
	_room_id = r.get("id", "")
	hud.show_location(r)
	_update_camera(1.0)


func _shot_tour(dir: String) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	await _wait(10)
	var tour := [
		["01_courtyard", Vector3(0, 0, 13.5), Vector3(0, 0, 0), 1.0],
		["02_fountain", Vector3(5.5, 0, 6.0), Vector3(0, 0, 0), 0.8],
		["03_council", Vector3(0, 0, -25.0), Vector3(0, 0, -40), 1.1],
		["04_council_dais", Vector3(0, 0, -36.0), Vector3(0, 0, -44), 0.85],
		["05_hall_of_kings", Vector3(25.0, 0, 0.5), Vector3(40, 0, 0), 1.2],
		["06_kings_table", Vector3(36.0, 0, 3.6), Vector3(36, 0, 0), 0.8],
		["07_petitions", Vector3(-22.0, 0, 2.0), Vector3(-28, 0, 0), 0.9],
		["08_audience", Vector3(-38.0, 0, 0.0), Vector3(-50, 0, 0), 1.15],
		["09_gallery", Vector3(0, 0, 25.0), Vector3(0, 0, 20), 0.9],
		["10_apartments", Vector3(-3.0, 0, 42.0), Vector3(-5, 0, 46), 1.1],
		["11_bedchamber", Vector3(7.5, 0, 46.0), Vector3(10, 0, 50), 0.8],
	]
	for s in tour:
		zoom = s[3]
		_teleport(s[1], s[2])
		await _wait(45)
		await _snap(dir, s[0])
	# conversations
	zoom = 1.0
	var talks := [["12_talk_emperor", "emperor", Vector3(-45.2, 0, 1.6)], ["13_talk_thrask", "thrask", Vector3(32.6, 0, -6.9)],
		["14_talk_ilsaveth", "ilsaveth", Vector3.INF], ["15_talk_halvana", "halvana", Vector3(-24.6, 0, 5.4)]]
	for t in talks:
		var n: NPC = by_id[t[1]]
		var at: Vector3 = t[2]
		if at == Vector3.INF:
			at = n.global_position + Vector3(1.2, 0, 1.2)
		_teleport(at, n.global_position)
		await _wait(5)
		begin_dialogue(n)
		await _wait(60)
		hud.skip_typing()
		await _wait(4)
		await _snap(dir, t[0])
		hud.close_dialogue()
		await _wait(5)
	# the court roster
	hud.toggle_roster()
	for r in [["16_roster_emperor", "emperor"], ["17_roster_thrask", "thrask"], ["18_roster_ilsaveth", "ilsaveth"], ["19_roster_oduvar", "oduvar"]]:
		hud.show_character(r[1])
		await _wait(30)
		await _snap(dir, r[0])
	hud.toggle_roster()
	# overview from high above, walls intact
	_cutaway = false
	for o in palace.occluders:
		(o as MeshInstance3D).visible = true
	hud.visible = false
	for n in npcs:
		(n as NPC).set_process(false)
	set_process(false)
	cam.position = Vector3(2, 95, 88)
	cam.look_at(Vector3(2, 0, 2))
	cam.fov = 50
	await _wait(10)
	await _snap(dir, "00_overview")
	get_tree().quit()


func _smoke() -> void:
	var ok := true
	await _wait(240)
	var moved := 0
	for n in npcs:
		var npc := n as NPC
		if npc.mode in ["routine", "wander"]:
			moved += 1
		if not is_finite(npc.global_position.x):
			ok = false
	for id in Cast.characters:
		if id != "player" and not by_id.has(id):
			print("SMOKE missing ", id)
			ok = false
		var c: Dictionary = Cast.characters[id]
		var place: Dictionary = c.get("place", {})
		if place.has("seat") and not palace.seats.has(place["seat"]):
			print("SMOKE %s: unknown seat %s" % [id, place["seat"]])
			ok = false
		for step in place.get("routine", []):
			if not palace.waypoints.has(step[0]):
				print("SMOKE %s: unknown waypoint %s" % [id, step[0]])
				ok = false
		if not Cast.species.has(c.get("species", "")):
			print("SMOKE %s: unknown species" % id)
			ok = false
		if c.get("faction", "") != "" and not Cast.kingdoms.has(c.get("faction", "")):
			print("SMOKE %s: unknown faction" % id)
			ok = false
		if palace.room_at(by_id[id].global_position if by_id.has(id) else Vector3.ZERO).is_empty() and id != "player":
			print("SMOKE %s: outside every room" % id)
			ok = false
	# every waypoint must be reachable from the courtyard
	for w in palace.waypoints:
		if palace.path_between("c_n", w).is_empty():
			print("SMOKE unreachable waypoint ", w)
			ok = false
	print("SMOKE rooms=%d waypoints=%d seats=%d occluders=%d npcs=%d mobile=%d notables=%d" % [
		palace.rooms.size() - 1, palace.waypoints.size(), palace.seats.size(), palace.occluders.size(), npcs.size(), moved, by_id.size()])
	print("SMOKE ", "PASS" if ok else "FAIL")
	get_tree().quit(0 if ok else 1)
