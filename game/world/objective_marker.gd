class_name ObjectiveMarker
extends Node2D
## A bobbing gold chevron over the current objective's target object, when it is in this area.

var _t := 0.0


func _process(delta: float) -> void:
	_t += delta
	var tgt := _target_cell()
	visible = tgt.x > -900 and not World.desk_open
	if visible:
		position = Iso.cell_to_local(Vector2(tgt)) + Vector2(0, -78 + sin(_t * 4.0) * 4.0)
	queue_redraw()


func _target_cell() -> Vector2i:
	var obj := Content.objective(GameState.objective)
	var tg: Variant = obj.get("target")
	if not (tg is Dictionary) or str((tg as Dictionary).get("area", "")) != World.area_id or World.model == null:
		return Vector2i(-999, -999)
	var o := World.model.object_by_id(str((tg as Dictionary).get("object", "")))
	if o.is_empty():
		return Vector2i(-999, -999)
	return World.model.object_cell(o)


func _draw() -> void:
	var gold := Color("#f6d67a")
	draw_colored_polygon(PackedVector2Array([Vector2(-7, -8), Vector2(7, -8), Vector2(0, 2)]), Color("#0d0b12"))
	draw_colored_polygon(PackedVector2Array([Vector2(-5, -7), Vector2(5, -7), Vector2(0, 0)]), gold)
