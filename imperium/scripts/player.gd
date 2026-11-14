class_name PlayerController
extends CharacterBody3D
## The King of Seravel. Moves on screen-relative input (joystick or WASD), or walks itself
## toward a tapped character (`walk_to`). Input is relative to the camera heading (`view_yaw`).

signal arrived(target: Node3D)

const WALK := 3.6

var rig: CharacterRig
var input_dir := Vector2.ZERO      # set by the HUD joystick; keyboard is read here
var view_yaw := 0.0                # camera heading: input is screen-relative
var frozen := false
var npcs: Array = []               # for soft separation
var _yaw := PI
var _auto_target: Node3D = null
var _auto_time := 0.0


func _ready() -> void:
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.34
	cap.height = 1.7
	shape.shape = cap
	shape.position = Vector3(0, 0.85, 0)
	add_child(shape)
	rig = CharacterBuilder.build_rig(Cast.look_for("player"))
	add_child(rig)
	floor_snap_length = 0.3
	rotation.y = _yaw


func walk_to(target: Node3D) -> void:
	_auto_target = target
	_auto_time = 8.0


func cancel_walk() -> void:
	_auto_target = null


func _physics_process(delta: float) -> void:
	var dir := Vector2.ZERO
	if not frozen:
		var k := Vector2(
			float(Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT)) - float(Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT)),
			float(Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN)) - float(Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP)))
		dir = input_dir if input_dir.length() > 0.05 else k
		if dir.length() > 0.05:
			var w := Basis(Vector3.UP, view_yaw) * Vector3(dir.x, 0, dir.y)
			dir = Vector2(w.x, w.z)
			_auto_target = null
		elif _auto_target != null:
			_auto_time -= delta
			var to := _auto_target.global_position - global_position
			to.y = 0.0
			if to.length() < 1.7 or _auto_time <= 0.0:
				var t := _auto_target
				_auto_target = null
				if to.length() < 2.6:
					arrived.emit(t)
			else:
				dir = Vector2(to.x, to.z).normalized()
	if dir.length() > 1.0:
		dir = dir.normalized()
	var v := Vector3(dir.x, 0, dir.y) * WALK
	velocity.x = v.x
	velocity.z = v.z
	velocity.y = 0.0 if is_on_floor() else velocity.y - 18.0 * delta
	move_and_slide()
	# soft separation from characters (they have no physics bodies)
	for n in npcs:
		var npc := n as Node3D
		var d := global_position - npc.global_position
		d.y = 0.0
		var l := d.length()
		if l < 0.7 and l > 0.001:
			global_position += d / l * (0.7 - l)
	var flat := Vector2(v.x, v.z)
	if flat.length() > 0.1:
		_yaw = lerp_angle(_yaw, atan2(-flat.x, -flat.y), minf(1.0, delta * 12.0))
		rotation.y = _yaw
	rig.speed = flat.length()


func face(p: Vector3) -> void:
	var d := p - global_position
	_yaw = atan2(-d.x, -d.z)
	rotation.y = _yaw
