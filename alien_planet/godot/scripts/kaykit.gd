class_name KayKit
extends RefCounted
## KayKit models (CC0, Kay Lousberg - www.kaylousberg.com) placed from assets/kaykit_layout.json, which
## blender/farm.py writes with exact ground heights. Repeated props ('mm') are batched into one MultiMesh per
## model (one draw call each), buildings ('col') get trimesh collision, and sails / fans / saws spin.

const DIR := "res://assets/kaykit/"
const LAYOUT := "res://assets/kaykit_layout.json"
const SPIN_PARTS := {"windmill_top_fan": Vector3.BACK, "windturbine_tall_fan": Vector3.BACK, "lumbermill_saw": Vector3.RIGHT}

## Adventurers (rigged, 76 animations) stand in for the Human species. Weapons are hidden unless asked for.
const WEAPON_WORDS := ["Sword", "Shield", "Axe", "Crossbow", "Knife", "Throwable", "Mug", "Wand", "Staff", "Spellbook", "Arrow", "Quiver", "Blade"]
const ANIM := {"Idle": "Idle", "Walk": "Walking_A", "Run": "Running_A", "Sit": "Sit_Chair_Idle", "Talk": "Interact",
	"Work": "1H_Melee_Attack_Chop", "Attack": "1H_Melee_Attack_Slice_Diagonal", "Cheer": "Cheer", "Lie": "Lie_Pose",
	"Dead": "Death_A_Pose", "SitFloor": "Sit_Floor_Pose"}


static func place_all(parent: Node3D, spinners: Array) -> void:
	var f := FileAccess.open(LAYOUT, FileAccess.READ)
	if f == null:
		return
	var items: Array = JSON.parse_string(f.get_as_text())
	var batches := {}
	var root := Node3D.new()
	root.name = "KayKit"
	parent.add_child(root)
	for e in items:
		var xf := Transform3D(Basis(Vector3.UP, deg_to_rad(float(e["r"]))).scaled(Vector3.ONE * float(e["s"])),
			Vector3(e["p"][0], e["p"][1], e["p"][2]))
		if e["t"] == "mm":
			if not batches.has(e["m"]):
				batches[e["m"]] = []
			batches[e["m"]].append(xf)
			continue
		var node: Node3D = load(DIR + e["m"] + ".gltf").instantiate()
		node.transform = xf
		root.add_child(node)
		for mi in node.find_children("*", "MeshInstance3D", true, false):
			var m: MeshInstance3D = mi
			for key in SPIN_PARTS:
				if String(m.name).contains(key):
					spinners.append([m, SPIN_PARTS[key], 1.2 if key != "lumbermill_saw" else 4.0])
			if e["t"] == "col":
				var body := StaticBody3D.new()
				var cs := CollisionShape3D.new()
				cs.shape = m.mesh.create_trimesh_shape()
				body.add_child(cs)
				m.add_child(body)
	for model in batches:
		var src: Node3D = load(DIR + model + ".gltf").instantiate()
		var mis := src.find_children("*", "MeshInstance3D", true, false)
		for mi in mis:
			var m: MeshInstance3D = mi
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = m.mesh
			var xfs: Array = batches[model]
			mm.instance_count = xfs.size()
			var local := m.transform
			for i in xfs.size():
				mm.set_instance_transform(i, xfs[i] * local)
			var mmi := MultiMeshInstance3D.new()
			mmi.name = String(model).get_file() + "_batch"
			mmi.multimesh = mm
			if String(model).contains("grain") or String(model).contains("fence"):
				mmi.visibility_range_end = 150.0
			root.add_child(mmi)
		src.free()


## A KayKit character (Knight, Barbarian, Mage, Rogue, Rogue_Hooded, Skeleton_Warrior, Skeleton_Minion).
## `anim` uses the planet's names (Idle, Talk, Work, Sit...) or any KayKit clip name.
static func character(model: String, anim := "Idle", keep := [], height := 1.8, offset := -1.0) -> Node3D:
	var pack := "skeletons/" if model.begins_with("Skeleton") else "adventurers/"
	var node: Node3D = load(DIR + pack + model + ".glb").instantiate()
	node.name = model
	node.scale = Vector3.ONE * (height / 2.45)
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		var n := String(mi.name)
		if n in keep:
			continue
		for w in WEAPON_WORDS:
			if n.contains(w):
				mi.visible = false
	var ap: AnimationPlayer = node.find_children("*", "AnimationPlayer", true, false)[0]
	var clip: String = ANIM.get(anim, anim)
	if ap.has_animation(clip):
		ap.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
		ap.play(clip)
		ap.seek((randf() if offset < 0.0 else offset) * ap.current_animation_length, true)
	node.set_meta("player", ap)
	return node
