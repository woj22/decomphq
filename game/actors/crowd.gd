class_name Crowd
extends Node
## Crowd souls in queue/bench zones driven by Sim counters; anonymous adjudication walkers.

var view: Node2D
var model: AreaModel
var queue_slots: Array = [] # flat list of cells, head first per lane, lanes interleaved
var bench_slots: Array = []
var queue_actors: Array = []
var bench_actors: Array = []
var container: Node2D


func setup(v: Node2D, m: AreaModel, parent: Node2D) -> void:
	view = v
	model = m
	container = parent
	var lanes := m.zone_cells("queue")
	# interleave lanes: slot i of every lane before slot i+1 (heads fill first)
	var max_len := 0
	for l: Array in lanes:
		max_len = maxi(max_len, l.size())
	for i in max_len:
		for l: Array in lanes:
			if i < l.size():
				queue_slots.append(l[i])
	for b: Array in m.zone_cells("bench"):
		bench_slots.append_array(b)
	refresh()


func _soul_sprite(i: int) -> String:
	return "chr_soul_%d" % (i % 4)


func refresh() -> void:
	var want_q := mini(Sim.arrival, queue_slots.size())
	var want_b := mini(Sim.bench, bench_slots.size())
	_sync(queue_actors, queue_slots, want_q, "ne")
	_sync(bench_actors, bench_slots, want_b, "ne")


func _sync(list: Array, slots: Array, want: int, dir: String) -> void:
	# occupied cells by named NPCs are skipped
	while list.size() < want:
		var i := list.size()
		var a := Actor.new()
		a.actor_id = "crowd"
		container.add_child(a)
		var cell: Vector2i = slots[i]
		a.setup(_soul_sprite(i * 7 + cell.x), model, Vector2(cell), dir)
		a._frame = (cell.x + cell.y) % 4
		var occupied := false
		for o: Variant in model.objects:
			if o is Dictionary and str((o as Dictionary).get("type", "")) == "npc" and JsonUtil.to_vec2i((o as Dictionary).get("cell")) == cell:
				occupied = true
		a.visible = not occupied
		list.append(a)
	while list.size() > want:
		var a: Actor = list.pop_back()
		a.queue_free()


## A bench soul is taken by an anonymous adjudicator and walks out of its door.
func adjudicated(side: String) -> void:
	var door := Vector2i(-1, -1)
	for o: Variant in model.objects:
		if o is Dictionary and str((o as Dictionary).get("type", "")) == "soul_door":
			var od: Dictionary = o
			var v := str(od.get("verdict", "heaven" if str(od.get("style", "")) == "gilt" else "hell"))
			if v == side:
				door = JsonUtil.to_vec2i(od.get("cell"))
	if door.x < 0 or bench_slots.is_empty():
		refresh()
		return
	var start: Vector2i = bench_slots[mini(bench_actors.size(), bench_slots.size()) - 1] if bench_actors.size() > 0 else bench_slots[0]
	refresh()
	var w := SoulActor.new()
	w.mode = "exit"
	container.add_child(w)
	w.setup(_soul_sprite(start.x), model, Vector2(start), "n")
	w.speed = 2.0
	var p := model.soul_path(start, door)
	if p.is_empty():
		w.queue_free()
		return
	w.arrived.connect(func() -> void: w.queue_free())
	w.walk_path(p)
