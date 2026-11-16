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
const SUN_AZ := -55.0
const SUN_EL := 35.0   # sun hidden behind the storm

const SOLID := preload("res://shaders/solid.gdshader")
const FLORA := preload("res://shaders/flora.gdshader")
const GLOW := preload("res://shaders/glow.gdshader")
const WATER_SHADER := preload("res://shaders/water.gdshader")
const SKY := preload("res://shaders/sky.gdshader")
const WHEAT := preload("res://shaders/wheat.gdshader")
const CLOUD := preload("res://shaders/cloud.gdshader")

var mats := {}
var floaters: Array = []   # [node, base_position, phase]
var spinners: Array = []   # [node, axis, speed]
var movers: Array = []     # [node, base_position, local x axis, half distance, phase]
var core: Node3D
var player: CharacterBody3D
var t := 0.0
var environment: Environment
var sun: DirectionalLight3D
var next_flash := 6.0
var flash := 0.0


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
	KayKit.place_all(self, spinners)
	_make_lake()
	_make_player()
	_make_rain()
	_spawn_inhabitants.call_deferred()
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
	var wm := ShaderMaterial.new()
	wm.shader = WHEAT
	var wd := dir_from(-30.0, 0.0)   # prevailing wind, towards the north-east
	wm.set_shader_parameter("wind_dir", Vector2(wd.x, wd.z))
	mats["Wheat"] = wm
	var cm := ShaderMaterial.new()
	cm.shader = CLOUD
	mats["Cloud"] = cm


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
	env.ambient_light_sky_contribution = 0.6
	env.ambient_light_color = Color(0.36, 0.4, 0.48)
	env.ambient_light_energy = 1.25
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.0
	env.tonemap_white = 1.6
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Color(0.3, 0.33, 0.38)
	env.fog_light_energy = 1.0
	env.fog_sun_scatter = 0.1
	env.fog_density = 0.011
	env.fog_sky_affect = 0.0
	env.fog_height = 1.0
	env.fog_height_density = 0.03
	env.glow_enabled = true
	env.glow_intensity = 0.9
	env.glow_strength = 1.0
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 0.7
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.adjustment_enabled = true
	env.adjustment_saturation = 0.82
	env.adjustment_contrast = 1.06
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	environment = env

	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	add_child(sun)
	sun.look_at_from_position(Vector3.ZERO, -sun_dir, Vector3.UP)
	sun.light_color = Color(0.72, 0.78, 0.88)
	sun.light_energy = 0.55
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
	sun.shadow_opacity = 0.55

	var fill := DirectionalLight3D.new()   # cool skylight from the opposite side, no shadows
	fill.name = "SkyFill"
	add_child(fill)
	fill.look_at_from_position(Vector3.ZERO, -dir_from(SUN_AZ + 180.0, 35.0), Vector3.UP)
	fill.light_color = Color(0.6, 0.68, 0.95)
	fill.light_energy = 0.15
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
	var still := n.begins_with("Deco_") or n.begins_with("Ruin_") or n.begins_with("Rock_") or n.begins_with("Build_") \
		or n.begins_with("Spin_") or n.begins_with("Mover_")
	for i in mesh.get_surface_count():
		var src := mesh.surface_get_material(i)
		var key := src.resource_name if src else "Terrain"
		if key == "Glow" and still:
			key = "GlowStill"
		mi.set_surface_override_material(i, mats.get(key, mats["Terrain"]))
	if n == "Terrain" or n.begins_with("Rock_") or n.begins_with("Ruin_") or n.begins_with("Build_"):
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
	if n.begins_with("Wheat_"):   # wind-blown fields: cheap, so no shadow casting; fade out far away
		mi.visibility_range_end = 85.0
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if n.begins_with("Crop_"):
		mi.visibility_range_end = 100.0
	if n.begins_with("Cloud_") or n.begins_with("Far_"):
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if n.begins_with("Spin_"):   # Spin_<axis>_<speed/100>_<id>
		var parts := n.split("_")
		var ax: Vector3 = {"x": Vector3.RIGHT, "y": Vector3.UP, "z": Vector3.BACK}[parts[1]]
		spinners.append([mi, ax, float(parts[2]) / 100.0])
	if n.begins_with("Mover_"):  # Mover_<distance>_<id>: glide back and forth along local X, hovering
		var dist := float(n.split("_")[1])
		if dist > 0.0:
			movers.append([mi, mi.position, mi.transform.basis.x.normalized(), dist / 2.0, randf() * TAU])
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
	m.set_shader_parameter("sun_dir", dir_from(SUN_AZ, SUN_EL))
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


