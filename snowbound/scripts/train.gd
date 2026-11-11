class_name Train
extends Node3D
## Assembles the train from the baked Blender modules, gives every surface its textured baked-light material, adds the
## real-time lamps (for characters and highlights) and builds the blizzard outside.

const COMPARTMENTS := 6
const BAY := 2.4
const DINING_Z := 17.6
const SHADER := preload("res://shaders/baked.gdshader")

# material name -> [albedo, normal, rough, tint, roughness, metallic, specular]
const TEX := "res://assets/textures/%s"
const LOOK := {
	"Panel": ["rosewood_veneer1_albedo.jpg", "rosewood_veneer1_normal.jpg", "rosewood_veneer1_rough.jpg", Color(0.5, 0.32, 0.26), 0.3, 0.0, 0.6],
	"Trim": ["wood_table_001_albedo.jpg", "wood_table_001_normal.jpg", "wood_table_001_rough.jpg", Color(0.7, 0.58, 0.52), 0.26, 0.0, 0.6],
	"Floorwood": ["wood_table_001_albedo.jpg", "wood_table_001_normal.jpg", "wood_table_001_rough.jpg", Color(0.62, 0.52, 0.48), 0.45, 0.0, 0.5],
	"Velvet": ["velour_velvet_grey.jpg", "velour_velvet_normal.jpg", "", Color(0.38, 0.05, 0.09), 0.85, 0.0, 0.25],
	"Damask": ["floral_jacquard_grey.jpg", "floral_jacquard_normal.jpg", "", Color(0.45, 0.09, 0.12), 0.8, 0.0, 0.3],
	"Carpet": ["floral_jacquard_grey.jpg", "floral_jacquard_normal.jpg", "", Color(0.36, 0.08, 0.1), 0.95, 0.0, 0.2],
	"Linen": ["rough_linen_grey.jpg", "rough_linen_normal.jpg", "", Color(0.95, 0.9, 0.84), 0.9, 0.0, 0.3],
	"Tablecloth": ["rough_linen_grey.jpg", "rough_linen_normal.jpg", "", Color(0.95, 0.92, 0.86), 0.85, 0.0, 0.3],
	"Leather": ["brown_leather_albedo.jpg", "brown_leather_normal.jpg", "brown_leather_rough.jpg", Color(1, 1, 1), 0.6, 0.0, 0.5],
	"Runner": ["runner_albedo.jpg", "", "", Color(1, 1, 1), 0.95, 0.0, 0.2],
	"Ceiling": ["ceiling_albedo.jpg", "", "", Color(0.72, 0.66, 0.58), 0.8, 0.0, 0.3],
	"Picture": ["picture_albedo.jpg", "", "", Color(1, 1, 1), 0.9, 0.0, 0.2],
	"Brass": ["", "", "", Color("c9a050"), 0.28, 0.85, 0.5],
	"Silver": ["", "", "", Color("c8c8cc"), 0.2, 0.9, 0.5],
}
const GLOW := {"LampShade": [Color(1.0, 0.74, 0.45), 1.6], "LampGlass": [Color(1.0, 0.86, 0.68), 2.2], "StoveGlow": [Color(1.0, 0.42, 0.12), 7.0]}

var lights: Array[OmniLight3D] = []
var _flicker_t := 0.0
var _snow: Array[GPUParticles3D] = []


func _ready() -> void:
	_environment()
	_place("sleeper_front", Vector3.ZERO)
	for i in COMPARTMENTS:
		_place("compartment", Vector3(0, 0, i * BAY))
		_place("corridor", Vector3(0, 0, i * BAY))
	_place("sleeper_rear", Vector3.ZERO)
	for i in 4:
		_place("dining_bay", Vector3(0, 0, DINING_Z + i * BAY))
	_place("dining_end", Vector3(0, 0, DINING_Z + 4 * BAY))
	_outside()
	_blizzard()


# ------------------------------------------------------------------ modules
var _mat_cache := {}


func _place(module: String, at: Vector3) -> void:
	var scene: Node3D = load("res://assets/train/%s.glb" % module).instantiate()
	scene.position = at
	add_child(scene)
	var lm: Texture2D = load("res://assets/train/%s_lm.png" % module)
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		var inst := mi as MeshInstance3D
		var glass := String(inst.name).ends_with("_glass")
		for s in inst.mesh.get_surface_count():
			var src := inst.mesh.surface_get_material(s)
			if src == null:
				continue
			inst.set_surface_override_material(s, _glass(src) if glass else _baked(module, src, lm))
		inst.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var f := FileAccess.open("res://assets/train/%s_lights.json" % module, FileAccess.READ)
	for l in JSON.parse_string(f.get_as_text()):
		var p: Array = l["pos"]
		_lamp(at + Vector3(p[0], p[1], p[2]), String(l["kind"]))


