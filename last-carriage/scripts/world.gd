class_name World
extends Node3D
## The snowbound carriage at midnight: the Blender carriage with textured materials, warm lamps, frosted windows,
## a blizzard outside (driven snow, snowed-in pines, a lamp post), and the player's first-person look-around camera.

signal looked_around

const SEATS := [  # bench centres round the table, clockwise from above: 0 = you (window), 1 = beside you, 2 = across from 1, 3 = opposite you
	{"pos": Vector3(-1.125, 0, 0.82), "rot": PI},
	{"pos": Vector3(-0.615, 0, 0.82), "rot": PI},
	{"pos": Vector3(-0.615, 0, -0.82), "rot": 0.0},
	{"pos": Vector3(-1.125, 0, -0.82), "rot": 0.0},
]
const EYE := Vector3(-1.125, 1.28, 0.79)
# How far a seated passenger can turn. Further than this the camera ends up inside the seat back and wall pillar
# (left) or the neighbour's head (right), and the near-plane clipping flickers with the carriage sway.
const YAW_LEFT := 1.75
const YAW_RIGHT := -1.9
const PITCH_DOWN := -1.15
const PITCH_UP := 0.95

var camera: Camera3D
var passengers: Array = []   # Passenger per seat (seat 0 is the player's own body, head hidden)
var yaw := 0.0
var pitch := -0.12
var target: Variant = null   # Vector2(yaw, pitch) to glide toward, or null
var auto_look := true
var _snow: Array[CPUParticles3D] = []
var _gust := 0.0
var _t := 0.0
var _ceiling: Array[OmniLight3D] = []
var _dragging := false
var _last_drag := -100.0  # auto-turn holds off for a few seconds after the player looks around


func _ready() -> void:
	_environment()
	_carriage()
	_lights()
	_outside()
	_blizzard()
	camera = Camera3D.new()
	camera.fov = 72
	camera.near = 0.03
	camera.far = 160
	camera.position = EYE
	add_child(camera)
	camera.make_current()


