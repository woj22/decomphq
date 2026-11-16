extends CharacterBody3D
## First-person explorer used to look around the prototype (movement only, no gameplay).
## Desktop: click to capture the mouse, WASD/arrows move, Shift runs, Space jumps, F toggles fly, Esc releases.
## Touch: see touch_controls.gd (left stick, right-side drag to look, jump and fly buttons).

const WALK := 5.5
const RUN := 10.0
const FLY := 16.0
const JUMP := 5.2
const GRAVITY := 11.0          # a little lighter than Earth
const EYE := 1.62
const BOUND := 96.0

var cam: Camera3D
var yaw := 0.0
var pitch := 0.0
var fly := false
var frozen := false
## Fed by touch_controls.gd every frame.
var stick := Vector2.ZERO
var touch_jump := false
var spawn_point := Vector3.ZERO
var _bob := 0.0


func _ready() -> void:
	var shape := CapsuleShape3D.new()
	shape.radius = 0.35
	shape.height = 1.75
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.position.y = 0.875
	add_child(cs)
	cam = Camera3D.new()
	cam.position.y = EYE
	cam.fov = 72.0
	cam.near = 0.08
	cam.far = 340.0
	add_child(cam)
	cam.make_current()
	floor_max_angle = deg_to_rad(52.0)
	floor_snap_length = 0.45
	_make_spores()


func spawn_at(p: Vector3, facing: Vector3) -> void:
	spawn_point = p
	position = p
	yaw = atan2(-facing.x, -facing.z)
	pitch = deg_to_rad(4.0)
	_apply_look()


func look_from(eye: Vector3, target: Vector3) -> void:
	position = eye - Vector3(0, EYE, 0)
	var d := (target - eye).normalized()
	yaw = atan2(-d.x, -d.z)
	pitch = asin(clampf(d.y, -1.0, 1.0))
	_apply_look()


func add_look(delta: Vector2) -> void:
	yaw -= delta.x
	pitch = clampf(pitch - delta.y, deg_to_rad(-85.0), deg_to_rad(85.0))
	_apply_look()


func _apply_look() -> void:
	rotation = Vector3(0, yaw, 0)
	if cam:
		cam.rotation = Vector3(pitch, 0, 0)


func toggle_fly() -> void:
	fly = not fly
	velocity = Vector3.ZERO


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and not OS.has_feature("mobile"):
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not DisplayServer.is_touchscreen_available():
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		add_look(e.relative * 0.0024)
	elif e is InputEventKey and e.pressed and not e.echo:
		match e.physical_keycode:
			KEY_ESCAPE:
				Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
			KEY_F:
				toggle_fly()


func _keys() -> Vector2:
	var v := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP): v.y += 1
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN): v.y -= 1
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT): v.x += 1
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT): v.x -= 1
	return v.limit_length(1.0)


func _physics_process(dt: float) -> void:
	if frozen:
		return
	var k := _keys()
	var inp := k if k != Vector2.ZERO else stick
	var running := Input.is_physical_key_pressed(KEY_SHIFT) or (k == Vector2.ZERO and stick.length() > 0.92)
	var jump := Input.is_physical_key_pressed(KEY_SPACE) or touch_jump
	var fwd := -global_transform.basis.z
	var right := global_transform.basis.x
	if fly:
		var look := -cam.global_transform.basis.z
		var v := (look * inp.y + right * inp.x) * FLY * (1.8 if running else 1.0)
		if jump: v.y += FLY * 0.6
		if Input.is_physical_key_pressed(KEY_CTRL) or Input.is_physical_key_pressed(KEY_C): v.y -= FLY * 0.6
		velocity = velocity.lerp(v, clampf(dt * 6.0, 0.0, 1.0))
	else:
		var speed := RUN if running else WALK
		var want := (fwd * inp.y + right * inp.x) * speed
		var accel := 10.0 if is_on_floor() else 2.5
		velocity.x = lerpf(velocity.x, want.x, clampf(dt * accel, 0.0, 1.0))
		velocity.z = lerpf(velocity.z, want.z, clampf(dt * accel, 0.0, 1.0))
		if is_on_floor():
			if jump:
				velocity.y = JUMP
		else:
			velocity.y -= GRAVITY * dt
	move_and_slide()
	# gentle head bob while walking
	var hs := Vector2(velocity.x, velocity.z).length()
	if not fly and is_on_floor() and hs > 0.5:
		_bob += dt * hs * 1.6
	cam.position.y = lerpf(cam.position.y, EYE + (sin(_bob) * 0.04 if not fly else 0.0), clampf(dt * 10.0, 0.0, 1.0))
	# keep inside the bowl
	var flat := Vector2(position.x, position.z)
	if flat.length() > BOUND:
		flat = flat.normalized() * BOUND
		position.x = flat.x
		position.z = flat.y
	if position.y < -40.0 or position.y > 160.0:
		position = spawn_point
		velocity = Vector3.ZERO


func _make_spores() -> void:
	var p := CPUParticles3D.new()
	p.amount = 140
	p.lifetime = 9.0
	p.preprocess = 9.0
	p.local_coords = false
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(22, 7, 22)
	p.direction = Vector3(0.3, 1, 0)
	p.spread = 60.0
	p.initial_velocity_min = 0.05
	p.initial_velocity_max = 0.3
	p.gravity = Vector3(0.05, 0.04, 0)
	p.scale_amount_min = 0.5
	p.scale_amount_max = 1.4
	var grad := Gradient.new()
	grad.set_color(0, Color(0.5, 1.0, 0.9, 0.0))
	grad.set_color(1, Color(1.0, 0.6, 0.9, 0.0))
	grad.add_point(0.2, Color(0.55, 1.0, 0.9, 1.0))
	grad.add_point(0.8, Color(0.95, 0.65, 1.0, 1.0))
	p.color_ramp = grad
	var q := QuadMesh.new()
	q.size = Vector2(0.07, 0.07)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.vertex_color_use_as_albedo = true
	m.albedo_color = Color(1.4, 1.4, 1.4)
	q.material = m
	p.mesh = q
	p.position.y = 3.0
	add_child(p)
