class_name GameUI
extends CanvasLayer
## Everything 2D, laid out for a landscape phone: joystick (left thumb), drag-to-look (anywhere else), a context
## action button, the conversation panel (rides above the keyboard), the journal, tribunal and vote panels, story
## cards and the start screen. Panels are awaited: `var v = await ui.card(...)`.

signal done(value: Variant)
signal action_pressed
signal send_line(text: String)

const GOLD := Color("d9b064")
const TEXT := Color("ede6d8")
const MUTED := Color("a49a8a")
const PANEL := Color(0.06, 0.045, 0.04, 0.9)
const RED := Color("d4776a")

var player: Player
var story: Story
var root: Control
var theme_: Theme
var phase_label: Label
var journal_btn: Button
var action_btn: Button
var joystick: Control
var knob: Control
var talk_panel: PanelContainer
var talk_name: Label
var talk_trust: ProgressBar
var talk_log: RichTextLabel
var talk_input: LineEdit
var talk_box: VBoxContainer
var journal: PanelContainer
var journal_text: RichTextLabel
var overlay: Control
var hint: Label
var fps_label: Label
var _fps_t := 0.0
var _joy_index := -1
var _look_index := -2
var _joy_center := Vector2.ZERO
var _last_mouse := Vector2.ZERO
var _mouse_look := false


func _ready() -> void:
	layer = 5
	theme_ = _theme()
	root = Control.new()
	root.theme = theme_
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_build_hud()
	get_viewport().size_changed.connect(_layout)
	_layout()


# ------------------------------------------------------------------ theme helpers
func _font(f: String) -> FontFile:
	return load("res://assets/fonts/LibreBaskerville-%s.ttf" % f)


func _box(bg: Color, border := Color(1, 1, 1, 0.12), radius := 12, pad := 12) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(1)
	s.set_corner_radius_all(radius)
	s.set_content_margin_all(pad)
	return s


func _theme() -> Theme:
	var t := Theme.new()
	t.default_font = _font("Regular")
	t.default_font_size = 17
	t.set_color("font_color", "Label", TEXT)
	t.set_stylebox("panel", "PanelContainer", _box(PANEL, Color(0.85, 0.7, 0.4, 0.25)))
	var b := _box(GOLD, Color(0, 0, 0, 0), 9, 10)
	t.set_stylebox("normal", "Button", b)
	var bh := b.duplicate() as StyleBoxFlat
	bh.bg_color = GOLD.lightened(0.12)
	t.set_stylebox("hover", "Button", bh)
	var bp := b.duplicate() as StyleBoxFlat
	bp.bg_color = GOLD.darkened(0.2)
	t.set_stylebox("pressed", "Button", bp)
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	var bd := b.duplicate() as StyleBoxFlat
	bd.bg_color = Color(0.35, 0.32, 0.28)
	t.set_stylebox("disabled", "Button", bd)
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		t.set_color(c, "Button", Color("1c1206"))
	t.set_font("font", "Button", _font("Bold"))
	var f := _box(Color(1, 1, 1, 0.07), Color(1, 1, 1, 0.18), 8, 9)
	for cls in ["LineEdit", "TextEdit"]:
		t.set_stylebox("normal", cls, f)
		var ff := f.duplicate() as StyleBoxFlat
		ff.border_color = GOLD
		t.set_stylebox("focus", cls, ff)
		t.set_color("font_color", cls, TEXT)
		t.set_color("font_placeholder_color", cls, MUTED)
		t.set_color("caret_color", cls, GOLD)
	t.set_font("normal_font", "RichTextLabel", _font("Regular"))
	t.set_font("bold_font", "RichTextLabel", _font("Bold"))
	t.set_font("italics_font", "RichTextLabel", _font("Italic"))
	for k in ["normal_font_size", "bold_font_size", "italics_font_size"]:
		t.set_font_size(k, "RichTextLabel", 15)
	t.set_color("default_color", "RichTextLabel", TEXT)
	for st in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
		t.set_stylebox(st, "CheckBox", StyleBoxEmpty.new())
	t.set_color("font_color", "CheckBox", TEXT)
	var bar := _box(Color(1, 1, 1, 0.08), Color(0, 0, 0, 0), 4, 0)
	t.set_stylebox("background", "ProgressBar", bar)
	var fill := _box(GOLD, Color(0, 0, 0, 0), 4, 0)
	t.set_stylebox("fill", "ProgressBar", fill)
	return t


func label(text: String, size := 17, col := TEXT, wrap := true) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


