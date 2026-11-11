class_name AreaView
extends Node2D
## Builds the visual nodes of an area from its AreaModel: floors, walls/kerbs/doors, windows, props, decor (Y-sorted),
## NPC actors and crowd souls.

var model: AreaModel
var floor_layer: Node2D
var decal_layer: Node2D
var sorted: Node2D
var npcs: Dictionary = {} # object_id -> NpcActor
var animated: Array = [] # [{sprite, id, frames, fps, t, f}]
var crowd: Crowd
var ambient: AmbientLife
var additive_mat := CanvasItemMaterial.new()
var sprite_count := 0


func build(m: AreaModel) -> void:
	model = m
	name = "Area_" + m.id
	additive_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	floor_layer = Node2D.new()
	floor_layer.name = "Floor"
	floor_layer.z_index = -10
	add_child(floor_layer)
	decal_layer = Node2D.new()
	decal_layer.name = "Decals"
	decal_layer.z_index = -9
	add_child(decal_layer)
	sorted = Node2D.new()
	sorted.name = "Sorted"
	sorted.y_sort_enabled = true
	add_child(sorted)
	y_sort_enabled = true
	_build_cells()
	_build_decor()
	_build_npcs()
	crowd = Crowd.new()
	add_child(crowd)
	crowd.setup(self, model, sorted)
	ambient = AmbientLife.new()
	add_child(ambient)
	ambient.setup(model, sorted)
	Sim.presentation_tick.connect(_on_tick)
	EventBus.sim_soul_adjudicated.connect(_on_adjudicated)
	EventBus.flag_changed.connect(func(_a: String, _b: Variant) -> void: refresh_npcs())


func _on_tick() -> void:
	if crowd != null:
		crowd.refresh()


func _on_adjudicated(side: String) -> void:
	if crowd != null:
		crowd.adjudicated(side)


## Places a sprite: `anchor` = continuous cell where the sprite origin sits; `sort_cell` = Y-sort point.
func place(id: String, anchor: Vector2, sort_cell: Vector2, parent: Node2D, h_hu: float = 0.0, kind_hint: String = "",
		z: int = 0) -> Sprite2D:
	var info := Assets.info(id, kind_hint)
	var s := Sprite2D.new()
	s.centered = false
	s.texture = Assets.frame(id, 0, kind_hint)
	s.position = Iso.cell_to_local(sort_cell)
	s.offset = Iso.cell_to_local(anchor) - s.position - (info["origin"] as Vector2) + Iso.height_offset(h_hu)
	s.z_index = z
	if bool(info.get("additive", false)) or id.begins_with("light_pool"):
		s.material = additive_mat
	parent.add_child(s)
	sprite_count += 1
	var nf := int(info.get("frames", 1))
	if nf > 1:
		animated.append({"sprite": s, "id": id, "frames": nf, "fps": float(info.get("fps", 6)), "t": 0.0, "f": 0})
	return s


func _floor_variant(family: String, c: Vector2i) -> String:
	if Assets.has(family):
		return family
	var n := 0
	while Assets.has("%s_%d" % [family, n]):
		n += 1
	if n == 0:
		return family + "_0"
	return "%s_%d" % [family, SeededRng.cell_hash(c.x, c.y) % n]


func _wall_axis(c: Vector2i) -> String:
	if c.x == 0 and c.y == 0:
		return "corner"
	if c.y == 0:
		return "x"
	if c.x == 0:
		return "y"
	if model.is_last_row(c) and model.is_last_col(c):
		return "corner"
	if model.is_last_row(c):
		return "x"
	if model.is_last_col(c):
		return "y"
	return "x"


func _window_at(c: Vector2i) -> String:
	for w: Variant in model.data.get("windows", []):
		if w is Dictionary and JsonUtil.to_vec2i((w as Dictionary).get("cell")) == c:
			return str((w as Dictionary).get("glass", "gold"))
	return ""


func _door_object_at(c: Vector2i) -> Dictionary:
	for o: Variant in model.objects:
		if o is Dictionary:
			var t := str((o as Dictionary).get("type", ""))
			if (t == "door" or t == "soul_door") and JsonUtil.to_vec2i((o as Dictionary).get("cell")) == c:
				return o
	return {}


