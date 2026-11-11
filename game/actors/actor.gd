class_name Actor
extends Node2D
## A character on the iso grid: continuous grid position, 8-dir facing, manifest-driven animation.

signal arrived()

var sprite_id := ""
var gpos := Vector2.ZERO
var height_hu := 0.0
var facing := "s"
var anim := "idle"
var speed := 3.0
var path: Array[Vector2i] = []
var model: AreaModel
var actor_id := ""
var idle_anim := "idle"
var _t := 0.0
var _frame := 0
var body: Sprite2D
var shadow: Sprite2D
var label: Label
var ring: Sprite2D
var use_soul_nav := false


func setup(sid: String, area: AreaModel, cell: Vector2, dir: String = "s") -> void:
	sprite_id = sid
	model = area
	facing = dir
	shadow = Sprite2D.new()
	shadow.centered = false
	shadow.texture = Assets.frame("shadow_blob", 0, "fx")
	shadow.offset = -(Assets.info("shadow_blob", "fx")["origin"] as Vector2)
	shadow.z_index = -1
	add_child(shadow)
	body = Sprite2D.new()
	body.centered = false
	add_child(body)
	if Assets.is_placeholder(sid):
		label = Label.new()
		label.text = sid.trim_prefix("chr_")
		label.add_theme_font_size_override("font_size", 8)
		label.position = Vector2(-20, 4)
		label.modulate = Color(1, 1, 1, 0.6)
		add_child(label)
	set_gpos(cell)
	_refresh()


func set_gpos(g: Vector2) -> void:
	gpos = g
	position = Iso.cell_to_local(g)
	if model != null:
		var c := Vector2i(roundi(g.x), roundi(g.y))
		height_hu = model.height_at(c) if model.in_bounds(c) else 0.0
	if body != null:
		body.position = Iso.height_offset(height_hu)


func cell() -> Vector2i:
	return Vector2i(roundi(gpos.x), roundi(gpos.y))


func face_towards(c: Vector2) -> void:
	var d := c - gpos
	if d.length_squared() > 0.0001:
		facing = Iso.facing_from_grid(d)
		_refresh()


func set_anim(a: String) -> void:
	if a == anim:
		return
	anim = a
	_frame = 0
	_t = 0.0
	_refresh()


func walk_path(p: Array[Vector2i]) -> void:
	path = p.duplicate()
	if not path.is_empty() and path[0] == cell():
		path.pop_front()
	if path.is_empty():
		arrived.emit()


func go_to(c: Vector2i) -> bool:
	if model == null:
		return false
	var p := model.soul_path(cell(), c) if use_soul_nav else model.path(cell(), c)
	if p.is_empty():
		return false
	walk_path(p)
	return true


func stop() -> void:
	path.clear()
	set_anim(idle_anim)


func moving() -> bool:
	return not path.is_empty()


func _process(delta: float) -> void:
	if not path.is_empty():
		var target := Vector2(path[0])
		var d := target - gpos
		var step := speed * delta
		if d.length() <= step:
			set_gpos(target)
			path.pop_front()
			if path.is_empty():
				set_anim(idle_anim)
				arrived.emit()
		else:
			set_gpos(gpos + d.normalized() * step)
			var f := Iso.facing_from_grid(d)
			if f != facing:
				facing = f
				_refresh()
			set_anim("walk")
	_animate(delta)


func _animate(delta: float) -> void:
	var a := Assets.anim_info(sprite_id, anim)
	var fps := float(a.get("fps", 2))
	var nf := int(a.get("frames", 1))
	if nf <= 1 or fps <= 0.0:
		return
	_t += delta
	if _t >= 1.0 / fps:
		_t = fmod(_t, 1.0 / fps)
		_frame = (_frame + 1) % nf
		_refresh()


func _refresh() -> void:
	if body == null:
		return
	body.texture = Assets.char_frame(sprite_id, facing, anim, _frame)
	body.offset = -(Assets.info(sprite_id, "character")["origin"] as Vector2)


func set_selected(on: bool) -> void:
	if on and ring == null:
		ring = Sprite2D.new()
		ring.centered = false
		ring.texture = Assets.frame("select_ring", 0, "fx")
		ring.offset = -(Assets.info("select_ring", "fx")["origin"] as Vector2)
		ring.z_index = -1
		add_child(ring)
	if ring != null:
		ring.visible = on
