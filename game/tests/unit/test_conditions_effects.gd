extends TestBase
## Every condition (CONTRACTS §3.1) and effect (§3.2) op.


func _c(c: Dictionary) -> bool:
	return Conditions.check_one(c)


func test_flag_stat_rank_day() -> void:
	fresh_game()
	SaveGame.enabled = false
	assert_false(_c({"op": "flag", "id": "f"}))
	assert_true(_c({"op": "not_flag", "id": "f"}))
	Effects.apply([{"op": "set_flag", "id": "f", "value": true}])
	assert_true(_c({"op": "flag", "id": "f"}))
	Effects.apply([{"op": "set_flag", "id": "s", "value": "kept_copy"}])
	assert_true(_c({"op": "flag", "id": "s"}))
	Effects.apply([{"op": "add_stat", "id": "merit", "value": 5}])
	assert_true(_c({"op": "stat_gte", "id": "merit", "value": 5}))
	assert_false(_c({"op": "stat_gte", "id": "merit", "value": 6}))
	assert_true(_c({"op": "stat_lte", "id": "merit", "value": 5}))
	assert_true(_c({"op": "rank_gte", "value": 1}))
	assert_false(_c({"op": "rank_gte", "value": 2}))
	assert_true(_c({"op": "day_eq", "value": 1}))
	assert_true(_c({"op": "any", "of": [{"op": "flag", "id": "zz"}, {"op": "flag", "id": "f"}]}))
	assert_false(_c({"op": "not", "of": {"op": "flag", "id": "f"}}))
	Effects.apply([{"op": "set_npc_line_flag", "id": "flag_line"}])
	assert_true(_c({"op": "flag", "id": "flag_line"}))
	Effects.apply([{"op": "set_objective", "id": "obj_report_marrow"}])
	assert_eq(GameState.objective, "obj_report_marrow")


func test_case_ops() -> void:
	fresh_game()
	SaveGame.enabled = false
	assert_true(_c({"op": "docket_empty"}))
	Effects.apply([{"op": "give_docket", "day": 1}, {"op": "start_shift", "day": 1}])
	assert_eq(GameState.docket, ["case_s001", "case_s002", "case_s003"])
	assert_true(Clock.running)
	assert_false(_c({"op": "docket_empty"}))
	assert_false(_c({"op": "has_active_case"}))
	assert_true(_c({"op": "case_state", "case": "case_s001", "value": "pending"}))
	Effects.apply([{"op": "call_soul"}])
	assert_eq(GameState.get_stat_i("queue"), 23)
	assert_true(_c({"op": "has_active_case"}))
	assert_true(_c({"op": "active_case_eq", "case": "case_s001"}))
	assert_true(_c({"op": "case_state", "case": "$active_case", "value": "called"}))
	Dialogue.clear()
	# archive: s001 has documents? use s002 to exercise give_archive
	GameState.case_rec("case_s001")["state"] = "judged"
	GameState.case_rec("case_s001")["verdict"] = "heaven"
	assert_true(_c({"op": "verdict", "case": "case_s001", "value": "heaven"}))
	Effects.apply([{"op": "call_soul"}])
	assert_true(_c({"op": "active_case_eq", "case": "case_s002"}))
	assert_true(_c({"op": "archive_available"}))
	var m := Clock.minutes
	Effects.apply([{"op": "give_archive"}])
	assert_eq(Clock.minutes, m + 15)
	assert_true(_c({"op": "holds_archive", "case": "case_s002", "id": "arc_002a"}))
	assert_true(_c({"op": "discovered", "case": "case_s002", "id": "d_two_ledgers"}))
	assert_false(_c({"op": "archive_available"}))
	Effects.apply([{"op": "give_archive"}])
	assert_eq(Clock.minutes, m + 15, "no docs -> no time")
	var s := JudgementSession.new("case_s002")
	s.ask("q1")
	assert_true(_c({"op": "asked", "case": "case_s002", "id": "q1"}))
	Effects.apply([{"op": "give_archive_one", "case": "case_s003", "id": "arc_003"}])
	assert_true(_c({"op": "holds_archive", "case": "case_s003", "id": "arc_003"}))
	Effects.apply([{"op": "advance_clock", "minutes": 7}])
	assert_eq(Clock.minutes, m + 15 + 10 + 7)
	Dialogue.clear()


