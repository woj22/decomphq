class_name GameUI
extends CanvasLayer
## Every 2D element: the start screen, the role card, the phase bar (with Next), the transcript log, speech
## bubbles that follow the passengers' heads, the player's caption and the input panels. Panels are awaited:
## `var v = await ui.ask_accuse(...)`. The panel rides above the on-screen keyboard on phones.

signal panel_done(value: Variant)
signal skip_pressed

const GOLD := Color("e0b25a")
const TEXT := Color("ece7dc")
const MUTED := Color("a39d90")
const PANEL := Color(0.07, 0.085, 0.115, 0.9)

var world: World
var names: Array = []        # figure names by seat
var colours: Array = []      # outfit colours by seat (for the log)
var root: Control
var theme_: Theme
var role_card: PanelContainer
var role_name: Label
var role_desc: Label
var phase_label: Label
var next_btn: Button
var phase_bar: PanelContainer
var log_panel: PanelContainer
var log_text: RichTextLabel
var log_btn: Button
var caption: PanelContainer
var caption_label: Label
var panel: PanelContainer
var panel_box: VBoxContainer
var hint: Label
var bubbles: Array = []      # per seat: {root: VBoxContainer, bubble: PanelContainer, label: Label, tag: Label}
var setup_screen: Control
var _log_open := false


func _ready() -> void:
	layer = 5
	theme_ = _make_theme()
	root = Control.new()
	root.theme = theme_
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_build_hud()
	get_viewport().size_changed.connect(_layout)


# ------------------------------------------------------------------ theme
func _font(file: String) -> FontFile:
	return load("res://assets/fonts/%s" % file)


func _box(bg: Color, border := Color(1, 1, 1, 0.12), radius := 12, pad := 12) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(1)
	s.set_corner_radius_all(radius)
	s.set_content_margin_all(pad)
	s.shadow_color = Color(0, 0, 0, 0.35)
	s.shadow_size = 6
	return s


func _make_theme() -> Theme:
	var t := Theme.new()
	t.default_font = _font("LibreBaskerville-Regular.ttf")
	t.default_font_size = 17
	t.set_color("font_color", "Label", TEXT)
	t.set_stylebox("panel", "PanelContainer", _box(PANEL))
	var btn := _box(GOLD, Color(0, 0, 0, 0), 9, 10)
	btn.shadow_size = 0
	t.set_stylebox("normal", "Button", btn)
	var hov := btn.duplicate() as StyleBoxFlat
	hov.bg_color = GOLD.lightened(0.12)
	t.set_stylebox("hover", "Button", hov)
	var prs := btn.duplicate() as StyleBoxFlat
	prs.bg_color = GOLD.darkened(0.15)
	t.set_stylebox("pressed", "Button", prs)
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	var dis := btn.duplicate() as StyleBoxFlat
	dis.bg_color = Color(0.4, 0.38, 0.34)
	t.set_stylebox("disabled", "Button", dis)
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		t.set_color(c, "Button", Color("1b1408"))
	t.set_font("font", "Button", _font("LibreBaskerville-Bold.ttf"))
	var field := _box(Color(1, 1, 1, 0.07), Color(1, 1, 1, 0.16), 8, 9)
	field.shadow_size = 0
	for cls in ["LineEdit", "TextEdit"]:
		t.set_stylebox("normal", cls, field)
		var f2 := field.duplicate() as StyleBoxFlat
		f2.border_color = GOLD
		t.set_stylebox("focus", cls, f2)
		t.set_color("font_color", cls, TEXT)
		t.set_color("font_placeholder_color", cls, MUTED)
		t.set_color("caret_color", cls, GOLD)
	t.set_stylebox("normal", "OptionButton", field)
	t.set_stylebox("hover", "OptionButton", field)
	t.set_stylebox("pressed", "OptionButton", field)
	t.set_stylebox("focus", "OptionButton", StyleBoxEmpty.new())
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		t.set_color(c, "OptionButton", TEXT)
	t.set_font("font", "OptionButton", _font("LibreBaskerville-Regular.ttf"))
	t.set_stylebox("panel", "PopupMenu", _box(Color(0.1, 0.11, 0.14, 0.98)))
	t.set_color("font_color", "PopupMenu", TEXT)
	for st in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
		t.set_stylebox(st, "CheckBox", StyleBoxEmpty.new())
	t.set_icon("unchecked", "CheckBox", _check_icon(false))
	t.set_icon("checked", "CheckBox", _check_icon(true))
	t.set_color("font_color", "CheckBox", TEXT)
	t.set_color("font_hover_color", "CheckBox", TEXT)
	t.set_color("font_pressed_color", "CheckBox", TEXT)
	t.set_font("normal_font", "RichTextLabel", _font("LibreBaskerville-Regular.ttf"))
	t.set_font("bold_font", "RichTextLabel", _font("LibreBaskerville-Bold.ttf"))
	t.set_font("italics_font", "RichTextLabel", _font("LibreBaskerville-Italic.ttf"))
	t.set_font_size("normal_font_size", "RichTextLabel", 14)
	t.set_font_size("bold_font_size", "RichTextLabel", 14)
	t.set_font_size("italics_font_size", "RichTextLabel", 13)
	t.set_color("default_color", "RichTextLabel", TEXT)
	return t


