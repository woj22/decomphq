extends TestBase
## PROJECT §3.3 rows, §10.8 reference profiles, §6 Order/pay, §4 gate — on the real case data.


func _row(cid: String, script: Array, verdict: String, ground: String, merit: int, label: String, key: Vector2i,
		known: int = 999) -> Dictionary:
	fresh_game()
	SaveGame.enabled = false
	var d := DeskDriver.new()
	var r := d.play(cid, script, verdict, ground)
	assert_eq(r["merit"], merit, "%s %s merit" % [cid, str(script)])
	assert_eq(r["audit"], label, "%s label" % cid)
	assert_eq(Vector2i(r["key_found"], r["key_total"]), key, "%s key" % cid)
	if known != 999:
		assert_eq(r["known_tally"], known, "%s known" % cid)
	assert_eq(d.wrong_links, 0)
	return r


func test_tallies() -> void:
	var want := {"case_s001": [3, 3], "case_s002": [2, -4], "case_s003": [-2, 1], "case_s004": [-5, 1], "case_s005": [0, -1],
		"case_s006": [1, -1], "case_s007": [5, 1], "case_s008": [-4, 3]}
	for cid: String in want:
		var c := Content.case(cid)
		assert_false(c.is_empty(), cid + " missing")
		assert_eq(Scoring.filed_tally(c), want[cid][0], cid + " filed")
		assert_eq(Scoring.corrected_tally(c), want[cid][1], cid + " corrected")


func test_s002_rows() -> void:
	var r := _row("case_s002", [["pell"], ["link", "r1", "arc_002a"]], "hell", "d_two_ledgers", 9, "upheld", Vector2i(2, 2))
	assert_eq([r["diligence"], r["verdict_pts"], r["ground_pts"]], [3, 4, 2])
	r = _row("case_s002", [["pell"]], "hell", "d_two_ledgers", 7, "upheld", Vector2i(1, 2), -1)
	assert_eq([r["diligence"], r["verdict_pts"], r["ground_pts"]], [1, 4, 2])
	r = _row("case_s002", [], "heaven", "", 0, "overturned", Vector2i(0, 2), 2)
	assert_eq([r["diligence"], r["verdict_pts"], r["ground_pts"]], [0, -2, 0])


func test_s004_rows() -> void:
	_row("case_s004", [["pell"], ["link", "r2", "arc_004a"]], "heaven", "d_enemy_boy", 9, "upheld", Vector2i(2, 2))
	var r := _row("case_s004", [["ask", "q2"]], "hell", "d_enemy_boy", 0, "overturned", Vector2i(1, 2), -2)
	assert_eq([r["diligence"], r["verdict_pts"], r["ground_pts"]], [1, -2, 0])
	_row("case_s004", [["ask", "q2"]], "heaven", "d_enemy_boy", 7, "upheld", Vector2i(1, 2), -2)


func test_s007_rows() -> void:
	var full: Array = DeskDriver.FULL["case_s007"]
	_row("case_s007", full, "heaven", "d_widows", 9, "noted", Vector2i(3, 3))
	_row("case_s007", full, "hell", "d_kell", 9, "noted", Vector2i(3, 3))
	var r := _row("case_s007", full, "heaven", "d_kell", 3, "noted", Vector2i(3, 3))
	assert_eq([r["diligence"], r["verdict_pts"], r["ground_pts"]], [3, 0, 0])
	_row("case_s007", [], "heaven", "", 0, "noted", Vector2i(0, 3))


func test_s008_rows() -> void:
	_row("case_s008", [["pell"], ["link", "r2", "arc_008a"], ["link", "r1", "arc_008b"]], "heaven", "d_violet_ink", 9, "upheld", Vector2i(3, 3))
	assert_true(GameState.flag_true("flag_found_violet_ink"), "violet ink flag via discovery effects")
	var r := _row("case_s008", [["pell"]], "hell", "", 0, "overturned", Vector2i(1, 3), -1)
	assert_eq([r["diligence"], r["verdict_pts"], r["ground_pts"]], [1, -2, 0])


func test_guidelines_and_sides() -> void:
	var g: Array = []
	for c: String in DeskDriver.ORDER:
		g.append(Scoring.guideline(Content.case(c)))
	assert_eq(g, ["heaven", "hell", "heaven", "heaven", "heaven", "heaven"])
	var c7 := Content.case("case_s007")
	for d: Dictionary in c7["discoveries"]:
		var want := {"d_false_name": "hell", "d_kell": "hell", "d_widows": "heaven"}
		assert_eq(Scoring.discovery_side(c7, d), want[d["id"]], d["id"])
		# authored sides agree with computed ones
	for cid: String in Content.case_ids():
		var c := Content.case(cid)
		for d: Dictionary in c.get("discoveries", []):
			var authored := str((d.get("fact", {}) as Dictionary).get("side", ""))
			if authored != "":
				assert_eq(Scoring.discovery_side(c, d), authored, "%s %s side" % [cid, d["id"]])


