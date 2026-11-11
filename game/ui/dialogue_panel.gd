class_name DialoguePanel
extends Control
## Dialogue UI (05 §5): bottom panel 104 px, 64 px portrait, name tab, typewriter reveal, numbered choices above.

var dim_rect: ColorRect
var margin: MarginContainer
var panel: PanelContainer
var portrait: TextureRect
var portrait_frame: PanelContainer
var name_label: Label
var text_label: Label
var more: Label
var choice_box: VBoxContainer
var _full := ""
var _shown := 0.0
var _choices_pending: Array = []


func _ready() -> void:
	theme = UiKit.theme()
	UiKit.full_rect(self)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false
	dim_rect = UiKit.dim(0.4)
	dim_rect.gui_input.connect(_on_input)
	add_child(dim_rect)
	margin = MarginContainer.new()
	UiKit.full_rect(margin)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(margin)
	UiKit.apply_safe(margin)
	var v := VBoxContainer.new()
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.alignment = BoxContainer.ALIGNMENT_END
	margin.add_child(v)
	choice_box = VBoxContainer.new()
	choice_box.size_flags_horizontal = Control.SIZE_SHRINK_END
	choice_box.custom_minimum_size.x = 300
	choice_box.add_theme_constant_override("separation", 8)
	v.add_child(choice_box)
	name_label = UiKit.label("", 16, UiKit.HEAVEN)
	name_label.add_theme_stylebox_override("normal", UiKit.box(UiKit.CHARCOAL_SOLID, UiKit.BORDER_GOLD, 1, 3))
	name_label.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	v.add_child(name_label)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	h.custom_minimum_size.y = 104
	v.add_child(h)
	portrait_frame = UiKit.panel(UiKit.box(UiKit.CHARCOAL_SOLID, UiKit.BORDER_GOLD, 1, 2))
	portrait_frame.size_flags_vertical = Control.SIZE_SHRINK_END
	h.add_child(portrait_frame)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(64, 64)
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait_frame.add_child(portrait)
	panel = UiKit.panel(UiKit.charcoal_box(8, true))
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.gui_input.connect(_on_input)
	h.add_child(panel)
	var pv := VBoxContainer.new()
	pv.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(pv)
	text_label = UiKit.wrap_label("", 16)
	text_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	text_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pv.add_child(text_label)
	more = UiKit.label("v", 12, UiKit.TEXT_DIM)
	more.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	more.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pv.add_child(more)
	Dialogue.line.connect(_on_line)
	Dialogue.choices.connect(_on_choices)
	Dialogue.closed.connect(func(_id: String) -> void: _hide())


func _on_line(speaker_id: String, speaker_name: String, text: String, portrait_id: String) -> void:
	visible = true
	for c in choice_box.get_children():
		c.queue_free()
	_choices_pending = []
	name_label.text = speaker_name
	name_label.visible = speaker_name != ""
	portrait_frame.visible = portrait_id != ""
	if portrait_id != "":
		portrait.texture = Assets.ui_texture(portrait_id, "bust" if portrait_id.begins_with("bust_") else "portrait")
	var h: HBoxContainer = panel.get_parent()
	h.move_child(portrait_frame, h.get_child_count() - 1 if speaker_id == "player" else 0)
	text_label.add_theme_color_override("font_color", UiKit.TEXT_DIM if speaker_id == "narrator" else UiKit.TEXT)
	_full = text
	_shown = 0.0
	text_label.text = text
	text_label.visible_characters = 0
	if Settings.text_speed >= 2:
		_shown = text.length()
		text_label.visible_characters = -1
	more.visible = false


func _on_choices(items: Array) -> void:
	visible = true
	_choices_pending = items
	if _revealed():
		_show_choices()


func _show_choices() -> void:
	for c in choice_box.get_children():
		c.queue_free()
	var i := 0
	for it: Dictionary in _choices_pending:
		var b := UiKit.button("%d  %s" % [i + 1, str(it["text"])], Vector2(300, 48))
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var idx := i
		b.pressed.connect(func() -> void: Dialogue.choose(idx))
		choice_box.add_child(b)
		i += 1
	_choices_pending = []
	if Dialogue.node.get("text", "") == "":
		# a choice-only node: keep the previous line visible
		pass


func _revealed() -> bool:
	return text_label.visible_characters < 0 or text_label.visible_characters >= _full.length()


func _process(delta: float) -> void:
	if not visible:
		return
	if not _revealed():
		var before := int(_shown)
		_shown += delta * Settings.chars_per_second()
		text_label.visible_characters = int(_shown)
		if int(_shown) / 3 != before / 3:
			Audio.sfx("sfx_quill")
		if _revealed():
			text_label.visible_characters = -1
	else:
		more.visible = not Dialogue.has_choices()
		if not _choices_pending.is_empty():
			_show_choices()


func _on_input(e: InputEvent) -> void:
	var pressed := (e is InputEventMouseButton and (e as InputEventMouseButton).pressed and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT)
	if not pressed:
		return
	tap()


## First tap completes the line, second advances.
func tap() -> void:
	if not _revealed():
		text_label.visible_characters = -1
		_shown = _full.length()
		return
	if Dialogue.has_choices():
		return
	Dialogue.advance()


func _unhandled_input(e: InputEvent) -> void:
	if visible and Dialogue.in_dialogue() and e.is_action_pressed("interact"):
		tap()
		get_viewport().set_input_as_handled()


func _hide() -> void:
	if not Dialogue.in_dialogue():
		visible = false
		for c in choice_box.get_children():
			c.queue_free()
