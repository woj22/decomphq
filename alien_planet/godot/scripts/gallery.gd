extends "res://scripts/main.gd"
## Species gallery: the whole cast lined up by species on an open plain, under the same sky and light
## as the world. Explore with the normal controls (fly with F / FLY). Run with:
##   godot --path alien_planet/godot res://scenes/gallery.tscn [-- --shots=DIR]

const ORDER := ["human", "avari", "keth", "luma", "vorn", "murrai"]
const TITLES := {"human": "Humans", "avari": "Avari", "keth": "Keth", "luma": "Luma", "vorn": "Vorn", "murrai": "Murrai"}
const POSES := ["Idle", "Talk", "Idle", "Talk", "Idle", "Idle"]
## Humans are KayKit Adventurers (CC0, Kay Lousberg): [model, name, height]
const HUMANS := [["Knight", "Ser Odric", 1.86], ["Barbarian", "Brannoc", 1.9], ["Mage", "Ilsa", 1.72],
	["Rogue", "Senna", 1.7], ["Rogue_Hooded", "Mbeki", 1.76]]
var groups := {}
var all_chars: Array = []


func _ready() -> void:
	_make_materials()
	_make_environment()
	_make_stage()
	_make_player()
	_lineup()
	_anim_sheet()
	(get_node("Sun") as DirectionalLight3D).shadow_normal_bias = 3.0
	player.look_from(Vector3(0, 2.2, 13), Vector3(0, 1.2, 0))
	var shots := _arg("--shots")
	if shots != "":
		_run_shots.call_deferred(shots)


func _spawn_inhabitants() -> void:
	pass


func _make_stage() -> void:
	var g := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(400, 400)
	g.mesh = pm
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.5, 0.42, 0.45)
	m.roughness = 1.0
	g.material_override = m
	add_child(g)
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var sh := WorldBoundaryShape3D.new()
	cs.shape = sh
	body.add_child(cs)
	add_child(body)


func _lineup() -> void:
	# six groups in a shallow arc facing +Z (towards the camera)
	for gi in ORDER.size():
		var sp: String = ORDER[gi]
		var a := deg_to_rad(lerpf(-50.0, 50.0, gi / 5.0))
		var center := Vector3(sin(a) * 11.0, 0, -cos(a) * 11.0 + 11.0)
		var facing := atan2(-center.x, 12.0 - center.z)
		var members := Cast.by_species(sp) if sp != "human" else HUMANS.map(func(h): return {"id": "kk:" + h[0], "name": h[1], "height": h[2]})
		var node := Node3D.new()
		node.name = sp
		add_child(node)
		node.position = center
		node.rotation.y = facing
		for i in members.size():
			var e: Dictionary = members[i]
			var c: Node3D
			if String(e["id"]).begins_with("kk:"):
				c = KayKit.character(String(e["id"]).substr(3), POSES[i % POSES.size()], [], float(e["height"]), 0.15 * i)
			else:
				c = Cast.spawn(e["id"], POSES[i % POSES.size()], 0.15 * i)
			node.add_child(c)
			c.position = Vector3((i - (members.size() - 1) / 2.0) * 0.95, 0, (0.25 if i % 2 else 0.0))
			c.rotation.y = (i - members.size() / 2.0) * -0.08
			all_chars.append(c)
			var lab := Label3D.new()
			lab.text = e["name"]
			lab.font_size = 22
			lab.pixel_size = 0.004
			lab.billboard = BaseMaterial3D.BILLBOARD_ENABLED
			lab.modulate = Color(1, 1, 1, 0.85)
			lab.outline_size = 6
			lab.position = Vector3(0, float(e["height"]) + 0.22, 0)
			c.add_child(lab)
		var title := Label3D.new()
		title.text = TITLES[sp]
		title.font_size = 64
		title.pixel_size = 0.006
		title.outline_size = 12
		title.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		title.position = Vector3(0, 3.0, 0)
		node.add_child(title)
		groups[sp] = node


const SHEET_ANIMS := ["Idle", "Walk", "Run", "Sit", "Talk", "Attack"]
const SHEET_AT := [0.0, 0.25, 0.25, 0.3, 0.35, 0.42]
var sheet_rows := {}


