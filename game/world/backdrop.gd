class_name Backdrop
extends CanvasLayer
## Screen-space backdrop: "court" = Gilt sky left + Ember sky right; "none" = void fog.

var root: Control


func _init() -> void:
	layer = -10


func build(kind: String) -> void:
	for c in get_children():
		c.queue_free()
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var base := ColorRect.new()
	base.color = Color("#0d0b12")
	base.set_anchors_preset(Control.PRESET_FULL_RECT)
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(base)
	if kind == "court":
		_half("bg_heaven_sky", 0.0, 0.5, false)
		_half("bg_hell_sky", 0.5, 1.0, false)
		_half("bg_heaven_skyline", 0.0, 0.5, true)
		_half("bg_hell_skyline", 0.5, 1.0, true)
	else:
		var t := TextureRect.new()
		t.texture = Assets.frame("bg_void_fog", 0, "backdrop")
		t.stretch_mode = TextureRect.STRETCH_TILE
		t.set_anchors_preset(Control.PRESET_FULL_RECT)
		t.modulate = Color(1, 1, 1, 0.5)
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(t)


func _half(id: String, a: float, b: float, skyline: bool) -> void:
	var t := TextureRect.new()
	t.texture = Assets.frame(id, 0, "backdrop")
	t.anchor_left = a
	t.anchor_right = b
	t.anchor_top = 0.35 if skyline else 0.0
	t.anchor_bottom = 1.0 if skyline else 1.0
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if b >= 1.0:
		t.flip_h = false
	root.add_child(t)
