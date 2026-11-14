extends Node3D
## Renders every notable character in a row (and seated variants) and saves a screenshot.
## godot --path . res://tests/lineup.tscn -- --out=path.png [--group=kings] [--close]

func _ready() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=")
		args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	var ids: Array = []
	if args.has("ids"):
		ids = args["ids"].split(",")
	else:
		for g in Cast.GROUPS:
			if args.has("group") and args["group"] != g[0]:
				continue
			ids.append_array(Cast.ids_in_group(g[0]))
		if not args.has("group"):
			ids.push_front("player")
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("2a2430")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("b8a890")
	env.environment.ambient_light_energy = 0.6
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 30, 0)
	sun.light_energy = 1.1
	sun.shadow_enabled = true
	add_child(sun)
	var floor_mb := MeshBuilder.new()
	floor_mb.box(Vector3(0, -0.05, 0), Vector3(60, 0.1, 10), Color("8a7f72"))
	add_child(floor_mb.instance())
	var spacing := 1.25
	var x0 := -spacing * (ids.size() - 1) * 0.5
	for i in ids.size():
		var rig := CharacterBuilder.build_rig(Cast.look_for(ids[i]))
		rig.position = Vector3(x0 + i * spacing, 0, 0)
		rig.rotation.y = PI + (0.35 if args.has("turn") else 0.0)
		if args.has("sit"):
			rig.seated = true
		if args.has("talk"):
			rig.talking = true
		add_child(rig)
	var cam := Camera3D.new()
	var w := spacing * ids.size()
	if args.has("close"):
		cam.position = Vector3(0, 2.2, 3.2)
		cam.fov = 45
	else:
		cam.position = Vector3(0, 1.6, maxf(4.0, w * 0.95))
		cam.fov = 50
	add_child(cam)
	cam.look_at(Vector3(0, 1.0, 0))
	for i in 30:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(args.get("out", "user://lineup.png"))
	print("lineup saved ", args.get("out", ""))
	get_tree().quit()
