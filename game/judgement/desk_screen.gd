class_name DeskScreen
extends Control
## Judgement desk (PROJECT §9.3, 05 §6.2): booth | tabs | document | actions, then verdict view, epilogue, audit slip.

signal closed()

const TABS := ["FILE", "RECORD", "ARCHIVE", "TALK", "NOTES"]
const PER_PAGE := 4

var case_id := ""
var session: JudgementSession
var tab := "FILE"
var page := 0
var sel_entry := ""
var sel_arc := ""
var unread := {}
var expression := "neutral"
var last_line := ""
var margin: MarginContainer
var body: HBoxContainer
var bust: TextureRect
var name_label: Label
var pips: HBoxContainer
var line_label: Label
var tab_buttons := {}
var doc_title: Label
var doc_list: VBoxContainer
var doc_footer: Label
var pager_prev: Button
var pager_next: Button
var pager_label: Label
var link_btn: Button
var judge_btn: Button
var sel_label: Label
var header_label: Label
var overlay: Control # answers / verdict / slip live here
var toast: Label
var verdict_view: VerdictView


func open(cid: String) -> void:
	case_id = cid
	session = JudgementSession.new(cid)
	theme = UiKit.theme()
	UiKit.full_rect(self)
	mouse_filter = Control.MOUSE_FILTER_STOP
	for c in get_children():
		c.queue_free()
	var bg := ColorRect.new()
	bg.color = Color("#0d0b12")
	UiKit.full_rect(bg)
	add_child(bg)
	margin = MarginContainer.new()
	UiKit.full_rect(margin)
	add_child(margin)
	UiKit.apply_safe(margin)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	margin.add_child(v)
	_build_header(v)
	body = HBoxContainer.new()
	body.add_theme_constant_override("separation", 8)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(body)
	_build_booth()
	_build_tabs()
	_build_doc()
	_build_actions()
	overlay = Control.new()
	UiKit.full_rect(overlay)
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(overlay)
	toast = UiKit.label("", 16, UiKit.TEXT)
	toast.add_theme_stylebox_override("normal", UiKit.charcoal_box(6, true))
	toast.set_anchors_preset(Control.PRESET_CENTER_TOP)
	toast.position.y = 56
	toast.visible = false
	add_child(toast)
	tab = "RECORD" if bool(session.rec().get("correction", false)) else "FILE"
	EventBus.composure_changed.connect(_on_composure)
	refresh()


func _on_composure(cid: String, _v: int) -> void:
	if cid == case_id and is_inside_tree():
		_refresh_booth()


# ---------------------------------------------------------------- build
func _build_header(v: VBoxContainer) -> void:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	v.add_child(h)
	var leave := UiKit.button("< Leave desk", Vector2(120, 40))
	leave.name = "LeaveDesk"
	leave.pressed.connect(leave_desk)
	h.add_child(leave)
	header_label = UiKit.label("", 16, UiKit.TEXT_DIM)
	header_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(header_label)


func _build_booth() -> void:
	var p := UiKit.panel(UiKit.charcoal_box(4))
	p.custom_minimum_size.x = 132
	body.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	p.add_child(v)
	var frame := UiKit.panel(UiKit.box(Color("#2a1f3d"), UiKit.EDGE, 1, 0))
	frame.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(frame)
	bust = TextureRect.new()
	bust.custom_minimum_size = Vector2(96, 96)
	bust.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bust.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	frame.add_child(bust)
	name_label = UiKit.wrap_label("", 16)
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(name_label)
	pips = HBoxContainer.new()
	pips.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(pips)
	line_label = UiKit.wrap_label("", 12, UiKit.TEXT_DIM)
	line_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	line_label.clip_text = true
	v.add_child(line_label)


func _build_tabs() -> void:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	v.custom_minimum_size.x = 48
	body.add_child(v)
	for t: String in TABS:
		var b := UiKit.button(t, Vector2(48, 48))
		b.name = "Tab" + t
		b.add_theme_font_size_override("font_size", 12)
		b.pressed.connect(func() -> void: set_tab(t))
		v.add_child(b)
		tab_buttons[t] = b