func button(text: String, ghost := false) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(100, 48)
	if ghost:
		var s := _box(Color(0, 0, 0, 0.25), Color(1, 1, 1, 0.25), 9, 10)
		for st in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(st, s)
		for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
			b.add_theme_color_override(c, TEXT)
		b.add_theme_font_override("font", _font("Regular"))
	return b


# ------------------------------------------------------------------ HUD
func _build_hud() -> void:
	phase_label = label("", 16, TEXT, false)
	var pp := PanelContainer.new()
	pp.add_theme_stylebox_override("panel", _box(PANEL, Color(0.85, 0.7, 0.4, 0.25), 18, 8))
	pp.add_child(phase_label)
	pp.name = "PhasePanel"
	root.add_child(pp)
	journal_btn = button("Journal", true)
	journal_btn.pressed.connect(toggle_journal)
	root.add_child(journal_btn)
	action_btn = button("")
	action_btn.custom_minimum_size = Vector2(150, 64)
	action_btn.visible = false
	action_btn.pressed.connect(func(): action_pressed.emit())
	root.add_child(action_btn)
	joystick = Control.new()
	joystick.custom_minimum_size = Vector2(170, 170)
	joystick.size = Vector2(170, 170)
	joystick.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var ring := Panel.new()
	ring.add_theme_stylebox_override("panel", _box(Color(1, 1, 1, 0.06), Color(1, 1, 1, 0.22), 85, 0))
	ring.size = Vector2(170, 170)
	ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	joystick.add_child(ring)
	knob = Panel.new()
	knob.add_theme_stylebox_override("panel", _box(Color(1, 1, 1, 0.22), Color(1, 1, 1, 0.4), 32, 0))
	knob.size = Vector2(64, 64)
	knob.position = Vector2(53, 53)
	knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	joystick.add_child(knob)
	root.add_child(joystick)
	hint = label("Left thumb: walk    Drag: look", 13, MUTED, false)
	root.add_child(hint)
	fps_label = label("", 12, MUTED, false)
	root.add_child(fps_label)
	# conversation
	talk_panel = PanelContainer.new()
	talk_box = VBoxContainer.new()
	talk_box.add_theme_constant_override("separation", 8)
	talk_panel.add_child(talk_box)
	var head := HBoxContainer.new()
	talk_name = label("", 20, GOLD, false)
	talk_name.add_theme_font_override("font", _font("Bold"))
	talk_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(talk_name)
	head.add_child(label("trust", 12, MUTED, false))
	talk_trust = ProgressBar.new()
	talk_trust.custom_minimum_size = Vector2(90, 10)
	talk_trust.show_percentage = false
	talk_trust.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	head.add_child(talk_trust)
	talk_box.add_child(head)
	talk_log = RichTextLabel.new()
	talk_log.bbcode_enabled = true
	talk_log.scroll_following = true
	talk_log.size_flags_vertical = Control.SIZE_EXPAND_FILL
	talk_box.add_child(talk_log)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	talk_input = LineEdit.new()
	talk_input.placeholder_text = "Say something as Confucius..."
	talk_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	talk_input.text_submitted.connect(func(t): _send())
	row.add_child(talk_input)
	var send := button("Say")
	send.pressed.connect(_send)
	row.add_child(send)
	talk_box.add_child(row)
	var row2 := HBoxContainer.new()
	row2.add_theme_constant_override("separation", 8)
	var show := button("Show a clue", true)
	show.pressed.connect(_show_clue)
	row2.add_child(show)
	var leave := button("Leave", true)
	leave.pressed.connect(func(): send_line.emit("__leave__"))
	row2.add_child(leave)
	talk_box.add_child(row2)
	talk_panel.visible = false
	root.add_child(talk_panel)
	# journal
	journal = PanelContainer.new()
	journal_text = RichTextLabel.new()
	journal_text.bbcode_enabled = true
	journal_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	var jv := VBoxContainer.new()
	jv.add_child(journal_text)
	var close := button("Close", true)
	close.pressed.connect(toggle_journal)
	jv.add_child(close)
	journal.add_child(jv)
	journal.visible = false
	root.add_child(journal)


