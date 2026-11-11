class_name ModalScreens
extends RefCounted
## Builders for the queued modal screens: title card, shift ledger, promotion ceremony, end-of-prototype summary.


static func _sheet(root: Control, parchment: bool, min_w: float) -> VBoxContainer:
	var cc := CenterContainer.new()
	UiKit.full_rect(cc)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(cc)
	var p := UiKit.panel(UiKit.parchment_box(14) if parchment else UiKit.charcoal_box(14, true))
	p.custom_minimum_size.x = min_w
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cc.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.add_child(v)
	return v


static func card(root: Control, data: Dictionary) -> void:
	root.add_child(UiKit.dim(0.92))
	var v := _sheet(root, false, 360)
	var t := UiKit.label(str(data.get("title", "")), 48 if str(data.get("title", "")).length() <= 20 else 24, UiKit.HEAVEN, "display")
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var s := UiKit.wrap_label(str(data.get("text", "")), 16)
	s.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	s.custom_minimum_size.x = 340
	v.add_child(s)
	var tap := UiKit.label("(tap to continue)", 12, UiKit.TEXT_DIM)
	tap.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(tap)


static func ledger_note(day: int) -> String:
	var notes: Variant = Content.cfg("ledger_notes", {})
	if notes is Dictionary:
		for n: Variant in (notes as Dictionary).get(str(day), []):
			if n is Dictionary and Conditions.check((n as Dictionary).get("conditions", [])):
				return str((n as Dictionary).get("text", ""))
	return ""


static func ledger(root: Control, s: Dictionary, on_sign: Callable) -> void:
	root.add_child(UiKit.dim(0.85))
	var v := _sheet(root, true, 420)
	var h := HBoxContainer.new()
	v.add_child(h)
	var t := UiKit.label("SHIFT LEDGER - Day %d" % int(s.get("day", 1)), 16, UiKit.INK)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(t)
	h.add_child(UiKit.label(Content.rank_title(GameState.rank), 12, UiKit.INK))
	var rows := [
		["Souls processed", "%d   (halo %d / flame %d)" % [int(s.get("processed", 0)), int(s.get("heaven", 0)), int(s.get("hell", 0))]],
		["Discoveries", "%d of %d" % [int(s.get("key_found", 0)), int(s.get("key_total", 0))]],
		["Overturned", str(int(s.get("overturned", 0)))],
		["Pay", "+%d  ->  purse %d" % [int(s.get("pay", 0)), GameState.get_stat_i("purse")]],
		["Order", "%d%%" % GameState.get_stat_i("order")],
		["Merit", "%d/%d" % [GameState.get_stat_i("merit"), int(s.get("merit_gate", 30))]],
	]
	for r: Array in rows:
		var hh := HBoxContainer.new()
		var a := UiKit.label(str(r[0]), 16, UiKit.INK)
		a.custom_minimum_size.x = 170
		hh.add_child(a)
		hh.add_child(UiKit.label(str(r[1]), 16, UiKit.INK))
		v.add_child(hh)
	var note := ledger_note(int(s.get("day", 1)))
	if note != "":
		var n := UiKit.wrap_label("Note: " + note, 16, UiKit.INK)
		n.custom_minimum_size.x = 400
		v.add_child(n)
	var b := UiKit.button("Sign and leave", Vector2(200, 48))
	b.name = "Sign"
	b.size_flags_horizontal = Control.SIZE_SHRINK_END
	b.pressed.connect(on_sign)
	v.add_child(b)


static func ceremony(root: Control, data: Dictionary, on_accept: Callable) -> void:
	root.add_child(UiKit.dim(0.94))
	var v := _sheet(root, false, 460)
	var to := int(data.get("to", 2))
	var from := int(data.get("from", 1))
	var t := UiKit.label("By order of the Chancery", 16, UiKit.TEXT_DIM)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var tt := UiKit.label("%s  ->  %s" % [Content.rank_title(from), Content.rank_title(to).to_upper()], 16, UiKit.HEAVEN)
	tt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(tt)
	var seal := UiKit.icon(str(Content.rank_info(to).get("crest", "icon_crest_r2")), Vector2(64, 64))
	seal.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(seal)
	var privs: Array = Content.rank_info(to).get("privileges", [])
	if privs.is_empty():
		privs = [{"icon": "icon_key", "text": "The stair in Clerk's Court is open to you"},
			{"icon": "icon_quill", "text": "Appeals may now be heard"}, {"icon": "icon_obol", "text": "Base pay 8 -> 12 obols"}]
	for p: Variant in privs:
		var pd: Dictionary = p
		var h := HBoxContainer.new()
		h.add_theme_constant_override("separation", 6)
		h.add_child(UiKit.icon(str(pd.get("icon", "icon_key")), Vector2(24, 24)))
		h.add_child(UiKit.label(str(pd.get("text", "")), 16))
		v.add_child(h)
	var b := UiKit.button("Accept the seal", Vector2(200, 48))
	b.name = "Accept"
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.pressed.connect(func() -> void:
		Audio.sfx("sfx_stamp")
		on_accept.call())
	v.add_child(b)


static func summary(root: Control, on_done: Callable) -> void:
	root.add_child(UiKit.dim(0.96))
	var v := _sheet(root, false, 440)
	var t := UiKit.label("End of prototype", 24, UiKit.HEAVEN, "display")
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var choice := str(GameState.get_flag("flag_tarrow_file"))
	var rows := [["Rank", Content.rank_title(GameState.rank)], ["Merit", "%d / 54" % GameState.get_stat_i("merit")],
		["Overturned", str(GameState.get_stat_i("overturned"))], ["Order", "%d%%" % GameState.get_stat_i("order")],
		["Obols", str(GameState.get_stat_i("purse"))], ["Tarrow file", choice if choice != "false" else "-"],
		["Souls to Gilt / Ember", "%d / %d" % [GameState.get_stat_i("favour_gilt"), GameState.get_stat_i("favour_ember")]]]
	for r: Array in rows:
		var h := HBoxContainer.new()
		var a := UiKit.label(str(r[0]), 16, UiKit.TEXT_DIM)
		a.custom_minimum_size.x = 190
		h.add_child(a)
		h.add_child(UiKit.label(str(r[1]), 16))
		v.add_child(h)
	var b := UiKit.button("Return to title", Vector2(200, 48))
	b.name = "ToTitle"
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.pressed.connect(on_done)
	v.add_child(b)
