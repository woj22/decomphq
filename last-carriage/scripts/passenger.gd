class_name Passenger
extends Node3D
## One seated passenger built from assets/models/passenger.glb: shows the figure's wardrobe pieces, recolours the
## Outfit/Accent/Skin/Lips/Hair materials, and animates the head (turns to look at people), the mouth (while speaking)
## and a little breathing and fidgeting.

const MODEL := preload("res://assets/models/passenger.glb")

var figure: Dictionary
var look_target: Variant = null  # Vector3 world point or null
var talking := false
var thinking := false
var model: Node3D
var head: Node3D
var mouth: Node3D
var _head_rest: Basis
var _t := randf() * 10.0
var _nod := 0.0


func setup(fig: Dictionary, first_person := false) -> void:
	figure = fig
	model = MODEL.instantiate()
	add_child(model)
	head = model.find_child("Head", true, false)
	mouth = model.find_child("Mouth", true, false)
	_head_rest = head.transform.basis
	var wanted: Array = fig["pieces"]
	for n in _all_nodes(model):
		var nm := String(n.name)
		for prefix in ["Hair_", "Beard_", "Hat_", "Costume_"]:
			if nm.begins_with(prefix):
				n.visible = nm in wanted
	var skin := Color(fig["skin"])
	var colours := {
		"Outfit": Color(fig["outfit"]),
		"Accent": Color(fig["accent"]),
		"Skin": skin,
		"Hair": Color(fig["hair"]),
		"Lips": skin.darkened(0.25).lerp(Color(0.62, 0.3, 0.3), 0.35),
	}
	for mi in _all_nodes(model):
		if mi is MeshInstance3D:
			_recolour(mi, colours)
	if first_person:  # the player sees their own arms and lap, not their own head or what sits under their chin
		head.visible = false
		for n in _all_nodes(model):
			if String(n.name) in ["Costume_Toga", "Costume_Ruff", "Costume_Usekh", "Costume_Scarf", "Costume_FurCollar", "Costume_Shawl", "Costume_Cravat", "Costume_Bowtie", "Costume_Beads", "Costume_Pearls"]:
				n.visible = false


func _recolour(mi: MeshInstance3D, colours: Dictionary) -> void:
	var mesh: Mesh = mi.mesh
	for i in mesh.get_surface_count():
		var m := mesh.surface_get_material(i) as BaseMaterial3D
		if m == null:
			continue
		var key := m.resource_name
		var nm := m.duplicate() as BaseMaterial3D
		if colours.has(key):
			nm.albedo_color = colours[key]
		if key == "Outfit":
			nm.roughness = 0.9
			nm.rim_enabled = true  # soft velvet/wool sheen in the lamplight
			nm.rim = 0.25
			nm.rim_tint = 0.6
		if key in ["Steel", "Gold", "Chrome", "Brass"]:  # no reflections in this renderer: keep metals bright
			nm.metallic = 0.45
			nm.roughness = 0.32
			nm.rim_enabled = true
			nm.rim = 0.5
		if key == "Skin" or key == "Lips":
			nm.roughness = 0.6
			nm.rim_enabled = true
			nm.rim = 0.15
			nm.rim_tint = 0.9
		mi.set_surface_override_material(i, nm)


func _all_nodes(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out.append_array(_all_nodes(c))
	return out


func head_world() -> Vector3:
	return head.global_position + Vector3(0, 0.14, 0)


func nod() -> void:
	_nod = 1.0


func _process(delta: float) -> void:
	_t += delta
	if head == null:
		return
	# head turn toward the look target, limited like a real neck
	var yaw := 0.0
	var pitch := 0.0
	if look_target != null:
		var local: Vector3 = model.global_transform.affine_inverse() * (look_target as Vector3)
		var from := head.position + Vector3(0, 0.13, 0)
		var d := local - from
		yaw = clampf(atan2(d.x, d.z), -1.25, 1.25)
		pitch = clampf(-atan2(d.y, Vector2(d.x, d.z).length()), -0.5, 0.45)
	yaw += sin(_t * 0.6) * 0.05
	if thinking:
		pitch += 0.12 + sin(_t * 1.3) * 0.05  # glance down, mulling it over
		yaw += sin(_t * 0.9) * 0.2
	_nod = maxf(0.0, _nod - delta * 1.6)
	pitch += sin(_nod * PI * 2.0) * 0.12 * _nod
	var cur := head.transform.basis
	var want := _head_rest * Basis.from_euler(Vector3(pitch, yaw, sin(_t * 0.4) * 0.03))
	head.transform.basis = cur.slerp(want.orthonormalized(), minf(1.0, delta * 5.0)).orthonormalized()
	# talking mouth and breathing
	if mouth:
		var open := 1.0
		if talking:
			open = 1.0 + absf(sin(_t * 13.0)) * 1.6 + absf(sin(_t * 7.3)) * 0.8
		mouth.scale.y = lerpf(mouth.scale.y, open, minf(1.0, delta * 18.0))
	model.position.y = sin(_t * 1.6) * 0.003
