extends Node3D
## Builds the environment prototype at runtime around the Blender-generated world.glb:
## materials, collision, sky/light/fog, the glowing lake, ambient spores and the explorer.
## Node-name conventions come from alien_planet/blender/build_world.py.

const WORLD_GLB := "res://assets/world.glb"

# Keep in sync with build_world.py (Blender Z-up: (x, y, z) -> Godot (x, z, -y)).
const WATER := -1.2
const LAKE := Vector3(14.0, -10.0, 25.0)       # blender x, y, radius
const SPAWN_B := Vector2(-36.0, 16.0)
const VIEW_AZ := 20.0                           # spawn facing / shrine ring axis, degrees from east (+X) towards north (+Y)
const SUN_AZ := -62.0
const SUN_EL := 21.0

const SOLID := preload("res://shaders/solid.gdshader")
const FLORA := preload("res://shaders/flora.gdshader")
const GLOW := preload("res://shaders/glow.gdshader")
const WATER_SHADER := preload("res://shaders/water.gdshader")
const SKY := preload("res://shaders/sky.gdshader")

var mats := {}
var floaters: Array = []   # [node, base_position, phase]
var core: Node3D
var player: CharacterBody3D
var t := 0.0


static func b2g(x: float, y: float, z: float) -> Vector3:
	return Vector3(x, z, -y)


static func dir_from(az_deg: float, el_deg: float) -> Vector3:
	var az := deg_to_rad(az_deg)
	var el := deg_to_rad(el_deg)
	return b2g(cos(el) * cos(az), cos(el) * sin(az), sin(el)).normalized()


func _ready() -> void:
	if OS.has_feature("mobile"):
		Engine.max_fps = 60
	_make_materials()
	_make_environment()
	_load_world()
	_make_lake()
	_make_player()
	var shots := _arg("--shots")
	if shots != "":
		_run_shots.call_deferred(shots)


func _arg(key: String) -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with(key + "="):
			return a.substr(key.length() + 1)
		if a == key:
			return "1"
	return ""


# ---------------------------------------------------------------------------------------- materials
func _make_materials() -> void:
	for n in ["Terrain", "Rock", "Ruin"]:
		var m := ShaderMaterial.new()
		m.shader = SOLID
		mats[n] = m
	mats["Ruin"].set_shader_parameter("brightness", 1.05)
	var f := ShaderMaterial.new()
	f.shader = FLORA
	mats["Flora"] = f
	var g := ShaderMaterial.new()
	g.shader = GLOW
	mats["Glow"] = g
	var gs := ShaderMaterial.new()   # glyphs and crystals: no sway
	gs.shader = GLOW
	gs.set_shader_parameter("sway_amount", 0.0)
	mats["GlowStill"] = gs


# ---------------------------------------------------------------------------------------- sky, light, fog
func _make_environment() -> void:
	var sun_dir := dir_from(SUN_AZ, SUN_EL)

	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = SKY
	sky_mat.set_shader_parameter("sun_dir", sun_dir)
	sky_mat.set_shader_parameter("moon_dir", dir_from(150.0, 38.0))
	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_64

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 0.75
	env.ambient_light_color = Color(0.5, 0.52, 0.68)
	env.ambient_light_energy = 1.0
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.08
	env.tonemap_white = 1.6
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Color(0.72, 0.66, 0.72)
	env.fog_light_energy = 1.0
	env.fog_sun_scatter = 0.55
	env.fog_density = 0.005
	env.fog_sky_affect = 0.0
	env.fog_height = 1.0
	env.fog_height_density = 0.012
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_strength = 1.0
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 0.85
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.1
	env.adjustment_contrast = 1.06
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	add_child(sun)
	sun.look_at_from_position(Vector3.ZERO, -sun_dir, Vector3.UP)
	sun.light_color = Color(1.0, 0.84, 0.68)
	sun.light_energy = 1.5
	sun.light_angular_distance = 1.2      # soft penumbra with the PCF filter
	sun.shadow_enabled = true
	# Two cascades: the first 18 m get most of the shadow map (crisp contact shadows), the rest fades out at 80 m.
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_split_1 = 0.22
	sun.directional_shadow_blend_splits = true
	sun.directional_shadow_max_distance = 80.0
	sun.directional_shadow_fade_start = 0.85
	sun.shadow_bias = 0.1
	sun.shadow_normal_bias = 1.4
	sun.shadow_blur = 1.6
	sun.shadow_opacity = 0.92

	var fill := DirectionalLight3D.new()   # cool skylight from the opposite side, no shadows
	fill.name = "SkyFill"
	add_child(fill)
	fill.look_at_from_position(Vector3.ZERO, -dir_from(SUN_AZ + 180.0, 35.0), Vector3.UP)
	fill.light_color = Color(0.6, 0.68, 0.95)
	fill.light_energy = 0.22
	fill.shadow_enabled = false


# ---------------------------------------------------------------------------------------- world
func _load_world() -> void:
	var world: Node3D = load(WORLD_GLB).instantiate()
	world.name = "World"
	add_child(world)
	for mi in world.find_children("*", "MeshInstance3D", true, false):
		_setup_mesh(mi as MeshInstance3D)