func _layout() -> void:
	if root == null:
		return
	var s := root.get_viewport_rect().size
	var m := 14.0
	var pp: Control = root.get_node("PhasePanel")
	pp.position = Vector2(m, m)
	journal_btn.position = Vector2(s.x - journal_btn.size.x - m, m)
	joystick.position = Vector2(m + 18, s.y - 170 - m - 10)
	action_btn.position = Vector2(s.x - action_btn.size.x - m - 12, s.y - action_btn.size.y - m - 30)
	hint.position = Vector2(m, s.y - 28)
	fps_label.position = Vector2(m + 4, m + 44)
	var kb := 0.0
	if DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
		kb = DisplayServer.virtual_keyboard_get_height() / maxf(1.0, get_window().content_scale_factor)
	var tw := minf(560.0, s.x * 0.52)
	talk_panel.position = Vector2(s.x - tw - m, m + 50)
	talk_panel.size = Vector2(tw, maxf(220.0, s.y - m * 2 - 50 - kb))
	journal.position = Vector2(s.x * 0.18, m + 10)
	journal.size = Vector2(s.x * 0.64, s.y - m * 2 - 10)
	if overlay:
		_fit_overlay()


func _process(d: float) -> void:
	if talk_panel.visible:
		_layout()
	_fps_t -= d
	if _fps_t <= 0.0:
		_fps_t = 0.5
		fps_label.text = "%d fps · %s" % [Engine.get_frames_per_second(), Quality.NAMES[Quality.level]]


func set_phase(t: String) -> void:
	phase_label.text = t


func set_action(text: String) -> void:
	action_btn.visible = text != ""
	action_btn.text = text


func hud_visible(on: bool) -> void:
	for c in [joystick, action_btn, hint]:
		c.visible = on and (c != action_btn or action_btn.text != "")
	joystick.visible = on


# ------------------------------------------------------------------ touch: joystick and look
func blocking_ui() -> bool:
	return talk_panel.visible or journal.visible or overlay != null


func _input(e: InputEvent) -> void:
	if player == null:
		return
	if e is InputEventScreenTouch:
		var st := e as InputEventScreenTouch
		if st.pressed:
			var jr := Rect2(joystick.position - Vector2(30, 30), joystick.size + Vector2(60, 60))
			if joystick.visible and jr.has_point(st.position) and _joy_index < 0:
				_joy_index = st.index
				_joy_center = joystick.position + joystick.size / 2
				_joy_update(st.position)
			elif _look_index < 0 and not _over_ui(st.position):
				_look_index = st.index
		else:
			if st.index == _joy_index:
				_joy_index = -1
				player.move = Vector2.ZERO
				knob.position = Vector2(53, 53)
			if st.index == _look_index:
				_look_index = -2
	elif e is InputEventScreenDrag:
		var sd := e as InputEventScreenDrag
		if sd.index == _joy_index:
			_joy_update(sd.position)
		elif sd.index == _look_index:
			player.look_drag(sd.relative)
	elif e is InputEventMouseButton and e.device != InputEvent.DEVICE_ID_EMULATION:
		var mb := e as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_mouse_look = mb.pressed and not _over_ui(mb.position)
	elif e is InputEventMouseMotion and _mouse_look and e.device != InputEvent.DEVICE_ID_EMULATION:
		player.look_drag((e as InputEventMouseMotion).relative)


func _scale() -> float:
	return maxf(0.01, get_window().content_scale_factor)


func _over_ui(p: Vector2) -> bool:
	for c in [talk_panel, journal, action_btn, journal_btn, root.get_node("PhasePanel")]:
		if (c as Control).visible and (c as Control).get_global_rect().has_point(p):
			return true
	return overlay != null


func _joy_update(p: Vector2) -> void:
	var v := (p - _joy_center) / 70.0
	v = v.limit_length(1.0)
	knob.position = Vector2(53, 53) + v * 55
	player.move = Vector2(v.x, -v.y)


# ------------------------------------------------------------------ conversation
var _talk_id := ""


func open_talk(id: String, trust: int) -> void:
	_talk_id = id
	talk_name.text = Cast.display(id)
	talk_trust.value = trust
	talk_log.clear()
	talk_panel.visible = true
	hud_visible(false)
	_layout()


func talk_line(who: String, text: String, mine := false) -> void:
	talk_log.append_text("[b][color=#%s]%s[/color][/b]  %s\n\n" % [(GOLD if not mine else MUTED).to_html(false), who.replace("[", "[lb]"), text.replace("[", "[lb]")])


func set_trust(v: int) -> void:
	talk_trust.value = v


func close_talk() -> void:
	talk_panel.visible = false
	talk_input.release_focus()
	hud_visible(true)


func _send() -> void:
	var t := talk_input.text.strip_edges()
	if t == "":
		return
	talk_input.text = ""
	send_line.emit(t)


