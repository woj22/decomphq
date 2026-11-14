class_name NPC
extends Node3D
## A palace inhabitant: a notable character (data/characters.json) or an extra (data/extras.json).
## Modes: "post" (stands at a spot), "seat" (sits), "routine" (walks a loop of waypoints with
## dwell times), "wander" (extras: random waypoints across the palace).

signal said(npc: NPC, text: String)

var id := ""
var info: Dictionary = {}       # character entry or extra template
var notable := false
var display_name := ""
var title := ""
var rig: CharacterRig
var palace: Palace

var mode := "post"
var home_pos := Vector3.ZERO
var home_yaw := 0.0
var seat: Dictionary = {}
var routine: Array = []         # [[waypoint, dwell], ...]
var speed := 1.25

var engaged := false            # talking with the player
var _engage_target := Vector3.ZERO
var _route_i := 0
var _path := PackedVector3Array()
var _path_i := 0
var _dwell := 0.0
var _rng := RandomNumberGenerator.new()
var _bubble: Label3D
var _bubble_t := 0.0
var _yaw := 0.0


func setup(p_palace: Palace, p_id: String, p_info: Dictionary, look: Dictionary, is_notable: bool, rng_seed: int) -> void:
	palace = p_palace
	id = p_id
	info = p_info
	notable = is_notable
	display_name = str(info.get("name", info.get("title", "")))
	title = str(info.get("title", ""))
	_rng.seed = rng_seed
	speed = float(info.get("speed", 1.25)) * _rng.randf_range(0.92, 1.08)
	rig = CharacterBuilder.build_rig(look)
	add_child(rig)
	_bubble = Label3D.new()
	_bubble.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_bubble.no_depth_test = true
	_bubble.fixed_size = true
	_bubble.pixel_size = 0.0011
	_bubble.font_size = 26
	_bubble.outline_size = 10
	_bubble.modulate = Color("fff6e0")
	_bubble.outline_modulate = Color(0.12, 0.08, 0.06, 0.9)
	_bubble.width = 420
	_bubble.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_bubble.position = Vector3(0, rig.height + 0.45, 0)
	_bubble.visible = false
	add_child(_bubble)


func place_at(p: Vector3, yaw: float) -> void:
	mode = "post"
	home_pos = p
	home_yaw = yaw
	position = p
	_yaw = yaw
	rotation.y = yaw


func sit_at(seat_info: Dictionary) -> void:
	mode = "seat"
	seat = seat_info
	var top: float = seat_info["top"]
	var shin: float = rig.dims["shin"]
	home_pos = seat_info["pos"] + Vector3(0, top - shin + 0.02, 0)
	home_yaw = seat_info["yaw"]
	position = home_pos
	_yaw = home_yaw
	rotation.y = home_yaw
	rig.seated = true


func follow_routine(r: Array) -> void:
	mode = "routine"
	routine = r
	_route_i = 0
	var start: String = routine[0][0]
	position = palace.waypoints[start]
	_dwell = _rng.randf_range(0.0, float(routine[0][1]))


func wander() -> void:
	mode = "wander"
	var names := palace.waypoints.keys()
	position = palace.waypoints[names[_rng.randi() % names.size()]]
	_dwell = _rng.randf_range(0.0, 4.0)


func is_available() -> bool:
	return not engaged


func engage(player_pos: Vector3) -> void:
	engaged = true
	_engage_target = player_pos
	rig.speed = 0.0
	rig.talking = true


func disengage() -> void:
	engaged = false
	rig.talking = false


func say(text: String, duration := 4.0) -> void:
	_bubble.text = text
	_bubble.visible = true
	_bubble_t = duration
	rig.talking = true
	said.emit(self, text)


func barks() -> Array:
	if notable:
		return info.get("overheard", [])
	return info.get("barks", [])


func _process(delta: float) -> void:
	if _bubble_t > 0.0:
		_bubble_t -= delta
		if _bubble_t <= 0.0:
			_bubble.visible = false
			if not engaged:
				rig.talking = false
	if engaged:
		if mode != "seat":
			_face_toward(_engage_target, delta, 6.0)
		return
	match mode:
		"post", "seat":
			_yaw = lerp_angle(_yaw, home_yaw, minf(1.0, delta * 3.0))
			rotation.y = _yaw
			if mode == "post" and position.distance_to(home_pos) > 0.05:
				position = position.move_toward(home_pos, delta * 1.0)
		"routine", "wander":
			_step_route(delta)


func _step_route(delta: float) -> void:
	if _path_i < _path.size():
		var target := _path[_path_i]
		var to := target - position
		to.y = 0.0
		var dist := to.length()
		if dist < 0.12:
			_path_i += 1
			return
		var step := minf(dist, speed * delta)
		position += to / dist * step
		_face_toward(target, delta, 7.0)
		rig.speed = speed
		return
	rig.speed = 0.0
	if _dwell > 0.0:
		_dwell -= delta
		return
	# choose the next destination
	var from := palace.nearest_waypoint(position)
	var dest := ""
	if mode == "routine":
		_route_i = (_route_i + 1) % routine.size()
		dest = routine[_route_i][0]
		_dwell = float(routine[_route_i][1]) * _rng.randf_range(0.8, 1.25)
	else:
		var names := palace.waypoints.keys()
		dest = names[_rng.randi() % names.size()]
		_dwell = _rng.randf_range(1.0, 7.0)
	_path = palace.path_between(from, dest)
	# scatter the end point a little so walkers don't stack
	if _path.size() > 0:
		_path[_path.size() - 1] += Vector3(_rng.randf_range(-0.7, 0.7), 0, _rng.randf_range(-0.7, 0.7))
	_path_i = 0


func _face_toward(p: Vector3, delta: float, rate: float) -> void:
	var d := p - position
	if Vector2(d.x, d.z).length() < 0.01:
		return
	var want := atan2(-d.x, -d.z)
	_yaw = lerp_angle(_yaw, want, minf(1.0, delta * rate))
	rotation.y = _yaw
