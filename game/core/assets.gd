class_name Assets
extends RefCounted
## Scans res://assets/**.json atlas manifests (CONTRACTS §1) and serves textures by sprite ID.
## Any missing ID gets a code-drawn placeholder (logged once).

static var sprites: Dictionary = {}
static var _tex_cache: Dictionary = {}
static var _frame_cache: Dictionary = {}
static var _placeholders: Dictionary = {}
static var missing_logged: Dictionary = {}
static var scanned := false
static var atlas_count := 0
static var font_cache: Dictionary = {}


static func scan(force: bool = false) -> void:
	if scanned and not force:
		return
	scanned = true
	sprites = {}
	_tex_cache = {}
	_frame_cache = {}
	atlas_count = 0
	for f: String in JsonUtil.list_files("res://assets", ".json"):
		var d: Variant = JsonUtil.load_file(f)
		if not (d is Dictionary) or not (d as Dictionary).has("sprites"):
			continue
		var m: Dictionary = d
		var img_name := str(m.get("image", f.get_file().get_basename() + ".png"))
		var img_path := f.get_base_dir().path_join(img_name)
		atlas_count += 1
		var sp: Dictionary = m["sprites"]
		for id: String in sp:
			var s: Dictionary = sp[id]
			var info := s.duplicate(true)
			var r: Array = s.get("rect", [0, 0, 0, 0])
			info["rect"] = Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3]))
			var o: Array = s.get("origin", [0, 0])
			info["origin"] = Vector2(float(o[0]), float(o[1]))
			info["image_path"] = str(s.get("image", "")) if s.has("image") else img_path
			if s.has("image"):
				info["image_path"] = f.get_base_dir().path_join(str(s["image"]))
			info["atlas"] = str(m.get("atlas", f.get_file().get_basename()))
			sprites[id] = info
	print("[Assets] %d sprites in %d manifests" % [sprites.size(), atlas_count])


static func has(id: String) -> bool:
	scan()
	return sprites.has(id)


static func _load_texture(path: String) -> Texture2D:
	if _tex_cache.has(path):
		return _tex_cache[path]
	var tex: Texture2D = null
	if ResourceLoader.exists(path):
		tex = load(path) as Texture2D
	if tex == null:
		var img := Image.load_from_file(ProjectSettings.globalize_path(path))
		if img != null and not img.is_empty():
			tex = ImageTexture.create_from_image(img)
	_tex_cache[path] = tex
	return tex


## Sprite info; generates and caches a placeholder for unknown IDs.
static func info(id: String, kind_hint: String = "") -> Dictionary:
	scan()
	if sprites.has(id):
		var s: Dictionary = sprites[id]
		if not s.has("texture"):
			var t := _load_texture(str(s["image_path"]))
			if t == null:
				_log_missing(id + " (image " + str(s["image_path"]) + ")")
				var ph := Placeholder.make(id, kind_hint if kind_hint != "" else str(s.get("kind", "")))
				sprites[id] = ph
				return ph
			s["texture"] = t
		return s
	if _placeholders.has(id):
		return _placeholders[id]
	_log_missing(id)
	var p := Placeholder.make(id, kind_hint)
	_placeholders[id] = p
	return p


static func is_placeholder(id: String) -> bool:
	return bool(info(id).get("placeholder", false))


static func _log_missing(id: String) -> void:
	if missing_logged.has(id):
		return
	missing_logged[id] = true
	print("[Assets] missing sprite '%s' -> placeholder" % id)


## Frame texture of a non-character sprite (frame 0 = rect).
static func frame(id: String, f: int = 0, kind_hint: String = "") -> Texture2D:
	var key := "%s#%d" % [id, f]
	if _frame_cache.has(key):
		return _frame_cache[key]
	var s := info(id, kind_hint)
	var at := AtlasTexture.new()
	at.atlas = s["texture"]
	var r: Rect2 = s["rect"]
	var nframes := int(s.get("frames", 1))
	at.region = Rect2(r.position + Vector2(r.size.x * (f % maxi(1, nframes)), 0), r.size)
	_frame_cache[key] = at
	return at


static func frame_count(id: String) -> int:
	return maxi(1, int(info(id).get("frames", 1)))


## Character frame (CONTRACTS §1): x = rect.x + dir_i*cell.w, y = rect.y + (row+f)*cell.h.
static func char_frame(id: String, dir: String, anim: String, f: int) -> Texture2D:
	var s := info(id, "character")
	var anims: Dictionary = s.get("anims", {})
	if not anims.has(anim):
		anim = "idle" if anims.has("idle") else (str(anims.keys()[0]) if anims.size() > 0 else "idle")
	var a: Dictionary = anims.get(anim, {"row": 0, "frames": 1})
	var nf := maxi(1, int(a.get("frames", 1)))
	f = f % nf
	var dirs: Array = s.get("dirs", Array(Iso.DIRS))
	var di := dirs.find(dir)
	if di < 0:
		di = 0
	var key := "%s|%d|%s|%d" % [id, di, anim, f]
	if _frame_cache.has(key):
		return _frame_cache[key]
	var cell_a: Array = s.get("cell", [32, 56])
	var cw := float(cell_a[0])
	var ch := float(cell_a[1])
	var r: Rect2 = s["rect"]
	var at := AtlasTexture.new()
	at.atlas = s["texture"]
	at.region = Rect2(r.position.x + di * cw, r.position.y + (int(a.get("row", 0)) + f) * ch, cw, ch)
	_frame_cache[key] = at
	return at


static func anim_info(id: String, anim: String) -> Dictionary:
	var anims: Dictionary = info(id, "character").get("anims", {})
	return anims.get(anim, anims.get("idle", {"row": 0, "frames": 1, "fps": 2}))


static func has_anim(id: String, anim: String) -> bool:
	return (info(id, "character").get("anims", {}) as Dictionary).has(anim)


## Whole-sprite texture for UI (portraits, icons, busts).
static func ui_texture(id: String, kind_hint: String = "ui") -> Texture2D:
	return frame(id, 0, kind_hint)


## Font lookup: res://assets/fonts/<name>*.ttf|otf; null when absent (callers use the default font).
static func font(role: String) -> Font:
	if font_cache.has(role):
		return font_cache[role]
	var wanted := {"display": ["jacquard"], "body": ["pixeloperator", "pixel_operator", "pixel-operator", "pixelify"],
		"bold": ["pixeloperator-bold", "pixeloperator_bold", "pixel_operator_bold", "pixeloperatorbold"],
		"mono": ["departure"], "large": ["jersey"]}
	var found: Font = null
	var files: PackedStringArray = JsonUtil.list_files("res://assets/fonts", ".ttf")
	files.append_array(JsonUtil.list_files("res://assets/fonts", ".otf"))
	for key: String in wanted.get(role, []):
		for f: String in files:
			var n := f.get_file().to_lower().replace(" ", "")
			if n.begins_with(key) or n.find(key) >= 0:
				if role == "body" and n.find("bold") >= 0:
					continue
				var ff := FontFile.new()
				if ff.load_dynamic_font(ProjectSettings.globalize_path(f)) == OK or ResourceLoader.exists(f):
					if ResourceLoader.exists(f):
						var loaded := load(f) as FontFile
						if loaded != null:
							ff = loaded
					ff.antialiasing = TextServer.FONT_ANTIALIASING_NONE
					ff.hinting = TextServer.HINTING_NONE
					ff.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
					found = ff
					break
		if found != null:
			break
	font_cache[role] = found
	return found