func _check_icon(on: bool) -> ImageTexture:
	var n := 22
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in n:
		for x in n:
			var edge := x < 2 or y < 2 or x >= n - 2 or y >= n - 2
			var c := Color(0, 0, 0, 0)
			if edge:
				c = GOLD
			elif on and x >= 5 and y >= 5 and x < n - 5 and y < n - 5:
				c = GOLD
			img.set_pixel(x, y, c)
	return ImageTexture.create_from_image(img)


func _label(text: String, size := 17, colour := TEXT, wrap := true) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", colour)
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


func _button(text: String, ghost := false) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(96, 46)
	if ghost:
		var s := _box(Color(0, 0, 0, 0), Color(1, 1, 1, 0.22), 9, 10)
		s.shadow_size = 0
		for st in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(st, s)
		for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
			b.add_theme_color_override(c, TEXT)
		b.add_theme_font_override("font", _font("LibreBaskerville-Regular.ttf"))
	return b


# ------------------------------------------------------------------ HUD
func _build_hud() -> void:
	role_card = PanelContainer.new()
	var rv := VBoxContainer.new()
	rv.add_theme_constant_override("separation", 2)
	rv.add_child(_label("You are secretly the human, playing", 12, MUTED))
	role_name = _label("", 19, GOLD)
	role_name.add_theme_font_override("font", _font("LibreBaskerville-Bold.ttf"))
	rv.add_child(role_name)
	role_desc = _label("", 12, MUTED)
	rv.add_child(role_desc)
	role_card.add_child(rv)
	root.add_child(role_card)

	phase_bar = PanelContainer.new()
	phase_bar.add_theme_stylebox_override("panel", _box(PANEL, Color(1, 1, 1, 0.12), 22, 7))
	var ph := HBoxContainer.new()
	ph.add_theme_constant_override("separation", 10)
	phase_label = _label("", 15, TEXT, false)
	phase_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	phase_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	phase_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	ph.add_child(phase_label)
	next_btn = _button("Next ▸", true)
	next_btn.custom_minimum_size = Vector2(84, 36)
	next_btn.visible = false
	next_btn.pressed.connect(func(): skip_pressed.emit())
	ph.add_child(next_btn)
	phase_bar.add_child(ph)
	root.add_child(phase_bar)

	log_panel = PanelContainer.new()
	log_text = RichTextLabel.new()
	log_text.bbcode_enabled = true
	log_text.scroll_following = true
	log_text.selection_enabled = false
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_panel.add_child(log_text)
	root.add_child(log_panel)
	log_btn = _button("Log", true)
	log_btn.custom_minimum_size = Vector2(70, 40)
	log_btn.pressed.connect(func():
		_log_open = not _log_open
		_layout())
	root.add_child(log_btn)

	caption = PanelContainer.new()
	caption.add_theme_stylebox_override("panel", _box(PANEL, GOLD, 10, 10))
	caption_label = _label("", 16)
	caption.add_child(caption_label)
	caption.visible = false
	root.add_child(caption)

	panel = PanelContainer.new()
	panel_box = VBoxContainer.new()
	panel_box.add_theme_constant_override("separation", 8)
	panel.add_child(panel_box)
	panel.visible = false
	root.add_child(panel)

	hint = _label("Drag to look around", 13, MUTED, false)
	root.add_child(hint)
	for c in [role_card, phase_bar, log_panel, log_btn, caption, panel, hint]:
		c.visible = false
	_layout()


