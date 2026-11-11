extends TestBase


func test_all_scripts_compile() -> void:
	for dir: String in ["res://autoload", "res://core", "res://world", "res://actors", "res://interact", "res://sim",
			"res://judgement", "res://dialogue", "res://ui"]:
		for f: String in JsonUtil.list_files(dir, ".gd"):
			var s := load(f) as GDScript
			assert_true(s != null and s.can_instantiate(), "compile " + f)
