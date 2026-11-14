class_name HUD
extends CanvasLayer
## Touch-first interface: location banner, virtual joystick, Speak button, dialogue panel with a
## live 3D portrait, and the Court roster (Dramatis Personae).

signal dialogue_closed
signal roster_toggled(open: bool)

const GOLD := Color("d9a63e")
const CREAM := Color("efe6d2")
const INK := Color("1c1512")
const DIM := Color("b9a98c")

var font_title: FontFile
var font_body: FontFile
var joystick := Vector2.ZERO

var _root: Control
var _loc_title: Label
var _loc_sub: Label
var _loc_small: Label
var _banner: Control
var _banner_t := 0.0
var _speak_btn: Button
var _speak_target: NPC
var _dialogue: PanelContainer
var _dlg_portrait: TextureRect
var _dlg_name: Label
var _dlg_title: Label
var _dlg_mood: Label
var _dlg_text: RichTextLabel
var _dlg_opts: VBoxContainer
var _dlg_vp: Portrait
var _dlg_npc: NPC
var _type_t := 0.0
var _roster: Control
var _roster_list: VBoxContainer
var _roster_detail: VBoxContainer
var _roster_vp: Portrait
var _roster_tex: TextureRect
var _joy_base: Control
var _joy_knob: Control
var _joy_touch := -1
var _joy_center := Vector2.ZERO
var main: Node


func _ready() -> void:
	layer = 10
	font_title = load("res://fonts/Cinzel.ttf")
	font_body = load("res://fonts/Alegreya.ttf")
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	var th := Theme.new()
	th.default_font = font_body
	th.default_font_size = 22
	_root.theme = th
	_build_location()
	_build_joystick()
	_build_buttons()
	_build_dialogue()
	_build_roster()


# ------------------------------------------------------------------ styling

func _panel_style(alpha := 0.9, border := 2) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.11, 0.085, 0.07, alpha)
	sb.border_color = GOLD
	sb.set_border_width_all(border)
	sb.set_corner_radius_all(6)
	sb.set_content_margin_all(14)
	sb.shadow_color = Color(0, 0, 0, 0.35)
	sb.shadow_size = 6
	return sb


func _label(text: String, size: int, col := CREAM, title := false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font_title if title else font_body)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.6))
	l.add_theme_constant_override("shadow_offset_y", 2)
	return l


func _button(text: String, size := 22) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_override("font", font_title)
	b.add_theme_font_size_override("font_size", size)
	b.add_theme_color_override("font_color", CREAM)
	b.add_theme_color_override("font_hover_color", Color("ffe3a3"))
	b.add_theme_color_override("font_pressed_color", GOLD)
	var n := _panel_style(0.88, 2)
	n.set_content_margin_all(10)
	var h := n.duplicate() as StyleBoxFlat
	h.bg_color = Color(0.22, 0.15, 0.1, 0.95)
	var p := n.duplicate() as StyleBoxFlat
	p.bg_color = Color(0.35, 0.22, 0.08, 0.95)
	b.add_theme_stylebox_override("normal", n)
	b.add_theme_stylebox_override("hover", h)
	b.add_theme_stylebox_override("pressed", p)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.custom_minimum_size = Vector2(0, 52)
	return b


# ------------------------------------------------------------------ location

func _build_location() -> void:
	var box := VBoxContainer.new()
	box.position = Vector2(24, 18)
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(box)
	_loc_small = _label("", 24, CREAM, true)
	box.add_child(_loc_small)
	var sub := _label("Caelora · The Palatium Ardens · First day of the Royal Session", 17, DIM)
	box.add_child(sub)
	_banner = VBoxContainer.new()
	_banner.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_banner.offset_left = -450
	_banner.offset_right = 450
	_banner.offset_top = 96
	_banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_banner.modulate.a = 0.0
	_root.add_child(_banner)
	_loc_title = _label("", 44, Color("ffe9b8"), true)
	_loc_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.add_child(_loc_title)
	var rule := ColorRect.new()
	rule.color = GOLD
	rule.custom_minimum_size = Vector2(0, 2)
	_banner.add_child(rule)
	_loc_sub = _label("", 21, CREAM)
	_loc_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.add_child(_loc_sub)


