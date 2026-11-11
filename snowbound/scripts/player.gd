class_name Player
extends Node3D
## You: first person as Confucius, with your own body (arms, robe, shoes) below the camera. Moves with a joystick
## vector (touch) or WASD, looks by dragging, stays inside the train's walkable space.

const SPEED := 1.25
const EYE := 1.6

var body: Person
var camera: Camera3D
var yaw := 0.0
var pitch := -0.05
var move := Vector2.ZERO        # from the on-screen joystick, x = strafe, y = forward
var frozen := false             # during conversations and the tribunal
var seated := false
var lying := false
var _pre := Vector3.ZERO          # where you stood before sitting or lying down
var _bob := 0.0
var _look_target: Variant = null
var blocker := Callable()        # extra collision test (closed doors), set by the game
var extra_rects: Array = []      # extra walkable areas (the baggage car)


func _ready() -> void:
	body = Person.new()
	add_child(body)
	body.setup(Cast.PLAYER, true)
	camera = Camera3D.new()
	camera.fov = 68
	camera.near = 0.05
	camera.far = 400
	add_child(camera)
	camera.position = Vector3(0, EYE, 0.04)
	camera.make_current()


func look_drag(rel: Vector2) -> void:
	yaw -= rel.x * 0.0045
	pitch = clampf(pitch - rel.y * 0.0038, -1.2, 1.1)
	_look_target = null


func face(point: Vector3) -> void:
	_look_target = point


func face_clear() -> void:
	_look_target = null


func _ok(p: Vector3) -> bool:
	if blocker.is_valid() and blocker.call(p):
		return false
	if Layout.walkable(p):
		return true
	for r in extra_rects:
		if p.x > r[0] and p.x < r[1] and p.z > r[2] and p.z < r[3]:
			return true
	return false


func sit(spot: Dictionary) -> void:
	if not seated and not lying:
		_pre = position
	lying = false
	body.visible = true
	position = spot["pos"]
	yaw = float(spot["rot"]) + PI   # the model faces +z, the camera looks along -z
	seated = true
	body.set_pose("sit")


func lie(head: Vector3, look_yaw: float) -> void:
	## Lie in a berth: the camera on the pillow, looking along the berth and up at the ceiling.
	if not seated and not lying:
		_pre = position
	seated = false
	lying = true
	position = head
	yaw = look_yaw
	pitch = 0.45
	body.visible = false


func stand() -> void:
	if (seated or lying) and _pre != Vector3.ZERO and Layout.walkable(_pre):
		position = _pre
	seated = false
	lying = false
	body.visible = true
	body.set_pose("idle")


func put(p: Vector3, look_yaw: float) -> void:
	## Place you standing somewhere (new mornings, the baggage car).
	seated = false
	lying = false
	body.visible = true
	body.set_pose("idle")
	position = p
	yaw = look_yaw


func forward() -> Vector3:
	return -camera.global_transform.basis.z


func _process(delta: float) -> void:
	var m := move
	if Input.is_key_pressed(KEY_W):
		m.y += 1
	if Input.is_key_pressed(KEY_S):
		m.y -= 1
	if Input.is_key_pressed(KEY_A):
		m.x -= 1
	if Input.is_key_pressed(KEY_D):
		m.x += 1
	if Input.is_key_pressed(KEY_LEFT):
		yaw += delta * 1.8
	if Input.is_key_pressed(KEY_RIGHT):
		yaw -= delta * 1.8
	if _look_target != null:
		var d: Vector3 = (_look_target as Vector3) - camera.global_position
		var want_yaw := atan2(-d.x, -d.z)
		var want_pitch := asin(clampf(d.normalized().y, -1, 1))
		yaw = lerp_angle(yaw, want_yaw, minf(1.0, delta * 4.0))
		pitch = lerpf(pitch, want_pitch, minf(1.0, delta * 4.0))
	var moving := false
	if not frozen and (seated or lying) and m.length() > 0.6:
		stand()   # push the stick to get up
	if not frozen and not seated and not lying and m.length() > 0.08:
		m = m.limit_length(1.0)
		var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
		var right := Vector3(cos(yaw), 0, -sin(yaw))
		var step := (fwd * m.y + right * m.x) * SPEED * delta
		var p := position + step
		if _ok(p):
			position = p
		elif _ok(position + Vector3(step.x, 0, 0)):
			position += Vector3(step.x, 0, 0)
		elif _ok(position + Vector3(0, 0, step.z)):
			position += Vector3(0, 0, step.z)
		moving = true
		_bob += delta * 8.0
	if seated:
		body.rotation.y = 0
	elif moving and body.pose != "walk":
		body.set_pose("walk")
	elif not moving and body.pose == "walk":
		body.set_pose("idle")
	# your body faces where you look (the model faces +z, the camera looks down -z)
	rotation.y = yaw
	body.rotation.y = PI
	var eye := EYE - (0.45 if seated else 0.0) + (absf(sin(_bob)) * 0.02 if moving else 0.0)
	if lying:
		eye = 0.74
	camera.position = Vector3(0, eye, -0.06)
	camera.rotation = Vector3(pitch, 0, 0)
