class_name Layout
## Where everything is in the train (Godot metres; x across, z along, the locomotive toward -z) and how to walk
## between places. Walkable space is a union of rectangles; routes run along the corridor and the dining aisle.

const BAY := 2.4
const DINING_Z := 17.6
const CORRIDOR_X := 0.92
const AISLE_X := 0.0

## [x0, x1, z0, z1]
static func walk_rects() -> Array:
	var r := [
		# neighbouring areas overlap by at least 0.25 m so you can always walk across a join
		[0.55, 1.3, -1.35, 16.75],          # sleeper corridor (front vestibule to the rear vestibule)
		[-1.2, 0.3, 14.6, 16.2],            # conductor's office
		[0.1, 0.7, 15.15, 15.75],           # office doorway
		[-1.3, 1.3, 16.3, 17.0],            # rear vestibule
		[-0.42, 0.42, 16.6, 18.0],          # gangway, through the dining car's end door
		[-0.36, 0.36, 17.6, 31.75],         # dining aisle
		[-0.75, 0.55, 27.35, 31.75],        # bar and stove end
	]
	for i in 6:
		var z := i * BAY
		r.append([-0.95, 0.32, z + 0.58, z + 1.55])   # compartment floor between the seat and the bed
		r.append([0.0, 0.75, z + 0.26, z + 0.89])     # its doorway, overlapping the floor and the corridor
	return r


static func walkable(p: Vector3, radius := 0.18) -> bool:
	for r in walk_rects():
		if p.x >= r[0] + radius * 0.5 - 0.05 and p.x <= r[1] - radius * 0.5 + 0.05 and p.z >= r[2] + radius * 0.5 - 0.05 and p.z <= r[3] - radius * 0.5 + 0.05:
			return true
	return false


static func compartment_z(n: int) -> float:  # n = 1..6
	return (n - 1) * BAY


static func door_point(n: int) -> Vector3:        # in the corridor outside compartment n
	return Vector3(CORRIDOR_X, 0, compartment_z(n) + 0.58)


static func inside_door(n: int) -> Vector3:
	return Vector3(0.0, 0, compartment_z(n) + 0.9)


static func compartment_seat(n: int) -> Dictionary:  # the upholstered seat on the front wall, facing the bed
	return {"pos": Vector3(-0.85, 0, compartment_z(n) + 0.43), "rot": 0.0}


static func compartment_bed(n: int) -> Dictionary:
	return {"pos": Vector3(0.22, 0, compartment_z(n) + 1.98), "rot": PI / 2.0}


static func compartment_stand(n: int) -> Vector3:
	return Vector3(-0.4, 0, compartment_z(n) + 1.05)


## Dining seats: bay i (0..3), side "L" (four-seat booth, 2 places per bench) or "R" (two-seat), facing +1/-1.
static func dining_seats() -> Array:
	var out := []
	for i in 4:
		var bz := DINING_Z + i * BAY + 1.2
		for face in [-1, 1]:
			var z: float = bz - face * 0.72
			var rot: float = 0.0 if face == 1 else PI
			out.append({"pos": Vector3(-1.2, 0, z), "rot": rot, "bay": i, "side": "L"})
			out.append({"pos": Vector3(-0.78, 0, z), "rot": rot, "bay": i, "side": "L"})
			out.append({"pos": Vector3(1.12, 0, z), "rot": rot, "bay": i, "side": "R"})
	return out


static func stove_chair() -> Dictionary:
	return {"pos": Vector3(-0.92, 0, DINING_Z + 4 * BAY + 0.5), "rot": PI / 2.0}


static func bar_spot() -> Dictionary:
	return {"pos": Vector3(1.15, 0, DINING_Z + 4 * BAY + 1.5), "rot": -PI / 2.0}


static func office_spot() -> Dictionary:
	return {"pos": Vector3(-0.6, 0, 15.3), "rot": PI / 2.0}


static func baggage_door() -> Vector3:
	return Vector3(0.0, 0, DINING_Z + 4 * BAY + 4.55)


## Routes: every place connects to the corridor/aisle spine; walk out to the spine, along it, and in again.
static func route(from: Vector3, to: Vector3) -> Array[Vector3]:
	var pts: Array[Vector3] = []
	var a := _to_spine(from)
	var b := _to_spine(to)
	pts.append_array(a)
	var sa: Vector3 = a[-1] if not a.is_empty() else from
	var sb: Vector3 = b[-1] if not b.is_empty() else to
	pts.append_array(_along_spine(sa, sb))
	var back := b.duplicate()
	back.reverse()
	pts.append_array(back)
	pts.append(to)
	return pts


static func _to_spine(p: Vector3) -> Array[Vector3]:
	var out: Array[Vector3] = []
	if p.z < 14.4 and p.x < 0.45:        # inside a compartment: to its door, then into the corridor
		var n := int(floor(p.z / BAY)) + 1
		out.append(inside_door(n))
		out.append(door_point(n))
	elif p.z >= 14.4 and p.z < 16.4 and p.x < 0.45:   # the office
		out.append(Vector3(0.4, 0, 15.45))
		out.append(Vector3(CORRIDOR_X, 0, 15.45))
	elif p.z >= 17.6 and absf(p.x) > 0.3:  # a dining seat, the stove or the bar: step into the aisle
		out.append(Vector3(clampf(p.x, -0.3, 0.3) * 0.0, 0, p.z))
	elif p.z < 16.4:
		out.append(Vector3(CORRIDOR_X, 0, p.z))
	else:
		out.append(Vector3(0, 0, p.z))
	return out


static func _along_spine(a: Vector3, b: Vector3) -> Array[Vector3]:
	var out: Array[Vector3] = []
	var a_corr := a.z < 16.6
	var b_corr := b.z < 16.6
	if a_corr and not b_corr:
		out.append(Vector3(CORRIDOR_X, 0, 16.7))
		out.append(Vector3(0, 0, 16.7))
		out.append(Vector3(0, 0, 17.9))
	elif b_corr and not a_corr:
		out.append(Vector3(0, 0, 17.9))
		out.append(Vector3(0, 0, 16.7))
		out.append(Vector3(CORRIDOR_X, 0, 16.7))
	out.append(Vector3(b.x, 0, b.z))
	return out
