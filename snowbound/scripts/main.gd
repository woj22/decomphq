extends Node
## Boot. Test flags after `--`: --tour=DIR saves screenshots from fixed viewpoints and quits.

var train: Train


func _ready() -> void:
	train = Train.new()
	add_child(train)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--tour="):
			_tour(a.substr(7))


func _tour(dir: String) -> void:
	var cam := Camera3D.new()
	cam.fov = 70
	add_child(cam)
	cam.make_current()
	DirAccess.make_dir_recursive_absolute(dir)
	var views := {
		"corridor": [Vector3(0.9, 1.55, -1.2), Vector3(0.9, 1.45, 12.0)],
		"compartment": [Vector3(0.2, 1.55, 2.6), Vector3(-1.3, 1.1, 4.4)],
		"bed": [Vector3(-0.6, 1.5, 3.0), Vector3(-1.2, 0.6, 4.6)],
		"window": [Vector3(-0.4, 1.4, 3.6), Vector3(-1.6, 1.3, 3.3)],
		"dining": [Vector3(0.0, 1.55, 18.0), Vector3(0.0, 1.2, 30.0)],
		"stove": [Vector3(0.3, 1.5, 27.0), Vector3(-1.2, 0.8, 29.5)],
	}
	await get_tree().create_timer(1.5).timeout
	for name in views:
		var v: Array = views[name]
		cam.position = v[0]
		cam.look_at(v[1])
		await get_tree().create_timer(0.6).timeout
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(dir.path_join(name + ".png"))
		print("shot ", name)
	get_tree().quit()
