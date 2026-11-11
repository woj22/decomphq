class_name Hud
extends Control
## Exploration HUD (PROJECT §9.2, D2): top-left stats panel, objective strip + minimap top-right,
## bottom bar Map / Journal / Pause, context action button bottom-right, floating joystick, notifications.

signal open_map()
signal open_journal()
signal open_pause()

var margin: MarginContainer
var loc_label: Label
var time_label: Label
var crest: TextureRect
var stat_labels := {}
var order_shown := 68.0
var objective_label: Label
var merit_label: Label
var objective_panel: PanelContainer
var objective_expanded := false
var minimap: Minimap
var action_btn: Button
var bar: HBoxContainer
var joy: JoystickView
var tooltip: Label
var _tooltip_t := 0.0
var notes: VBoxContainer
var top_left: PanelContainer


func _ready() -> void:
	theme = UiKit.theme()
	UiKit.full_rect(self)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	joy = JoystickView.new()
	UiKit.full_rect(joy)
	joy.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(joy)
	margin = MarginContainer.new()
	UiKit.full_rect(margin)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(margin)
	UiKit.apply_safe(margin)
	var root := Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(root)
	_build_top_left(root)
	_build_top_right(root)
	_build_bottom(root)
	World.joystick_changed.connect(func(a: bool, b: Vector2, k: Vector2) -> void: joy.set_state(a, b, k))
	World.focus_changed.connect(_on_focus)
	World.area_loaded.connect(func(_id: String) -> void: refresh())
	EventBus.stat_changed.connect(func(_a: String, _b: Variant, _c: Variant) -> void: refresh())
	EventBus.clock_ticked.connect(func(_d: int, _m: int) -> void: refresh())
	EventBus.objective_changed.connect(func(_o: String) -> void: refresh())
	EventBus.rank_changed.connect(func(_r: int) -> void: refresh())
	EventBus.notify.connect(show_note)
	EventBus.case_called.connect(func(cid: String) -> void: show_note("%s follows you." % str(Content.case(cid).get("name", "A soul"))))
	EventBus.archive_received.connect(func(_c: String, ids: Array) -> void: show_note("Received %d document%s." % [ids.size(), "" if ids.size() == 1 else "s"]))
	EventBus.item_bought.connect(func(_i: String) -> void: show_note("Bought: desk lamp."))
	EventBus.game_saved.connect(func() -> void: pass)
	order_shown = GameState.get_stat("order")
	refresh()


func _build_top_left(root: Control) -> void:
	top_left = UiKit.panel(UiKit.charcoal_box(4))
	top_left.position = Vector2.ZERO
	top_left.custom_minimum_size = Vector2(168, 56)
	root.add_child(top_left)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 4)
	top_left.add_child(h)
	crest = UiKit.icon("icon_crest_r1", Vector2(32, 32))
	crest.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	h.add_child(crest)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	h.add_child(v)
	loc_label = UiKit.label("", 16)
	v.add_child(loc_label)
	time_label = UiKit.label("", 12, UiKit.TEXT_DIM)
	v.add_child(time_label)
	var stats := HBoxContainer.new()
	stats.add_theme_constant_override("separation", 2)
	v.add_child(stats)
	for s: Array in [["queue", "icon_soul", "Queue: souls waiting in the fortress"], ["purse", "icon_obol", "Obols: your purse"],
			["order", "icon_order", "Order: how well the Border is running"]]:
		var b := Button.new()
		b.flat = true
		b.focus_mode = Control.FOCUS_NONE
		b.icon = Assets.ui_texture(s[1])
		b.text = "0"
		b.add_theme_font_size_override("font_size", 16)
		b.add_theme_constant_override("h_separation", 2)
		b.custom_minimum_size = Vector2(40, 18)
		b.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
		b.add_theme_stylebox_override("hover", StyleBoxEmpty.new())
		b.add_theme_stylebox_override("pressed", StyleBoxEmpty.new())
		var tip: String = s[2]
		b.pressed.connect(func() -> void: _show_tooltip(tip))
		stats.add_child(b)
		stat_labels[s[0]] = b
	World.touch_blockers.append(top_left)
	tooltip = UiKit.label("", 12)
	tooltip.add_theme_stylebox_override("normal", UiKit.charcoal_box(4, true))
	tooltip.position = Vector2(0, 62)
	tooltip.visible = false
	root.add_child(tooltip)
	notes = VBoxContainer.new()
	notes.position = Vector2(0, 62)
	notes.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(notes)


func _build_top_right(root: Control) -> void:
	var box := HBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	box.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	box.alignment = BoxContainer.ALIGNMENT_END
	box.add_theme_constant_override("separation", 6)
	root.add_child(box)
	objective_panel = UiKit.panel(UiKit.charcoal_box(4))
	objective_panel.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	objective_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	objective_panel.gui_input.connect(func(e: InputEvent) -> void:
		if (e is InputEventMouseButton and (e as InputEventMouseButton).pressed) or (e is InputEventScreenTouch and (e as InputEventScreenTouch).pressed):
			objective_expanded = not objective_expanded
			refresh())
	box.add_child(objective_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 0)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	objective_panel.add_child(v)
	objective_label = UiKit.label("", 16)
	objective_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(objective_label)
	merit_label = UiKit.label("", 12, UiKit.TEXT_DIM)
	merit_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(merit_label)
	minimap = Minimap.new()
	minimap.custom_minimum_size = Vector2(72, 72)
	minimap.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	minimap.pressed.connect(func() -> void: open_map.emit())
	box.add_child(minimap)
	World.touch_blockers.append(objective_panel)
	World.touch_blockers.append(minimap)


