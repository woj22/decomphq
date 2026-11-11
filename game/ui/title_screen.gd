class_name TitleScreen
extends Control
## Title: New / Continue / Settings.

signal new_game()
signal continue_game()


func _ready() -> void:
	theme = UiKit.theme()
	UiKit.full_rect(self)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var bg := ColorRect.new()
	bg.color = Color("#0d0b12")
	UiKit.full_rect(bg)
	add_child(bg)
	for side: Array in [["bg_heaven_sky", 0.0, 0.5], ["bg_hell_sky", 0.5, 1.0], ["bg_heaven_skyline", 0.0, 0.5], ["bg_hell_skyline", 0.5, 1.0]]:
		var t := TextureRect.new()
		t.texture = Assets.frame(str(side[0]), 0, "backdrop")
		t.anchor_left = float(side[1])
		t.anchor_right = float(side[2])
		t.anchor_top = 0.3 if str(side[0]).ends_with("skyline") else 0.0
		t.anchor_bottom = 1.0
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		t.modulate = Color(0.75, 0.75, 0.8, 1)
		add_child(t)
	var cc := CenterContainer.new()
	UiKit.full_rect(cc)
	add_child(cc)
	var p := UiKit.panel(UiKit.charcoal_box(16, true))
	cc.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	p.add_child(v)
	var t1 := UiKit.label("The Purgatory Border", 48, UiKit.HEAVEN, "display")
	t1.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t1)
	var t2 := UiKit.label("A career in the Border Chancery of Limen", 16, UiKit.TEXT_DIM)
	t2.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t2)
	var nb := UiKit.button("New game", Vector2(240, 48))
	nb.name = "New"
	nb.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	nb.pressed.connect(func() -> void: new_game.emit())
	v.add_child(nb)
	var cb := UiKit.button("Continue", Vector2(240, 48))
	cb.name = "Continue"
	cb.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	cb.disabled = not SaveGame.has_save()
	cb.pressed.connect(func() -> void: continue_game.emit())
	v.add_child(cb)
	var sb := UiKit.button("Settings", Vector2(240, 48))
	sb.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	sb.pressed.connect(func() -> void: add_child(SettingsScreen.new()))
	v.add_child(sb)
