class_name SettingsScreen
extends ScreenBase
## Settings (PROJECT §9.4): text speed, hold/tap stamp, joystick, haptics, screen shake.

var rows: VBoxContainer


func _ready() -> void:
	Settings.load_settings()
	setup(0.85)
	var p := UiKit.panel(UiKit.charcoal_box(12, true))
	center.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	p.add_child(v)
	v.add_child(UiKit.label("Settings", 24, UiKit.TEXT, "display"))
	# Rows scroll so the panel always fits a landscape phone (360 px tall base).
	var sc := ScrollContainer.new()
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.custom_minimum_size = Vector2(400, 200)
	v.add_child(sc)
	rows = VBoxContainer.new()
	rows.add_theme_constant_override("separation", 4)
	rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(rows)
	var b := UiKit.button("Back", Vector2(260, 44))
	b.pressed.connect(func() -> void:
		Settings.save_settings()
		close())
	v.add_child(b)
	_fill()


func _row(label: String, value: String, cb: Callable) -> void:
	var h := HBoxContainer.new()
	var l := UiKit.label(label, 16)
	l.custom_minimum_size.x = 150
	h.add_child(l)
	var b := UiKit.button(value, Vector2(120, 44))
	b.pressed.connect(func() -> void:
		cb.call()
		_fill())
	h.add_child(b)
	rows.add_child(h)


## A text field row (the companion's API key is kept only on this device, in user://companion.cfg).
func _text_row(label: String, value: String, secret: bool, cb: Callable) -> void:
	var h := HBoxContainer.new()
	var l := UiKit.label(label, 16)
	l.custom_minimum_size.x = 150
	h.add_child(l)
	var e := LineEdit.new()
	e.text = value
	e.secret = secret
	e.placeholder_text = "sk-..." if secret else "gpt-4o-mini"
	e.custom_minimum_size = Vector2(220, 44)
	e.virtual_keyboard_enabled = true
	e.text_changed.connect(func(t: String) -> void: cb.call(t))
	h.add_child(e)
	rows.add_child(h)


func _fill() -> void:
	for c in rows.get_children():
		c.queue_free()
	_row("Text speed", ["Slow", "Normal", "Instant"][Settings.text_speed], func() -> void: Settings.text_speed = (Settings.text_speed + 1) % 3)
	_row("Stamp", "Tap" if Settings.tap_stamp else "Hold", func() -> void: Settings.tap_stamp = not Settings.tap_stamp)
	_row("Joystick", "On" if Settings.joystick else "Off", func() -> void: Settings.joystick = not Settings.joystick)
	_row("Haptics", "On" if Settings.haptics else "Off", func() -> void: Settings.haptics = not Settings.haptics)
	_row("Screen shake", "On" if Settings.shake else "Off", func() -> void: Settings.shake = not Settings.shake)
	_text_row("OpenAI key", Companion.api_key, true, func(t: String) -> void:
		Companion.api_key = t.strip_edges()
		Companion.save_settings())
	_text_row("Model", Companion.model, false, func(t: String) -> void:
		if t.strip_edges() != "":
			Companion.model = t.strip_edges()
			Companion.save_settings())
