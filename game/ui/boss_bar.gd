class_name BossBar
extends Control
## Boss name and health across the top of the screen during story fights.

var title := ""
var frac := -1.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_CENTER_TOP)
	custom_minimum_size = Vector2(300, 26)
	offset_left = -150
	offset_right = 150
	offset_top = 64
	offset_bottom = 90
	Combat.boss_hp.connect(func(n: String, f: float) -> void:
		if n != "":
			title = n
		frac = f
		queue_redraw())
	World.area_loaded.connect(func(_a: String) -> void:
		frac = -1.0
		queue_redraw())


func _draw() -> void:
	if frac < 0.0:
		return
	var font := get_theme_default_font()
	draw_string(font, Vector2(0, 10), title, HORIZONTAL_ALIGNMENT_CENTER, size.x, 12, Color("#f6d67a"))
	draw_rect(Rect2(0, 14, size.x, 8), Color(0.1, 0.08, 0.12, 0.9))
	draw_rect(Rect2(0, 14, size.x * frac, 8), Color("#8b3fd9") if title.contains("Thrace") else Color("#b3261e"))
	draw_rect(Rect2(0, 14, size.x, 8), Color("#e0a83e"), false, 1.0)