func show_hud(on: bool) -> void:
	for c in [role_card, phase_bar, log_btn, hint]:
		c.visible = on
	_layout()


func narrow() -> bool:
	var s := root.get_viewport_rect().size
	return s.x < 900 or s.x < s.y


func _layout() -> void:
	if root == null:
		return
	var s := root.get_viewport_rect().size
	var m := 12.0
	var nar := narrow()
	role_card.position = Vector2(m, m if not nar else 62)
	role_card.size = Vector2(0, 0)
	role_card.custom_minimum_size.x = 250 if not nar else 200
	role_desc.visible = not nar
	var pw := minf(560.0, s.x - 2 * m)
	phase_bar.custom_minimum_size = Vector2(minf(460, s.x - 110) if nar else 460, 0)
	phase_bar.size = Vector2(0, 0)
	phase_bar.position = Vector2(m, m) if nar else Vector2((s.x - phase_bar.custom_minimum_size.x) / 2, m)
	log_btn.position = Vector2(s.x - 70 - m, m)
	log_btn.visible = role_card.visible and nar
	if nar:
		log_panel.visible = role_card.visible and _log_open
		log_panel.position = Vector2(m, 62)
		log_panel.size = Vector2(s.x - 2 * m, s.y * 0.5)
	else:
		log_panel.visible = role_card.visible
		log_panel.position = Vector2(s.x - 330 - m, m)
		log_panel.size = Vector2(330, s.y - 2 * m - (0 if not panel.visible else 0))
	panel.custom_minimum_size.x = pw
	panel.size = Vector2(pw, 0)
	var kb := 0.0
	if DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
		kb = DisplayServer.virtual_keyboard_get_height() / maxf(1.0, get_window().content_scale_factor)
	var pw_x := (s.x - pw) / 2
	if not nar and pw_x + pw > s.x - 330 - 2 * m:
		pw_x = maxf(m, s.x - 330 - 2 * m - pw)
	panel.position = Vector2(pw_x, s.y - panel.get_combined_minimum_size().y - m - kb)
	caption.custom_minimum_size.x = minf(520, s.x - 2 * m)
	caption.size = Vector2(0, 0)
	caption.position = Vector2((s.x - caption.custom_minimum_size.x) / 2, panel.position.y - caption.get_combined_minimum_size().y - 10 if panel.visible else s.y - 140)
	hint.position = Vector2(m, s.y - 30)
	hint.visible = role_card.visible and not panel.visible and not nar and hint.modulate.a > 0


func _process(_d: float) -> void:
	if panel.visible:
		_layout()
	_update_bubbles()


