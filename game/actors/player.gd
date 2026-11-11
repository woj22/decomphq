class_name Player
extends Actor
## The player: path following (tap), continuous joystick movement with slide collision, interaction target.

signal reached_target(object_id: String)

var move_vec := Vector2.ZERO # grid-space direction from joystick/keyboard
var target_object := ""
var trail: Array[Vector2i] = []
var locked := false
const RADIUS := 0.3


func _ready() -> void:
	arrived.connect(_on_arrived)


func _on_arrived() -> void:
	if target_object != "":
		var t := target_object
		target_object = ""
		reached_target.emit(t)


func set_gpos(g: Vector2) -> void:
	var before := cell()
	super.set_gpos(g)
	var now := cell()
	if trail.is_empty() or trail[trail.size() - 1] != now:
		if before != now or trail.is_empty():
			trail.append(now)
			if trail.size() > 8:
				trail.pop_front()


func _process(delta: float) -> void:
	if locked:
		move_vec = Vector2.ZERO
		if not path.is_empty():
			path.clear()
		set_anim("idle")
		_animate(delta)
		return
	if move_vec.length_squared() > 0.01:
		path.clear()
		target_object = ""
		var v := move_vec.normalized() * speed * delta
		var ng := _slide(gpos, v)
		if ng.distance_squared_to(gpos) > 0.0000001:
			set_gpos(ng)
			set_anim("walk")
		else:
			set_anim("idle")
		var f := Iso.facing_from_grid(move_vec)
		if f != facing:
			facing = f
			_refresh()
		_animate(delta)
		return
	if path.is_empty() and anim == "walk":
		set_anim("idle")
	super._process(delta)


func _free_at(p: Vector2) -> bool:
	if not model.walkable(cell()):
		return true # never trap the player on a blocked cell
	for off: Vector2 in [Vector2(RADIUS, 0), Vector2(-RADIUS, 0), Vector2(0, RADIUS), Vector2(0, -RADIUS), Vector2.ZERO]:
		if not model.walkable(Vector2i(roundi(p.x + off.x), roundi(p.y + off.y))):
			return false
	return true


func _slide(from: Vector2, v: Vector2) -> Vector2:
	if _free_at(from + v):
		return from + v
	if _free_at(from + Vector2(v.x, 0)):
		return from + Vector2(v.x, 0)
	if _free_at(from + Vector2(0, v.y)):
		return from + Vector2(0, v.y)
	return from


## The cell the joystick is pushing into (for door entry).
func pushing_into() -> Vector2i:
	if move_vec.length_squared() < 0.01:
		return Vector2i(-999, -999)
	var d := move_vec.normalized() * 0.75
	return Vector2i(roundi(gpos.x + d.x), roundi(gpos.y + d.y))


func follow_cell() -> Vector2i:
	# the cell one step behind the player (for the docket soul)
	if trail.size() >= 2:
		return trail[trail.size() - 2]
	return cell()