func _baked(module: String, src: Material, lm: Texture2D) -> Material:
	var key := module + "/" + src.resource_name
	if _mat_cache.has(key):
		return _mat_cache[key]
	var m := ShaderMaterial.new()
	m.shader = SHADER
	m.set_shader_parameter("lightmap", lm)
	var name := src.resource_name
	var base := (src as BaseMaterial3D).albedo_color if src is BaseMaterial3D else Color.WHITE
	if LOOK.has(name):
		var d: Array = LOOK[name]
		if d[0] != "":
			m.set_shader_parameter("albedo_tex", load(TEX % d[0]))
			m.set_shader_parameter("use_albedo", true)
		if d[1] != "":
			m.set_shader_parameter("normal_tex", load(TEX % d[1]))
			m.set_shader_parameter("use_normal", true)
		if d[2] != "":
			m.set_shader_parameter("rough_tex", load(TEX % d[2]))
			m.set_shader_parameter("use_rough", true)
		m.set_shader_parameter("tint", d[3] if d[0] != "" else d[3])
		m.set_shader_parameter("roughness", d[4])
		m.set_shader_parameter("metallic", d[5])
		m.set_shader_parameter("specular", d[6])
	else:
		m.set_shader_parameter("tint", base)
		m.set_shader_parameter("roughness", (src as BaseMaterial3D).roughness if src is BaseMaterial3D else 0.6)
	if GLOW.has(name):
		m.set_shader_parameter("glow_color", GLOW[name][0])
		m.set_shader_parameter("glow_energy", GLOW[name][1])
	_mat_cache[key] = m
	return m


func _glass(src: Material) -> Material:
	var key := "glass/" + src.resource_name
	if _mat_cache.has(key):
		return _mat_cache[key]
	var g := StandardMaterial3D.new()
	g.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var c := (src as BaseMaterial3D).albedo_color if src is BaseMaterial3D else Color(0.7, 0.8, 0.9)
	g.albedo_color = Color(c.r, c.g, c.b, 0.14 if src.resource_name == "Glass" else 0.55)
	g.roughness = 0.04
	g.metallic_specular = 0.9
	g.cull_mode = BaseMaterial3D.CULL_DISABLED
	_mat_cache[key] = g
	return g


func _lamp(p: Vector3, kind: String) -> void:
	var l := OmniLight3D.new()
	l.position = p
	match kind:
		"sconce":
			l.light_color = Color(1.0, 0.72, 0.46)
			l.light_energy = 0.9
			l.omni_range = 3.0
		"dome":
			l.light_color = Color(1.0, 0.8, 0.58)
			l.light_energy = 1.0
			l.omni_range = 3.4
		"table_lamp":
			l.light_color = Color(1.0, 0.7, 0.42)
			l.light_energy = 0.6
			l.omni_range = 2.0
		"fire":
			l.light_color = Color(1.0, 0.45, 0.15)
			l.light_energy = 1.2
			l.omni_range = 3.5
	l.omni_attenuation = 1.4
	l.light_specular = 1.0
	l.set_meta("base", l.light_energy)
	l.set_meta("kind", kind)
	add_child(l)
	lights.append(l)


# ------------------------------------------------------------------ outside
func _environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/sky.gdshader")
	sky.sky_material = sm
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.3, 0.32, 0.42)
	env.ambient_light_energy = 0.25
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 0.82
	env.tonemap_white = 6.0
	env.glow_enabled = true
	env.glow_intensity = 0.55
	env.glow_bloom = 0.03
	env.glow_hdr_threshold = 1.2
	env.fog_enabled = true
	env.fog_light_color = Color(0.2, 0.24, 0.36)
	env.fog_density = 0.02
	env.fog_sky_affect = 0.4
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.12
	env.adjustment_saturation = 0.95
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	var moon := DirectionalLight3D.new()  # cold dusk light on the snow outside (the bake carries it indoors)
	moon.rotation_degrees = Vector3(-18, 70, 0)
	moon.light_color = Color(0.55, 0.64, 0.92)
	moon.light_energy = 0.35
	moon.light_cull_mask = 1 << 1  # outside only (layer 2)
	add_child(moon)


