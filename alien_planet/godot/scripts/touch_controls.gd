extends Control
## Multi-touch controls for phones/tablets, plus a small HUD (FPS + control hints).
## Left half: floating move stick (push to the edge to run). Right half: drag to look.
## Buttons: JUMP (hold to climb while flying) and FLY (toggle a free camera for viewing the world).

var explorer: CharacterBody3D
var force_touch := false

const STICK_R := 70.0
const LOOK_SENS := 0.0045

var touch_mode := false
var stick_id := -1
var stick_origin := Vector2.ZERO
var stick_pos := Vector2.ZERO
var look_id := -1
var jump_id := -1
var hud: Label
var hint: Label
var hint_t := 9.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	touch_mode = force_touch or DisplayServer.is_touchscreen_available() or OS.has_feature("mobile")
	hud = Label.new()
	hud.position = Vector2(14, 10)
	hud.add_theme_font_size_override("font_size", 15)
	hud.add_theme_color_override("font_color", Color(1, 1, 1, 0.75))
	hud.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.6))
	add_child(hud)
	hint = Label.new()
	hint.add_theme_font_size_override("font_size", 17)
	hint.add_theme_color_override("font_color", Color(1, 0.95, 0.9, 0.9))
	hint.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.7))
	hint.text = ("Left: move (push far to run)   Right: drag to look   JUMP   FLY   CAST: species gallery" if touch_mode else
		"Click to look around   WASD move   Shift run   Space jump   F fly (Space/Ctrl up/down)   Esc release mouse   G species gallery")
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(hint)
	hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	hint.offset_top = -(64 if not touch_mode else 250)
	hint.offset_bottom = hint.offset_top + 30


func _btn_jump() -> Vector2:
	return Vector2(size.x - 110, size.y - 120)


func _btn_fly() -> Vector2:
	return Vector2(size.x - 70, 70)


func _btn_cast() -> Vector2:
	return Vector2(size.x - 70, 170)


## World <-> species gallery (G on desktop, CAST/WORLD button on touch).
func _swap_scene() -> void:
	var gallery := get_tree().current_scene.scene_file_path.ends_with("gallery.tscn")
	get_tree().change_scene_to_file.call_deferred("res://scenes/main.tscn" if gallery else "res://scenes/gallery.tscn")


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo and e.physical_keycode == KEY_G:
		_swap_scene()


func _input(e: InputEvent) -> void:
	if not touch_mode:
		return
	if e is InputEventScreenTouch:
		if e.pressed:
			hint_t = min(hint_t, 2.0)
			if e.position.distance_to(_btn_jump()) < 62:
				jump_id = e.index
				explorer.touch_jump = true
			elif e.position.distance_to(_btn_fly()) < 46:
				explorer.toggle_fly()
			elif e.position.distance_to(_btn_cast()) < 46:
				_swap_scene()
			elif e.position.x < size.x * 0.45 and stick_id == -1:
				stick_id = e.index
				stick_origin = e.position
				stick_pos = e.position
			elif look_id == -1:
				look_id = e.index
		else:
			if e.index == stick_id:
				stick_id = -1
				explorer.stick = Vector2.ZERO
			elif e.index == look_id:
				look_id = -1
			elif e.index == jump_id:
				jump_id = -1
				explorer.touch_jump = false
		get_viewport().set_input_as_handled()
		queue_redraw()
	elif e is InputEventScreenDrag:
		if e.index == stick_id:
			stick_pos = e.position
			var d: Vector2 = (stick_pos - stick_origin) / STICK_R
			d = d.limit_length(1.0)
			explorer.stick = Vector2(d.x, -d.y)
		elif e.index == look_id:
			explorer.add_look(e.relative * LOOK_SENS)
		get_viewport().set_input_as_handled()
		queue_redraw()


func _process(dt: float) -> void:
	if touch_mode:
		queue_redraw()
	hud.text = "%d fps%s" % [Engine.get_frames_per_second(), "   FLY" if explorer and explorer.fly else ""]
	hint_t -= dt
	hint.modulate.a = clampf(hint_t, 0.0, 1.0)


func _draw() -> void:
	if not touch_mode:
		return
	var white := Color(1, 1, 1, 0.22)
	var strong := Color(1, 1, 1, 0.5)
	if stick_id != -1:
		draw_circle(stick_origin, STICK_R, Color(0.1, 0.05, 0.2, 0.25))
		draw_arc(stick_origin, STICK_R, 0, TAU, 48, white, 2.0, true)
		var k := stick_origin + (stick_pos - stick_origin).limit_length(STICK_R)
		draw_circle(k, 30, strong)
	else:
		var c := Vector2(150, size.y - 150)
		draw_arc(c, STICK_R, 0, TAU, 48, Color(1, 1, 1, 0.12), 2.0, true)
		draw_circle(c, 26, Color(1, 1, 1, 0.12))
	var jc := _btn_jump()
	draw_circle(jc, 58, Color(0.2, 0.9, 0.85, 0.35 if jump_id != -1 else 0.18))
	draw_arc(jc, 58, 0, TAU, 48, strong, 2.0, true)
	_label(jc, "JUMP")
	var fc := _btn_fly()
	draw_circle(fc, 42, Color(1.0, 0.45, 0.8, 0.4 if explorer.fly else 0.16))
	draw_arc(fc, 42, 0, TAU, 40, strong, 2.0, true)
	_label(fc, "FLY")
	var cc := _btn_cast()
	draw_circle(cc, 42, Color(0.95, 0.75, 0.3, 0.16))
	draw_arc(cc, 42, 0, TAU, 40, strong, 2.0, true)
	var gal := get_tree().current_scene != null and get_tree().current_scene.scene_file_path.ends_with("gallery.tscn")
	_label(cc, "WORLD" if gal else "CAST")


func _label(c: Vector2, s: String) -> void:
	var f := get_theme_default_font()
	var fs := 18
	var w := f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	draw_string(f, c + Vector2(-w / 2, fs * 0.35), s, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(1, 1, 1, 0.85))