## Animation sheet behind the lineup: one row per species (same rig, same animation set), one column per
## animation, frozen at a telling moment. Sitters get a stone seat at knee height.
func _anim_sheet() -> void:
	for gi in ORDER.size():
		var sp: String = ORDER[gi]
		var e: Dictionary = Cast.by_species(sp)[0] if sp != "human" else {"id": "kk:Knight", "height": 1.86}
		var row := Node3D.new()
		row.name = "sheet_" + sp
		add_child(row)
		row.position = Vector3(0, 0, -40.0 - gi * 14.0)
		sheet_rows[sp] = row
		for k in SHEET_ANIMS.size():
			var c: Node3D
			if String(e["id"]).begins_with("kk:"):
				c = KayKit.character("Knight", SHEET_ANIMS[k] if SHEET_ANIMS[k] != "Attack" else "Attack", ["1H_Sword"] if SHEET_ANIMS[k] == "Attack" else [], 1.86, SHEET_AT[k])
			else:
				c = Cast.spawn(e["id"], SHEET_ANIMS[k], SHEET_AT[k])
			row.add_child(c)
			c.position = Vector3((k - 2.5) * 1.6, 0, 0)
			(c.get_meta("player") as AnimationPlayer).speed_scale = 0.0
			if SHEET_ANIMS[k] == "Sit":
				var seat := MeshInstance3D.new()
				var bm := BoxMesh.new()
				bm.size = Vector3(0.6, 0.48 * float(e["height"]) / 1.75, 0.5)
				seat.mesh = bm
				seat.position = Vector3(0, bm.size.y / 2.0, -0.12)
				c.add_child(seat)
			var lab := Label3D.new()
			lab.text = SHEET_ANIMS[k]
			lab.font_size = 28
			lab.pixel_size = 0.005
			lab.outline_size = 8
			lab.billboard = BaseMaterial3D.BILLBOARD_ENABLED
			lab.position = Vector3(0, float(e["height"]) + 0.3, 0)
			c.add_child(lab)


func _all(anim: String, at: float) -> void:
	for c in all_chars:
		Cast.play(c, anim, at)


func _run_shots(dir: String) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	player.frozen = true
	for i in 3:
		await get_tree().physics_frame
	var views := []
	views.append(["g00_lineup", Vector3(0, 3.2, 15.5), Vector3(0, 1.0, 3), ""])
	for sp in ORDER:
		var n: Node3D = groups[sp]
		var fwd := n.global_transform.basis.z
		var eye := n.global_position + fwd * 4.4 + Vector3(0, 1.45, 0)
		views.append(["g_" + sp, eye, n.global_position + Vector3(0, 1.0, 0), ""])
	for sp in ["human", "keth", "murrai"]:
		var n: Node3D = groups[sp]
		var fwd := n.global_transform.basis.z
		var side := n.global_transform.basis.x
		views.append(["g_" + sp + "_side_walk", n.global_position + fwd * 2.2 + side * 4.0 + Vector3(0, 1.3, 0),
			n.global_position + Vector3(0, 0.9, 0), "Walk"])
	views.append(["g_avari_face", groups["avari"].global_position + groups["avari"].global_transform.basis.z * 1.5 + Vector3(0, 2.0, 0),
		groups["avari"].global_position + Vector3(0, 1.9, 0), ""])
	views.append(["g_vorn_face", groups["vorn"].global_position + groups["vorn"].global_transform.basis.z * 1.4 + Vector3(0, 1.65, 0),
		groups["vorn"].global_position + Vector3(0, 1.55, 0), ""])
	views.append(["g_murrai_face", groups["murrai"].global_position + groups["murrai"].global_transform.basis.z * 1.4 + Vector3(0, 1.5, 0),
		groups["murrai"].global_position + Vector3(0, 1.35, 0), ""])
	for sp in ORDER:
		var row: Node3D = sheet_rows[sp]
		views.append(["s_" + sp, row.global_position + Vector3(3.0, 1.5, 5.2), row.global_position + Vector3(0.6, 0.85, 0), ""])
	for v in views:
		if v[3] != "":
			_all(v[3], 0.4 if v[3] == "Attack" else 0.25)
		player.look_from(v[1], v[2])
		for i in 8:
			await get_tree().process_frame
		if v[3] != "":
			for c in all_chars:
				(c.get_meta("player") as AnimationPlayer).pause()
		for i in 4:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(dir.path_join(v[0] + ".png"))
		print("SHOT ", v[0])
		if v[3] != "":
			for c in all_chars:
				Cast.play(c, "Idle", randf())
	get_tree().quit()
