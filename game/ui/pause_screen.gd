class_name PauseScreen
extends ScreenBase
## Pause: Resume / Settings / Save & quit.

signal quit_to_title()


func _ready() -> void:
	setup(0.8)
	var p := UiKit.panel(UiKit.charcoal_box(12, true))
	center.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	p.add_child(v)
	v.add_child(UiKit.label("Paused", 24, UiKit.TEXT, "display"))
	var r := UiKit.button("Resume", Vector2(220, 48))
	r.pressed.connect(close)
	v.add_child(r)
	var s := UiKit.button("Settings", Vector2(220, 48))
	s.pressed.connect(func() -> void:
		var st := SettingsScreen.new()
		get_parent().add_child(st))
	v.add_child(s)
	var q := UiKit.button("Save & quit", Vector2(220, 48))
	q.pressed.connect(func() -> void:
		SaveGame.autosave("quit")
		quit_to_title.emit()
		close())
	v.add_child(q)