func _show_clue() -> void:
	var found := story.clues.filter(func(c): return c["found"] or c["public"])
	if found.is_empty():
		talk_line("—", "You have found nothing to show yet.", true)
		return
	var v: Variant = await choose("Show which clue?", found.map(func(c): return c["text"]))
	if v != null:
		send_line.emit("__clue__" + found[v]["text"])


func set_busy(on: bool) -> void:
	talk_input.editable = not on
	talk_input.placeholder_text = "..." if on else "Say something as Confucius..."


# ------------------------------------------------------------------ journal
func toggle_journal() -> void:
	journal.visible = not journal.visible
	if journal.visible:
		_fill_journal()


func _fill_journal() -> void:
	var t := journal_text
	t.clear()
	t.append_text("[b][color=#d9b064]Passengers[/color][/b]\n")
	for id in Cast.ids():
		var g: Dictionary = story.guests[id]
		var st: String = {"aboard": "", "dead": "  — dead", "locked": "  — locked in the baggage car", "stove": "  — sleeping by the stove"}[g["status"]]
		t.append_text("%s (compartment %d)%s    [color=#a49a8a]trusts you %d · suspects you %d[/color]\n" % [Cast.display(id), Cast.compartment_of(id), st, g["trust"], g["suspicion"]])
	t.append_text("\n[b][color=#d9b064]Clues[/color][/b]\n")
	var any := false
	for c in story.clues:
		if c["found"] or c["public"]:
			any = true
			t.append_text("• %s%s\n" % [c["text"], "" if c["found"] else "  [color=#a49a8a](found by the conductor)[/color]"])
	if not any:
		t.append_text("[color=#a49a8a]Nothing yet.[/color]\n")
	t.append_text("\n[b][color=#d9b064]Notes[/color][/b]\n")
	for n in story.journal:
		t.append_text("• %s\n" % n)
	t.append_text("\n[b][color=#d9b064]The rules of the train[/color][/b]\n[color=#a49a8a]Each morning the passengers vote to lock one person in the baggage car, then vote who sleeps by the stove (warm, watched: no one can leave it unseen). Lock up the killer before the snowplough arrives after the third night.[/color]\n")


# ------------------------------------------------------------------ overlays: cards, choices, text, tribunal
func _overlay_begin(dim := 0.55) -> VBoxContainer:
	if overlay:
		overlay.queue_free()
	overlay = ColorRect.new()
	(overlay as ColorRect).color = Color(0.02, 0.015, 0.01, dim)
	overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(overlay)
	var p := PanelContainer.new()
	p.name = "Card"
	overlay.add_child(p)
	var sc := ScrollContainer.new()
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.name = "Scroll"
	p.add_child(sc)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(v)
	hud_visible(false)
	_fit_overlay()
	return v


func _fit_overlay() -> void:
	var s := root.get_viewport_rect().size
	var p: PanelContainer = overlay.get_node_or_null("Card")
	if p == null:
		return
	var kb := 0.0
	if DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
		kb = DisplayServer.virtual_keyboard_get_height() / maxf(1.0, get_window().content_scale_factor)
	var w := minf(760.0, s.x - 40)
	var h := minf(s.y - 30 - kb, 560.0)
	p.position = Vector2((s.x - w) / 2, maxf(10.0, (s.y - kb - h) / 2))
	p.size = Vector2(w, h)
	(p.get_node("Scroll") as ScrollContainer).custom_minimum_size = Vector2(w - 26, h - 26)


func _overlay_end() -> void:
	if overlay:
		overlay.queue_free()
		overlay = null
	hud_visible(true)


func card(title: String, body: String, button_text := "Continue") -> void:
	var v := _overlay_begin()
	var t := label(title, 26, GOLD)
	t.add_theme_font_override("font", _font("Bold"))
	v.add_child(t)
	v.add_child(label(body, 17))
	var b := button(button_text)
	b.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	b.pressed.connect(func(): done.emit(true))
	v.add_child(b)
	await done
	_overlay_end()


func choose(title: String, options: Array, body := "", allow_cancel := true) -> Variant:
	var v := _overlay_begin()
	var t := label(title, 22, GOLD)
	t.add_theme_font_override("font", _font("Bold"))
	v.add_child(t)
	if body != "":
		v.add_child(label(body, 16, MUTED))
	for i in options.size():
		var b := button(str(options[i]), true)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		b.pressed.connect(func(): done.emit(i))
		v.add_child(b)
	if allow_cancel:
		var c := button("Cancel", true)
		c.pressed.connect(func(): done.emit(null))
		v.add_child(c)
	var r: Variant = await done
	_overlay_end()
	return r


