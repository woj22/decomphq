class_name AreaModel
extends RefCounted
## Pure data model of one area built from the CONTRACTS §2 ASCII format: cell defs, walkability, objects, zones.

var id := ""
var name := ""
var data: Dictionary = {}
var size := Vector2i.ZERO
var grid: PackedStringArray = []
var legend: Dictionary = {}
var overrides: Dictionary = {} # Vector2i -> def
var objects: Array = []
var spawns: Dictionary = {}
var zones: Dictionary = {}
var astar := AStarGrid2D.new()
var soul_astar := AStarGrid2D.new()


static func from_id(area_id: String) -> AreaModel:
	var m := AreaModel.new()
	m.load_data(Content.area(area_id))
	return m


func load_data(d: Dictionary) -> void:
	data = d
	id = str(d.get("id", ""))
	name = str(d.get("name", id))
	var s: Array = d.get("size", [0, 0])
	size = Vector2i(int(s[0]), int(s[1]))
	grid = PackedStringArray()
	for row: Variant in d.get("grid", []):
		grid.append(str(row))
	if size == Vector2i.ZERO and grid.size() > 0:
		size = Vector2i(grid[0].length(), grid.size())
	legend = d.get("legend", {})
	overrides = {}
	for o: Variant in d.get("overrides", []):
		if o is Dictionary:
			overrides[JsonUtil.to_vec2i((o as Dictionary).get("cell"))] = o
	objects = d.get("objects", [])
	spawns = d.get("spawns", {})
	zones = d.get("zones", {})
	rebuild_nav()


func in_bounds(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < size.x and c.y < size.y


func char_at(c: Vector2i) -> String:
	if not in_bounds(c) or c.y >= grid.size() or c.x >= grid[c.y].length():
		return " "
	return grid[c.y][c.x]


## Resolved definition of a cell: legend entry merged with an override.
func def_at(c: Vector2i) -> Dictionary:
	var d: Dictionary = {}
	var l: Variant = legend.get(char_at(c), {})
	if l is Dictionary:
		d = (l as Dictionary).duplicate()
	elif l is String:
		d = {"kind": l}
	if overrides.has(c):
		d.merge(overrides[c] as Dictionary, true)
	if not d.has("kind"):
		d["kind"] = "floor" if char_at(c) != " " else "void"
	return d


func kind_at(c: Vector2i) -> String:
	return str(def_at(c).get("kind", "void"))


func height_at(c: Vector2i) -> float:
	var d := def_at(c)
	if d.has("h_hu"):
		return float(d["h_hu"])
	if d.has("height_hu"):
		return float(d["height_hu"])
	return 0.0


func is_last_row(c: Vector2i) -> bool:
	return c.y == size.y - 1


func is_last_col(c: Vector2i) -> bool:
	return c.x == size.x - 1


## Static solidity for the player (before NPC occupancy).
func cell_solid(c: Vector2i) -> bool:
	if not in_bounds(c):
		return true
	var d := def_at(c)
	var kind := str(d.get("kind", "floor"))
	match kind:
		"wall", "kerb", "door", "void":
			return true
		"stair":
			if d.has("solid_until"):
				return not Conditions.check(d["solid_until"])
			return GameState.rank < 2
		"queue":
			return not bool(d.get("walkable", false))
		"seat":
			return bool(d.get("solid", true))
		"prop":
			return bool(d.get("solid", true))
		_:
			if float(d.get("h_hu", 0)) != 0.0:
				return true # raised cells (dais) are not walkable; only stairs allow a height step
			return bool(d.get("solid", false))


func object_visible(o: Dictionary) -> bool:
	if str(o.get("type", "")) == "npc" and Clock.is_night() and not bool(o.get("night", false)):
		return false # asleep in the Dormitory
	if o.has("day_only") and Clock.is_night():
		return false
	if bool(o.get("night_only", false)) and not Clock.is_night():
		return false
	if o.has("visible_if"):
		return Conditions.check(o["visible_if"])
	if str(o.get("type", "")) == "npc" and o.has("conditions"):
		return Conditions.check(o["conditions"])
	return true


func rebuild_nav() -> void:
	for a: AStarGrid2D in [astar, soul_astar]:
		a.region = Rect2i(Vector2i.ZERO, size)
		a.cell_size = Vector2.ONE
		a.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
		a.default_compute_heuristic = AStarGrid2D.HEURISTIC_OCTILE
		a.default_estimate_heuristic = AStarGrid2D.HEURISTIC_OCTILE
		a.update()
	for y in size.y:
		for x in size.x:
			var c := Vector2i(x, y)
			var solid := cell_solid(c)
			astar.set_point_solid(c, solid)
			var k := kind_at(c)
			var soul_ok := not solid or k == "queue" or k == "seat" or k == "door"
			soul_astar.set_point_solid(c, not soul_ok)
	# NPC cells stay walkable for A* (CONTRACT_CHANGES #8); actors do not block paths.


func walkable(c: Vector2i) -> bool:
	return in_bounds(c) and not astar.is_point_solid(c)


func path(from: Vector2i, to: Vector2i) -> Array[Vector2i]:
	if not in_bounds(from) or not in_bounds(to):
		return []
	var was_solid := astar.is_point_solid(from)
	astar.set_point_solid(from, false)
	var p: Array[Vector2i] = astar.get_id_path(from, to)
	astar.set_point_solid(from, was_solid)
	return p


func soul_path(from: Vector2i, to: Vector2i) -> Array[Vector2i]:
	if not in_bounds(from) or not in_bounds(to):
		return []
	var a := soul_astar.is_point_solid(from)
	var b := soul_astar.is_point_solid(to)
	soul_astar.set_point_solid(from, false)
	soul_astar.set_point_solid(to, false)
	var p: Array[Vector2i] = soul_astar.get_id_path(from, to)
	soul_astar.set_point_solid(from, a)
	soul_astar.set_point_solid(to, b)
	return p


func nearest_walkable(c: Vector2i, from: Vector2i = Vector2i(-1, -1)) -> Vector2i:
	if walkable(c):
		return c
	var best := Vector2i(-1, -1)
	var best_d := 1.0e9
	for r in range(1, maxi(size.x, size.y)):
		for y in range(c.y - r, c.y + r + 1):
			for x in range(c.x - r, c.x + r + 1):
				var n := Vector2i(x, y)
				if maxi(absi(x - c.x), absi(y - c.y)) != r or not walkable(n):
					continue
				var d := Vector2(n - c).length()
				if from.x >= 0:
					d += Vector2(n - from).length() * 0.01
				if d < best_d:
					best_d = d
					best = n
		if best.x >= 0:
			return best
	return c


func object_by_id(oid: String) -> Dictionary:
	for o: Variant in objects:
		if o is Dictionary and str((o as Dictionary).get("id", "")) == oid:
			return o
	return {}


func object_at(c: Vector2i) -> Dictionary:
	for o: Variant in objects:
		if not (o is Dictionary):
			continue
		var od: Dictionary = o
		if not object_visible(od):
			continue
		if JsonUtil.to_vec2i(od.get("cell")) == c:
			return od
		if od.has("cells"):
			for cc: Variant in od["cells"]:
				if JsonUtil.to_vec2i(cc) == c:
					return od
	return {}


func object_cell(o: Dictionary) -> Vector2i:
	return JsonUtil.to_vec2i(o.get("cell"))


## Where the player stands to use an object (default: nearest walkable neighbour).
func use_cell(o: Dictionary) -> Vector2i:
	if o.has("use_cell"):
		return JsonUtil.to_vec2i(o["use_cell"])
	var c := object_cell(o)
	for d: Vector2i in [Vector2i(0, 1), Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, -1), Vector2i(1, 1), Vector2i(-1, 1), Vector2i(1, -1), Vector2i(-1, -1)]:
		if walkable(c + d):
			return c + d
	return nearest_walkable(c)


