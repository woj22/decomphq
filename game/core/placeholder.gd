class_name Placeholder
extends RefCounted
## Code-drawn placeholder sprites (CONTRACTS §1): diamond / block / capsule tinted by kind.

const INK := Color("#0d0b12")
const STONE := [Color("#1a1722"), Color("#27232f"), Color("#37323f"), Color("#4b4654"), Color("#66616e"), Color("#8a8591"), Color("#b5b0b8")]
const PURPLE := [Color("#2a1f3d"), Color("#43325c"), Color("#6a5484"), Color("#9a86ad")]
const GOLD := [Color("#6b4a1e"), Color("#a8742a"), Color("#e0a83e"), Color("#f6d67a"), Color("#fff3c4")]
const RED := [Color("#3a0f14"), Color("#74161b"), Color("#b3261e"), Color("#e8552b")]
const WOOD := Color("#5a3f2e")
const SOUL := [Color("#cfe0e6"), Color("#8fa3b3")]


static func kind_for(id: String) -> String:
	if id.begins_with("floor_") or id.begins_with("decal_"):
		return "floor" if id.begins_with("floor_") else "decal"
	if id.begins_with("wall_kerb"):
		return "kerb"
	if id.begins_with("wall_") or id.begins_with("works_hatch") or id.begins_with("stairs"):
		return "wall"
	if id.begins_with("chr_"):
		return "character"
	if id.begins_with("por_"):
		return "portrait"
	if id.begins_with("bust_"):
		return "bust"
	if id.begins_with("bg_"):
		return "backdrop"
	if id.begins_with("light_pool") or id.begins_with("shadow") or id.begins_with("select_ring") or id.begins_with("dust") or id.begins_with("tap_marker"):
		return "fx"
	if id.begins_with("icon_") or id.begins_with("pip_") or id.begins_with("stamp_") or id.begins_with("btn_") or id.ends_with("_9"):
		return "ui"
	return "prop"


static func make(id: String, kind_hint: String = "") -> Dictionary:
	var kind := kind_hint if kind_hint != "" else kind_for(id)
	if kind == "prop" or kind == "":
		kind = kind_for(id) if kind_for(id) != "prop" else "prop"
	var img: Image
	var origin := Vector2.ZERO
	var extra := {}
	match kind:
		"floor":
			img = _diamond(64, 32, STONE[2] if id.find("carpet") < 0 else RED[1], STONE[3] if id.find("gold") < 0 else GOLD[1])
			origin = Vector2(32, 16)
		"decal":
			img = _ring(256, 128, GOLD[1])
			origin = Vector2(128, 64)
		"wall":
			var col := STONE[1]
			if id.find("gilt") >= 0:
				col = GOLD[1]
			elif id.find("ember") >= 0:
				col = RED[1]
			img = _wall(64, 128, col, id)
			origin = Vector2(32, 112)
		"kerb":
			img = _wall(64, 48, STONE[2], id)
			origin = Vector2(32, 32)
		"character":
			var info := _char_sheet(id)
			return info
		"portrait":
			img = _portrait(64, id)
		"bust":
			img = _portrait(96, id)
		"backdrop":
			img = _backdrop(id)
		"fx":
			if id.begins_with("light_pool"):
				img = _glow(192, 96, GOLD[3] if id.find("gold") >= 0 else RED[3])
				origin = Vector2(96, 48)
				extra["additive"] = true
			elif id.begins_with("shadow"):
				img = _glow(32, 16, Color(0, 0, 0, 0.6))
				origin = Vector2(16, 8)
			elif id.begins_with("select_ring") or id.begins_with("tap_marker"):
				img = _ring(32, 16, GOLD[2])
				origin = Vector2(16, 8)
			else:
				img = Image.create(8, 8, false, Image.FORMAT_RGBA8)
				img.fill(Color(GOLD[4], 0.6))
				origin = Vector2(4, 4)
		"ui":
			img = _icon(id)
		_:
			# props: a block sized by name
			var size := Vector2i(32, 48)
			if id.begins_with("desk") or id.begins_with("counter") or id.begins_with("bench") or id.begins_with("dais") or id.begins_with("queue_rail"):
				size = Vector2i(64, 48)
			elif id.begins_with("shelf") or id.begins_with("ticket"):
				size = Vector2i(64, 112)
			elif id.begins_with("statue"):
				size = Vector2i(128, 192)
			elif id.begins_with("banner"):
				size = Vector2i(32, 96)
			elif id.begins_with("stool") or id.begins_with("rope") or id.begins_with("queue_post"):
				size = Vector2i(32, 32)
			var col := WOOD
			if id.find("statue") >= 0:
				col = STONE[4]
			elif id.find("brazier") >= 0 or id.find("torch") >= 0:
				col = GOLD[1]
			elif id.find("banner") >= 0:
				col = RED[1]
			elif id.find("shelf") >= 0:
				col = Color("#5a3f2e")
			img = _block(size.x, size.y, col, id.find("empty") >= 0)
			origin = Vector2(size.x / 2.0, size.y - size.x / 4.0)
			if id.begins_with("statue"):
				origin = Vector2(64, 192 - 32)
	var tex := ImageTexture.create_from_image(img)
	var d := {"texture": tex, "rect": Rect2(0, 0, img.get_width(), img.get_height()), "origin": origin, "kind": kind,
		"placeholder": true, "frames": 1}
	d.merge(extra, true)
	return d


