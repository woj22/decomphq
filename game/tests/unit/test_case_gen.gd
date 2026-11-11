extends TestBase
## Procedural cases: 400 generated souls must be well-formed, scorable and solvable.


func test_generated_cases() -> void:
	var names := {}
	var violet := 0
	for i in 400:
		var id := "gen_t%d" % i
		var c := CaseGen.generate(id, 0.3)
		assert_false(c.is_empty(), "generated " + id)
		names[str(c["name"])] = true
		assert_true((c["entries"] as Array).size() >= 4, id + " entries")
		for e: Dictionary in c["entries"]:
			assert_true(str(e["text"]).length() <= 80, id + " entry budget: " + str(e["text"]))
			assert_false(str(e["text"]).contains("{"), id + " unfilled placeholder: " + str(e["text"]))
		for a: Dictionary in c["archive"]:
			for card: Variant in a["cards"]:
				assert_true(str(card).length() <= 80, id + " card budget: " + str(card))
		for q: Dictionary in c["questions"]:
			for box: Variant in q["answer"]:
				assert_true(str(box).length() <= 140, id + " answer budget")
		var ex: Dictionary = c["expected"]
		assert_eq(Scoring.filed_tally(c), int(ex["tally_filed"]), id + " filed")
		assert_eq(Scoring.corrected_tally(c), int(ex["tally_corrected"]), id + " corrected")
		assert_eq(Scoring.all_discovery_ids(c).size(), (c["discoveries"] as Array).size(), id + " discoveries reachable")
		assert_true(Scoring.key_total(c) >= 1, id + " key facts")
		# a perfect investigation scores the full guideline verdict
		var r := Scoring.score(c, Scoring.all_discovery_ids(c), [], str(ex["guideline"]) if str(ex["guideline"]) != "abstain" else "heaven", "")
		assert_true(int(r["diligence"]) == 3, id + " full diligence when all found")
		if "violet" in (c["ext"]["twists"] as Array):
			violet += 1
	assert_true(names.size() >= 300, "at least 300 distinct names in 400 souls (got %d)" % names.size())
	assert_true(violet > 60 and violet < 200, "violet forgeries appear at roughly the set rate (%d)" % violet)
	assert_eq(CaseGen.generate("gen_same").hash(), CaseGen.generate("gen_same").hash(), "deterministic")
