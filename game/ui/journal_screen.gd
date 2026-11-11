class_name JournalScreen
extends ScreenBase
## Journal: objectives, case notes, last 20 dialogue lines (paged).

var tab := "Objectives"
var page := 0
var body: VBoxContainer
var pager: Label
const PER := 6


func _ready() -> void:
	setup(0.85)
	var p := UiKit.panel(UiKit.charcoal_box(8, true))
	p.custom_minimum_size = Vector2(560, 300)
	center.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	p.add_child(v)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	v.add_child(h)
	for t: String in ["Objectives", "Case notes", "Dialogue"]:
		var b := UiKit.button(t, Vector2(110, 40))
		b.pressed.connect(func() -> void:
			tab = t
			page = 0
			_fill())
		h.add_child(b)
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(sp)
	var c := UiKit.button("Close", Vector2(72, 40))
	c.pressed.connect(close)
	h.add_child(c)
	body = VBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(body)
	var pg := HBoxContainer.new()
	pg.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(pg)
	var prev := UiKit.button("<", Vector2(48, 32))
	prev.pressed.connect(func() -> void:
		page = maxi(0, page - 1)
		_fill())
	pg.add_child(prev)
	pager = UiKit.label("", 12, UiKit.TEXT_DIM)
	pg.add_child(pager)
	var nxt := UiKit.button(">", Vector2(48, 32))
	nxt.pressed.connect(func() -> void:
		page += 1
		_fill())
	pg.add_child(nxt)
	_fill()


func _lines() -> Array:
	var out: Array = []
	match tab:
		"Objectives":
			var o := GameState.objective_text()
			out.append("Current: " + (o if o != "" else "-"))
			out.append("Merit %d / %d    Overturned %d" % [GameState.get_stat_i("merit"), Content.cfg_i("merit_gate", 30), GameState.get_stat_i("overturned")])
			for cid: Variant in GameState.docket:
				var c := Content.case(str(cid))
				out.append("%s - %s" % [str(c.get("name", cid)), GameState.case_state(str(cid))])
		"Case notes":
			var cid := GameState.active_case_id()
			if cid == "":
				out.append("No soul is with you.")
			else:
				var s := JudgementSession.new(cid)
				out.append(str(s.data.get("name", "")) + ": " + str(s.data.get("summary", "")).left(70))
				for f: Dictionary in s.facts():
					out.append("- " + str(f["text"]))
				out.append("Documents held: %d" % s.held_archive().size())
		"Dialogue":
			for l: Dictionary in GameState.dialogue_log:
				var sp := str(l.get("speaker", ""))
				out.append((sp + ": " if sp != "" else "") + str(l.get("text", "")))
	return out


func _fill() -> void:
	for c in body.get_children():
		c.queue_free()
	var lines := _lines()
	var pages := maxi(1, int(ceil(lines.size() / float(PER))))
	page = clampi(page, 0, pages - 1)
	pager.text = "%s  p %d/%d" % [tab, page + 1, pages]
	for i in range(page * PER, mini(lines.size(), (page + 1) * PER)):
		var l := UiKit.wrap_label(str(lines[i]), 16)
		l.max_lines_visible = 2
		body.add_child(l)
