class_name JoystickView
extends Control
## Floating joystick visual: base 96, knob 40 (PROJECT §9.1).

var active := false
var base := Vector2.ZERO
var knob := Vector2.ZERO


func set_state(a: bool, b: Vector2, k: Vector2) -> void:
	active = a
	base = b
	knob = k
	queue_redraw()


func _draw() -> void:
	if not active:
		return
	var inv := get_global_transform_with_canvas().affine_inverse()
	var b := inv * base
	var k := inv * knob
	draw_circle(b, 48, Color(0.1, 0.09, 0.13, 0.45))
	draw_arc(b, 48, 0, TAU, 32, Color("#9a86ad"), 1.0)
	draw_circle(k, 20, Color(0.6, 0.53, 0.68, 0.7))
	draw_arc(k, 20, 0, TAU, 24, Color("#e0a83e"), 1.0)