func show_location(room: Dictionary) -> void:
	_loc_small.text = str(room.get("name", ""))
	_loc_title.text = str(room.get("name", ""))
	_loc_sub.text = str(room.get("subtitle", ""))
	_banner_t = 4.0


# ------------------------------------------------------------------ buttons & joystick

func _build_buttons() -> void:
	var court := _button("Court", 22)
	court.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	court.offset_left = -160
	court.offset_right = -24
	court.offset_top = 20
	court.offset_bottom = 72
	court.pressed.connect(toggle_roster)
	_root.add_child(court)
	_speak_btn = _button("Speak", 22)
	_speak_btn.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	_speak_btn.offset_left = -400
	_speak_btn.offset_right = -30
	_speak_btn.offset_top = -130
	_speak_btn.offset_bottom = -44
	_speak_btn.visible = false
	_speak_btn.pressed.connect(func(): if _speak_target: main.begin_dialogue(_speak_target))
	_root.add_child(_speak_btn)


func set_speak_target(npc: NPC) -> void:
	_speak_target = npc
	var show := npc != null and not _dialogue.visible and not _roster.visible
	_speak_btn.visible = show
	if npc != null:
		_speak_btn.text = "Speak · " + _short_name(npc)


func _short_name(npc: NPC) -> String:
	if not npc.notable:
		return npc.title
	return npc.display_name


func _build_joystick() -> void:
	_joy_base = Control.new()
	_joy_base.custom_minimum_size = Vector2(190, 190)
	_joy_base.size = Vector2(190, 190)
	_joy_base.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_reset_joy()
	_joy_base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_joy_base.draw.connect(func():
		_joy_base.draw_circle(Vector2(95, 95), 92, Color(0.1, 0.07, 0.05, 0.35))
		_joy_base.draw_arc(Vector2(95, 95), 92, 0, TAU, 48, Color(GOLD, 0.7), 2.5, true))
	_root.add_child(_joy_base)
	_joy_knob = Control.new()
	_joy_knob.size = Vector2(80, 80)
	_joy_knob.position = Vector2(55, 55)
	_joy_knob.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_joy_knob.draw.connect(func():
		_joy_knob.draw_circle(Vector2(40, 40), 38, Color(0.85, 0.65, 0.25, 0.55))
		_joy_knob.draw_arc(Vector2(40, 40), 38, 0, TAU, 32, Color(1, 0.92, 0.7, 0.9), 2.0, true))
	_joy_base.add_child(_joy_knob)


## Returns true when the joystick consumed the event.
func joystick_input(ev: InputEvent) -> bool:
	if _dialogue.visible or _roster.visible:
		return false
	var vp := _root.get_viewport_rect().size
	if ev is InputEventScreenTouch:
		var t := ev as InputEventScreenTouch
		if t.pressed and _joy_touch < 0 and t.position.x < vp.x * 0.42 and t.position.y > vp.y * 0.35:
			_joy_touch = t.index
			_joy_center = t.position
			_joy_base.position = t.position - Vector2(95, 95)
			_update_knob(Vector2.ZERO)
			return true
		if not t.pressed and t.index == _joy_touch:
			_joy_touch = -1
			joystick = Vector2.ZERO
			_update_knob(Vector2.ZERO)
			_reset_joy()
			return true
	elif ev is InputEventScreenDrag:
		var dr := ev as InputEventScreenDrag
		if dr.index == _joy_touch:
			var off := (dr.position - _joy_center).limit_length(90.0)
			joystick = off / 90.0
			_update_knob(off)
			return true
	return false