static func _diamond(w: int, h: int, fill: Color, edge: Color) -> Image:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var dx := absf(x + 0.5 - w / 2.0) / (w / 2.0)
			var dy := absf(y + 0.5 - h / 2.0) / (h / 2.0)
			if dx + dy <= 1.0:
				img.set_pixel(x, y, edge if dx + dy > 0.9 else fill)
	return img


static func _ring(w: int, h: int, col: Color) -> Image:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var dx := absf(x + 0.5 - w / 2.0) / (w / 2.0)
			var dy := absf(y + 0.5 - h / 2.0) / (h / 2.0)
			var d := dx + dy
			if d <= 1.0 and d > 0.85:
				img.set_pixel(x, y, col)
	return img


static func _wall(w: int, h: int, col: Color, id: String) -> Image:
	# an iso block: top diamond + two faces
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	var top := 16
	for y in h:
		for x in w:
			var c := Color(0, 0, 0, 0)
			var cx := x + 0.5 - w / 2.0
			var t := absf(cx) / (w / 2.0)
			var ytop := t * top
			var ybot := h - top + t * top - top
			ybot = h - top * (1.0 - t)
			if y >= ytop and y <= ybot:
				if y < top * 2 - ytop and y >= ytop and y < top * (2.0 - t):
					c = col.lightened(0.25)
				else:
					c = col.darkened(0.15) if cx < 0 else col
				if (y % 6 == 0) and y > top * 2:
					c = c.darkened(0.2)
			img.set_pixel(x, y, c)
	if id.find("window") >= 0:
		var g := GOLD[3] if id.find("gold") >= 0 else RED[3]
		for y in range(h / 3, h / 3 + 28):
			for x in range(w / 2 - 6, w / 2 + 6):
				img.set_pixel(x, y, g)
	if id.find("door") >= 0:
		var g := INK
		if id.find("gilt") >= 0:
			g = GOLD[2]
		elif id.find("ember") >= 0:
			g = RED[3]
		for y in range(h - 70, h - 18):
			for x in range(w / 2 - 10, w / 2 + 10):
				img.set_pixel(x, y, g)
	return img


static func _block(w: int, h: int, col: Color, hollow: bool) -> Image:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	var top := w / 4
	for y in h:
		for x in w:
			var cx := x + 0.5 - w / 2.0
			var t := absf(cx) / (w / 2.0)
			var ytop := t * top
			var ybot := h - top * (1.0 - t)
			if y >= ytop and y <= ybot:
				var c := col.darkened(0.2) if cx < 0 else col
				if y < top * (2.0 - t):
					c = col.lightened(0.2)
				if hollow and y > top * 2 and (y / 8) % 2 == 0:
					c = INK
				if absf(cx) > w / 2.0 - 1.5 or y >= ybot - 1:
					c = INK
				img.set_pixel(x, y, c)
	return img