func _build_bottom(root: Control) -> void:
	bar = HBoxContainer.new()
	bar.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	bar.grow_vertical = Control.GROW_DIRECTION_BEGIN
	bar.add_theme_constant_override("separation", 8)
	root.add_child(bar)
	for item: Array in [["Map", "icon_map"], ["Journal", "icon_journal"], ["Pause", "icon_pause"]]:
		var b := Button.new()
		b.focus_mode = Control.FOCUS_NONE
		b.custom_minimum_size = Vector2(48, 48)
		b.name = "Bar" + str(item[0])
		var vb := VBoxContainer.new()
		vb.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.alignment = BoxContainer.ALIGNMENT_CENTER
		vb.add_theme_constant_override("separation", 0)
		UiKit.full_rect(vb)
		b.add_child(vb)
		var ic := UiKit.icon(item[1], Vector2(24, 24))
		vb.add_child(ic)
		var cap := UiKit.label(item[0], 12)
		cap.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cap.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.add_child(cap)
		b.custom_minimum_size = Vector2(52, 48)
		bar.add_child(b)
		match str(item[0]):
			"Map":
				b.pressed.connect(func() -> void: open_map.emit())
			"Journal":
				b.pressed.connect(func() -> void: open_journal.emit())
			"Pause":
				b.pressed.connect(func() -> void: open_pause.emit())
		b.pressed.connect(func() -> void: Audio.sfx("sfx_tap"))
	World.touch_blockers.append(bar)
	action_btn = Button.new()
	action_btn.name = "ContextButton"
	action_btn.focus_mode = Control.FOCUS_NONE
	action_btn.custom_minimum_size = Vector2(64, 64)
	action_btn.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	action_btn.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	action_btn.grow_vertical = Control.GROW_DIRECTION_BEGIN
	action_btn.add_theme_font_size_override("font_size", 16)
	action_btn.add_theme_stylebox_override("normal", UiKit.box(Color("#27232f"), UiKit.BORDER_GOLD, 1, 4))
	action_btn.add_theme_stylebox_override("hover", UiKit.box(Color("#37323f"), UiKit.BORDER_GOLD, 1, 4))
	action_btn.add_theme_stylebox_override("pressed", UiKit.box(Color("#43325c"), UiKit.BORDER_GOLD, 1, 4))
	action_btn.visible = false
	action_btn.pressed.connect(func() -> void: World.interact_focused())
	root.add_child(action_btn)
	World.touch_blockers.append(action_btn)


func _on_focus(_oid: String, verb: String) -> void:
	action_btn.visible = verb != ""
	action_btn.text = verb.to_upper()


func _show_tooltip(t: String) -> void:
	tooltip.text = t
	tooltip.visible = true
	_tooltip_t = 2.0


func show_note(t: String) -> void:
	var l := UiKit.label(t, 16)
	l.add_theme_stylebox_override("normal", UiKit.charcoal_box(4, true))
	notes.add_child(l)
	l.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(l, "modulate:a", 1.0, 0.2)
	tw.tween_interval(2.5)
	tw.tween_property(l, "modulate:a", 0.0, 0.3)
	tw.tween_callback(l.queue_free)
	while notes.get_child_count() > 3:
		notes.get_child(0).queue_free()
		notes.remove_child(notes.get_child(0))


func refresh() -> void:
	if loc_label == null:
		return
	var a := Content.area(World.area_id)
	loc_label.text = str(a.get("name", ""))
	time_label.text = Clock.label()
	var crest_id := str(Content.rank_info(GameState.rank).get("crest", "icon_crest_r%d" % GameState.rank))
	crest.texture = Assets.ui_texture(crest_id)
	(stat_labels["queue"] as Button).text = str(GameState.get_stat_i("queue"))
	(stat_labels["purse"] as Button).text = str(GameState.get_stat_i("purse"))
	(stat_labels["order"] as Button).text = "%d%%" % int(round(order_shown))
	var obj := GameState.objective_text()
	objective_label.text = ("(!) " + obj) if obj != "" else "(!) Explore"
	var gate := Content.cfg_i("merit_gate", 30)
	if GameState.rank >= 2:
		merit_label.text = "Merit %d" % GameState.get_stat_i("merit")
	else:
		merit_label.text = "Merit %d/%d" % [GameState.get_stat_i("merit"), gate]
	if objective_expanded:
		var o := Content.objective(GameState.objective)
		var tgt: Dictionary = o.get("target", {})
		merit_label.text += "  -  " + str(Content.area(str(tgt.get("area", ""))).get("name", ""))
	minimap.queue_redraw()


func _process(delta: float) -> void:
	var target := GameState.get_stat("order")
	if absf(order_shown - target) > 0.01:
		order_shown = move_toward(order_shown, target, delta * 1.0)
		(stat_labels["order"] as Button).text = "%d%%" % int(round(order_shown))
	if _tooltip_t > 0.0:
		_tooltip_t -= delta
		if _tooltip_t <= 0.0:
			tooltip.visible = false
	visible = not (Dialogue.in_dialogue() or World.desk_open or (Dialogue.current_kind in ["ceremony", "summary", "card", "ledger"]))
	if not visible:
		joy.set_state(false, Vector2.ZERO, Vector2.ZERO)
