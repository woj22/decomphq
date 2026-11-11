extends Node
## Boot: scale the UI for the screen, build the world, the HUD, the AI client and the game, start the wind.
## Test flags (after `--`):  --autoplay  plays the human's turns automatically and quits after one game.
##                           --demo      canned AI lines instead of API calls.
##                           --shots=DIR saves a screenshot gallery to DIR and quits.

var world: World
var ui: GameUI
var ai: AIClient
var game: Game
var _wind: AudioStreamGeneratorPlayback
var _brown := 0.0
var _brown2 := 0.0
var _phase := 0.0


func _ready() -> void:
	_fit_screen()
	get_window().size_changed.connect(_fit_screen)
	world = World.new()
	add_child(world)
	_fit_screen()
	ai = AIClient.new()
	add_child(ai)
	ai.load_settings()
	ui = GameUI.new()
	ui.world = world
	add_child(ui)
	game = Game.new()
	game.world = world
	game.ui = ui
	game.ai = ai
	add_child(game)
	world.looked_around.connect(ui.hide_hint)
	_start_wind()

	var args := OS.get_cmdline_user_args()
	var shots := ""
	for a in args:
		if a.begins_with("--shots="):
			shots = a.substr(8)
	game.autoplay = "--autoplay" in args or shots != ""
	if "--demo" in args:
		ai.demo = true
	for a in args:
		if a.begins_with("--lineup="):
			_lineup(a.substr(9))
			return
	if shots != "":
		_gallery(shots)
		return
	if game.autoplay:
		if not ai.demo and ai.api_key == "":
			ai.demo = true
		await game.play_once()
		get_tree().quit()
		return
	await ui.show_setup(ai)
	game.run()


func _fit_screen() -> void:
	# UI in "logical pixels": the short side of the screen is about 660 of them, so text is readable on phones
	var s := DisplayServer.window_get_size()
	get_window().content_scale_factor = clampf(minf(s.x, s.y) / 660.0, 0.75, 4.0)
	if world and world.camera:  # upright phones: keep a ~62 degree horizontal view instead of a narrow slice
		world.camera.keep_aspect = Camera3D.KEEP_WIDTH if s.y > s.x else Camera3D.KEEP_HEIGHT
		world.camera.fov = 62.0 if s.y > s.x else 72.0


# ------------------------------------------------------------------ wind: filtered noise that swells with the gusts
func _start_wind() -> void:
	var gen := AudioStreamGenerator.new()
	gen.mix_rate = 22050
	gen.buffer_length = 0.3
	var p := AudioStreamPlayer.new()
	p.stream = gen
	p.volume_db = -9.0
	add_child(p)
	p.play()
	_wind = p.get_stream_playback()


func _process(_d: float) -> void:
	if _wind == null:
		return
	var n := _wind.get_frames_available()
	var gust := world.gust_level() if world else 0.0
	for i in n:
		_phase += 1.0 / 22050.0
		var w := randf() * 2.0 - 1.0
		_brown = clampf(_brown * 0.985 + w * 0.035, -1.0, 1.0)              # low roar
		_brown2 = clampf(_brown2 * 0.9 + w * 0.12, -1.0, 1.0)               # higher whistle
		var swell := 0.45 + 0.25 * sin(_phase * 0.23) + 0.15 * sin(_phase * 0.71) + gust * 0.5
		var whistle := _brown2 * (0.12 + 0.1 * sin(_phase * 1.7)) * swell
		var v := (_brown * 0.9 + whistle) * swell
		_wind.push_frame(Vector2(v, v * 0.92))


# ------------------------------------------------------------------ screenshot gallery (tests)
func _snap(dir: String, name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	DirAccess.make_dir_recursive_absolute(dir)
	img.save_png(dir.path_join(name + ".png"))
	print("screenshot ", name)


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _gallery(dir: String) -> void:
	ai.demo = true
	ui.show_setup(ai)
	await _wait(1.0)
	await _snap(dir, "00_setup")
	ui.panel_done.emit(true)
	await _wait(0.5)
	game.play_once()
	world.auto_look = false
	await _wait(5.0)
	world.target = null
	world.yaw = 0.0
	world.pitch = -0.15
	await _wait(1.5)
	await _snap(dir, "01_table")
	world.yaw = 1.35
	world.pitch = -0.05
	await _wait(1.0)
	await _snap(dir, "02_window")
	world.yaw = -0.75
	world.pitch = -0.2
	await _wait(1.0)
	await _snap(dir, "03_beside")
	world.yaw = 0.0
	world.pitch = -0.95
	await _wait(0.8)
	await _snap(dir, "04_table_top")
	world.yaw = 2.4
	world.pitch = 0.05
	await _wait(0.8)
	await _snap(dir, "05_behind")
	world.yaw = 0.25
	world.pitch = -0.12
	ui.ask_accuse(1)
	await _wait(1.0)
	await _snap(dir, "06_panel")
	ui.panel_done.emit({"target": 1, "text": "x"})
	get_tree().quit()


func _lineup(dir: String) -> void:
	## close-ups of every figure, two at a time on the empty bay at z = -4 (model check)
	ui.visible = false
	var cam := Camera3D.new()
	cam.fov = 45
	world.add_child(cam)
	var figs: Array = Figures.ALL
	var page := 0
	for start in range(0, figs.size(), 2):
		var row: Array[Passenger] = []
		for i in mini(2, figs.size() - start):
			var p := Passenger.new()
			world.add_child(p)
			p.position = Vector3(-0.615 if i == 0 else -1.125, 0, -4.82)
			p.setup(figs[start + i])
			row.append(p)
		await _wait(0.1)
		var mid := Vector3(-0.87, 1.22, -4.82)
		cam.position = mid + Vector3(0.0, 0.0, 0.95)
		cam.look_at(mid - Vector3(0, 0.1, 0))
		cam.make_current()
		for p in row:
			p.look_target = cam.global_position
		await _wait(1.5)
		await _snap(dir, "lineup_%02d" % page)
		page += 1
		for p in row:
			p.queue_free()
	get_tree().quit()
