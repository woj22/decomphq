class_name SoulActor
extends Actor
## Docket soul following the player one cell behind; walker souls leaving by a soul door.

var case_id := ""
var follow: Player
var mode := "follow" # follow | seated | exit | idle
var _repath := 0.0
signal left_room()


func _ready() -> void:
	use_soul_nav = false
	speed = 3.2


func _process(delta: float) -> void:
	if mode == "follow" and follow != null and is_instance_valid(follow):
		_repath -= delta
		var goal := follow.follow_cell()
		if goal == follow.cell():
			goal = cell()
		if path.is_empty() and goal != cell() and Vector2(goal - cell()).length() > 0.5 and _repath <= 0.0:
			_repath = 0.2
			var p := model.soul_path(cell(), goal)
			if p.size() > 0:
				walk_path(p)
		elif path.size() > 0 and Vector2(follow.gpos - gpos).length() < 1.05:
			path.clear()
			set_anim(idle_anim)
			face_towards(follow.gpos)
	super._process(delta)
