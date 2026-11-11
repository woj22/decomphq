class_name NpcActor
extends Actor
## Named NPC: idle/work animation, optional simple wander inside a zone.

var npc_id := ""
var object_id := ""
var home := Vector2i.ZERO
var wander_cells: Array = []
var _wander_t := 0.0
var rng := RandomNumberGenerator.new()


func _process(delta: float) -> void:
	if not wander_cells.is_empty() and path.is_empty():
		_wander_t -= delta
		if _wander_t <= 0.0:
			_wander_t = rng.randf_range(2.0, 6.0)
			var c: Vector2i = wander_cells[rng.randi_range(0, wander_cells.size() - 1)]
			go_to(c)
	super._process(delta)