# ------------------------------------------------------------------ setup screen
func show_setup(ai: AIClient) -> bool:
	setup_screen = ColorRect.new()
	(setup_screen as ColorRect).color = Color(0.02, 0.03, 0.04, 0.72)
	setup_screen.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(setup_screen)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	setup_screen.add_child(center)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var s := root.get_viewport_rect().size
	scroll.custom_minimum_size = Vector2(minf(500, s.x - 24), minf(s.y - 24, 640))
	center.add_child(scroll)
	var card := PanelContainer.new()
	card.add_theme_stylebox_override("panel", _box(PANEL, Color(1, 1, 1, 0.14), 14, 22))
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(card)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	card.add_child(v)
	var title := _label("Last Carriage", 34, GOLD, false)
	title.add_theme_font_override("font", _font("LibreBaskerville-Bold.ttf"))
	v.add_child(title)
	v.add_child(_label("Midnight. A blizzard has stopped the night train dead in the snow. Four passengers share a table, each claiming to be a figure from history. Three of them are AIs. One is you.\n\nOver four rounds everyone says who they think the human is and why, then asks the passenger beside them one yes-or-no question. After round 4, everyone votes. Don't get caught.", 15))
	v.add_child(_label("OpenAI API key", 13, MUTED))
	var key := LineEdit.new()
	key.secret = true
	key.placeholder_text = "sk-..."
	key.text = ai.api_key
	key.virtual_keyboard_type = LineEdit.KEYBOARD_TYPE_PASSWORD
	v.add_child(key)
	var rem := CheckBox.new()
	rem.text = "Remember the key on this device"
	rem.button_pressed = ai.remember
	v.add_child(rem)
	var adv := _button("Advanced ▾", true)
	adv.custom_minimum_size = Vector2(0, 36)
	adv.alignment = HORIZONTAL_ALIGNMENT_LEFT
	v.add_child(adv)
	var advbox := VBoxContainer.new()
	advbox.visible = false
	advbox.add_child(_label("Model", 13, MUTED))
	var mdl := LineEdit.new()
	mdl.text = ai.model
	advbox.add_child(mdl)
	advbox.add_child(_label("API base URL", 13, MUTED))
	var url := LineEdit.new()
	url.text = ai.base_url
	advbox.add_child(url)
	v.add_child(advbox)
	adv.pressed.connect(func(): advbox.visible = not advbox.visible)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var go := _button("Board the train")
	var demo := _button("Demo without a key", true)
	row.add_child(go)
	row.add_child(demo)
	v.add_child(row)
	v.add_child(_label("The key goes only from this device to the API base URL above, and is stored only if you tick Remember.", 12, MUTED))
	var err := _label("", 14, Color("e2726a"))
	v.add_child(err)
	go.pressed.connect(func():
		if key.text.strip_edges() == "":
			err.text = "Paste your OpenAI API key first (or try the demo)."
			return
		ai.api_key = key.text.strip_edges()
		ai.remember = rem.button_pressed
		ai.model = mdl.text.strip_edges() if mdl.text.strip_edges() != "" else "gpt-6-luna"
		ai.base_url = url.text.strip_edges() if url.text.strip_edges() != "" else "https://api.openai.com/v1"
		ai.demo = false
		ai.save_settings()
		panel_done.emit(false))
	demo.pressed.connect(func():
		ai.demo = true
		panel_done.emit(true))
	var result: bool = await panel_done
	setup_screen.queue_free()
	setup_screen = null
	return result


# ------------------------------------------------------------------ roster, log, speech
func set_cast(figs: Array) -> void:
	names = figs.map(func(f): return f["name"])
	colours = figs.map(func(f): return Color(f["outfit"]).lightened(0.5))
	role_name.text = names[0]
	role_desc.text = figs[0]["desc"]
	log_text.clear()
	for b in bubbles:
		b["root"].queue_free()
	bubbles.clear()
	for seat in 4:
		var col := VBoxContainer.new()
		col.alignment = BoxContainer.ALIGNMENT_END
		col.mouse_filter = Control.MOUSE_FILTER_IGNORE
		col.add_theme_constant_override("separation", 5)
		var bub := PanelContainer.new()
		var bs := _box(Color("f4eee0"), Color(0, 0, 0, 0), 12, 9)
		bub.add_theme_stylebox_override("panel", bs)
		var bl := _label("", 15, Color("1d1a14"))
		bub.add_child(bl)
		bub.visible = false
		col.add_child(bub)
		var tag := _label(names[seat], 12, TEXT, false)
		tag.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		var tp := PanelContainer.new()
		tp.add_theme_stylebox_override("panel", _box(Color(0.04, 0.05, 0.07, 0.75), Color(1, 1, 1, 0.14), 10, 3))
		tp.add_child(tag)
		tp.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		col.add_child(tp)
		col.visible = seat != 0
		root.add_child(col)
		root.move_child(col, 0)
		bubbles.append({"root": col, "bubble": bub, "label": bl, "tag": tag, "tagbox": tp})