# ---------------------------------------------------------------------------------------- inhabitants
## A few residents placed around the world so it feels lived in (static animation loops, no AI).
## [character id, blender x, y, animation, look-at blender x, y]
const INHABITANTS := [
	["kk:Rogue", -22.0, 5.0, "Talk", -19.5, 3.0], ["avari_1", -19.5, 3.0, "Talk", -22.0, 5.0],
	["keth_3", 18.6, 21.2, "Idle", 0.0, 10.0], ["avari_4", 38.5, 27.5, "Idle", 44.0, 32.0],
	["murrai_1", -9.5, -15.5, "Sit", 10.0, -10.0], ["murrai_2", -8.0, -17.0, "Idle", -9.5, -15.5],
	["keth_0", -12.5, 34.0, "Idle", -6.5, 33.0], ["vorn_1", -9.5, 35.0, "Talk", -12.0, 37.0],
	["luma_0", -49.0, -11.0, "Idle", -36.0, 0.0], ["vorn_0", -29.0, -29.0, "Talk", -27.0, -31.0],
	["kk:Barbarian", -31.0, 12.0, "Idle", -36.0, 16.0], ["luma_3", -27.0, -31.0, "Talk", -29.0, -29.0],
	# farming valley: people living and working
	["keth_1", -16.0, 87.0, "Work", -16.0, 92.0], ["kk:Rogue_Hooded", -21.0, 85.5, "Idle", -16.0, 87.0],
	["vorn_1", -16.6, 102.6, "Work", -18.0, 104.5], ["kk:Knight", -21.5, 99.5, "Talk", -23.5, 98.5],
	["vorn_2", -23.5, 98.5, "Talk", -21.5, 99.5], ["luma_2", -31.0, 103.6, "SitBench", -31.0, 98.0],
	["kk:Rogue@1.15", -8.0, 103.5, "Cheer", -9.8, 104.8], ["murrai_2", -9.8, 104.8, "Talk", -8.0, 103.5],
	["avari_2", 22.5, 105.5, "Idle", 25.0, 109.5], ["murrai_0", 12.5, 84.0, "Idle", 14.0, 90.0],
	["keth_2", 13.0, 109.5, "Talk", 15.0, 108.0], ["kk:Mage", 15.0, 108.0, "Talk", 13.0, 109.5],
	["murrai_4", 13.8, 110.8, "SitBench", 13.0, 106.0], ["kk:Barbarian", -6.5, 84.0, "Work", -6.5, 90.0],
	# remains of an older war among the ruins
	["kk:Skeleton_Warrior", 40.5, 27.0, "Dead", 44.0, 32.0], ["kk:Skeleton_Minion", -17.0, 3.0, "Lie", -10.0, 0.0],
	["kk:Skeleton_Minion", -13.5, 40.0, "SitFloor", -16.0, 42.0],
]


func _spawn_inhabitants() -> void:
	for i in 2:
		await get_tree().physics_frame
	var root := Node3D.new()
	root.name = "Inhabitants"
	add_child(root)
	for e in INHABITANTS:
		var c: Node3D
		var anim: String = e[3]
		var bench: bool = anim == "SitBench"   # sits on a KayKit bench placed by the layout (no stone block)
		if bench:
			anim = "Sit"
		if String(e[0]).begins_with("kk:"):   # KayKit adventurers stand in for Humans; skeletons as old remains
			var spec := String(e[0]).substr(3).split("@")
			var h := 1.8 if spec.size() < 2 else float(spec[1])
			c = KayKit.character(spec[0], anim, [], h if not spec[0].begins_with("Skeleton") else 1.7)
		else:
			var work: bool = anim == "Work"   # farm work: the swing animation, looped (hoeing, hammering)
			c = Cast.spawn(e[0], "Attack" if work else anim)
			if work:
				Cast.loop(c, "Attack")
		var p := b2g(e[1], e[2], 0.0)
		p.y = _ground_y(p)
		root.add_child(c)
		c.position = p
		var tgt := b2g(e[4], e[5], 0.0)
		c.rotation.y = atan2(tgt.x - p.x, tgt.z - p.z)   # models face +Z
		if e[3] == "Sit" and not String(e[0]).begins_with("kk:"):   # a stone to sit on, at knee height
			var seat := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = Vector3(0.7, 0.5, 0.55)
			seat.mesh = bm
			var sm := StandardMaterial3D.new()
			sm.albedo_color = Color(0.45, 0.4, 0.36)
			sm.roughness = 1.0
			seat.material_override = sm
			c.add_child(seat)
			seat.position = Vector3(0, 0.22, -0.18)