func _setup_mesh(mi: MeshInstance3D) -> void:
	var n := String(mi.name)
	var mesh := mi.mesh
	var still := n.begins_with("Deco_") or n.begins_with("Ruin_") or n.begins_with("Rock_")
	for i in mesh.get_surface_count():
		var src := mesh.surface_get_material(i)
		var key := src.resource_name if src else "Terrain"
		if key == "Glow" and still:
			key = "GlowStill"
		mi.set_surface_override_material(i, mats.get(key, mats["Terrain"]))
	if n == "Terrain" or n.begins_with("Rock_") or n.begins_with("Ruin_"):
		var body := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		cs.shape = mesh.create_trimesh_shape()
		body.add_child(cs)
		mi.add_child(body)
	if n.begins_with("Detail_"):
		mi.visibility_range_end = 48.0
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if n.begins_with("Deco_"):
		mi.visibility_range_end = 140.0
	if n.begins_with("Float_"):
		if n == "Float_core":
			core = mi
			var l := OmniLight3D.new()
			l.light_color = Color(0.45, 1.0, 0.95)
			l.light_energy = 2.2
			l.omni_range = 16.0
			l.shadow_enabled = false
			mi.add_child(l)
		floaters.append([mi, mi.position, randf() * TAU])


func _make_lake() -> void:
	var pm := PlaneMesh.new()
	pm.size = Vector2(120, 120)
	pm.subdivide_width = 80   # ~1.5 m quads for the Gerstner waves (~13k tris)
	pm.subdivide_depth = 80
	var m := ShaderMaterial.new()
	m.shader = WATER_SHADER
	if _arg("--debug-water") != "":
		m.set_shader_parameter("debug_depth", true)
	var lake := MeshInstance3D.new()
	lake.name = "Lake"
	lake.mesh = pm
	lake.material_override = m
	lake.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	lake.position = b2g(LAKE.x, LAKE.y, WATER)
	add_child(lake)


func _make_player() -> void:
	player = preload("res://scripts/explorer.gd").new()
	player.name = "Explorer"
	add_child(player)
	var p := b2g(SPAWN_B.x, SPAWN_B.y, 0.0)
	player.spawn_at(Vector3(p.x, 3.0, p.z), dir_from(VIEW_AZ, 0.0))
	var ui := preload("res://scripts/touch_controls.gd").new()
	ui.explorer = player
	ui.force_touch = _arg("--touch") != ""
	var layer := CanvasLayer.new()
	layer.add_child(ui)
	add_child(layer)


func _process(delta: float) -> void:
	t += delta
	for f in floaters:
		var node: Node3D = f[0]
		var base: Vector3 = f[1]
		var ph: float = f[2]
		if node == core:
			node.position = base + Vector3(0, sin(t * 0.9) * 0.35, 0)
			node.rotation.y = t * 0.6
		else:
			node.position = base + Vector3(0, sin(t * 0.35 + ph) * 0.6, 0)
			node.rotation.y = sin(t * 0.1 + ph) * 0.08


# ---------------------------------------------------------------------------------------- screenshots
## godot --path . -- --shots=/abs/dir   renders a fixed set of viewpoints and quits.
func _run_shots(dir: String) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	# [name, eye (blender x, y, metres above ground), target (blender x, y, z)]
	var views := [
		["01_spawn", null, null],
		["02_overlook", Vector3(-60, 44, 20), Vector3(30, 18, 4)],
		["03_shrine_stairs", Vector3(13, 12, 1.7), Vector3(44, 32, 13)],
		["04_lake_islands", Vector3(-13, -13, 1.7), Vector3(14, -10, 13)],
		["05_grove", Vector3(-44, -28, 2.0), Vector3(-60, -14, 6)],
		["06_natural_arch", Vector3(18, -26, 1.7), Vector3(32, -44, 9)],
		["07_colonnade", Vector3(-34, 9, 1.7), Vector3(-6, -2, 3)],
		["08_gateway", Vector3(-8, 28, 1.7), Vector3(-16, 42, 7)],
		["09_ring_shrine", Vector3(34, 25, 1.7), Vector3(44, 32, 14)],
		["11_water_close", Vector3(-11, -15, 2.4), Vector3(-2, -12, -2.5)],
		["10_basalt", Vector3(-27, -31, 7.0), Vector3(-42, -40, 1)],
	]
	player.frozen = true
	for i in 3:
		await get_tree().physics_frame
	for v in views:
		if v[1] != null:
			var e: Vector3 = v[1]
			var tg: Vector3 = v[2]
			var eye := b2g(e.x, e.y, 0.0)
			eye.y = _ground_y(eye) + e.z
			player.look_from(eye, b2g(tg.x, tg.y, tg.z))
		else:
			player.frozen = false
			for i in 60:
				await get_tree().physics_frame
			player.frozen = true
		for i in 20:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(dir.path_join(v[0] + ".png"))
		print("SHOT ", v[0], " draws=",
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			" prims=", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME))
	get_tree().quit()


func _ground_y(p: Vector3) -> float:
	var q := PhysicsRayQueryParameters3D.create(Vector3(p.x, 300, p.z), Vector3(p.x, -100, p.z))
	q.exclude = [player.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit.position.y if hit else 0.0
