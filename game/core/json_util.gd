class_name JsonUtil
extends RefCounted
## Small JSON helpers. All content is UTF-8 JSON.

static var last_error: String = ""


static func load_file(path: String) -> Variant:
	last_error = ""
	if not FileAccess.file_exists(path):
		last_error = "missing file " + path
		return null
	var text := FileAccess.get_file_as_string(path)
	var json := JSON.new()
	var err := json.parse(text)
	if err != OK:
		last_error = "%s:%d %s" % [path, json.get_error_line(), json.get_error_message()]
		push_error("JSON parse error " + last_error)
		return null
	return json.data


static func save_file(path: String, data: Variant, atomic: bool = true) -> bool:
	var text := JSON.stringify(data, "\t", false)
	var target := path
	if atomic:
		target = path + ".tmp"
	var f := FileAccess.open(target, FileAccess.WRITE)
	if f == null:
		push_error("Cannot write " + target)
		return false
	f.store_string(text)
	f.close()
	if atomic:
		var dir := DirAccess.open(path.get_base_dir())
		if dir == null:
			return false
		if FileAccess.file_exists(path):
			if FileAccess.file_exists(path + ".bak"):
				dir.remove(path.get_file() + ".bak")
			dir.rename(path.get_file(), path.get_file() + ".bak")
		var e := dir.rename(target.get_file(), path.get_file())
		if e != OK:
			push_error("Rename failed for " + path)
			return false
	return true


## Lists files under `dir` (recursive) whose name ends with `suffix`.
static func list_files(dir_path: String, suffix: String, recursive: bool = true) -> PackedStringArray:
	var out: PackedStringArray = []
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return out
	dir.list_dir_begin()
	var name := dir.get_next()
	while name != "":
		if name.begins_with("."):
			name = dir.get_next()
			continue
		var full := dir_path.path_join(name)
		if dir.current_is_dir():
			if recursive:
				out.append_array(list_files(full, suffix, true))
		elif name.ends_with(suffix):
			out.append(full)
		name = dir.get_next()
	dir.list_dir_end()
	out.sort()
	return out


static func dir_exists(path: String) -> bool:
	return DirAccess.dir_exists_absolute(path)


static func to_vec2i(v: Variant, fallback: Vector2i = Vector2i.ZERO) -> Vector2i:
	if v is Array and (v as Array).size() >= 2:
		var a: Array = v
		return Vector2i(int(a[0]), int(a[1]))
	if v is Vector2i:
		return v
	if v is Vector2:
		return Vector2i(v)
	return fallback


static func deep_copy(v: Variant) -> Variant:
	if v is Dictionary:
		return (v as Dictionary).duplicate(true)
	if v is Array:
		return (v as Array).duplicate(true)
	return v