## Rain: vertical streaks spawned in a box above the explorer (world-space, so they fall past you as
## you walk). CPU particles: cheap and supported everywhere on mobile.
func _make_rain() -> void:
	var p := CPUParticles3D.new()
	p.name = "Rain"
	p.amount = 700
	p.lifetime = 1.1
	p.preprocess = 1.1
	p.local_coords = false
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	p.emission_box_extents = Vector3(18, 1, 18)
	p.position = Vector3(0, 14, 0)
	p.direction = Vector3(0.12, -1, 0.08)
	p.spread = 3.0
	p.initial_velocity_min = 17.0
	p.initial_velocity_max = 21.0
	p.gravity = Vector3(0, -6, 0)
	var q := QuadMesh.new()
	q.size = Vector2(0.025, 0.55)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(0.72, 0.78, 0.86, 0.32)
	m.disable_receive_shadows = true
	q.material = m
	p.mesh = q
	player.add_child(p)


## Lightning: every 8-20 s a double flicker brightens the sky, ambient and sun for a moment.
func _lightning(delta: float) -> void:
	next_flash -= delta
	if next_flash <= 0.0:
		flash = 0.45
		next_flash = randf_range(8.0, 20.0)
	if flash > 0.0:
		flash -= delta
		var k := 0.0
		if flash > 0.33 or (flash > 0.12 and flash < 0.24):
			k = 1.0
		environment.background_energy_multiplier = 1.0 + 2.2 * k
		environment.ambient_light_energy = 1.25 + 1.6 * k
		sun.light_energy = 0.55 + 1.4 * k
	elif environment.background_energy_multiplier != 1.0:
		environment.background_energy_multiplier = 1.0
		environment.ambient_light_energy = 1.25
		sun.light_energy = 0.55


func _process(delta: float) -> void:
	t += delta
	_lightning(delta)
	for s in spinners:
		(s[0] as Node3D).rotate_object_local(s[1], s[2] * delta)
	for m in movers:
		var node: Node3D = m[0]
		var half: float = m[3]
		var speed := 0.9 / maxf(half, 1.0)   # ~0.9 m/s peak
		node.position = m[1] + m[2] * sin(t * speed + m[4]) * half + Vector3(0, sin(t * 1.3 + m[4]) * 0.12, 0)
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
		["12_residents_colonnade", Vector3(-27.5, 5.6, 1.6), Vector3(-20.7, 4.0, 1.2)],
		["13_residents_gateway", Vector3(-6.5, 33.0, 1.6), Vector3(-11, 36.5, 1.3)],
		["14_residents_lake", Vector3(-7.0, -19.5, 1.5), Vector3(-9.0, -15.5, 0.6)],
		["15_farm_pass", Vector3(-4, 66, 2.0), Vector3(-6, 104, 3)],
		["16_farm_overview", Vector3(-58, 72, 24), Vector3(-4, 108, 0)],
		["23_farm_hero", Vector3(4, 89, 2.4), Vector3(-22, 110, 4.0)],
		["24_farm_hero2", Vector3(-30, 96, 2.0), Vector3(0, 118, 3.0)],
		["17_wheat_field", Vector3(-32, 86, 1.7), Vector3(-46, 94, 1.0)],
		["18_homestead_a", Vector3(-8, 98, 2.0), Vector3(-26, 108, 3)],
		["19_harvester", Vector3(4, 112, 2.6), Vector3(-8, 119, 1.5)],
		["20_pivot_field", Vector3(24, 92, 3.0), Vector3(38, 98, 2.0)],
		["21_homestead_b", Vector3(8, 100, 2.0), Vector3(20, 113, 3)],
		["22_workers", Vector3(-11, 83, 1.8), Vector3(-17, 88, 1.0)],
		["10_basalt", Vector3(-27, -31, 7.0), Vector3(-42, -40, 1)],
	]
	player.frozen = true
	for i in 3:
		await get_tree().physics_frame
	var only := _arg("--only")
	if only != "":
		var pre: Array = Array(only.split(","))
		views = views.filter(func(v): return pre.any(func(p): return String(v[0]).begins_with(p)))
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
