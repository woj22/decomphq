class_name UiKit
extends RefCounted
## Shared UI theme, style tokens (PROJECT §9.5) and widget helpers. One Theme for every screen.

const CHARCOAL := Color(0.102, 0.090, 0.133, 0.92) # #1a1722 @ 92 %
const CHARCOAL_SOLID := Color("#1a1722")
const EDGE := Color("#37323f")
const BORDER_GOLD := Color("#e0a83e")
const HEAVEN := Color("#f6d67a")
const HELL := Color("#b3261e")
const EMBER := Color("#e8552b")
const SELECT := Color("#9a86ad")
const SELECT_ON_PARCHMENT := Color("#6a5484")
const PARCHMENT := Color("#E6D9B8")
const PARCHMENT_SHADE := Color("#CBB98F")
const INK := Color("#2A2320")
const TEXT := Color("#EDE6D6")
const TEXT_DIM := Color("#A59E90")
const VIOLET := Color("#8b3fd9")
const BODY := 16
const CAPTION := 12

static var _theme: Theme


static func theme() -> Theme:
	if _theme != null:
		return _theme
	var t := Theme.new()
	var body := Assets.font("body")
	if body != null:
		t.default_font = body
	t.default_font_size = BODY
	t.set_color("font_color", "Label", TEXT)
	t.set_color("font_color", "Button", TEXT)
	t.set_color("font_hover_color", "Button", TEXT)
	t.set_color("font_pressed_color", "Button", TEXT)
	t.set_color("font_focus_color", "Button", TEXT)
	t.set_color("font_disabled_color", "Button", TEXT_DIM)
	t.set_stylebox("normal", "Button", box(Color("#27232f"), EDGE, 1, 4))
	t.set_stylebox("hover", "Button", box(Color("#37323f"), EDGE, 1, 4))
	t.set_stylebox("pressed", "Button", box(Color("#43325c"), SELECT, 1, 4))
	t.set_stylebox("disabled", "Button", box(Color("#1a1722"), EDGE, 1, 4))
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	t.set_stylebox("panel", "PanelContainer", box(CHARCOAL, EDGE, 1, 6))
	t.set_stylebox("panel", "Panel", box(CHARCOAL, EDGE, 1, 6))
	t.set_constant("line_spacing", "Label", 2)
	_theme = t
	return t


static func font(role: String) -> Font:
	var f := Assets.font(role)
	return f


static func box(bg: Color, border: Color = Color(0, 0, 0, 0), bw: int = 0, pad: int = 6) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(bw)
	s.content_margin_left = pad
	s.content_margin_right = pad
	s.content_margin_top = pad
	s.content_margin_bottom = pad
	s.anti_aliasing = false
	return s


static func charcoal_box(pad: int = 6, gold: bool = false) -> StyleBoxFlat:
	return box(CHARCOAL, BORDER_GOLD if gold else EDGE, 1, pad)


static func parchment_box(pad: int = 8) -> StyleBoxFlat:
	return box(PARCHMENT, PARCHMENT_SHADE, 2, pad)


static func panel(style: StyleBox) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", style)
	return p


static func label(text: String, size: int = BODY, color: Color = TEXT, role: String = "") -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if role != "":
		var f := font(role)
		if f != null:
			l.add_theme_font_override("font", f)
	return l


static func wrap_label(text: String, size: int = BODY, color: Color = TEXT) -> Label:
	var l := label(text, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size.x = 40
	return l


static func button(text: String, min_size: Vector2 = Vector2(48, 48), icon_id: String = "") -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = min_size
	b.focus_mode = Control.FOCUS_NONE
	if icon_id != "":
		b.icon = Assets.ui_texture(icon_id)
		b.expand_icon = false
	b.pressed.connect(func() -> void: Audio.sfx("sfx_tap"))
	return b


static func icon(id: String, size: Vector2 = Vector2(16, 16)) -> TextureRect:
	var t := TextureRect.new()
	t.texture = Assets.ui_texture(id)
	t.custom_minimum_size = size
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return t


static func full_rect(c: Control) -> Control:
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.offset_left = 0
	c.offset_top = 0
	c.offset_right = 0
	c.offset_bottom = 0
	return c


static func dim(alpha: float = 0.6) -> ColorRect:
	var r := ColorRect.new()
	r.color = Color(0.05, 0.04, 0.07, alpha)
	full_rect(r)
	r.mouse_filter = Control.MOUSE_FILTER_STOP
	return r


## Safe-area margins in base px: max(device inset / scale, 12), bottom >= 16.
static func safe_margins(vp: Viewport) -> Dictionary:
	var m := {"left": 12, "top": 12, "right": 12, "bottom": 16}
	var safe := DisplayServer.get_display_safe_area()
	var win := DisplayServer.window_get_size()
	if safe.size.x <= 0 or win.x <= 0 or DisplayServer.get_name() == "headless":
		return m
	var scale := float(win.x) / maxf(1.0, vp.get_visible_rect().size.x)
	var l := safe.position.x / scale
	var r := (win.x - safe.end.x) / scale
	var t := safe.position.y / scale
	var b := (win.y - safe.end.y) / scale
	if l >= 0 and l < 200:
		m["left"] = maxi(12, int(ceil(l)))
	if r >= 0 and r < 200:
		m["right"] = maxi(12, int(ceil(r)))
	if t >= 0 and t < 200:
		m["top"] = maxi(12, int(ceil(t)))
	if b >= 0 and b < 200:
		m["bottom"] = maxi(16, int(ceil(b)))
	return m


static func apply_safe(mc: MarginContainer) -> void:
	var m := safe_margins(mc.get_viewport()) if mc.is_inside_tree() else {"left": 12, "top": 12, "right": 12, "bottom": 16}
	mc.add_theme_constant_override("margin_left", m["left"])
	mc.add_theme_constant_override("margin_top", m["top"])
	mc.add_theme_constant_override("margin_right", m["right"])
	mc.add_theme_constant_override("margin_bottom", m["bottom"])


static func side_color(side: String) -> Color:
	if side == "heaven":
		return Color("#a8742a")
	if side == "hell":
		return HELL
	return INK
