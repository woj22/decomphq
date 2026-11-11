extends Node
## Boot: scale the UI for the screen, build the train, you, the HUD and the game.
## Test flags after `--`: --tour=DIR (screenshots from fixed viewpoints), --autoplay (plays a whole game with demo
## lines and prints the outcome), --demo (canned AI lines), --shots=DIR (gameplay screenshots).

var train: Train
var player: Player
var ui: GameUI
var ai: AIClient
var game: Game


func _ready() -> void:
	Quality.load_setting()
	Quality.apply_viewport(get_viewport())
	_fit_screen()
	get_window().size_changed.connect(_fit_screen)
	train = Train.new()
	add_child(train)
	var args := OS.get_cmdline_user_args()
	for a in args:
		if a.begins_with("--tour="):
			_tour(a.substr(7))
			return
	player = Player.new()
	train.add_child(player)
	ai = AIClient.new()
	add_child(ai)
	ai.load_settings()
	ui = GameUI.new()
	add_child(ui)
	ui.player = player
	game = Game.new()
	game.train = train
	game.player = player
	game.ui = ui
	game.ai = ai
	add_child(game)
	if "--autoplay" in args:
		ai.demo = ai.api_key == "" or "--demo" in args
		game.autoplay = true
		await game.start()
		while game.story.phase != "ending":
			await get_tree().create_timer(0.2).timeout
			if game.story.phase in ["evening", "day"] and not game._busy:
				await game.sleep()
			elif game.story.phase == "morning" and game._tribunal_pending:
				await game.tribunal()
		await get_tree().create_timer(0.5).timeout
		get_tree().quit()
		return
	for a in args:
		if a == "--bench":
			_bench()
			return
	for a in args:
		if a.begins_with("--shots="):
			_shots(a.substr(8))
			return
	await ui.setup_screen(ai)
	game.start()


func _fit_screen() -> void:
	var s := DisplayServer.window_get_size()
	get_window().content_scale_factor = clampf(minf(s.x, s.y) / 640.0, 0.75, 4.0)


func _snap(dir: String, name: String) -> void:
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(dir)
	get_viewport().get_texture().get_image().save_png(dir.path_join(name + ".png"))
	print("shot ", name)


func _shots(dir: String) -> void:
	ai.demo = true
	game.autoplay = true
	await game.start()
	await get_tree().create_timer(1.5).timeout
	player.position = Vector3(0, 0, Layout.DINING_Z + 0.3)
	player.yaw = PI
	player.pitch = -0.12
	await get_tree().create_timer(0.8).timeout
	await _snap(dir, "01_dining")
	player.position = Vector3(0.0, 0, Layout.DINING_Z + 6.5)
	player.yaw = PI * 0.75
	await get_tree().create_timer(0.6).timeout
	await _snap(dir, "02_dining_close")
	player.position = Vector3(0.95, 0, -0.8)
	player.yaw = PI
	player.pitch = -0.05
	game._staff_positions()
	await get_tree().create_timer(0.6).timeout
	await _snap(dir, "03_corridor")
	player.position = Vector3(0.0, 0, 1.1)
	player.yaw = PI / 2
	player.pitch = -0.2
	await get_tree().create_timer(0.6).timeout
	await _snap(dir, "04_compartment")
	player.pitch = -1.0
	player.yaw = 0
	await get_tree().create_timer(0.4).timeout
	await _snap(dir, "05_own_body")
	# sitting at a dining table opposite two guests, and lying in your berth
	player.sit(Layout.dining_seats()[2])
	player.pitch = -0.15
	await get_tree().create_timer(0.6).timeout
	await _snap(dir, "08_sit")
	player.lie(Vector3(-1.08, 0, Layout.compartment_z(1) + 1.98), -PI / 2.0)
	await get_tree().create_timer(0.6).timeout
	await _snap(dir, "09_lie")
	player.stand()
	# a conversation (demo lines) and the tribunal
	player.position = Vector3(0.0, 0, Layout.DINING_Z + 0.9)
	player.pitch = -0.1
	game.autoplay = false
	game._talk("tesla")
	await get_tree().create_timer(0.5).timeout
	ui.send_line.emit("Good evening, Mr Tesla. Did you sleep well before dinner?")
	await get_tree().create_timer(3.5).timeout
	await _snap(dir, "06_talk")
	ui.send_line.emit("__leave__")
	await get_tree().create_timer(0.5).timeout
	ui.tribunal_open("The tribunal — morning 1")
	ui.tribunal_line("Napoleon", "I have commanded armies; I know a deserter's eyes. The Florentine has them. (demo)")
	ui.tribunal_line("Cleopatra", "The nurse counts doses she does not account for. Ask her about the missing one. (demo)")
	await get_tree().create_timer(0.6).timeout
	await _snap(dir, "07_tribunal")
	get_tree().quit()


func _tour(dir: String) -> void:
	var cam := Camera3D.new()
	cam.fov = 70
	add_child(cam)
	cam.make_current()
	DirAccess.make_dir_recursive_absolute(dir)
	var views := {
		"corridor": [Vector3(0.9, 1.55, -1.2), Vector3(0.9, 1.45, 12.0)],
		"compartment": [Vector3(0.2, 1.55, 2.6), Vector3(-1.3, 1.1, 4.4)],
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
		await _snap(dir, name)
	get_tree().quit()


func _bench() -> void:
	## Frame time, draw calls and triangles from three viewpoints (dining car, corridor, compartment window).
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	ai.demo = true
	game.autoplay = true
	await game.start()
	await get_tree().create_timer(1.0).timeout
	for v in [["dining", Vector3(0, 0, Layout.DINING_Z + 0.6), PI], ["corridor", Vector3(0.95, 0, -0.8), PI], ["window", Vector3(-0.3, 0, 3.4), PI / 2.0]]:
		player.put(v[1], v[2])
		await get_tree().create_timer(0.5).timeout
		var frames := 0
		var t0 := Time.get_ticks_usec()
		while Time.get_ticks_usec() - t0 < 2_000_000:
			await get_tree().process_frame
			frames += 1
		var ms := (Time.get_ticks_usec() - t0) / 1000.0 / frames
		print("BENCH %s quality=%s ms=%.1f draws=%d prims=%d" % [v[0], Quality.NAMES[Quality.level], ms,
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)])
	get_tree().quit()