func _build_doc() -> void:
	var p := UiKit.panel(UiKit.parchment_box(6))
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	p.add_child(v)
	doc_title = UiKit.label("", 16, UiKit.INK)
	v.add_child(doc_title)
	doc_list = VBoxContainer.new()
	doc_list.add_theme_constant_override("separation", 4)
	doc_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(doc_list)
	doc_footer = UiKit.label("", 16, UiKit.INK)
	v.add_child(doc_footer)
	var pg := HBoxContainer.new()
	pg.alignment = BoxContainer.ALIGNMENT_CENTER
	pg.add_theme_constant_override("separation", 8)
	v.add_child(pg)
	pager_prev = UiKit.button("<", Vector2(48, 32))
	pager_prev.pressed.connect(func() -> void: _turn(-1))
	pg.add_child(pager_prev)
	pager_label = UiKit.label("", 12, UiKit.INK)
	pg.add_child(pager_label)
	pager_next = UiKit.button(">", Vector2(48, 32))
	pager_next.pressed.connect(func() -> void: _turn(1))
	pg.add_child(pager_next)


func _build_actions() -> void:
	var v := VBoxContainer.new()
	v.custom_minimum_size.x = 96
	v.add_theme_constant_override("separation", 8)
	body.add_child(v)
	link_btn = UiKit.button("LINK", Vector2(96, 56), "icon_link")
	link_btn.name = "Link"
	link_btn.pressed.connect(do_link)
	v.add_child(link_btn)
	sel_label = UiKit.wrap_label("", 12, UiKit.TEXT_DIM)
	sel_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(sel_label)
	judge_btn = UiKit.button("PASS\nJUDGEMENT", Vector2(96, 64))
	judge_btn.name = "PassJudgement"
	judge_btn.add_theme_stylebox_override("normal", UiKit.box(Color("#27232f"), UiKit.BORDER_GOLD, 1, 4))
	judge_btn.pressed.connect(open_verdict)
	v.add_child(judge_btn)


# ---------------------------------------------------------------- refresh
func refresh() -> void:
	if session == null:
		return
	var docket := GameState.docket
	var idx := docket.find(case_id) + 1
	header_label.text = "Case %d of %d    %s    Queue %d" % [maxi(idx, 1), maxi(docket.size(), 1), Clock.label(), GameState.get_stat_i("queue")]
	_refresh_booth()
	for t: String in TABS:
		var b: Button = tab_buttons[t]
		b.text = t + ("*" if unread.get(t, false) else "")
		b.add_theme_stylebox_override("normal", UiKit.box(Color("#43325c") if t == tab else Color("#27232f"),
			UiKit.SELECT if t == tab else UiKit.EDGE, 1, 2))
	for c in doc_list.get_children():
		doc_list.remove_child(c)
		c.queue_free()
	doc_footer.text = ""
	doc_footer.visible = false
	match tab:
		"FILE":
			_page_file()
		"RECORD":
			_page_record()
		"ARCHIVE":
			_page_archive()
		"TALK":
			_page_talk()
		"NOTES":
			_page_notes()
	link_btn.disabled = not (sel_entry != "" and sel_arc != "")
	var parts: Array = []
	if sel_entry != "":
		parts.append("Entry " + sel_entry)
	if sel_arc != "":
		parts.append(str(Scoring.find_archive(session.data, sel_arc).get("title", sel_arc)))
	sel_label.text = "\n".join(parts) if not parts.is_empty() else "Select a record entry and an archive document, then LINK."


func _refresh_booth() -> void:
	var correction := bool(session.rec().get("correction", false))
	var bid := "bust_%s_%s" % [case_id, expression]
	bust.texture = Assets.ui_texture(bid, "bust")
	bust.modulate = Color(1, 1, 1, 0.35) if correction else Color.WHITE
	name_label.text = str(session.data.get("name", ""))
	for c in pips.get_children():
		c.queue_free()
	var full := Content.cfg_i("composure", 3)
	for i in full:
		pips.add_child(UiKit.icon("pip_full" if i < session.composure() else "pip_empty", Vector2(16, 16)))
	if correction:
		line_label.text = "Correction: the soul has gone. The file remains."
	else:
		line_label.text = ("\"" + last_line + "\"") if last_line != "" else ""