# ------------------------------------------------------------------ scene
func _environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("10141c")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("4a5266")
	env.ambient_light_energy = 0.85
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_exposure = 0.95
	env.fog_enabled = true
	env.fog_light_color = Color("2a3140")
	env.fog_density = 0.045
	env.fog_sky_affect = 1.0
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 1.4
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.08
	env.adjustment_contrast = 1.05
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _tex_mat(tex: String, scale: float, tint := Color.WHITE, rough := 0.6, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_texture = load("res://assets/textures/%s.png" % tex)
	m.albedo_color = tint
	m.uv1_triplanar = true
	m.uv1_world_triplanar = true
	m.uv1_scale = Vector3.ONE * scale
	m.roughness = rough
	m.metallic = metal
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	return m


func _carriage() -> void:
	var car: Node3D = load("res://assets/models/carriage.glb").instantiate()
	add_child(car)
	var swap := {
		"Wood": _tex_mat("wood", 1.6, Color(0.66, 0.58, 0.55), 0.42),
		"WoodDark": _tex_mat("wood", 2.2, Color(0.42, 0.36, 0.34), 0.38),
		"Upholstery": _tex_mat("moquette", 3.0, Color.WHITE, 0.95),
		"Carpet": _tex_mat("carpet", 0.5, Color.WHITE, 1.0),
		"Runner": _tex_mat("carpet", 0.9, Color(1.4, 0.9, 0.9), 1.0),
		"Cream": _tex_mat("cream", 0.6, Color.WHITE, 0.85),
	}
	var frost := ShaderMaterial.new()
	frost.shader = load("res://shaders/frost.gdshader")
	for mi in car.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = (mi as MeshInstance3D).mesh
		for i in mesh.get_surface_count():
			var m := mesh.surface_get_material(i)
			if m == null:
				continue
			var key := m.resource_name
			if swap.has(key):
				(mi as MeshInstance3D).set_surface_override_material(i, swap[key])
			elif key == "Glass" and String(mi.name).begins_with("Windows"):
				(mi as MeshInstance3D).set_surface_override_material(i, frost)
			elif key == "Glass":  # door windows: dark glass onto the gangway
				var g := StandardMaterial3D.new()
				g.albedo_color = Color(0.05, 0.07, 0.1)
				g.roughness = 0.05
				g.metallic = 0.5
				(mi as MeshInstance3D).set_surface_override_material(i, g)
			elif key == "LampGlow" or key == "LampShade":
				var bm := (m as BaseMaterial3D).duplicate() as BaseMaterial3D
				bm.emission_enabled = true
				bm.emission_energy_multiplier = 0.9 if key == "LampGlow" else 0.45
				(mi as MeshInstance3D).set_surface_override_material(i, bm)
			elif key == "Brass":
				var b := (m as BaseMaterial3D).duplicate() as BaseMaterial3D
				b.metallic = 0.85
				b.roughness = 0.3
				b.albedo_color = Color("c9a04e")
				b.rim_enabled = true
				b.rim = 0.4
				(mi as MeshInstance3D).set_surface_override_material(i, b)
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if key == "Upholstery" or key == "WoodDark" else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _lights() -> void:
	# a warm globe over our table casts the only shadows; the others light the length of the carriage
	for z in [0.0, -3.0, 3.0, -6.0, 6.0]:
		var l := OmniLight3D.new()
		l.position = Vector3(0, 2.25, z)
		l.light_color = Color("ffd9a6")
		l.light_energy = 1.05 if z == 0.0 else 0.8
		l.omni_range = 4.2
		l.omni_attenuation = 1.2
		l.shadow_enabled = z == 0.0
		l.shadow_bias = 0.04
		add_child(l)
		_ceiling.append(l)
	var lamp := OmniLight3D.new()  # the little table lamp by your window
	lamp.position = Vector3(-1.27, 0.97, 0)
	lamp.light_color = Color("ffb867")
	lamp.light_energy = 0.55
	lamp.omni_range = 1.9
	lamp.omni_attenuation = 1.6
	add_child(lamp)
	var moon := DirectionalLight3D.new()  # cold storm-light through the windows
	moon.rotation_degrees = Vector3(-35, -70, 0)
	moon.light_color = Color("8fa6d8")
	moon.light_energy = 0.35
	add_child(moon)


func _outside() -> void:
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(170, 170)
	pm.subdivide_width = 90
	pm.subdivide_depth = 90
	ground.mesh = pm
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/snow_ground.gdshader")
	ground.material_override = sm
	ground.position.y = -1.5
	add_child(ground)
	# rails buried in snow and the bank either side
	var pines := [load("res://assets/models/pine_a.glb"), load("res://assets/models/pine_b.glb"), load("res://assets/models/pine_c.glb")]
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	for i in 110:
		var side := -1.0 if i % 2 == 0 else 1.0
		var x := side * rng.randf_range(4.5, 55.0)
		var z := rng.randf_range(-70.0, 70.0)
		if side < 0 and absf(z + 2.5) < 3.0 and absf(x) < 9.0:
			continue  # keep a clear view to the lamp post
		var t: Node3D = pines[rng.randi() % 3].instantiate()
		t.position = Vector3(x, -1.3 + rng.randf_range(-0.2, 0.3), z)
		t.rotation.y = rng.randf() * TAU
		t.scale = Vector3.ONE * rng.randf_range(0.7, 1.4)
		add_child(t)
	# a railway lamp outside your window, the only light out there
	var post: Node3D = load("res://assets/models/lamp_post.glb").instantiate()
	post.position = Vector3(-5.2, -1.2, -2.6)
	post.rotation.y = PI
	add_child(post)
	var pl := OmniLight3D.new()
	pl.position = Vector3(-5.65, 1.6, -2.6)
	pl.light_color = Color("ffc070")
	pl.light_energy = 3.0
	pl.omni_range = 11.0
	pl.omni_attenuation = 1.3
	add_child(pl)
	# far snowbound hills
	var hill_mat := StandardMaterial3D.new()
	hill_mat.albedo_color = Color("aab4c4")
	hill_mat.roughness = 0.9
	for i in 10:
		var h := MeshInstance3D.new()
		var s := SphereMesh.new()
		s.radius = rng.randf_range(18, 32)
		s.height = s.radius * 2
		h.mesh = s
		h.material_override = hill_mat
		var side := -1.0 if i % 2 == 0 else 1.0
		h.position = Vector3(side * rng.randf_range(60, 80), -s.radius * 0.75, rng.randf_range(-60, 60))
		h.scale = Vector3(1.6, 0.6, 1.4)
		add_child(h)


func _snow_material(size: float) -> QuadMesh:
	var grad := Gradient.new()
	grad.set_color(0, Color(1, 1, 1, 1))
	grad.set_color(1, Color(1, 1, 1, 0))
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 32
	tex.height = 32
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.albedo_texture = tex
	m.albedo_color = Color(0.92, 0.95, 1.0, 0.95)
	m.vertex_color_use_as_albedo = true
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	q.material = m
	return q


func _blizzard() -> void:
	for side in [-1.0, 1.0]:
		for layer in [{"x": 9.0, "ext": Vector3(7, 4.5, 16), "n": 1800, "size": 0.05},
				{"x": 2.4, "ext": Vector3(0.6, 1.6, 10), "n": 420, "size": 0.03}]:
			var p := CPUParticles3D.new()
			p.amount = layer["n"]
			p.lifetime = 3.2
			p.preprocess = 3.2
			p.local_coords = false
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
			p.emission_box_extents = layer["ext"]
			p.position = Vector3(side * float(layer["x"]), 2.0, -6.0)
			p.direction = Vector3(side * 0.12, -0.25, 1.0)
			p.spread = 12
			p.initial_velocity_min = 6.0
			p.initial_velocity_max = 10.0
			p.gravity = Vector3(0, -1.6, 0)
			p.scale_amount_min = 0.5
			p.scale_amount_max = 1.6
			p.color = Color(1, 1, 1, 0.9)
			p.mesh = _snow_material(layer["size"])
			add_child(p)
			_snow.append(p)


# ------------------------------------------------------------------ passengers
func seat_passengers(figs: Array) -> void:
	for p in passengers:
		p.queue_free()
	passengers.clear()
	for seat in 4:
		var p := Passenger.new()
		add_child(p)
		p.position = SEATS[seat]["pos"]
		p.rotation.y = SEATS[seat]["rot"]
		p.setup(figs[seat], seat == 0)
		passengers.append(p)


func head_point(seat: int) -> Vector3:
	if seat == 0:
		return camera.global_position
	return passengers[seat].head_world()


func everyone_look_at(seat: int, speaker_target := -1) -> void:
	for s in range(1, 4):
		var p: Passenger = passengers[s]
		if s == seat:
			p.look_target = head_point(speaker_target) if speaker_target >= 0 else null
		else:
			p.look_target = head_point(seat)


func turn_to(seat: int) -> void:
	if not auto_look or seat == 0 or _t - _last_drag < 4.0:
		return
	var d := (head_point(seat) - Vector3(0, 0.06, 0) - EYE).normalized()
	var ty := clampf(atan2(-d.x, -d.z), YAW_RIGHT, YAW_LEFT)
	target = Vector2(ty, clampf(asin(d.y), pitch_floor(ty), PITCH_UP))


## Looking straight down shows your hands on the table; turned to the side, looking down would put the camera
## inside your own shoulder, so the lowest pitch rises as you turn.
func pitch_floor(y: float) -> float:
	return lerpf(PITCH_DOWN, -0.4, smoothstep(0.2, 1.0, absf(y)))


func reset_view() -> void:
	target = Vector2(0.0, -0.12)


# ------------------------------------------------------------------ look controls
func _unhandled_input(e: InputEvent) -> void:
	if e.device == InputEvent.DEVICE_ID_EMULATION:
		return  # a phone touch also arrives as an emulated mouse event: count it once
	if e is InputEventScreenTouch or (e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT):
		_dragging = e.pressed
		if e.pressed:
			target = null
	elif e is InputEventScreenDrag or (e is InputEventMouseMotion and _dragging):
		var rel: Vector2 = e.relative
		var k := 0.0045 * 1280.0 / maxf(640.0, get_viewport().get_visible_rect().size.x)
		yaw += rel.x * k
		pitch += rel.y * k * 0.8
		target = null
		_last_drag = _t
		looked_around.emit()


func _process(delta: float) -> void:
	_t += delta
	if Input.is_key_pressed(KEY_LEFT):
		yaw += delta * 1.6
	if Input.is_key_pressed(KEY_RIGHT):
		yaw -= delta * 1.6
	if Input.is_key_pressed(KEY_UP):
		pitch += delta * 1.2
	if Input.is_key_pressed(KEY_DOWN):
		pitch -= delta * 1.2
	if target != null:
		var tv: Vector2 = target
		yaw = lerpf(yaw, tv.x, minf(1.0, delta * 3.0))
		pitch = lerpf(pitch, tv.y, minf(1.0, delta * 3.0))
		if absf(yaw - tv.x) < 0.004 and absf(pitch - tv.y) < 0.004:
			target = null
	yaw = clampf(yaw, YAW_RIGHT, YAW_LEFT)
	pitch = clampf(pitch, pitch_floor(yaw), PITCH_UP)
	# the stopped carriage only rocks when the wind gusts against it
	_gust = maxf(0.0, _gust - delta * 0.5)
	if randf() < delta * 0.07:
		_gust = 1.0
	var sway := sin(_t * 2.3) * 0.006 * _gust
	camera.position = EYE + Vector3(sway, 0, 0)
	camera.rotation = Vector3(pitch, yaw, sway * 0.6)
	for p in _snow:
		p.gravity = Vector3(0, -1.6, 2.5 * _gust)
	# the power struggles in the cold: now and then the ceiling lamps dip
	var dip := sin(_t * 13.0) > 0.97 and sin(_t * 0.31) > 0.6
	for i in _ceiling.size():
		_ceiling[i].light_energy = (0.7 if dip else 1.0) * (1.05 if i == 0 else 0.8)


func gust_level() -> float:
	return _gust
