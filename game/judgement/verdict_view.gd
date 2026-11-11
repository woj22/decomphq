class_name VerdictView
extends Control
## Verdict view (05 §6.3 + grounds slot): pick Heaven/Hell, pick a ground, hold 0.6 s (or tap) on the writ to seal,
## soul leaves by its door, epilogue, audit slip (PROJECT §9.3).

const HOLD_S := 0.6

var desk: DeskScreen
var verdict := ""
var ground := ""
var stage := "choose" # choose | sealed | epilogue | slip | done
var result: Dictionary = {}
var heaven_btn: Button
var hell_btn: Button
var defer_btn: Button
const PURGATORY_COL := Color("#9a86ad")
var defer_mark: Label
var writ: PanelContainer
var ground_btn: Button
var hint: Label
var ring: HoldRing
var imprint: TextureRect
var chooser: Control
var _holding := false
var _hold_t := 0.0
var _epi: Array = []
var _epi_i := 0
var content: Control


func build() -> void:
	theme = UiKit.theme()
	UiKit.full_rect(self)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Verdict"
	var bg := ColorRect.new()
	bg.color = Color(0.05, 0.04, 0.07, 0.96)
	UiKit.full_rect(bg)
	add_child(bg)
	var m := MarginContainer.new()
	UiKit.full_rect(m)
	add_child(m)
	UiKit.apply_safe(m)
	content = VBoxContainer.new()
	(content as VBoxContainer).add_theme_constant_override("separation", 6)
	m.add_child(content)
	var top := HBoxContainer.new()
	content.add_child(top)
	var back := UiKit.button("< Back to file", Vector2(130, 40))
	back.name = "Back"
	back.pressed.connect(func() -> void:
		if stage == "choose":
			queue_free())
	top.add_child(back)
	var title := UiKit.label("FINAL JUDGEMENT", 24, UiKit.TEXT, "display")
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	top.add_child(title)
	var spacer := Control.new()
	spacer.custom_minimum_size.x = 130
	top.add_child(spacer)
	var row := HBoxContainer.new()
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row.add_theme_constant_override("separation", 12)
	content.add_child(row)
	heaven_btn = _stamp_button("HEAVEN", "stamp_heaven", "Gilt Gate", UiKit.HEAVEN)
	heaven_btn.name = "StampHeaven"
	heaven_btn.pressed.connect(func() -> void: choose("heaven"))
	row.add_child(heaven_btn)
	writ = UiKit.panel(UiKit.parchment_box(10))
	writ.name = "Writ"
	writ.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	writ.mouse_filter = Control.MOUSE_FILTER_STOP
	writ.gui_input.connect(_on_writ_input)
	row.add_child(writ)
	var wv := VBoxContainer.new()
	wv.mouse_filter = Control.MOUSE_FILTER_IGNORE
	wv.add_theme_constant_override("separation", 4)
	writ.add_child(wv)
	var d := desk.session.data
	var s := desk.session
	var arc_total := (d.get("archive", []) as Array).size()
	for t: String in ["%s, %s" % [str(d.get("name", "")), str(GameState.normalize(d.get("age", "")))],
			"Discoveries: %d    Facts: %d" % [s.discoveries().size(), s.facts().size()],
			"Archive consulted: %d of %d" % [s.held_archive().size(), arc_total]]:
		var l := UiKit.wrap_label(t, 16, UiKit.INK)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		wv.add_child(l)
	ground_btn = UiKit.button("Grounds: No ground", Vector2(0, 48))
	ground_btn.name = "Grounds"
	ground_btn.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ground_btn.pressed.connect(open_chooser)
	wv.add_child(ground_btn)
	defer_btn = UiKit.button("DEFERRED - keep the soul in Purgatory", Vector2(0, 48))
	defer_btn.name = "StampDeferred"
	defer_btn.add_theme_color_override("font_color", PURGATORY_COL)
	defer_btn.add_theme_stylebox_override("normal", UiKit.box(Color("#2a1f3d"), PURGATORY_COL.darkened(0.3), 1, 6))
	defer_btn.add_theme_stylebox_override("pressed", UiKit.box(Color("#43325c"), PURGATORY_COL, 2, 6))
	defer_btn.pressed.connect(func() -> void: choose("purgatory"))
	wv.add_child(defer_btn)
	var holder := CenterContainer.new()
	holder.size_flags_vertical = Control.SIZE_EXPAND_FILL
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	wv.add_child(holder)
	ring = HoldRing.new()
	ring.custom_minimum_size = Vector2(48, 48)
	ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(ring)
	imprint = TextureRect.new()
	imprint.custom_minimum_size = Vector2(64, 64)
	imprint.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	imprint.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	imprint.visible = false
	imprint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(imprint)
	defer_mark = UiKit.label("DEFERRED", 24, PURGATORY_COL, "display")
	defer_mark.visible = false
	defer_mark.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(defer_mark)
	hell_btn = _stamp_button("HELL", "stamp_hell", "Ember Gate", UiKit.HELL)
	hell_btn.name = "StampHell"
	hell_btn.pressed.connect(func() -> void: choose("hell"))
	row.add_child(hell_btn)
	hint = UiKit.label("Choose a stamp, then %s the writ to seal." % ("tap" if Settings.tap_stamp else "hold it on"), 16, UiKit.TEXT_DIM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(hint)
	_update()


func _stamp_button(word: String, icon_id: String, door: String, col: Color) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(112, 140)
	b.icon = Assets.ui_texture(icon_id)
	b.expand_icon = false
	b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
	b.text = word + "\n" + door
	b.add_theme_color_override("font_color", col)
	b.add_theme_color_override("font_hover_color", col)
	b.add_theme_color_override("font_pressed_color", col)
	b.add_theme_stylebox_override("normal", UiKit.box(Color("#1a1722"), col.darkened(0.3), 1, 6))
	b.add_theme_stylebox_override("hover", UiKit.box(Color("#27232f"), col, 1, 6))
	b.add_theme_stylebox_override("pressed", UiKit.box(Color("#27232f"), col, 2, 6))
	return b


func _update() -> void:
	heaven_btn.modulate = Color(1, 1, 1, 1.0 if verdict == "" or verdict == "heaven" else 0.4)
	hell_btn.modulate = Color(1, 1, 1, 1.0 if verdict == "" or verdict == "hell" else 0.4)
	defer_btn.modulate = Color(1, 1, 1, 1.0 if verdict == "" or verdict == "purgatory" else 0.4)
	heaven_btn.position.y = -6 if verdict == "heaven" else 0
	var gtxt := "No ground"
	for f: Dictionary in desk.session.facts():
		if f["id"] == ground:
			gtxt = str(f["text"])
	ground_btn.text = "Grounds: " + gtxt


func choose(v: String) -> void:
	if stage != "choose":
		return
	verdict = v
	Audio.sfx("sfx_tap")
	_update()


func set_ground(fid: String) -> void:
	ground = fid
	_update()


func open_chooser() -> void:
	if stage != "choose":
		return
	chooser = Control.new()
	UiKit.full_rect(chooser)
	chooser.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(chooser)
	chooser.add_child(UiKit.dim(0.5))
	var c := CenterContainer.new()
	UiKit.full_rect(c)
	chooser.add_child(c)
	var p := UiKit.panel(UiKit.parchment_box(8))
	p.custom_minimum_size.x = 380
	c.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	p.add_child(v)
	v.add_child(UiKit.label("Cite one ground", 16, UiKit.INK))
	var facts := desk.session.facts()
	for i in mini(facts.size(), 4):
		var f: Dictionary = facts[i]
		var b := UiKit.button(str(f["text"]), Vector2(360, 48))
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var fid := str(f["id"])
		b.pressed.connect(func() -> void:
			set_ground(fid)
			chooser.queue_free())
		v.add_child(b)
	var none := UiKit.button("No ground", Vector2(360, 48))
	none.pressed.connect(func() -> void:
		set_ground("")
		chooser.queue_free())
	v.add_child(none)


func _on_writ_input(e: InputEvent) -> void:
	if stage != "choose" or verdict == "":
		return
	if e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		var mb: InputEventMouseButton = e
		if Settings.tap_stamp:
			if mb.pressed:
				seal()
			return
		_holding = mb.pressed
		_hold_t = 0.0
		ring.progress = 0.0
		ring.queue_redraw()


func _process(delta: float) -> void:
	if _holding and stage == "choose":
		_hold_t += delta
		ring.progress = clampf(_hold_t / HOLD_S, 0.0, 1.0)
		ring.queue_redraw()
		if _hold_t >= HOLD_S:
			_holding = false
			seal()


## Stamps the verdict (irreversible).
func seal() -> void:
	if stage != "choose" or verdict == "":
		return
	stage = "sealed"
	result = desk.session.stamp(verdict, ground)
	Audio.sfx("sfx_stamp")
	if Settings.haptics:
		Input.vibrate_handheld(40)
	if verdict == "purgatory":
		defer_mark.visible = true
		defer_mark.pivot_offset = defer_mark.size * 0.5
		defer_mark.rotation = deg_to_rad(randf_range(-8.0, 8.0))
	else:
		imprint.texture = Assets.ui_texture("stamp_" + verdict)
		imprint.visible = true
	imprint.pivot_offset = Vector2(32, 32)
	imprint.rotation = deg_to_rad(randf_range(-6.0, 6.0))
	ring.visible = false
	hint.text = ""
	if Settings.shake:
		var tw := create_tween()
		for i in 4:
			tw.tween_property(desk, "position", Vector2(2 if i % 2 == 0 else -2, 0), 0.03)
		tw.tween_property(desk, "position", Vector2.ZERO, 0.03)
	# the soul leaves by its door (booth), then the epilogue
	var tw2 := create_tween()
	tw2.tween_interval(0.5)
	tw2.tween_callback(_soul_leaves)
	tw2.tween_interval(0.7)
	tw2.tween_callback(show_epilogue)


func _soul_leaves() -> void:
	visible = false
	desk.expression = {"heaven": "relieved", "hell": "distressed"}.get(verdict, "neutral")
	desk._refresh_booth()
	Audio.sfx("sfx_door")
	var tw := desk.create_tween()
	tw.tween_property(desk.bust, "position:x", {"heaven": -40.0, "hell": 40.0}.get(verdict, 0.0), 0.6)
	tw.parallel().tween_property(desk.bust, "modulate:a", 0.0, 0.6)


func show_epilogue() -> void:
	if stage != "sealed":
		return
	stage = "epilogue"
	visible = true
	_epi = desk.session.epilogue(verdict)
	_epi_i = 0
	if _epi.is_empty():
		show_slip()
		return
	_show_sheet([str(_epi[0])], false)


func _show_sheet(rows: Array, slip: bool) -> void:
	for c in content.get_children():
		content.remove_child(c)
		c.queue_free()
	var cc := CenterContainer.new()
	cc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	cc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.add_child(cc)
	var p := UiKit.panel(UiKit.parchment_box(12))
	p.name = "Slip" if slip else "Epilogue"
	p.custom_minimum_size.x = 340
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	p.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and (e as InputEventMouseButton).pressed:
			advance())
	cc.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(v)
	if slip:
		var t := UiKit.label("AUDIT SLIP", 16, UiKit.INK)
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		v.add_child(t)
	for r: Variant in rows:
		if r is Array:
			var h := HBoxContainer.new()
			h.mouse_filter = Control.MOUSE_FILTER_IGNORE
			var a := UiKit.label(str(r[0]), 16, UiKit.INK)
			a.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			a.mouse_filter = Control.MOUSE_FILTER_IGNORE
			h.add_child(a)
			var b := UiKit.label(str(r[1]), 16, UiKit.INK)
			b.mouse_filter = Control.MOUSE_FILTER_IGNORE
			h.add_child(b)
			v.add_child(h)
		else:
			var l := UiKit.wrap_label(str(r), 16, UiKit.INK)
			l.custom_minimum_size.x = 316
			l.mouse_filter = Control.MOUSE_FILTER_IGNORE
			v.add_child(l)
	var tap := UiKit.label("(tap)", 12, Color("#6b4a1e"))
	tap.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	tap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(tap)


func slip_rows() -> Array:
	var r := result
	var audit := {"upheld": "Upheld", "overturned": "Overturned", "noted": "Noted", "deferred": "Deferred"}
	var gl := {"sound": "Sound", "unsound": "Unsound", "none": "None"}
	return [["Diligence", "%d/3" % int(r.get("diligence", 0))],
		["Verdict", str(audit.get(str(r.get("audit", "")), ""))],
		["Ground", str(gl.get(str(r.get("ground_label", "none")), "None"))],
		["Merit", "+%d" % int(r.get("merit", 0))],
		["Order", "%+d" % int(r.get("order_delta", 0))]]


func show_slip() -> void:
	stage = "slip"
	Audio.sfx("sfx_page")
	_show_sheet(slip_rows(), true)


## Tap: next epilogue box, then the slip, then done.
func advance() -> void:
	match stage:
		"epilogue":
			_epi_i += 1
			if _epi_i < _epi.size():
				_show_sheet([str(_epi[_epi_i])], false)
			else:
				show_slip()
		"slip":
			stage = "done"
			desk.verdict_finished(verdict)