func _pager(total: int) -> void:
	var pages := maxi(1, int(ceil(total / float(PER_PAGE))))
	page = clampi(page, 0, pages - 1)
	pager_label.text = "p %d/%d" % [page + 1, pages]
	pager_prev.disabled = page <= 0
	pager_next.disabled = page >= pages - 1


func _turn(d: int) -> void:
	page += d
	Audio.sfx("sfx_page")
	refresh()


func set_tab(t: String) -> void:
	if t != tab:
		page = 0
		Audio.sfx("sfx_page")
	tab = t
	unread[t] = false
	refresh()


func _card(bb: String, selected: bool = false, lamp: bool = false, kind: String = "") -> PanelContainer:
	var border := UiKit.PARCHMENT_SHADE
	var bw := 1
	if lamp:
		border = Color("#fff3c4")
		bw = 2
	if selected:
		border = UiKit.SELECT_ON_PARCHMENT
		bw = 2
	var sb := UiKit.box(Color("#efe4c6") if not selected else Color("#e2d3ee"), border, bw, 4)
	var p := UiKit.panel(sb)
	p.custom_minimum_size.y = 44
	var h := HBoxContainer.new()
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.add_theme_constant_override("separation", 4)
	p.add_child(h)
	var rt := RichTextLabel.new()
	rt.bbcode_enabled = true
	rt.fit_content = true
	rt.scroll_active = false
	rt.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	rt.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rt.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rt.add_theme_color_override("default_color", UiKit.INK)
	rt.add_theme_font_size_override("normal_font_size", 16)
	rt.text = bb
	rt.name = "Text"
	h.add_child(rt)
	p.set_meta("kind", kind)
	return p


func _clickable(p: Control, cb: Callable) -> void:
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	p.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and (e as InputEventMouseButton).pressed and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
			cb.call())


func _page_file() -> void:
	var d := session.data
	doc_title.text = "FILE  %s" % str(d.get("ref", ""))
	var lines := [
		"[b]%s[/b], %s" % [str(d.get("name", "")), str(d.get("age", ""))],
		"%s, %s" % [str(d.get("era", "")), str(d.get("place", ""))],
		"Cause: %s" % str(d.get("cause", "")),
		str(d.get("summary", "")),
	]
	for l: String in lines:
		var c := _card(l)
		doc_list.add_child(c)
	_pager(1)


func _pips(r: Dictionary) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 0)
	h.custom_minimum_size.x = 48
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var w := int(r["weight"])
	var tag := str(r["tag"])
	if w == 0:
		var l := UiKit.label("-", 16, UiKit.INK)
		h.add_child(l)
	else:
		for i in absi(w):
			h.add_child(UiKit.icon("icon_halo" if w > 0 else "icon_flame", Vector2(16, 16)))
	if tag == "neutral" and w == 0:
		pass
	return h


