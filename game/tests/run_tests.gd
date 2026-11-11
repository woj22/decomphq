extends SceneTree
## Headless unit test runner: godot --headless --path game -s res://tests/run_tests.gd [-- --only=name]

var _started := false


func _initialize() -> void:
	process_frame.connect(_run_once)
	# Watchdog: a script error must never hang CI.
	create_timer(600.0).timeout.connect(func() -> void:
		print("UNIT TESTS: watchdog timeout")
		quit(2))


func _run_once() -> void:
	if _started:
		return
	_started = true
	var only := ""
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--only="):
			only = a.substr(7)
	var total := 0
	var failed := 0
	var checks := 0
	var files := JsonUtil.list_files("res://tests/unit", ".gd", false)
	for f: String in files:
		if not f.get_file().begins_with("test_"):
			continue
		var script := load(f) as GDScript
		if script == null:
			print("LOAD FAIL ", f)
			failed += 1
			continue
		if not script.can_instantiate():
			print("LOAD FAIL ", f)
			failed += 1
			continue
		var inst: Object = script.new()
		for m: Dictionary in script.get_script_method_list():
			var name := str(m["name"])
			if not name.begins_with("test_"):
				continue
			if only != "" and name.find(only) < 0 and f.find(only) < 0:
				continue
			total += 1
			inst.set("current", f.get_file() + ":" + name)
			var before: int = (inst.get("failures") as PackedStringArray).size()
			inst.call(name)
			var after: int = (inst.get("failures") as PackedStringArray).size()
			if after > before:
				failed += 1
				for i in range(before, after):
					print("  FAIL ", (inst.get("failures") as PackedStringArray)[i])
			else:
				print("  ok   ", f.get_file(), ":", name)
		checks += int(inst.get("checks"))
	print("UNIT TESTS: %d tests, %d checks, %d failed" % [total, checks, failed])
	quit(1 if failed > 0 else 0)