static func _glow(w: int, h: int, col: Color) -> Image:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var dx := (x + 0.5 - w / 2.0) / (w / 2.0)
			var dy := (y + 0.5 - h / 2.0) / (h / 2.0)
			var d := sqrt(dx * dx + dy * dy)
			if d < 1.0:
				img.set_pixel(x, y, Color(col, col.a * (1.0 - d) * 0.5))
	return img


static func _portrait(s: int, id: String) -> Image:
	var img := Image.create(s, s, false, Image.FORMAT_RGBA8)
	img.fill(PURPLE[0])
	var soul := id.begins_with("bust_") or id == "por_soul"
	var body := SOUL[1] if soul else STONE[4]
	var head := SOUL[0] if soul else STONE[6]
	for y in s:
		for x in s:
			var dx := x - s / 2.0
			var dyh := y - s * 0.4
			if dx * dx + dyh * dyh < (s * 0.18) * (s * 0.18):
				img.set_pixel(x, y, head)
			elif y > s * 0.62 and absf(dx) < s * 0.32 + (y - s * 0.62) * 0.4:
				img.set_pixel(x, y, body)
	var mood := 0
	if id.ends_with("distressed"):
		mood = -1
	elif id.ends_with("relieved"):
		mood = 1
	var ey := int(s * 0.38)
	for ex: int in [int(s * 0.44), int(s * 0.56)]:
		img.set_pixel(ex, ey, INK)
		img.set_pixel(ex, ey + 1, INK)
	var my := int(s * 0.48)
	for mx in range(int(s * 0.46), int(s * 0.55)):
		var off := 0
		if mood != 0:
			off = int(-mood * (1.0 - absf(mx - s * 0.5) / (s * 0.05)))
		img.set_pixel(mx, clampi(my + off, 0, s - 1), INK)
	# frame
	for i in s:
		img.set_pixel(i, 0, GOLD[1])
		img.set_pixel(i, s - 1, GOLD[1])
		img.set_pixel(0, i, GOLD[1])
		img.set_pixel(s - 1, i, GOLD[1])
	return img


static func _backdrop(id: String) -> Image:
	var w := 320
	var h := 180
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	var a: Color
	var b: Color
	if id.find("heaven") >= 0:
		a = GOLD[3]
		b = GOLD[1]
	elif id.find("hell") >= 0:
		a = RED[1]
		b = RED[0]
	else:
		a = PURPLE[1]
		b = INK
	for y in h:
		var c := a.lerp(b, float(y) / h)
		for x in w:
			var cc := c
			if id.find("skyline") >= 0:
				var hh := int(60 + 40 * absf(sin(x * 0.07)) + 30 * absf(sin(x * 0.023)))
				cc = Color(0, 0, 0, 0) if y < h - hh else c.darkened(0.5)
			img.set_pixel(x, y, cc)
	return img


