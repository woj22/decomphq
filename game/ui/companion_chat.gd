class_name CompanionChat
extends ScreenBase
## Chat with Odalys Wick (the LLM companion in the Back Room). Typed questions; her replies in a scrolling ledger.

var log_box: RichTextLabel
var input: LineEdit
var send_btn: Button
var status: Label


func _ready() -> void:
	setup(0.88)
	var p := UiKit.panel(UiKit.charcoal_box(10, true))
	p.custom_minimum_size = Vector2(560, 300)
	center.add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	p.add_child(v)
	var top := HBoxContainer.new()
	v.add_child(top)
	var por := UiKit.icon("por_marrow", Vector2(40, 40))
	por.modulate = Color(0.8, 0.75, 1.0)
	top.add_child(por)
	var t := UiKit.label("%s  - formerly of Room 0" % Companion.NAME, 16, UiKit.HEAVEN)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(t)
	var close_b := UiKit.button("Leave", Vector2(80, 40))
	close_b.pressed.connect(close)
	top.add_child(close_b)
	log_box = RichTextLabel.new()
	log_box.bbcode_enabled = true
	log_box.scroll_following = true
	log_box.custom_minimum_size = Vector2(540, 180)
	log_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_box.add_theme_font_size_override("normal_font_size", 16)
	v.add_child(log_box)
	status = UiKit.label("", 12, UiKit.TEXT_DIM)
	v.add_child(status)
	var row := HBoxContainer.new()
	v.add_child(row)
	input = LineEdit.new()
	input.placeholder_text = "Say something to Odalys..."
	input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	input.custom_minimum_size.y = 48
	input.max_length = 400
	input.virtual_keyboard_enabled = true
	input.text_submitted.connect(func(_t: String) -> void: _send())
	row.add_child(input)
	send_btn = UiKit.button("Say", Vector2(80, 48))
	send_btn.pressed.connect(_send)
	row.add_child(send_btn)
	Companion.reply.connect(_on_reply)
	Companion.failed.connect(_on_failed)
	Companion.busy_changed.connect(func(b: bool) -> void:
		send_btn.disabled = b
		status.text = "Odalys is thinking..." if b else "")
	_render()
	if not Companion.connected():
		status.text = "Not connected: add an OpenAI API key in Pause > Settings to let her speak freely."
	if Companion.history.is_empty():
		var hello := "You found the room. Good. Sit; Pell says you can be trusted, and Pell is never wrong about paper." \
			if Companion.connected() else Companion.offline_line()
		Companion.history.append({"role": "assistant", "content": hello})
		_render()


func _render() -> void:
	var out := ""
	for m: Dictionary in Companion.history.slice(-30):
		var who := "You" if str(m.get("role", "")) == "user" else "Odalys"
		var col := "#a59e90" if who == "You" else "#f6d67a"
		out += "[color=%s]%s:[/color] %s\n\n" % [col, who, str(m.get("content", "")).replace("[", "(")]
	log_box.text = out


func _send() -> void:
	var t := input.text.strip_edges()
	if t == "" or Companion.busy:
		return
	input.text = ""
	Companion.ask(t)
	_render()


func _on_reply(_t: String) -> void:
	_render()


func _on_failed(msg: String) -> void:
	status.text = msg
	_render()