func _update_bubbles() -> void:
	if world == null or bubbles.is_empty() or world.passengers.size() < 4:
		return
	var cam := world.camera
	var s := root.get_viewport_rect().size
	var scale := get_window().content_scale_factor
	for seat in range(1, 4):
		var b: Dictionary = bubbles[seat]
		var col: VBoxContainer = b["root"]
		var p: Vector3 = world.passengers[seat].head_world() + Vector3(0, 0.2, 0)
		if cam.is_position_behind(p):
			col.visible = false
			continue
		var sp := cam.unproject_position(p) / maxf(scale, 0.01)
		if sp.x < -150 or sp.x > s.x + 150 or sp.y < -100 or sp.y > s.y + 300:
			col.visible = false
			continue
		col.visible = true
		var lbl: Label = b["label"]
		var width := 290.0 if not narrow() else 220.0
		var tw := lbl.get_theme_font("font").get_string_size(lbl.text, HORIZONTAL_ALIGNMENT_LEFT, -1, lbl.get_theme_font_size("font_size")).x
		var w := clampf(tw + 2, 10, width)
		if absf(lbl.custom_minimum_size.x - w) > 0.5:
			lbl.custom_minimum_size.x = w
			(b["bubble"] as Control).reset_size()
		col.reset_size()
		var sz := col.get_combined_minimum_size()
		col.position = Vector2(clampf(sp.x - sz.x / 2, 4, s.x - sz.x - 4), maxf(4.0, sp.y - sz.y))


func say(seat: int, text: String, is_thinking := false) -> void:
	for i in bubbles.size():
		var tag: Label = bubbles[i]["tag"]
		tag.add_theme_color_override("font_color", GOLD if i == seat and text != "" else TEXT)
	if seat == 0:
		caption.visible = text != ""
		caption_label.text = "You: " + text
		_layout()
		return
	var b: Dictionary = bubbles[seat]
	b["bubble"].visible = text != ""
	b["label"].text = text
	b["label"].add_theme_color_override("font_color", Color("6c655a") if is_thinking else Color("1d1a14"))


func set_phase(t: String) -> void:
	phase_label.text = t


func log_system(t: String) -> void:
	log_text.append_text("\n[center][i][color=#a39d90]— %s —[/color][/i][/center]\n" % _esc(t))


func log_line(seat: int, tag: String, text: String) -> void:
	var who: String = names[seat] + (" (you)" if seat == 0 else "")
	log_text.append_text("[b][color=#%s]%s[/color][/b] [color=#a39d90][font_size=11]%s[/font_size][/color]\n%s\n" % [
		(colours[seat] as Color).to_html(false), _esc(who), _esc(tag.to_upper()), _esc(text)])


func _esc(s: String) -> String:
	return s.replace("[", "[lb]")


func wait(seconds: float) -> void:
	next_btn.visible = true
	var t := 0.0
	var skipped := [false]
	var cb := func(): skipped[0] = true
	skip_pressed.connect(cb)
	while t < seconds and not skipped[0]:
		await get_tree().process_frame
		t += get_process_delta_time()
	skip_pressed.disconnect(cb)
	next_btn.visible = false


# ------------------------------------------------------------------ input panels
func _open(title: String, sub := "") -> void:
	for c in panel_box.get_children():
		c.queue_free()
	var h := _label(title, 18, GOLD)
	h.add_theme_font_override("font", _font("LibreBaskerville-Bold.ttf"))
	panel_box.add_child(h)
	if sub != "":
		panel_box.add_child(_label(sub, 13, MUTED))
	panel.visible = true
	hint.visible = false


func _close() -> void:
	panel.visible = false
	for c in panel_box.get_children():
		c.queue_free()
	_layout()


func _text_box(placeholder: String, multi := true) -> Control:
	if multi:
		var t := TextEdit.new()
		t.placeholder_text = placeholder
		t.custom_minimum_size = Vector2(0, 84)
		t.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
		panel_box.add_child(t)
		t.grab_focus.call_deferred()
		return t
	var l := LineEdit.new()
	l.placeholder_text = placeholder
	panel_box.add_child(l)
	l.grab_focus.call_deferred()
	return l


func _picker(options: Array) -> OptionButton:
	var o := OptionButton.new()
	for seat in options:
		o.add_item("%s — %s" % [names[seat], ["your seat", "beside you", "diagonally across", "opposite you"][seat]], seat)
	panel_box.add_child(o)
	return o