func _build_cells() -> void:
	var family := str(model.data.get("floor", "floor_flag"))
	for y in model.size.y:
		for x in model.size.x:
			var c := Vector2i(x, y)
			var d := model.def_at(c)
			var kind := str(d.get("kind", "floor"))
			var cv := Vector2(c)
			var near := model.is_last_row(c) or model.is_last_col(c)
			match kind:
				"void":
					continue
				"wall":
					var axis := _wall_axis(c)
					var sid := str(d.get("sprite", ""))
					if sid == "":
						var glass := _window_at(c)
						if axis == "corner":
							sid = "wall_corner"
						elif glass != "":
							sid = "wall_window_%s_%s" % [glass, axis]
						else:
							sid = "wall_plain_" + axis
					if near and sid.begins_with("wall_plain"):
						sid = "wall_kerb_" + axis if axis != "corner" else "wall_kerb_corner"
					place(sid, cv, cv, sorted, 0.0, "wall")
				"kerb":
					var axis := _wall_axis(c)
					place("wall_kerb_corner" if axis == "corner" else "wall_kerb_" + axis, cv, cv, sorted, 0.0, "kerb")
				"door":
					var o := _door_object_at(c)
					var style := str(o.get("style", "plain"))
					var axis := _wall_axis(c)
					if near:
						# near-side doors are openings in the kerb: floor plus an optional low gateway sprite
						place(_floor_variant(family, c), cv, cv, floor_layer, 0.0, "floor")
						if Assets.has("wall_kerb_door_" + axis):
							place("wall_kerb_door_" + axis, cv, cv, sorted, 0.0, "kerb")
					else:
						var sid := "wall_door_" + axis if style == "plain" else "wall_door_%s_%s" % [style, axis]
						place(sid, cv, cv, sorted, 0.0, "wall")
				_:
					var fam := str(d.get("floor", family))
					var fid := str(d.get("floor_sprite", _floor_variant(fam, c)))
					var h := model.height_at(c)
					place(fid, cv, cv, floor_layer, h if not d.has("prop") else 0.0, "floor")
					if kind == "stair":
						place(str(d.get("sprite", "stairs_up")), cv, cv, sorted, 0.0, "wall", -1)
					var prop := str(d.get("prop", ""))
					if prop != "":
						_place_prop(prop, c, d)


func _place_prop(prop: String, c: Vector2i, d: Dictionary) -> void:
	if prop.begins_with("cell_bars_") or prop.begins_with("cell_door_"):
		prop = _bars_variant(prop, c)
	var fp := JsonUtil.to_vec2i(d.get("footprint", Assets.info(prop).get("footprint", [1, 1])), Vector2i.ONE)
	var ch := model.char_at(c)
	if fp != Vector2i.ONE:
		# draw multi-cell props once, at the front (max x, max y) cell
		if model.char_at(c + Vector2i(1, 0)) == ch or model.char_at(c + Vector2i(0, 1)) == ch:
			return
		var anchor := Vector2(c) - Vector2(fp - Vector2i.ONE) / 2.0
		place(prop, anchor, Vector2(c), sorted)
		return
	var flat := not model.cell_solid(c) or prop == "dais"
	var h := 0.0
	if d.has("h_hu") and prop != "dais":
		h = float(d["h_hu"])
	place(prop, Vector2(c), Vector2(c), sorted, h, "prop", -1 if flat else 0)


func _build_decor() -> void:
	for dd: Variant in model.data.get("decor", []):
		if not (dd is Dictionary):
			continue
		var de: Dictionary = dd
		var sid := str(de.get("sprite", ""))
		var c := JsonUtil.to_vec2i(de.get("cell"))
		var fp := JsonUtil.to_vec2i(de.get("footprint", [1, 1]), Vector2i.ONE)
		var anchor := Vector2(c) + Vector2(fp - Vector2i.ONE) / 2.0
		var info := Assets.info(sid)
		var kind := str(info.get("kind", Placeholder.kind_for(sid)))
		if sid.begins_with("light_pool") or sid.begins_with("decal") or kind == "decal" or kind == "floor":
			place(sid, anchor, anchor, decal_layer, 0.0, "")
		else:
			# wall-mounted decor (torches, banners) sorts with its wall cell, drawn just above it
			place(sid, anchor, anchor + Vector2(0.01, 0.01), sorted, 0.0, "", 1)