func _reset_joy() -> void:
	_joy_base.offset_left = 50
	_joy_base.offset_right = 240
	_joy_base.offset_top = -250
	_joy_base.offset_bottom = -60


func _update_knob(off: Vector2) -> void:
	_joy_knob.position = Vector2(55, 55) + off


# ------------------------------------------------------------------ dialogue

func _build_dialogue() -> void:
	_dialogue = PanelContainer.new()
	_dialogue.add_theme_stylebox_override("panel", _panel_style(0.94, 2))
	_dialogue.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_dialogue.offset_left = 30
	_dialogue.offset_right = -30
	_dialogue.offset_top = -330
	_dialogue.offset_bottom = -22
	_dialogue.visible = false
	_root.add_child(_dialogue)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 22)
	_dialogue.add_child(row)
	var frame := PanelContainer.new()
	var fs := _panel_style(1.0, 3)
	fs.bg_color = Color("3a2a22")
	fs.set_content_margin_all(0)
	frame.add_theme_stylebox_override("panel", fs)
	frame.custom_minimum_size = Vector2(250, 280)
	row.add_child(frame)
	_dlg_portrait = TextureRect.new()
	_dlg_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_dlg_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	frame.add_child(_dlg_portrait)
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 4)
	row.add_child(col)
	var head := HBoxContainer.new()
	col.add_child(head)
	_dlg_name = _label("", 30, Color("ffe9b8"), true)
	head.add_child(_dlg_name)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(spacer)
	_dlg_mood = _label("", 19, DIM)
	head.add_child(_dlg_mood)
	_dlg_title = _label("", 19, GOLD)
	col.add_child(_dlg_title)
	_dlg_text = RichTextLabel.new()
	_dlg_text.bbcode_enabled = true
	_dlg_text.fit_content = false
	_dlg_text.scroll_active = true
	_dlg_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_dlg_text.add_theme_font_override("normal_font", font_body)
	_dlg_text.add_theme_font_size_override("normal_font_size", 23)
	_dlg_text.add_theme_font_size_override("italics_font_size", 22)
	_dlg_text.add_theme_color_override("default_color", CREAM)
	col.add_child(_dlg_text)
	_dlg_opts = VBoxContainer.new()
	_dlg_opts.custom_minimum_size = Vector2(330, 0)
	_dlg_opts.add_theme_constant_override("separation", 8)
	row.add_child(_dlg_opts)


func open_dialogue(npc: NPC) -> void:
	_dlg_npc = npc
	_dialogue.visible = true
	_speak_btn.visible = false
	if _dlg_vp:
		_dlg_vp.queue_free()
	_dlg_vp = Portrait.make(npc.rig.look, Vector2i(250, 280))
	add_child(_dlg_vp)
	_dlg_portrait.texture = _dlg_vp.get_texture()
	_dlg_name.text = npc.display_name if npc.notable else npc.title
	if npc.notable:
		var sp: Dictionary = Cast.species.get(npc.info.get("species", "human"), {})
		_dlg_title.text = "%s  ·  %s" % [npc.title, sp.get("name", "")]
		var op: int = Cast.opinion.get(npc.id, 0)
		_dlg_mood.text = "Disposition: " + Cast.opinion_word(op)
		_say(_greeting(npc))
	else:
		_dlg_title.text = "Palace household"
		_dlg_mood.text = ""
		var b := npc.barks()
		_say("\"%s\"" % (b[randi() % b.size()] if b.size() > 0 else "Majesty."))
	_options(npc)


func _greeting(npc: NPC) -> String:
	var lines: Dictionary = npc.info.get("lines", {})
	var op: int = Cast.opinion.get(npc.id, 0)
	var key := "greet_neutral"
	if op >= 30:
		key = "greet_warm"
	elif op <= -20:
		key = "greet_cold"
	var pool: Array = lines.get(key, lines.get("greet_neutral", ["..."]))
	return "\"%s\"" % pool[randi() % pool.size()]


