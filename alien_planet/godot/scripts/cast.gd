class_name Cast
extends RefCounted
## Loads the procedurally built characters (alien_planet/blender/build_characters.py) and plays their
## shared animation set: Idle, Walk, Run, Sit, Talk, Attack. Same skeleton and bone names for every species.

const DIR := "res://assets/chars/"
const LOOPING := ["Idle", "Walk", "Run", "Sit", "Talk"]
const BODY := preload("res://shaders/character.gdshader")
const GLOW := preload("res://shaders/glow.gdshader")

static var _mats := {}
static var manifest: Array = []


static func load_manifest() -> Array:
	if manifest.is_empty():
		var f := FileAccess.open(DIR + "manifest.json", FileAccess.READ)
		manifest = JSON.parse_string(f.get_as_text())
	return manifest


static func by_species(sp: String) -> Array:
	return load_manifest().filter(func(e): return e["species"] == sp)


static func _material(name: String) -> Material:
	if not _mats.has(name):
		var m := ShaderMaterial.new()
		if name == "CharGlow":
			m.shader = GLOW
			m.set_shader_parameter("sway_amount", 0.0)
			m.set_shader_parameter("intensity", 1.3)
		else:
			m.shader = BODY
		_mats[name] = m
	return _mats[name]


## Instantiates character `id`, playing `anim` (offset so crowds don't move in lockstep).
static func spawn(id: String, anim := "Idle", offset := -1.0) -> Node3D:
	var node: Node3D = load(DIR + id + ".glb").instantiate()
	node.name = id
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = mi
		for i in m.mesh.get_surface_count():
			var src := m.mesh.surface_get_material(i)
			m.set_surface_override_material(i, _material(src.resource_name if src else "CharBody"))
	var ap: AnimationPlayer = node.find_children("*", "AnimationPlayer", true, false)[0]
	for a in ap.get_animation_list():
		ap.get_animation(a).loop_mode = Animation.LOOP_LINEAR if a in LOOPING else Animation.LOOP_NONE
	ap.play(anim)
	if offset < 0.0:
		offset = randf()
	ap.seek(offset * ap.current_animation_length, true)
	node.set_meta("player", ap)
	return node


static func play(node: Node3D, anim: String, at := 0.0) -> void:
	var ap: AnimationPlayer = node.get_meta("player")
	ap.play(anim)
	ap.seek(at * ap.current_animation_length, true)