func _page_record() -> void:
	var rows := session.visible_rows()
	doc_title.text = "LIFE RECORD"
	var lamp := session.lamp_entry()
	_pager(rows.size())
	var violet_found := false
	for d: Variant in session.discoveries():
		var dd := Scoring.find_discovery(session.data, str(d))
		for op: Dictionary in dd.get("ops", []):
			for r: Dictionary in rows:
				if r["id"] == str(op.get("entry", "")) and r["ink"] == "violet":
					violet_found = true
	for i in range(page * PER_PAGE, mini(rows.size(), (page + 1) * PER_PAGE)):
		var r: Dictionary = rows[i]
		var txt := str(r["text"])
		if r["ink"] == "violet":
			txt = "[color=#8b3fd9]%s[/color]" % txt
		if r["voided"]:
			txt = "[s]%s[/s]" % txt
		var prefix := "[b]%s[/b] " % str(r["id"])
		if r["revealed"]:
			prefix += "[i](new)[/i] "
		if r["reweighted"]:
			prefix += "[i](%+d->%+d)[/i] " % [int(r["filed_weight"]), int(r["weight"])]
		var c := _card(prefix + txt, sel_entry == r["id"], lamp == r["id"], "entry")
		c.name = "Entry_" + str(r["id"])
		var hb: HBoxContainer = c.get_child(0)
		var pp := _pips(r if not r["voided"] else {"weight": 0, "tag": "neutral"})
		hb.add_child(pp)
		hb.move_child(pp, 0)
		if r["ink"] == "violet" and violet_found:
			hb.add_child(UiKit.icon("stamp_rm0", Vector2(32, 16)))
		var eid := str(r["id"])
		_clickable(c, func() -> void:
			sel_entry = "" if sel_entry == eid else eid
			refresh())
		doc_list.add_child(c)
	var t := session.known_tally()
	var gate := "Gilt Gate" if t > 0 else ("Ember Gate" if t < 0 else "abstains")
	doc_footer.text = "Rubric: %+d -> %s" % [t, gate] if t != 0 else "Rubric: 0 -> the Rubric abstains"
	doc_footer.visible = true


func _page_archive() -> void:
	var held := session.held_archive()
	doc_title.text = "ARCHIVE"
	if held.is_empty():
		doc_list.add_child(_card("[i]No documents. Walk to the Records Annexe and ask Pell for the originals.[/i]"))
		_pager(1)
		return
	# one document per page
	page = clampi(page, 0, held.size() - 1)
	pager_label.text = "doc %d/%d" % [page + 1, held.size()]
	pager_prev.disabled = page <= 0
	pager_next.disabled = page >= held.size() - 1
	var aid := str(held[page])
	var a := Scoring.find_archive(session.data, aid)
	var head := _card("[b]%s[/b]  [i](tap to select)[/i]" % str(a.get("title", aid)), sel_arc == aid, false, "arc")
	head.name = "Arc_" + aid
	_clickable(head, func() -> void:
		sel_arc = "" if sel_arc == aid else aid
		refresh())
	doc_list.add_child(head)
	for card: Variant in a.get("cards", []):
		var c := _card(str(card), sel_arc == aid)
		_clickable(c, func() -> void:
			sel_arc = "" if sel_arc == aid else aid
			refresh())
		doc_list.add_child(c)


func _page_talk() -> void:
	doc_title.text = "TALK"
	var correction := bool(session.rec().get("correction", false))
	var items: Array = []
	for q: Dictionary in session.open_questions():
		items.append({"q": q})
	for qid: Variant in session.asked():
		items.append({"asked": str(qid)})
	_pager(items.size())
	if items.is_empty():
		doc_list.add_child(_card("[i]Nothing more to ask.[/i]"))
	for i in range(page * PER_PAGE, mini(items.size(), (page + 1) * PER_PAGE)):
		var it: Dictionary = items[i]
		if it.has("q"):
			var q: Dictionary = it["q"]
			var confront := str(q.get("kind", "general")) == "confront"
			var b := UiKit.button(("! " if confront else "? ") + str(q.get("text", "")), Vector2(0, 44))
			b.name = "Ask_" + str(q["id"])
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			b.disabled = not session.can_ask() or correction
			var qid := str(q["id"])
			b.pressed.connect(func() -> void: ask(qid))
			doc_list.add_child(b)
		else:
			var q := Scoring.find_question(session.data, str(it["asked"]))
			doc_list.add_child(_card("[i]%s[/i] %s" % [str(q.get("text", "")), str(q.get("card", ""))]))
	if not session.can_ask() and not correction:
		doc_footer.text = "The soul has stopped answering."
		doc_footer.visible = true
	elif not correction:
		doc_footer.text = "? costs 1 Composure.  ! costs none."
		doc_footer.visible = true