static func _icon(id: String) -> Image:
	var s := 16
	if id.begins_with("btn_"):
		s = 64
	elif id.begins_with("stamp_"):
		s = 64
	elif id.begins_with("icon_crest"):
		s = 32
	elif id.ends_with("_9"):
		s = 24
	var img := Image.create(s, s, false, Image.FORMAT_RGBA8)
	var col := STONE[6]
	if id.find("halo") >= 0 or id.find("heaven") >= 0 or id.find("obol") >= 0 or id.find("crest") >= 0:
		col = GOLD[3]
	elif id.find("flame") >= 0 or id.find("hell") >= 0:
		col = RED[2]
	elif id.find("rm0") >= 0:
		col = Color("#8b3fd9")
	elif id.find("link") >= 0 or id.find("pip") >= 0:
		col = PURPLE[3]
	if id.ends_with("_9"):
		img.fill(Color("#e6d9b8") if id.begins_with("parchment") else STONE[0])
		return img
	for y in s:
		for x in s:
			var dx := x + 0.5 - s / 2.0
			var dy := y + 0.5 - s / 2.0
			var r := sqrt(dx * dx + dy * dy)
			var on := false
			if id.find("flame") >= 0 or id.find("hell") >= 0:
				on = dy > -s * 0.4 and absf(dx) < (dy + s * 0.4) * 0.5 and dy < s * 0.4
			elif id.find("halo") >= 0 or id.find("heaven") >= 0:
				on = absf(r - s * 0.32) < s * 0.09
			elif id == "pip_empty":
				on = absf(r - s * 0.3) < 1.0
			else:
				on = r < s * 0.4
			if on:
				img.set_pixel(x, y, col)
	return img


## Placeholder character sheet: 8 dirs x rows idle(2) walk(4) work(2).
static func _char_sheet(id: String) -> Dictionary:
	var cw := 32
	var chh := 56
	var rows := 8
	var img := Image.create(cw * 8, chh * rows, false, Image.FORMAT_RGBA8)
	var soul := id.begins_with("chr_soul")
	var body := STONE[4]
	var hem := STONE[5]
	if soul:
		body = Color(SOUL[0], 0.75)
		hem = Color(SOUL[1], 0.75)
	elif id.begins_with("chr_player"):
		body = STONE[3]
		hem = GOLD[2]
	elif id.find("lilac") >= 0:
		hem = PURPLE[3]
	elif id.find("guard") >= 0:
		body = STONE[2]
		hem = RED[1]
	elif id.find("archivist") >= 0:
		body = PURPLE[1]
	var dir_vec := [Vector2(-1, 0.5), Vector2(-1, 0), Vector2(-1, -0.5), Vector2(0, -1), Vector2(1, -0.5), Vector2(1, 0), Vector2(1, 0.5), Vector2(0, 1)]
	for di in 8:
		for row in rows:
			var ox := di * cw
			var oy := row * chh
			var bob := 0
			if row >= 2 and row < 6:
				bob = [0, -1, 0, -1][row - 2]
			elif row < 2:
				bob = row
			var outline := PURPLE[2] if soul else INK
			for y in range(14, 48):
				for x in range(6, 26):
					var dx := x + 0.5 - 16
					var wdt := 6.0 + (y - 14) * 0.12
					if absf(dx) < wdt:
						var c := hem if y > 42 else body
						if absf(dx) > wdt - 1.0:
							c = outline
						img.set_pixel(ox + x, oy + y + bob - (1 if y > 46 else 0), c)
			for y in range(4, 17):
				for x in range(9, 23):
					var dx := x + 0.5 - 16
					var dy := y + 0.5 - 10
					if dx * dx + dy * dy < 30:
						img.set_pixel(ox + x, oy + y + bob, outline if dx * dx + dy * dy > 20 else (body.lightened(0.25) if not soul else SOUL[0]))
			var dv: Vector2 = dir_vec[di]
			var fx := int(16 + dv.x * 4)
			var fy := int(10 + dv.y * 3)
			if dv.y <= 0.5:
				img.set_pixel(ox + fx, oy + fy + bob, GOLD[3] if not soul else PURPLE[2])
				img.set_pixel(ox + fx, oy + fy + 1 + bob, GOLD[3] if not soul else PURPLE[2])
	var tex := ImageTexture.create_from_image(img)
	return {"texture": tex, "rect": Rect2(0, 0, cw * 8, chh * rows), "origin": Vector2(16, 48), "kind": "character",
		"cell": [cw, chh], "dirs": Array(Iso.DIRS), "placeholder": true,
		"anims": {"idle": {"row": 0, "frames": 2, "fps": 2}, "walk": {"row": 2, "frames": 4, "fps": 8}, "work": {"row": 6, "frames": 2, "fps": 2}}}
