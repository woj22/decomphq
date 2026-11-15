class_name Minimap
extends Control
## Fortress map drawn from Content.map_layout() (derived from doors, so it grows with the fortress).
## Small (HUD): centred on the current room. Big (Map screen): every visited room, draggable; unexplored doors as stubs.

signal pressed()

var big := false
var pan := Vector2.ZERO
const CELL := 36.0 # px per layout unit (big)
const CELL_SMALL := 16.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(e: InputEvent) -> void:
	if big:
		if e is InputEventScreenDrag:
			pan += (e as InputEventScreenDrag).relative
			queue_redraw()
		elif e is InputEventMouseMotion and ((e as InputEventMouseMotion).button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
			pan += (e as InputEventMouseMotion).relative
			queue_redraw()
		return
	if (e is InputEventMouseButton and (e as InputEventMouseButton).pressed) or (e is InputEventScreenTouch and (e as InputEventScreenTouch).pressed):
		pressed.emit()
		accept_event()


func _process(_d: float) -> void:
	queue_redraw()


func _unit() -> float:
	return CELL if big else CELL_SMALL


func _room_rect(id: String, origin: Vector2) -> Rect2:
	var lay := Content.map_layout()
	var p: Vector2i = lay.get(id, Vector2i.ZERO)
	var sz := JsonUtil.to_vec2i(Content.area(id).get("size", [10, 8]))
	var u := _unit()
	var w := clampf(sz.x / 26.0, 0.35, 0.95) * u
	var h := clampf(sz.y / 14.0, 0.35, 0.8) * u
	var c := origin + Vector2(p) * u
	return Rect2(c - Vector2(w, h) * 0.5, Vector2(w, h))


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), UiKit.CHARCOAL)
	var lay := Content.map_layout()
	var cur: Vector2i = lay.get(World.area_id, Vector2i.ZERO)
	var origin := size * 0.5 - Vector2(cur) * _unit() + (pan if big else Vector2.ZERO)
	var obj := Content.objective(GameState.objective)
	var obj_area := str((obj.get("target", {}) as Dictionary).get("area", ""))
	var font := get_theme_default_font()
	var known := GameState.visited.duplicate()
	known[World.area_id] = true
	# links (and stubs to unexplored neighbours)
	for id: String in known:
		var a := _room_rect(id, origin)
		for o: Variant in Content.area(id).get("objects", []):
			if o is Dictionary and str((o as Dictionary).get("type", "")) == "door":
				var b := str(((o as Dictionary).get("to", {}) as Dictionary).get("area", ""))
				if not lay.has(b):
					continue
				var br := _room_rect(b, origin)
				if known.has(b):
					draw_line(a.get_center(), br.get_center(), UiKit.EDGE, 2.0 if big else 1.0)
				else:
					var mid := a.get_center().lerp(br.get_center(), 0.45)
					draw_line(a.get_center(), mid, Color(UiKit.EDGE, 0.5), 1.0)
	for id: String in known:
		var r := _room_rect(id, origin)
		if not Rect2(Vector2.ZERO, size).grow(40).intersects(r):
			continue
		var current := id == World.area_id
		draw_rect(r, Color("#43325c") if current else Color("#27232f"))
		draw_rect(r, UiKit.BORDER_GOLD if current else UiKit.SELECT, false, 1.0)
		if id == obj_area:
			draw_rect(Rect2(r.get_center() - Vector2(3, 3), Vector2(6, 6)), Color("#f6d67a"))
		if big:
			var nm := str(Content.area(id).get("name", id)).trim_prefix("The ")
			draw_string(font, Vector2(r.position.x, r.end.y + 11), nm, HORIZONTAL_ALIGNMENT_LEFT, maxf(r.size.x * 2.2, 60.0), 9, UiKit.TEXT)
	draw_rect(Rect2(Vector2.ZERO, size), UiKit.EDGE, false, 1.0)
