class_name Person
extends Node3D
## A character in the train: the Blender-built model (assets/people/<id>.glb) with its animations, walking routes,
## sitting, lying, talking and a head that turns to look at people.

signal arrived

const WALK_SPEED := 1.05

var id := ""
var model: Node3D
var anim: AnimationPlayer
var skel: Skeleton3D
var head_bone := -1
var look_target: Variant = null      # Vector3 world point
var talking := false
var pose := "idle"                   # idle | sit | sit_table | lie | walk
var status := "aboard"               # aboard | dead | locked | stove
var _route: Array[Vector3] = []
var _final_rot := 0.0
var _final_pose := "idle"
var _head_q := Quaternion.IDENTITY
var _t := randf() * 10.0


func setup(person_id: String, first_person := false) -> void:
	id = person_id
	name = person_id
	model = load("res://assets/people/%s.glb" % person_id).instantiate()
	add_child(model)
	anim = model.find_child("AnimationPlayer", true, false)
	for s in model.find_children("*", "Skeleton3D", true, false):
		skel = s
	head_bone = skel.find_bone("head")
	anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	for a in ["idle", "walk", "sit", "sit_talk", "sit_table", "talk"]:
		var res := anim.get_animation(a)
		if res:
			res.loop_mode = Animation.LOOP_LINEAR
	anim.play("idle")
	if first_person:  # your own body: no head, hair or hat in front of the camera
		for n in ["Head", "Hair", "Beard", "Cap", "Collar"]:
			var m := model.find_child(n, true, false)
			if m:
				(m as Node3D).visible = false
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func place(spot: Dictionary, p := "idle") -> void:
	position = spot["pos"]
	rotation.y = spot["rot"]
	set_pose(p)


func set_pose(p: String) -> void:
	pose = p
	if p == "lie":   # flat on the back in a berth: the node sits at the feet, the head toward the window
		model.rotation = Vector3(-PI / 2.0, 0, 0)
		model.position = Vector3(0, 0.62, 0)
		anim.play("idle", 0.0)
		return
	model.rotation = Vector3.ZERO
	model.position = Vector3.ZERO
	var a := p
	if talking and p in ["sit", "sit_table"]:
		a = "sit_talk"
	elif talking and p == "idle":
		a = "talk"
	if anim.current_animation != a:
		anim.play(a, 0.35)


func set_talking(on: bool) -> void:
	talking = on
	set_pose(pose)


func walk_to(spot: Dictionary, end_pose := "idle") -> void:
	_route = Layout.route(position, spot["pos"])
	_final_rot = spot["rot"]
	_final_pose = end_pose
	pose = "walk"
	anim.play("walk", 0.3)


func is_walking() -> bool:
	return not _route.is_empty()


func head_position() -> Vector3:
	if skel and head_bone >= 0:
		return skel.global_transform * skel.get_bone_global_pose(head_bone).origin + Vector3(0, 0.12, 0)
	return global_position + Vector3(0, 1.6, 0)


func _process(delta: float) -> void:
	_t += delta
	if not _route.is_empty():
		var target: Vector3 = _route[0]
		var d := target - position
		d.y = 0
		if d.length() < 0.06:
			_route.pop_front()
			if _route.is_empty():
				rotation.y = _final_rot
				set_pose(_final_pose)
				arrived.emit()
		else:
			var step := minf(d.length(), WALK_SPEED * delta)
			position += d.normalized() * step
			var want := atan2(d.x, d.z)
			rotation.y = lerp_angle(rotation.y, want, minf(1.0, delta * 8.0))
	anim.advance(delta)
	_apply_look(delta)


func _apply_look(delta: float) -> void:
	if skel == null or head_bone < 0:
		return
	var rest := skel.get_bone_pose_rotation(head_bone)
	var want := Quaternion.IDENTITY
	if look_target != null and pose != "lie" and status != "dead":
		var hp := head_position()
		var local := (global_transform.basis.inverse() * ((look_target as Vector3) - hp))
		var yaw := clampf(atan2(local.x, local.z), -1.1, 1.1)
		var pitch := clampf(-atan2(local.y, Vector2(local.x, local.z).length()), -0.5, 0.45)
		want = Quaternion(Vector3.UP, yaw) * Quaternion(Vector3.RIGHT, pitch)
	if talking:
		want = want * Quaternion(Vector3.RIGHT, sin(_t * 5.0) * 0.04)
	_head_q = _head_q.slerp(want, minf(1.0, delta * 5.0))
	# the head bone's local frame has X along the character's left-right axis (see tools/people.py), so convert the
	# character-space rotation into it before applying it on top of the animated pose
	var bone_rest := skel.get_bone_global_rest(head_bone).basis.get_rotation_quaternion()
	var q := bone_rest.inverse() * _head_q * bone_rest
	skel.set_bone_pose_rotation(head_bone, rest * q)