func _options(npc: NPC) -> void:
	for ch in _dlg_opts.get_children():
		ch.queue_free()
	if npc.notable:
		var lines: Dictionary = npc.info.get("lines", {})
		_opt("Who are you?", func(): _say("\"%s\"" % lines.get("about", "")))
		_opt("What occupies you at court?", func(): _say("\"%s\"" % lines.get("agenda", "")))
		var faction := str(npc.info.get("faction", ""))
		if npc.info.get("group", "") == "kings" and Cast.kingdoms.has(faction):
			_opt("Tell me of your realm.", func():
				var k: Dictionary = Cast.kingdoms[faction]
				_say("[i]%s.[/i] %s" % [k["name"], k["summary"]]))
		else:
			_opt("What do they say of you?", func(): _say("[i]%s[/i]" % npc.info.get("bio", "")))
	_opt("Farewell.", func(): close_dialogue())


func _opt(text: String, fn: Callable) -> void:
	var b := _button(text, 19)
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.pressed.connect(fn)
	_dlg_opts.add_child(b)


func _say(bb: String) -> void:
	_dlg_text.text = bb
	_dlg_text.visible_ratio = 0.0
	_type_t = 0.0


func close_dialogue() -> void:
	if not _dialogue.visible:
		return
	_dialogue.visible = false
	if _dlg_vp:
		_dlg_vp.queue_free()
		_dlg_vp = null
	_dlg_npc = null
	dialogue_closed.emit()


func dialogue_open() -> bool:
	return _dialogue.visible


# ------------------------------------------------------------------ roster

func _build_roster() -> void:
	_roster = PanelContainer.new()
	_roster.add_theme_stylebox_override("panel", _panel_style(0.96, 2))
	_roster.set_anchors_preset(Control.PRESET_FULL_RECT)
	_roster.offset_left = 24
	_roster.offset_top = 24
	_roster.offset_right = -24
	_roster.offset_bottom = -24
	_roster.visible = false
	_root.add_child(_roster)
	var outer := VBoxContainer.new()
	_roster.add_child(outer)
	var head := HBoxContainer.new()
	outer.add_child(head)
	head.add_child(_label("The Court of Aurex IV", 34, Color("ffe9b8"), true))
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(sp)
	var close := _button("Close", 20)
	close.custom_minimum_size = Vector2(120, 48)
	close.pressed.connect(toggle_roster)
	head.add_child(close)
	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 20)
	outer.add_child(body)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(330, 0)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(scroll)
	_roster_list = VBoxContainer.new()
	_roster_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_roster_list.add_theme_constant_override("separation", 4)
	scroll.add_child(_roster_list)
	var figure := PanelContainer.new()
	var fs := _panel_style(1.0, 2)
	fs.bg_color = Color("2a201b")
	fs.set_content_margin_all(0)
	figure.add_theme_stylebox_override("panel", fs)
	figure.custom_minimum_size = Vector2(300, 0)
	body.add_child(figure)
	_roster_tex = TextureRect.new()
	_roster_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_roster_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	figure.add_child(_roster_tex)
	var dscroll := ScrollContainer.new()
	dscroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	dscroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(dscroll)
	_roster_detail = VBoxContainer.new()
	_roster_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_roster_detail.add_theme_constant_override("separation", 6)
	dscroll.add_child(_roster_detail)
	for g in Cast.GROUPS:
		_roster_list.add_child(_label(g[1], 20, GOLD, true))
		var ids: Array = Cast.ids_in_group(g[0])
		if g[0] == "household":
			ids.push_front("player")
		for id in ids:
			var c: Dictionary = Cast.character(id)
			var b := _button(c["name"], 18)
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			b.custom_minimum_size = Vector2(0, 44)
			b.pressed.connect(show_character.bind(id))
			_roster_list.add_child(b)


func toggle_roster() -> void:
	_roster.visible = not _roster.visible
	if _roster.visible:
		close_dialogue()
		_speak_btn.visible = false
		show_character("emperor")
	elif _roster_vp:
		_roster_vp.queue_free()
		_roster_vp = null
	roster_toggled.emit(_roster.visible)