func _npc_sprite(npc_id: String) -> String:
	var n := Content.npc(npc_id)
	if n.has("sprite"):
		return str(n["sprite"])
	return "chr_clerk_grey"


func _build_npcs() -> void:
	for o: Variant in model.objects:
		if not (o is Dictionary):
			continue
		var od: Dictionary = o
		if str(od.get("type", "")) != "npc":
			continue
		var oid := str(od.get("id", ""))
		var npc_id := str(od.get("npc", ""))
		var a := NpcActor.new()
		a.npc_id = npc_id
		a.object_id = oid
		a.actor_id = npc_id
		sorted.add_child(a)
		var c := JsonUtil.to_vec2i(od.get("cell"))
		a.setup(_npc_sprite(npc_id), model, Vector2(c), str(od.get("facing", "s")))
		a.home = c
		var n := Content.npc(npc_id)
		var work := str(od.get("anim", n.get("anim", "")))
		if work == "" and od.has("desk"):
			work = "work"
		if work != "" and Assets.has_anim(a.sprite_id, work):
			a.idle_anim = work
			a.set_anim(work)
		npcs[oid] = a
	refresh_npcs()


func refresh_npcs() -> void:
	if model == null:
		return
	var changed := false
	for oid: String in npcs:
		var a: NpcActor = npcs[oid]
		var vis := model.object_visible(model.object_by_id(oid))
		if a.visible != vis:
			a.visible = vis
			changed = true
	if changed:
		model.rebuild_nav()


func _process(delta: float) -> void:
	for a: Dictionary in animated:
		a["t"] = float(a["t"]) + delta
		if float(a["t"]) >= 1.0 / float(a["fps"]):
			a["t"] = 0.0
			a["f"] = (int(a["f"]) + 1) % int(a["frames"])
			(a["sprite"] as Sprite2D).texture = Assets.frame(str(a["id"]), int(a["f"]))


## Object under a tap (NPC sprites first, then cell objects).
func object_at_point(world_pos: Vector2) -> Dictionary:
	var best: Dictionary = {}
	var best_y := -1.0e9
	for oid: String in npcs:
		var a: NpcActor = npcs[oid]
		if not a.visible:
			continue
		var r := Rect2(a.position + Vector2(-14, -50 - a.height_hu * Iso.HU), Vector2(28, 54))
		if r.has_point(world_pos) and a.position.y > best_y:
			best_y = a.position.y
			best = model.object_by_id(oid)
	if not best.is_empty():
		return best
	return model.object_at(Iso.local_to_cell_i(world_pos))


## Connection-aware iron bars: pick `cell_bars_m<mask>` / `cell_door_m<mask>` from the 4 neighbours
## (bits 1 = -y, 2 = +x, 4 = +y, 8 = -x). A neighbour connects if it is bars/cell door or a wall/kerb/door cell.
func _bars_variant(prop: String, c: Vector2i) -> String:
	var mask := 0
	var dirs := [[Vector2i(0, -1), 1], [Vector2i(1, 0), 2], [Vector2i(0, 1), 4], [Vector2i(-1, 0), 8]]
	for e: Array in dirs:
		var n: Vector2i = c + (e[0] as Vector2i)
		if not model.in_bounds(n):
			continue
		var nd := model.def_at(n)
		var nk := str(nd.get("kind", ""))
		var np := str(nd.get("prop", ""))
		if np.begins_with("cell_bars") or np.begins_with("cell_door") or nk in ["wall", "kerb", "door"]:
			mask |= int(e[1])
	var base := "cell_door_m" if prop.begins_with("cell_door") else "cell_bars_m"
	var sid := "%s%d" % [base, mask]
	return sid if Assets.has(sid) else prop
