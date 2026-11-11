class_name Iso
extends RefCounted
## Grid math for the 64x32 2:1 dimetric grid (PROJECT §8.2). No inline iso maths anywhere else.

const TILE := Vector2(64, 32)
const HALF := Vector2(32, 16)
const HU := 16
const STOREY := 96
const DIRS: PackedStringArray = ["sw", "w", "nw", "n", "ne", "e", "se", "s"]


## Cell centre (continuous allowed) -> local pixel position.
static func cell_to_local(cell: Vector2) -> Vector2:
	return Vector2((cell.x - cell.y) * HALF.x + HALF.x, (cell.x + cell.y) * HALF.y + HALF.y)


static func cellv(cell: Vector2i) -> Vector2:
	return cell_to_local(Vector2(cell))


## Local pixel position -> continuous cell coordinates (cell centres are integers).
static func local_to_cell(p: Vector2) -> Vector2:
	var q := p - HALF
	return Vector2(q.x / TILE.x + q.y / TILE.y, q.y / TILE.y - q.x / TILE.x)


static func local_to_cell_i(p: Vector2) -> Vector2i:
	var g := local_to_cell(p)
	return Vector2i(roundi(g.x), roundi(g.y))


## Converts a grid-space delta to a screen-space delta.
static func grid_delta_to_screen(d: Vector2) -> Vector2:
	return Vector2((d.x - d.y) * HALF.x, (d.x + d.y) * HALF.y)


## Converts a screen-space direction to a grid-space direction (not normalised).
static func screen_delta_to_grid(s: Vector2) -> Vector2:
	return Vector2(s.x / TILE.x + s.y / TILE.y, s.y / TILE.y - s.x / TILE.x)


## Nearest of 8 facings for a screen-space velocity.
static func facing_from_screen(v: Vector2) -> String:
	if v.length_squared() < 0.0001:
		return "s"
	var a := atan2(v.y, v.x) # 0 = east (screen right), +pi/2 = south (screen down)
	var octant := wrapi(roundi(a / (PI / 4.0)), 0, 8)
	# octant 0=e,1=se,2=s,3=sw,4=w,5=nw,6=n,7=ne
	return ["e", "se", "s", "sw", "w", "nw", "n", "ne"][octant]


static func facing_from_grid(d: Vector2) -> String:
	return facing_from_screen(grid_delta_to_screen(d))


## Height offset (in HU) to pixel offset.
## Unit grid-space vector for an 8-way facing name (inverse of facing_from_grid).
static func grid_dir(facing: String) -> Vector2:
	var m := {"se": Vector2(1, 0), "sw": Vector2(0, 1), "nw": Vector2(-1, 0), "ne": Vector2(0, -1),
		"s": Vector2(1, 1), "w": Vector2(-1, 1), "n": Vector2(-1, -1), "e": Vector2(1, -1)}
	return (m.get(facing, Vector2(1, 1)) as Vector2).normalized()


static func height_offset(h_hu: float) -> Vector2:
	return Vector2(0, -h_hu * HU)


static func level_offset(level: int) -> Vector2:
	return Vector2(0, -level * STOREY)


static func cell_distance(a: Vector2, b: Vector2) -> float:
	return a.distance_to(b)