func test_wrong_link_and_composure() -> void:
	fresh_game()
	SaveGame.enabled = false
	var s := DeskDriver.seat("case_s002")
	s.request_archive()
	var r := s.link("r2", "arc_002a")
	assert_false(r["ok"])
	assert_eq(s.composure(), 2)
	fresh_game()
	s = DeskDriver.seat("case_s001")
	for q: String in ["q1", "q2", "q3"]:
		assert_true(s.ask(q)["ok"], q)
	assert_eq(s.composure(), 0)
	assert_false(s.can_ask())
	# links still allowed at zero, no further cost
	assert_eq(s.composure(), 0)


func test_profiles_10_8() -> void:
	var want := {"perfect": [[9, 9, 9, 9, 9, 9], 54, 0, "pass"], "attentive": [[4, 9, 7, 7, 7, 9], 43, 0, "pass"],
		"half_diligent": [[4, 9, 9, 0, 0, 9], 31, 1, "pass"], "rubric_only": [[9, 0, 0, 0, 0, 0], 9, 4, "correction"],
		"careless": [[4, 0, 0, 0, 0, 0], 4, 4, "correction"]}
	var profiles := DeskDriver.profiles()
	for name: String in want:
		fresh_game()
		SaveGame.enabled = false
		var d := DeskDriver.new()
		var merits: Array = []
		for c: String in DeskDriver.ORDER:
			var spec: Array = profiles[name][c]
			merits.append(d.play(c, spec[0], spec[1], spec[2])["merit"])
		assert_eq(merits, want[name][0], name)
		assert_eq(GameState.get_stat_i("merit"), want[name][1], name + " merit")
		assert_eq(GameState.get_stat_i("overturned"), want[name][2], name + " overturned")
		assert_eq(GameState.gate_result(), want[name][3], name + " gate")
		assert_eq(d.wrong_links, 0, name)
		if want[name][3] == "correction":
			# Pell's correction: reopen, arc_008a, link, re-stamp -> reissue
			GameState.reopen_case("case_s008")
			GameState.give_archive_one("case_s008", "arc_008a")
			var s := JudgementSession.new("case_s008")
			assert_true(s.link("r2", "arc_008a")["ok"], name + " correction link")
			var v := Scoring.side_of(s.known_tally())
			var gr := DeskDriver.best_ground(s, v) if name == "rubric_only" else ""
			s.stamp(v, gr)
			assert_eq(GameState.get_stat_i("cases_processed"), 6)
			assert_eq(GameState.gate_result(), "reissue", name + " after correction")


func test_order_and_pay() -> void:
	assert_eq(Scoring.order_value(68, 3, 0, 24, 1, 0), 78)
	assert_eq(Scoring.order_value(68, 0, 0, 24, 0, 0), 68)
	assert_eq(Scoring.order_value(68, 0, 2, 35, 0, 1), 68 - 10 - 5 - 4)
	assert_eq(Scoring.order_value(68, 0, 20, 24, 0, 0), 0)
	assert_eq(Scoring.pay_value(8, 3, 3, 0), 17)
	assert_eq(12 + Scoring.pay_value(8, 3, 3, 0), 29)
	assert_eq(Scoring.pay_value(8, 3, 2, 1), 8 + 3 + 2 - 2)
	assert_eq(Scoring.pay_value(12, 3, 3, 0), 21)
	# end_shift applies the pay to the purse
	fresh_game()
	SaveGame.enabled = false
	GameState.give_docket(1)
	GameState.start_shift(1)
	var d := DeskDriver.new()
	for c: String in ["case_s001", "case_s002", "case_s003"]:
		d.play(c, DeskDriver.FULL[c], "guideline", "auto")
	GameState.end_shift()
	assert_eq(GameState.get_stat_i("purse"), 29)
	assert_eq(GameState.last_ledger["pay"], 17)
	Dialogue.clear()


func test_hud_start_values() -> void:
	fresh_game()
	assert_eq(GameState.get_stat_i("queue"), 24)
	assert_eq(GameState.get_stat_i("purse"), 12)
	assert_eq(GameState.get_stat_i("order"), 68)


func test_sim_counters() -> void:
	fresh_game()
	SaveGame.enabled = false
	GameState.start_shift(1)
	Clock.advance(120, "test") # 08:00 -> 10:00 : +6 arrivals, registrar ~4.8, adjudicators 2.4
	assert_eq(Sim.arrival + Sim.bench + Sim.heaven_out + Sim.hell_out, 24 + 6)
	assert_eq(Sim.heaven_out + Sim.hell_out, 2)
	assert_true(Sim.bench <= 12)
	var q := GameState.get_stat_i("queue")
	GameState.call_soul("case_s001")
	assert_eq(GameState.get_stat_i("queue"), q - 1)
	Dialogue.clear()
