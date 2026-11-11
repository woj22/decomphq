class_name FaceButtons
extends Control
## PlayStation-style face-button diamond (owner request), bottom-right:
##   TRIANGLE (top) = Gilt Lance · CIRCLE (right) = Ember Brand · CROSS (bottom) = jump · SQUARE (left) = interact.
## Touches are read directly from any finger (multi-touch), so the joystick thumb and a button can be held together.
## Spell buttons: tap = quick cast, hold = charged cast (a ring fills while held). HP and mana bars sit above.

const SIZE := 48.0
const GAP := 4.0
const SYMBOL := {"cross": Color("#7fa7e8"), "circle": Color("#e85a5a"), "triangle": Color("#4fc9a0"), "square": Color("#e08ad6")}

var rects := {} # button -> Rect2 (local)
var pressed_by := {} # touch index or -2 (mouse) -> button
var down := {} # button -> true
var verb := ""
var charge := {"triangle": 0.0, "circle": 0.0}
var hp_frac := 1.0
var mana_frac := 1.0
var show_bars := false
var verb_label: Label


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var span := SIZE * 3 + GAP * 2
	custom_minimum_size = Vector2(span, span + 14)
	size = custom_minimum_size
	set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	offset_right = -12
	offset_bottom = -12
	offset_left = offset_right - span
	offset_top = offset_bottom - (span + 14)
	var y0 := 14.0
	rects = {
		"triangle": Rect2(SIZE + GAP, y0, SIZE, SIZE),
		"square": Rect2(0, y0 + SIZE + GAP, SIZE, SIZE),
		"circle": Rect2((SIZE + GAP) * 2, y0 + SIZE + GAP, SIZE, SIZE),
		"cross": Rect2(SIZE + GAP, y0 + (SIZE + GAP) * 2, SIZE, SIZE)}
	verb_label = UiKit.label("", 12, UiKit.TEXT)
	verb_label.position = Vector2(-4, y0 + SIZE * 2 + GAP + 2)
	verb_label.size = Vector2(SIZE + 8, 14)
	verb_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	verb_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(verb_label)
	Combat.charge_changed.connect(func(b: String, t: float) -> void:
		charge[b] = t
		queue_redraw())
	Combat.hp_changed.connect(func(h: float, m: float) -> void:
		hp_frac = clampf(h / m, 0, 1)
		_bars())
	Combat.mana_changed.connect(func(h: float, m: float) -> void:
		mana_frac = clampf(h / m, 0, 1)
		_bars())
	Combat.hostiles_changed.connect(func(_n: int) -> void: _bars())


func _bars() -> void:
	show_bars = Combat.in_hostile_area() or hp_frac < 0.999 or mana_frac < 0.999
	queue_redraw()


func set_verb(v: String) -> void:
	verb = v
	verb_label.text = v.to_upper()
	queue_redraw()


func _button_at(local: Vector2) -> String:
	for b: String in rects:
		if (rects[b] as Rect2).grow(4).has_point(local):
			return b
	return ""


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	var idx := 0
	var is_press := false
	if event is InputEventScreenTouch:
		idx = (event as InputEventScreenTouch).index
		is_press = (event as InputEventScreenTouch).pressed
	elif event is InputEventMouseButton and (event as InputEventMouseButton).device != InputEvent.DEVICE_ID_EMULATION:
		if (event as InputEventMouseButton).button_index != MOUSE_BUTTON_LEFT:
			return
		idx = -2
		is_press = (event as InputEventMouseButton).pressed
	else:
		return
	if is_press:
		var local: Vector2 = (make_input_local(event) as InputEventMouseButton).position if event is InputEventMouseButton \
			else (make_input_local(event) as InputEventScreenTouch).position
		var b := _button_at(local)
		if b == "":
			return
		pressed_by[idx] = b
		down[b] = true
		Combat.press(b)
		queue_redraw()
		get_viewport().set_input_as_handled()
	elif pressed_by.has(idx):
		var b: String = pressed_by[idx]
		pressed_by.erase(idx)
		down.erase(b)
		Combat.release(b)
		queue_redraw()
		get_viewport().set_input_as_handled()


## Playtest/keyboard helpers.
func tap_button(b: String) -> void:
	Combat.press(b)
	Combat.release(b)


func _draw() -> void:
	for b: String in rects:
		var r: Rect2 = rects[b]
		var is_down := down.has(b)
		var tex := Assets.ui_texture("btn_%s%s" % [b, "_down" if is_down else ""])
		var dim := b == "square" and verb == ""
		var mod := Color(1, 1, 1, 0.45 if dim else 0.92)
		if tex != null and not Assets.is_placeholder("btn_" + b):
			draw_texture_rect(tex, r, false, mod)
		else:
			_draw_fallback(b, r, is_down, mod)
		if charge.get(b, 0.0) > 0.0:
			var c: Vector2 = r.get_center()
			draw_arc(c, SIZE * 0.5 + 1, -PI / 2, -PI / 2 + TAU * float(charge[b]), 24, SYMBOL[b], 3.0)
	if show_bars:
		var w := SIZE * 3 + GAP * 2
		draw_rect(Rect2(0, 0, w, 5), Color(0.1, 0.08, 0.12, 0.9))
		draw_rect(Rect2(0, 0, w * hp_frac, 5), Color("#b3261e"))
		draw_rect(Rect2(0, 7, w, 5), Color(0.1, 0.08, 0.12, 0.9))
		draw_rect(Rect2(0, 7, w * mana_frac, 5), Color("#7fa7e8"))


## Code-drawn button used until the art pipeline's btn_* sprites exist.
func _draw_fallback(b: String, r: Rect2, is_down: bool, mod: Color) -> void:
	var c := r.get_center() + (Vector2(0, 2) if is_down else Vector2.ZERO)
	var rad := SIZE * 0.5 - 2
	draw_circle(c, rad, Color(0.10, 0.09, 0.13, mod.a))
	draw_arc(c, rad, 0, TAU, 32, Color(0.35, 0.32, 0.4, mod.a), 2.0)
	var col: Color = SYMBOL[b]
	col.a = mod.a
	var s := rad * 0.45
	match b:
		"cross":
			draw_line(c + Vector2(-s, -s), c + Vector2(s, s), col, 4.0)
			draw_line(c + Vector2(-s, s), c + Vector2(s, -s), col, 4.0)
		"circle":
			draw_arc(c, s, 0, TAU, 24, col, 3.5)
		"triangle":
			draw_polyline(PackedVector2Array([c + Vector2(0, -s * 1.1), c + Vector2(s * 1.05, s * 0.75),
				c + Vector2(-s * 1.05, s * 0.75), c + Vector2(0, -s * 1.1)]), col, 3.5)
		"square":
			draw_rect(Rect2(c - Vector2(s, s) * 0.85, Vector2(s, s) * 1.7), col, false, 3.5)
