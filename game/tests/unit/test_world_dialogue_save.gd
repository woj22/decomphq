extends TestBase
## Areas (pathfinding reachability), dialogue traversal, triggers, save -> load equality.


func test_every_interactable_reachable() -> void:
	GameState.rank = 1
	for aid: Variant in Content.area_ids():
		var m := AreaModel.from_id(str(aid))
		for spawn: String in m.spawns:
			var s := m.spawn_cell(spawn)
			assert_true(m.walkable(s), "%s spawn %s walkable" % [aid, spawn])
		var start := m.spawn_cell("default")
		for o: Dictionary in m.objects:
			var t := str(o.get("type", ""))
			if t == "soul_door" or o.has("via"):
				continue
			if t == "stair":
				continue # opens at rank 2 (checked below)
			var uc := m.use_cell(o)
			var p := m.path(start, uc)
			assert_true(not p.is_empty() or start == uc, "%s: %s use cell %s reachable" % [aid, o.get("id"), str(uc)])


func test_stair_opens_at_rank2() -> void:
	fresh_game()
	var m := AreaModel.from_id("area_clerks_court")
	var st := m.object_by_id("obj_stair")
	assert_false(m.walkable(Vector2i(4, 2)), "stair solid at rank 1")
	GameState.rank = 2
	m.rebuild_nav()
	assert_true(m.walkable(Vector2i(4, 2)), "stair open at rank 2")
	assert_false(m.path(m.spawn_cell("default"), m.use_cell(st)).is_empty())
	GameState.rank = 1


func test_soul_doors_reachable_from_bench() -> void:
	var m := AreaModel.from_id("area_booths")
	for o: Dictionary in m.objects:
		if str(o.get("type", "")) == "soul_door":
			assert_false(m.soul_path(Vector2i(10, 5), m.object_cell(o)).is_empty(), "soul exit " + str(o["id"]))
			assert_false(m.soul_path(Vector2i(4, 6), m.object_cell(o)).is_empty(), "bench exit " + str(o["id"]))


func test_doors_reciprocal() -> void:
	for aid: Variant in Content.area_ids():
		var m := AreaModel.from_id(str(aid))
		for o: Dictionary in m.doors():
			var to: Dictionary = o.get("to", {})
			var other := Content.area(str(to.get("area", "")))
			assert_false(other.is_empty(), "door target " + str(o["id"]))
			var om := AreaModel.from_id(str(to.get("area", "")))
			assert_true(om.walkable(om.spawn_cell(str(to.get("spawn", "default")))), "spawn %s in %s" % [to.get("spawn"), to.get("area")])


func test_dialogue_graphs() -> void:
	for id: Variant in Content.dialogue_ids():
		var d := Content.dialogue(str(id))
		var nodes: Dictionary = d.get("nodes", {})
		assert_true(nodes.has(str(d.get("start", ""))), "%s start" % id)
		for nid: String in nodes:
			var n: Dictionary = nodes[nid]
			var nexts: Array = []
			if n.has("next"):
				nexts.append(str(n["next"]))
			if n.has("else"):
				nexts.append(str(n["else"]))
			for c: Dictionary in n.get("choices", []):
				nexts.append(str(c.get("next", "end")))
			for nx: String in nexts:
				assert_true(nx == "end" or nodes.has(nx), "%s.%s -> %s" % [id, nid, nx])
			assert_true(str(n.get("text", "")).length() <= 140, "%s.%s text <= 140" % [id, nid])


func test_npc_dialogues_resolve() -> void:
	fresh_game()
	for nid: Variant in Content.npc_ids():
		var n := Content.npc(str(nid))
		for d: Variant in n.get("dialogue", []):
			var did := str((d as Dictionary).get("id", "")) if d is Dictionary else str(d)
			assert_false(Content.dialogue(did).is_empty(), "%s -> %s" % [nid, did])


func test_registrar_call_flow() -> void:
	fresh_game()
	SaveGame.enabled = false
	Dialogue.clear()
	Dialogue.talk_to("npc_marrow")
	drain()
	assert_eq(GameState.docket.size(), 3)
	assert_eq(Dialogue.dialogue_for_npc("npc_registrar"), "dlg_registrar_call")
	Dialogue.talk_to("npc_registrar")
	drain(["call next"])
	assert_eq(GameState.active_case_id(), "case_s001")
	assert_eq(GameState.objective, "obj_take_desk")


func test_save_load_equal() -> void:
	fresh_game()
	SaveGame.enabled = true
	SaveGame.path = "user://test_save.json"
	GameState.give_docket(1)
	GameState.start_shift(1)
	GameState.call_soul()
	GameState.seat_case("case_s001")
	var s := JudgementSession.new("case_s001")
	s.ask("q2")
	Clock.advance(33, "t")
	var before := SaveGame.snapshot()
	assert_true(SaveGame.autosave("test"))
	GameState.reset()
	Clock.reset()
	Sim.reset()
	SaveGame.restore(SaveGame.read())
	var after := SaveGame.snapshot()
	assert_eq(JSON.stringify(after["state"]), JSON.stringify(before["state"]))
	assert_eq(JSON.stringify(after["clock"]), JSON.stringify(before["clock"]))
	assert_eq(JSON.stringify(after["sim"]), JSON.stringify(before["sim"]))
	assert_eq(GameState.case_state("case_s001"), "seated")
	assert_eq(JudgementSession.new("case_s001").composure(), 2)
	SaveGame.delete_save()
	SaveGame.enabled = false
	Dialogue.clear()