func _row(buttons: Array) -> void:
	var r := HBoxContainer.new()
	r.add_theme_constant_override("separation", 10)
	for b in buttons:
		r.add_child(b)
	panel_box.add_child(r)


func ask_intro() -> String:
	_open("Introduce yourself", "Speak as %s. Sound like the others: they are AIs." % names[0])
	var t: TextEdit = _text_box("Good evening...")
	var ok := _button("Say it")
	ok.pressed.connect(func():
		if t.text.strip_edges() != "":
			panel_done.emit(t.text.strip_edges()))
	_row([ok])
	var v: String = await panel_done
	_close()
	return v


func ask_accuse(round_no: int) -> Dictionary:
	_open("Round %d: who do you believe is the human?" % round_no, "Name someone and say why, in character.")
	var o := _picker([1, 2, 3])
	var t: TextEdit = _text_box("Because...")
	var ok := _button("Accuse")
	ok.pressed.connect(func():
		if t.text.strip_edges() != "":
			panel_done.emit({"target": o.get_selected_id(), "text": t.text.strip_edges()}))
	_row([ok])
	var v: Dictionary = await panel_done
	_close()
	return v


func ask_question() -> String:
	_open("Ask %s a yes-or-no question" % names[1], "They sit beside you and must answer yes or no.")
	var l: LineEdit = _text_box("Have you ever...?", false)
	var ok := _button("Ask")
	var go := func(_x = null):
		if l.text.strip_edges() != "":
			panel_done.emit(l.text.strip_edges())
	ok.pressed.connect(go)
	l.text_submitted.connect(go)
	_row([ok])
	var v: String = await panel_done
	_close()
	return v


func ask_answer(asker: int, q: String) -> Dictionary:
	_open("%s asks you:" % names[asker])
	panel_box.add_child(_label("“%s”" % q, 16))
	var l: LineEdit = _text_box("Optional: a short remark in character", false)
	var y := _button("Yes")
	var n := _button("No")
	y.pressed.connect(func(): panel_done.emit({"answer": "Yes", "text": l.text.strip_edges()}))
	n.pressed.connect(func(): panel_done.emit({"answer": "No", "text": l.text.strip_edges()}))
	_row([y, n])
	var v: Dictionary = await panel_done
	_close()
	return v


func ask_vote() -> int:
	_open("Final vote", "Who do you vote for as the human? Voting for someone else keeps suspicion off you.")
	var o := _picker([1, 2, 3])
	var ok := _button("Cast vote")
	ok.pressed.connect(func(): panel_done.emit(o.get_selected_id()))
	_row([ok])
	var v: int = await panel_done
	_close()
	return v


func ask_error(who: String, msg: String) -> String:
	_open("%s lost the thread" % who)
	panel_box.add_child(_label(msg, 14, Color("e2726a")))
	var r := _button("Retry")
	var s := _button("Skip (generic line)", true)
	r.pressed.connect(func(): panel_done.emit("retry"))
	s.pressed.connect(func(): panel_done.emit("skip"))
	_row([r, s])
	var v: String = await panel_done
	_close()
	return v


func show_results(caught: bool, verdict: String, rows: Array, notes: Array) -> void:
	_open("Unmasked" if caught else "Undetected")
	panel_box.add_child(_label(verdict, 15))
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 14)
	for h in ["Passenger", "Voted for", "Received"]:
		grid.add_child(_label(h, 12, MUTED, false))
	for r in rows:
		for c in r:
			grid.add_child(_label(str(c), 13, TEXT, false))
	panel_box.add_child(grid)
	var more := _button("What the AIs were privately thinking ▾", true)
	more.custom_minimum_size = Vector2(0, 36)
	panel_box.add_child(more)
	var nb := VBoxContainer.new()
	nb.visible = false
	for n in notes:
		nb.add_child(_label(n, 12, MUTED))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(0, 160)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	nb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(nb)
	sc.visible = false
	panel_box.add_child(sc)
	more.pressed.connect(func():
		sc.visible = not sc.visible
		nb.visible = sc.visible)
	var again := _button("Ride again")
	again.pressed.connect(func(): panel_done.emit(true))
	_row([again])
	await panel_done
	_close()


func hide_hint() -> void:
	hint.modulate.a = 0.0
	hint.visible = false
