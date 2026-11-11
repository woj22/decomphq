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
	rows = VBoxContainer.new()
	rows.add_theme_constant_override("separation", 6)
	v.add_child(rows)
	var b := UiKit.button("Back", Vector2(260, 48))
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
	var b := UiKit.button(value, Vector2(120, 48))
	b.pressed.connect(func() -> void:
		cb.call()
		_fill())
	h.add_child(b)
	rows.add_child(h)


func _fill() -> void:
	for c in rows.get_children():
		c.queue_free()
	_row("Text speed", ["Slow", "Normal", "Instant"][Settings.text_speed], func() -> void: Settings.text_speed = (Settings.text_speed + 1) % 3)
	_row("Stamp", "Tap" if Settings.tap_stamp else "Hold", func() -> void: Settings.tap_stamp = not Settings.tap_stamp)
	_row("Joystick", "On" if Settings.joystick else "Off", func() -> void: Settings.joystick = not Settings.joystick)
	_row("Haptics", "On" if Settings.haptics else "Off", func() -> void: Settings.haptics = not Settings.haptics)
	_row("Screen shake", "On" if Settings.shake else "Off", func() -> void: Settings.shake = not Settings.shake)
