extends Node
## Root scene: world container + UI layers; routes title, desk, menus and queued modal screens.

var world_root: Node2D
var hud: Hud
var hud_layer: CanvasLayer
var desk_layer: CanvasLayer
var menu_layer: CanvasLayer
var dialog_layer: CanvasLayer
var modal_layer: CanvasLayer
var title_layer: CanvasLayer
var desk: DeskScreen
var dialogue_panel: DialoguePanel
var title: TitleScreen
var modal_root: Control


func _ready() -> void:
	Settings.load_settings()
	Assets.scan()
	world_root = Node2D.new()
	world_root.name = "WorldRoot"
	add_child(world_root)
	World.set_root(world_root)
	hud_layer = _layer(10)
	desk_layer = _layer(20)
	menu_layer = _layer(25)
	dialog_layer = _layer(30)
	modal_layer = _layer(40)
	title_layer = _layer(50)
	hud = Hud.new()
	hud_layer.add_child(hud)
	hud.open_map.connect(func() -> void: _menu(MapScreen.new()))
	hud.open_journal.connect(func() -> void: _menu(JournalScreen.new()))
	hud.open_pause.connect(open_pause)
	dialogue_panel = DialoguePanel.new()
	dialog_layer.add_child(dialogue_panel)
	World.desk_requested.connect(open_desk)
	World.tap_marker.connect(_tap_marker)
	Dialogue.modal_opened.connect(_on_modal)
	EventBus.rank_changed.connect(func(_r: int) -> void: World.refresh_player_sprite())
	hud_layer.visible = false
	Playtest.attach(self)
	if not Playtest.active:
		show_title()


func _layer(n: int) -> CanvasLayer:
	var l := CanvasLayer.new()
	l.layer = n
	add_child(l)
	return l


func show_title() -> void:
	hud_layer.visible = false
	World.clear()
	title = TitleScreen.new()
	title_layer.add_child(title)
	title.new_game.connect(start_new_game)
	title.continue_game.connect(continue_game)


func _close_title() -> void:
	if title != null:
		title.queue_free()
		title = null


func start_new_game() -> void:
	_close_title()
	Dialogue.clear()
	var start: Dictionary = Content.cfg("start", {}) if Content.cfg("start", {}) is Dictionary else {}
	var area := str(start.get("area", "area_arrival_hall"))
	if Content.area(area).is_empty():
		area = str(Content.area_ids()[0])
	GameState.reset()
	Sim.reset()
	Clock.reset()
	World.load_area(area, str(start.get("spawn", "default")))
	hud_layer.visible = true
	GameState.new_game()
	SaveGame.autosave("new_game")


func continue_game() -> void:
	_close_title()
	if not SaveGame.continue_game():
		show_title()
		return
	hud_layer.visible = true


func open_pause() -> void:
	var p := PauseScreen.new()
	p.quit_to_title.connect(func() -> void:
		_clear_layer(menu_layer)
		_clear_layer(desk_layer)
		Dialogue.clear()
		GameState.in_game = false
		show_title())
	_menu(p)


func _menu(s: ScreenBase) -> void:
	World.ui_blocking += 1
	s.done.connect(func() -> void: World.ui_blocking = maxi(0, World.ui_blocking - 1))
	menu_layer.add_child(s)


func _clear_layer(l: CanvasLayer) -> void:
	for c in l.get_children():
		c.queue_free()
	World.ui_blocking = 0


# ---------------------------------------------------------------- desk
func open_desk(cid: String) -> void:
	if desk != null:
		desk.queue_free()
	desk = DeskScreen.new()
	desk_layer.add_child(desk)
	desk.open(cid)
	desk.closed.connect(close_desk)
	desk.verdict_done.connect(_on_verdict_done)


func close_desk() -> void:
	if desk != null:
		desk.queue_free()
		desk = null
	World.close_desk()


func _on_verdict_done(cid: String, verdict: String) -> void:
	close_desk()
	World.soul_exit(cid, verdict)
	GameState.finish_case(cid)


# ---------------------------------------------------------------- modals
func _on_modal(kind: String, data: Dictionary) -> void:
	modal_root = Control.new()
	UiKit.full_rect(modal_root)
	modal_root.theme = UiKit.theme()
	modal_root.mouse_filter = Control.MOUSE_FILTER_STOP
	modal_layer.add_child(modal_root)
	var root := modal_root
	match kind:
		"card":
			ModalScreens.card(root, data)
			root.gui_input.connect(func(e: InputEvent) -> void:
				if e is InputEventMouseButton and (e as InputEventMouseButton).pressed:
					_modal_done(root))
		"ledger":
			ModalScreens.ledger(root, data, func() -> void: _modal_done(root))
		"ceremony":
			ModalScreens.ceremony(root, data, func() -> void: _modal_done(root))
		"summary":
			ModalScreens.summary(root, func() -> void:
				_modal_done(root)
				SaveGame.autosave("end")
				GameState.in_game = false
				show_title())
		_:
			_modal_done(root)


func _modal_done(root: Control) -> void:
	if is_instance_valid(root):
		root.queue_free()
	if modal_root == root:
		modal_root = null
	Dialogue.modal_done()


func dismiss_modal() -> void:
	if modal_root != null:
		var kind := Dialogue.current_kind
		if kind == "summary":
			_modal_done(modal_root)
			GameState.in_game = false
			show_title()
		else:
			_modal_done(modal_root)


func _tap_marker(p: Vector2) -> void:
	if World.view == null:
		return
	var s := Sprite2D.new()
	s.centered = false
	s.texture = Assets.frame("tap_marker", 0, "fx")
	s.offset = -(Assets.info("tap_marker", "fx")["origin"] as Vector2)
	s.position = p
	World.view.decal_layer.add_child(s)
	var tw := s.create_tween()
	tw.tween_property(s, "modulate:a", 0.0, 0.8)
	tw.tween_callback(s.queue_free)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if GameState.in_game and title == null and not Playtest.active and hud_layer.visible:
			if what == NOTIFICATION_APPLICATION_PAUSED:
				open_pause()
