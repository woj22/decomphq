class_name HoldRing
extends Control
## Hold-to-stamp progress ring (48 px).

var progress := 0.0


func _draw() -> void:
	var c := size / 2.0
	draw_arc(c, 20, 0, TAU, 32, UiKit.PARCHMENT_SHADE, 3.0)
	if progress > 0.0:
		draw_arc(c, 20, -PI / 2, -PI / 2 + TAU * progress, 32, UiKit.SELECT_ON_PARCHMENT, 3.0)
