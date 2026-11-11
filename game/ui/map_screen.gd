class_name MapScreen
extends ScreenBase
## Map (prototype): room graph, current room lit, objective marked. Read-only.


func _ready() -> void:
	setup(0.85)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	center.add_child(v)
	var h := HBoxContainer.new()
	v.add_child(h)
	var t := UiKit.label("The Border Chancery", 24, UiKit.TEXT, "display")
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(t)
	var c := UiKit.button("Close", Vector2(80, 48))
	c.pressed.connect(close)
	h.add_child(c)
	var m := Minimap.new()
	m.big = true
	m.custom_minimum_size = Vector2(440, 230)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(m)
	var obj := GameState.objective_text()
	v.add_child(UiKit.label("Objective: " + (obj if obj != "" else "-"), 16, UiKit.TEXT_DIM))