func roster_open() -> bool:
	return _roster.visible


func show_character(id: String) -> void:
	var c: Dictionary = Cast.character(id)
	if _roster_vp:
		_roster_vp.queue_free()
	_roster_vp = Portrait.make(Cast.look_for(id), Vector2i(300, 520), true, true)
	add_child(_roster_vp)
	_roster_tex.texture = _roster_vp.get_texture()
	for ch in _roster_detail.get_children():
		ch.queue_free()
	var sp: Dictionary = Cast.species.get(c.get("species", "human"), {})
	_roster_detail.add_child(_label(c["name"], 34, Color("ffe9b8"), true))
	_roster_detail.add_child(_label(c.get("title", ""), 22, GOLD))
	var facts := "%s %s  ·  age %d" % [sp.get("name", ""), "(" + str(sp.get("epithet", "")) + ")", int(c.get("age", 0))]
	var realm := Cast.kingdom_name(str(c.get("faction", "")))
	if realm != "":
		facts += "  ·  " + realm
	_roster_detail.add_child(_label(facts, 18, DIM))
	_roster_detail.add_child(_para(c.get("role", "")))
	_roster_detail.add_child(_heading("Character"))
	_roster_detail.add_child(_para(", ".join(PackedStringArray(c.get("traits", [])))))
	_roster_detail.add_child(_para(c.get("bio", ""), true))
	_roster_detail.add_child(_heading("Ambition"))
	_roster_detail.add_child(_para(c.get("ambition", "")))
	if c.has("agenda"):
		_roster_detail.add_child(_heading("At court this season"))
		_roster_detail.add_child(_para(c.get("agenda", "")))
	if id != "player":
		var op: int = Cast.opinion.get(id, 0)
		_roster_detail.add_child(_heading("Disposition toward you"))
		_roster_detail.add_child(_opinion_bar(op))
		if main and main.has_method("whereabouts"):
			_roster_detail.add_child(_heading("Whereabouts"))
			_roster_detail.add_child(_para(main.whereabouts(id)))
	_roster_detail.add_child(_heading("The %s" % sp.get("plural", "")))
	_roster_detail.add_child(_para(sp.get("summary", ""), true))


func _heading(t: String) -> Label:
	var l := _label(t, 18, GOLD, true)
	return l


func _para(t: String, italic := false) -> Label:
	var l := _label(t, 20, CREAM if not italic else Color("d8ccb4"))
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(380, 0)
	return l


func _opinion_bar(op: int) -> Control:
	var row := HBoxContainer.new()
	var bar := ProgressBar.new()
	bar.min_value = -100
	bar.max_value = 100
	bar.value = op
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(300, 18)
	var fg := StyleBoxFlat.new()
	fg.bg_color = Color("5f8a4a") if op >= 10 else (Color("a8483a") if op <= -10 else Color("9a8a72"))
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.4)
	bar.add_theme_stylebox_override("fill", fg)
	bar.add_theme_stylebox_override("background", bg)
	row.add_child(bar)
	row.add_child(_label("  %s (%+d)" % [Cast.opinion_word(op), op], 19, CREAM))
	return row


# ------------------------------------------------------------------ frame

func _process(delta: float) -> void:
	if _banner_t > 0.0:
		_banner_t -= delta
		_banner.modulate.a = clampf(minf(_banner_t, 4.0 - _banner_t) * 2.0, 0.0, 1.0)
	if _dialogue.visible and _dlg_text.visible_ratio < 1.0:
		_type_t += delta
		var n := maxi(1, _dlg_text.get_total_character_count())
		_dlg_text.visible_ratio = minf(1.0, _type_t * 70.0 / n)
	_joy_base.visible = not (_dialogue.visible or _roster.visible)


func skip_typing() -> void:
	_dlg_text.visible_ratio = 1.0