func spawn_cell(spawn: String) -> Vector2i:
	if spawns.has(spawn):
		var s: Variant = spawns[spawn]
		if s is Dictionary:
			return JsonUtil.to_vec2i((s as Dictionary).get("cell"))
		return JsonUtil.to_vec2i(s)
	if spawns.has("default"):
		return spawn_cell("default")
	return Vector2i(size.x / 2, size.y / 2)


## Zones of a kind. Falls back to legend-derived queue/seat cells when the area defines none.
func zone_cells(kind: String) -> Array:
	var out: Array = []
	var keys := zones.keys()
	keys.sort()
	for k: Variant in keys:
		var z: Dictionary = zones[k]
		var zk := str(z.get("kind", ""))
		if zk == kind or (kind == "bench" and zk == "seat"):
			var cells: Array = []
			for c: Variant in z.get("cells", []):
				cells.append(JsonUtil.to_vec2i(c))
			if zk == "queue":
				var head := JsonUtil.to_vec2i(z.get("head", cells[cells.size() - 1] if cells.size() > 0 else [0, 0]))
				cells.sort_custom(func(a: Vector2i, b: Vector2i) -> bool: return Vector2(a - head).length() < Vector2(b - head).length())
			out.append(cells)
	if out.is_empty() and bool(data.get("crowd_from_legend", false)):
		var legend_kind := "seat" if kind == "bench" else kind
		var cells: Array = []
		for y in size.y:
			for x in size.x:
				if kind_at(Vector2i(x, y)) == legend_kind:
					cells.append(Vector2i(x, y))
		if not cells.is_empty():
			out.append(cells)
	return out


## Bounding rectangle of the area in local pixels.
func pixel_bounds() -> Rect2:
	var pts := [Iso.cellv(Vector2i(0, 0)) + Vector2(0, -16 - 112), Iso.cellv(Vector2i(size.x - 1, 0)) + Vector2(32, 0),
		Iso.cellv(Vector2i(0, size.y - 1)) + Vector2(-32, 0), Iso.cellv(size - Vector2i.ONE) + Vector2(0, 16)]
	var r := Rect2(pts[0], Vector2.ZERO)
	for p: Vector2 in pts:
		r = r.expand(p)
	return r


func doors() -> Array:
	var out: Array = []
	for o: Variant in objects:
		if o is Dictionary and str((o as Dictionary).get("type", "")) == "door":
			out.append(o)
	return out