func ask_text(title: String, body: String, placeholder: String) -> String:
	var v := _overlay_begin()
	var t := label(title, 22, GOLD)
	t.add_theme_font_override("font", _font("Bold"))
	v.add_child(t)
	v.add_child(label(body, 16, MUTED))
	var e := TextEdit.new()
	e.placeholder_text = placeholder
	e.custom_minimum_size = Vector2(0, 110)
	e.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	v.add_child(e)
	var b := button("Speak")
	b.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	b.pressed.connect(func():
		if e.text.strip_edges() != "":
			done.emit(e.text.strip_edges()))
	v.add_child(b)
	e.grab_focus.call_deferred()
	var r: String = await done
	_overlay_end()
	return r


var _tribunal_log: RichTextLabel


func tribunal_open(title: String) -> void:
	var v := _overlay_begin(0.35)
	var t := label(title, 22, GOLD)
	t.add_theme_font_override("font", _font("Bold"))
	v.add_child(t)
	_tribunal_log = RichTextLabel.new()
	_tribunal_log.bbcode_enabled = true
	_tribunal_log.fit_content = true
	_tribunal_log.scroll_following = true
	v.add_child(_tribunal_log)


func tribunal_line(who: String, text: String) -> void:
	if _tribunal_log:
		_tribunal_log.append_text("[b][color=#d9b064]%s[/color][/b]  %s\n\n" % [who.replace("[", "[lb]"), text.replace("[", "[lb]")])


func tribunal_close() -> void:
	_tribunal_log = null
	_overlay_end()


func ask_error(who: String, msg: String) -> String:
	var r: Variant = await choose("%s lost the thread" % who, ["Retry", "Skip (they say nothing)"], msg, false)
	return "retry" if r == 0 else "skip"


# ------------------------------------------------------------------ start screen
func setup_screen(ai: AIClient) -> void:
	var v := _overlay_begin(0.6)
	var t := label("Snowbound", 34, GOLD)
	t.add_theme_font_override("font", _font("Bold"))
	v.add_child(t)
	v.add_child(label("A sleeper train, stopped dead in a mountain blizzard. You are Confucius. Five other famous passengers share the carriage, and one of them will kill tonight. Each morning everyone votes to lock someone in the freezing baggage car. Find the killer before the snowplough comes, and don't get locked up yourself.", 16))
	v.add_child(label("OpenAI API key", 13, MUTED))
	var key := LineEdit.new()
	key.secret = true
	key.placeholder_text = "sk-..."
	key.text = ai.api_key
	v.add_child(key)
	var rem := CheckBox.new()
	rem.text = "Remember the key on this device"
	rem.button_pressed = ai.remember
	v.add_child(rem)
	v.add_child(label("Model", 13, MUTED))
	var mdl := LineEdit.new()
	mdl.text = ai.model
	v.add_child(mdl)
	v.add_child(label("Graphics quality", 13, MUTED))
	var qrow := HBoxContainer.new()
	qrow.add_theme_constant_override("separation", 8)
	for i in 3:
		var qb := button(Quality.NAMES[i], i != Quality.level)
		qb.custom_minimum_size = Vector2(120, 44)
		qb.pressed.connect(func():
			if i == Quality.level:
				return
			Quality.level = i
			Quality.save_setting()
			get_tree().reload_current_scene())   # materials, lights and snow are built for one quality level
		qrow.add_child(qb)
	v.add_child(qrow)
	v.add_child(label("Low: fastest, baked lighting only. Balanced: recommended for most phones. High: sharper, more lamps, bloom.", 12, MUTED))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var go := button("Board the train")
	var demo := button("Play without a key (demo lines)", true)
	row.add_child(go)
	row.add_child(demo)
	v.add_child(row)
	var err := label("", 14, RED)
	v.add_child(err)
	go.pressed.connect(func():
		if key.text.strip_edges() == "":
			err.text = "Paste your OpenAI API key first, or play the demo."
			return
		ai.api_key = key.text.strip_edges()
		ai.remember = rem.button_pressed
		ai.model = mdl.text.strip_edges() if mdl.text.strip_edges() != "" else "gpt-6-luna"
		ai.demo = false
		ai.save_settings()
		done.emit(true))
	demo.pressed.connect(func():
		ai.demo = true
		done.emit(true))
	await done
	_overlay_end()