func _outside() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 21
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(260, 300)
	pm.subdivide_width = 100
	pm.subdivide_depth = 100
	ground.mesh = pm
	var gm := ShaderMaterial.new()
	gm.shader = load("res://shaders/snow_ground.gdshader")
	ground.material_override = gm
	ground.position = Vector3(0, -1.3, 15)
	ground.layers = 2
	add_child(ground)
	var pines := [load("res://assets/outside/pine_a.glb"), load("res://assets/outside/pine_b.glb"), load("res://assets/outside/pine_c.glb")]
	for i in 220:
		var side := -1.0 if i % 2 == 0 else 1.0
		var x := side * (5.0 + pow(rng.randf(), 1.4) * 80.0)
		var t: Node3D = pines[rng.randi() % 3].instantiate()
		t.position = Vector3(x, -1.3, rng.randf_range(-70, 100))
		t.rotation.y = rng.randf() * TAU
		t.scale = Vector3.ONE * rng.randf_range(0.8, 1.7)
		_set_layer(t, 2)
		add_child(t)
	for side in [-1.0, 1.0]:
		var ridge := MeshInstance3D.new()
		ridge.mesh = _mountains(rng, side)
		var mm := StandardMaterial3D.new()
		mm.vertex_color_use_as_albedo = true
		mm.roughness = 0.9
		ridge.material_override = mm
		ridge.layers = 2
		add_child(ridge)


func _set_layer(n: Node, layer: int) -> void:
	if n is VisualInstance3D:
		(n as VisualInstance3D).layers = layer
	for c in n.get_children():
		_set_layer(c, layer)


func _mountains(rng: RandomNumberGenerator, side: float) -> ArrayMesh:
	## A ring segment of snow-capped peaks along one side of the line: dark rock below, snow above.
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 90
	var dist := 150.0
	var prev_top := Vector3.ZERO
	var prev_bot := Vector3.ZERO
	var noise := FastNoiseLite.new()
	noise.seed = int(side * 7 + 11)
	noise.frequency = 0.02
	for i in n + 1:
		var z := -200.0 + 450.0 * i / n
		var h := 30.0 + 55.0 * absf(noise.get_noise_1d(z)) + 25.0 * absf(noise.get_noise_1d(z * 3.1))
		var top := Vector3(side * (dist + absf(noise.get_noise_1d(z * 0.5)) * 50.0), h, z)
		var bot := Vector3(side * (dist - 20.0), -2.0, z)
		if i > 0:
			for v in [[prev_bot, 0.0], [prev_top, 1.0], [top, 1.0], [prev_bot, 0.0], [top, 1.0], [bot, 0.0]]:
				var p: Vector3 = v[0]
				var snow := smoothstep(25.0, 50.0, p.y + rng.randf() * 6.0)
				st.set_color(Color(0.12, 0.13, 0.17).lerp(Color(0.72, 0.78, 0.9), snow))
				st.add_vertex(p)
		prev_top = top
		prev_bot = bot
	st.generate_normals()
	return st.commit()


func _blizzard() -> void:
	for side in [-1.0, 1.0]:
		var p := GPUParticles3D.new()
		p.amount = 2600
		p.lifetime = 3.0
		p.preprocess = 3.0
		p.visibility_aabb = AABB(Vector3(-20, -8, -40), Vector3(40, 20, 80))
		var pm := ParticleProcessMaterial.new()
		pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
		pm.emission_box_extents = Vector3(8, 4, 26)
		pm.direction = Vector3(side * 0.1, -0.3, -1.0)
		pm.spread = 14
		pm.initial_velocity_min = 7.0
		pm.initial_velocity_max = 12.0
		pm.gravity = Vector3(0, -1.5, 0)
		pm.turbulence_enabled = true
		pm.turbulence_noise_strength = 1.4
		pm.scale_min = 0.5
		pm.scale_max = 1.5
		p.process_material = pm
		var q := QuadMesh.new()
		q.size = Vector2(0.05, 0.05)
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		var grad := Gradient.new()
		grad.set_color(0, Color(1, 1, 1, 1))
		grad.set_color(1, Color(1, 1, 1, 0))
		var tex := GradientTexture2D.new()
		tex.gradient = grad
		tex.fill = GradientTexture2D.FILL_RADIAL
		tex.fill_from = Vector2(0.5, 0.5)
		tex.fill_to = Vector2(1, 0.5)
		m.albedo_texture = tex
		m.albedo_color = Color(0.85, 0.9, 1.0, 0.9)
		q.material = m
		p.draw_pass_1 = q
		p.position = Vector3(side * 10.5, 2.5, 15)
		p.layers = 2
		add_child(p)
		_snow.append(p)


func _process(delta: float) -> void:
	_flicker_t += delta
	for l in lights:
		if String(l.get_meta("kind")) == "fire":
			l.light_energy = float(l.get_meta("base")) * (0.85 + 0.15 * sin(_flicker_t * 9.0) * sin(_flicker_t * 5.3))
