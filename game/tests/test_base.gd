class_name TestBase
extends RefCounted
## Minimal assertion helpers for headless unit tests.

var failures: PackedStringArray = []
var checks := 0
var current := ""


func assert_true(v: bool, msg: String = "") -> void:
	checks += 1
	if not v:
		failures.append("%s: expected true %s" % [current, msg])


func assert_false(v: bool, msg: String = "") -> void:
	assert_true(not v, msg)


func assert_eq(a: Variant, b: Variant, msg: String = "") -> void:
	checks += 1
	var same := false
	if (a is int or a is float) and (b is int or b is float):
		same = is_equal_approx(float(a), float(b))
	else:
		same = typeof(a) == typeof(b) and a == b
	if not same:
		failures.append("%s: %s != %s %s" % [current, str(a), str(b), msg])


func assert_near(a: float, b: float, eps: float, msg: String = "") -> void:
	checks += 1
	if absf(a - b) > eps:
		failures.append("%s: %f !~ %f %s" % [current, a, b, msg])


## Resets the global game to a fresh new game without UI.
func fresh_game() -> void:
	Dialogue.clear()
	GameState.new_game()
	Dialogue.clear()


## Drains the dialogue/modal queue: advances lines, picks first choice (or one matching `prefer`), closes modals.
func drain(prefer: Array = [], max_steps: int = 200) -> void:
	for i in max_steps:
		if Dialogue.current_kind == "":
			if Dialogue.queue.is_empty():
				return
			Dialogue._pump()
			continue
		if Dialogue.current_kind == "dialogue":
			if Dialogue.has_choices():
				var pick := 0
				for j in Dialogue.visible_choices.size():
					var t := str(Dialogue.visible_choices[j]["text"]).to_lower()
					for p: Variant in prefer:
						if t.find(str(p).to_lower()) >= 0:
							pick = j
				Dialogue.choose(pick)
			else:
				Dialogue.advance()
		else:
			Dialogue.modal_done()
