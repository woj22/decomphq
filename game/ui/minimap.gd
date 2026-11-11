class_name Minimap
extends Control
## Static 5-room schematic (prototype): current room lit, objective blip. Also drawn large by the Map screen.

signal pressed()

const ROOMS := {
	"area_adjudicator_chamber": Rect2(0.08, 0.06, 0.26, 0.22),
	"area_records_annexe": Rect2(0.56, 0.06, 0.30, 0.22),
	"area_clerks_court": Rect2(0.30, 0.34, 0.40, 0.34),
	"area_arrival_hall": Rect2(0.02, 0.44, 0.24, 0.30),
	"area_booths": Rect2(0.62, 0.72, 0.36, 0.24),
}
const LINKS := [["area_clerks_court", "area_arrival_hall"], ["area_clerks_court", "area_records_annexe"],
	["area_clerks_court", "area_booths"], ["area_clerks_court", "area_adjudicator_chamber"]]
var big := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP


func _gui_input(e: InputEvent) -> void:
	if (e is InputEventMouseButton and (e as InputEventMouseButton).pressed) or (e is InputEventScreenTouch and (e as InputEventScreenTouch).pressed):
		pressed.emit()
		accept_event()


func room_rect(id: String) -> Rect2:
	var r: Rect2 = ROOMS.get(id, Rect2(0.4, 0.4, 0.2, 0.2))
	return Rect2(r.position * size, r.size * size)


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), UiKit.CHARCOAL)
	draw_rect(Rect2(Vector2.ZERO, size), UiKit.EDGE, false, 1.0)
	for l: Array in LINKS:
		var a := room_rect(str(l[0]))
		var b := room_rect(str(l[1]))
		draw_line(a.get_center(), b.get_center(), UiKit.EDGE, 2.0 if big else 1.0)
	var obj := Content.objective(GameState.objective)
	var obj_area := str((obj.get("target", {}) as Dictionary).get("area", ""))
	var font := get_theme_default_font()
	for id: String in ROOMS:
		var r := room_rect(id)
		var current := id == World.area_id
		var locked := id == "area_adjudicator_chamber" and GameState.rank < 2
		var fill := Color("#43325c") if current else Color("#27232f")
		if locked:
			fill = Color("#1a1722")
		draw_rect(r, fill)
		draw_rect(r, UiKit.BORDER_GOLD if current else UiKit.SELECT, false, 1.0)
		if big:
			var name := str(Content.area(id).get("name", id))
			if locked:
				name += " (locked)"
			draw_string(font, r.position + Vector2(4, 16), name, HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 6, 12, UiKit.TEXT)
		if id == obj_area:
			var c := r.get_center() + (Vector2(0, 8) if big else Vector2.ZERO)
			draw_rect(Rect2(c - Vector2(3, 3), Vector2(6, 6)), UiKit.TEXT)
