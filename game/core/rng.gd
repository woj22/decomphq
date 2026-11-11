class_name SeededRng
extends RefCounted
## Deterministic RNG wrapper (seeded streams; state is saveable).

var _rng := RandomNumberGenerator.new()


func _init(seed_value: int = 1) -> void:
	_rng.seed = seed_value


func randf() -> float:
	return _rng.randf()


func randi_range(a: int, b: int) -> int:
	return _rng.randi_range(a, b)


func get_state() -> int:
	return _rng.state


func set_state(s: int) -> void:
	_rng.state = s


## Stable hash of a cell for picking floor variants.
static func cell_hash(cx: int, cy: int, salt: int = 0) -> int:
	var h := (cx * 73856093) ^ (cy * 19349663) ^ (salt * 83492791)
	h = (h ^ (h >> 13)) * 1274126177
	return absi(h ^ (h >> 16))