func test_snapshot_restore_reset_reopen() -> void:
	fresh_game()
	SaveGame.enabled = false
	GameState.add_stat("merit", 10)
	Effects.apply([{"op": "snapshot_stats", "tag": "t"}])
	GameState.add_stat("merit", 7)
	GameState.add_stat("overturned", 2)
	Effects.apply([{"op": "restore_stats", "tag": "t"}])
	assert_eq(GameState.get_stat_i("merit"), 10)
	assert_eq(GameState.get_stat_i("overturned"), 0)
	var d := DeskDriver.new()
	d.play("case_s008", [["pell"]], "hell", "")
	assert_eq(GameState.case_state("case_s008"), "judged")
	var merit := GameState.get_stat_i("merit")
	var r: Dictionary = GameState.cases["case_s008"]["result"]
	Effects.apply([{"op": "reopen_case", "case": "case_s008"}])
	assert_eq(GameState.get_stat_i("merit"), merit - int(r["merit"]))
	assert_eq(GameState.case_state("case_s008"), "seated")
	assert_eq(GameState.active_case_id(), "case_s008")
	assert_true(GameState.holds_archive("case_s008", "arc_008c"), "evidence kept")
	Effects.apply([{"op": "reset_cases", "ids": ["case_s008"]}])
	assert_eq(GameState.case_state("case_s008"), "pending")
	assert_false(GameState.holds_archive("case_s008", "arc_008c"))


func test_incident_rank_items_misc() -> void:
	fresh_game()
	SaveGame.enabled = false
	Effects.apply([{"op": "start_incident", "id": "inc"}])
	assert_eq(GameState.incidents["inc"], "active")
	Effects.apply([{"op": "resolve_incident", "id": "inc", "resolved": true}])
	assert_eq(GameState.get_stat_i("resolved"), 1)
	assert_eq(GameState.get_stat_i("order"), 72)
	Effects.apply([{"op": "resolve_incident", "id": "inc", "resolved": false}])
	assert_eq(GameState.get_stat_i("unresolved"), 0, "decided once")
	Effects.apply([{"op": "unlock_area", "id": "area_adjudicator_chamber"}])
	assert_true(GameState.unlocked_areas.has("area_adjudicator_chamber"))
	Effects.apply([{"op": "buy_item", "id": "item_desk_lamp", "price": 20}])
	assert_false(GameState.items.has("item_desk_lamp"), "12 obols is not enough")
	GameState.add_stat("purse", 10)
	Effects.apply([{"op": "buy_item", "id": "item_desk_lamp", "price": 20}])
	assert_true(GameState.items.has("item_desk_lamp"))
	assert_eq(GameState.get_stat_i("purse"), 2)
	Effects.apply([{"op": "set_rank", "value": 2}])
	assert_eq(GameState.rank, 2)
	assert_eq(Dialogue.current_kind, "ceremony")
	Dialogue.modal_done()
	Effects.apply([{"op": "show_card", "title": "T", "text": "x"}])
	assert_eq(Dialogue.current_kind, "card")
	Dialogue.modal_done()
	Effects.apply([{"op": "end_prototype"}])
	assert_eq(Dialogue.current_kind, "summary")
	Dialogue.modal_done()
	Effects.apply([{"op": "start_dialogue", "id": "dlg_statue"}])
	assert_eq(Dialogue.current_kind, "dialogue")
	Dialogue.clear()
	Effects.apply([{"op": "teleport", "area": "area_booths", "spawn": "default"}])
	GameState.give_docket(1)
	GameState.start_shift(1)
	Effects.apply([{"op": "end_shift"}])
	assert_eq(Dialogue.current_kind, "ledger")
	assert_eq(GameState.get_stat_i("purse"), 2 + 12, "rank 2 base pay")
	Dialogue.clear()


func test_all_content_ops_known() -> void:
	var cond_ops := {}
	var eff_ops := {}
	for o: String in Conditions.OPS:
		cond_ops[o] = true
	for o: String in Effects.OPS:
		eff_ops[o] = true
	var schema: Variant = JsonUtil.load_file("res://../tools/schemas/ops.json") if false else null
	# walk all content for ops
	var stack: Array = []
	for id: Variant in Content.dialogue_ids():
		stack.append(Content.dialogue(str(id)))
	for id: Variant in Content.case_ids():
		stack.append(Content.case(str(id)))
	for id: Variant in Content.npc_ids():
		stack.append(Content.npc(str(id)))
	for id: Variant in Content.area_ids():
		stack.append(Content.area(str(id)))
	stack.append(Content.triggers)
	var bad: Array = []
	while not stack.is_empty():
		var v: Variant = stack.pop_back()
		if v is Dictionary:
			var d: Dictionary = v
			for k: String in d:
				if (k == "effects") and d[k] is Array:
					for e: Variant in d[k]:
						if e is Dictionary and not eff_ops.has(str((e as Dictionary).get("op", ""))):
							bad.append("effect " + str((e as Dictionary).get("op", "")))
				if (k == "conditions" or k == "requires" or k == "solid_until") and (d[k] is Array or d[k] is Dictionary):
					var arr: Array = d[k] if d[k] is Array else [d[k]]
					for c: Variant in arr:
						if c is Dictionary and not cond_ops.has(str((c as Dictionary).get("op", ""))):
							bad.append("condition " + str((c as Dictionary).get("op", "")))
				stack.append(d[k])
		elif v is Array:
			stack.append_array(v)
	assert_eq(bad, [], "unknown ops in content")