func _page_notes() -> void:
	doc_title.text = "NOTES (grounds)"
	var facts := session.facts()
	_pager(facts.size())
	if facts.is_empty():
		doc_list.add_child(_card("[i]No facts yet. Link the record to the archive, or interview the soul.[/i]"))
	for i in range(page * PER_PAGE, mini(facts.size(), (page + 1) * PER_PAGE)):
		var f: Dictionary = facts[i]
		var c := _card(str(f["text"]))
		var side := str(f["side"])
		if side == "heaven" or side == "hell":
			var hb: HBoxContainer = c.get_child(0)
			var ic := UiKit.icon("icon_halo" if side == "heaven" else "icon_flame", Vector2(16, 16))
			hb.add_child(ic)
			hb.move_child(ic, 0)
		doc_list.add_child(c)


# ---------------------------------------------------------------- actions
func show_toast(t: String, col: Color = UiKit.TEXT) -> void:
	toast.text = t
	toast.add_theme_color_override("font_color", col)
	toast.visible = true
	toast.modulate.a = 1.0
	var tw := create_tween()
	tw.tween_interval(1.4)
	tw.tween_property(toast, "modulate:a", 0.0, 0.3)
	tw.tween_callback(func() -> void: toast.visible = false)


func do_link() -> void:
	if sel_entry == "" or sel_arc == "":
		return
	var r := session.link(sel_entry, sel_arc)
	if r.get("ok", false):
		Audio.sfx("sfx_link")
		var d := Scoring.find_discovery(session.data, str(r["discovery"]))
		show_toast("Discrepancy: " + str((d.get("fact", {}) as Dictionary).get("text", "")), UiKit.EMBER)
		expression = "distressed"
		unread["NOTES"] = true
		unread["RECORD"] = true
	elif not r.get("invalid", false):
		show_toast("No discrepancy. (-1 Composure)", UiKit.TEXT)
	sel_entry = ""
	sel_arc = ""
	refresh()


func ask(qid: String) -> void:
	var r := session.ask(qid)
	if not r.get("ok", false):
		return
	var answer: Array = r["answer"]
	expression = "neutral" if r.get("general", true) else "distressed"
	if not (r["discoveries"] as Array).is_empty():
		unread["NOTES"] = true
		unread["RECORD"] = true
	var q := Scoring.find_question(session.data, qid)
	if q.has("fact"):
		unread["NOTES"] = true
	last_line = str(answer[answer.size() - 1]) if not answer.is_empty() else ""
	if last_line.length() > 70:
		last_line = last_line.substr(0, 67) + "..."
	refresh()
	show_answers(answer)


## Answers play in a dialogue-style panel over the desk (<= 3 boxes).
func show_answers(boxes: Array) -> void:
	if boxes.is_empty():
		return
	var layer := Control.new()
	UiKit.full_rect(layer)
	layer.name = "Answer"
	layer.mouse_filter = Control.MOUSE_FILTER_STOP
	overlay.add_child(layer)
	var dimr := UiKit.dim(0.35)
	dimr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(dimr)
	var p := UiKit.panel(UiKit.charcoal_box(8, true))
	p.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	p.offset_left = 16
	p.offset_right = -16
	p.offset_top = -112
	p.offset_bottom = -16
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(p)
	var v := VBoxContainer.new()
	p.add_child(v)
	var nm := UiKit.label(str(session.data.get("name", "")), 16, UiKit.HEAVEN)
	v.add_child(nm)
	var tl := UiKit.wrap_label("", 16)
	tl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(tl)
	var state := {"i": 0}
	tl.text = str(boxes[0])
	layer.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and (e as InputEventMouseButton).pressed:
			state["i"] = int(state["i"]) + 1
			if int(state["i"]) >= boxes.size():
				layer.queue_free()
			else:
				tl.text = str(boxes[int(state["i"])]))


func dismiss_overlays() -> void:
	for c in overlay.get_children():
		if c.name == "Answer":
			c.queue_free()


func leave_desk() -> void:
	closed.emit()


func open_verdict() -> void:
	dismiss_overlays()
	verdict_view = VerdictView.new()
	verdict_view.desk = self
	overlay.add_child(verdict_view)
	verdict_view.build()


signal verdict_done(case_id: String, verdict: String)


func verdict_finished(v: String) -> void:
	verdict_done.emit(case_id, v)
