class_name CharacterRig
extends Node3D
## A built character: Skeleton3D + one skinned MeshInstance3D, animated procedurally.
## Callers set `speed` (m/s, drives the walk cycle), `seated`, `talking`.


var skeleton: Skeleton3D
var mesh_instance: MeshInstance3D
var look: Dictionary
var dims: Dictionary
var height := 1.8

var speed := 0.0
var seated := false
var talking := false
var gesture_bias := 0.0   # per-character variety in idle motion

var _phase := 0.0
var _t := 0.0
var _walk_w := 0.0
var _sit_w := 0.0
var _talk_w := 0.0


func setup(builder: CharacterBuilder, mesh: ArrayMesh) -> void:
	look = builder.look
	dims = builder.d
	height = builder.height()
	skeleton = builder.make_skeleton()
	skeleton.name = "Skeleton"
	add_child(skeleton)
	mesh_instance = MeshInstance3D.new()
	mesh_instance.name = "Body"
	mesh_instance.mesh = mesh
	skeleton.add_child(mesh_instance)
	mesh_instance.skeleton = NodePath("..")
	mesh_instance.skin = skeleton.create_skin_from_rest_transforms()
	gesture_bias = randf() * TAU
	_t = randf() * 10.0
	_apply()


func _process(delta: float) -> void:
	_t += delta
	var stride: float = maxf(0.6, float(dims["leg"]) * 1.5)
	_phase += delta * speed / stride * PI
	_walk_w = move_toward(_walk_w, clampf(speed / 1.2, 0.0, 1.0), delta * 5.0)
	_sit_w = move_toward(_sit_w, 1.0 if seated else 0.0, delta * 4.0)
	_talk_w = move_toward(_talk_w, 1.0 if talking else 0.0, delta * 3.0)
	_apply()


func _rot(bone: int, x: float, y := 0.0, z := 0.0) -> void:
	skeleton.set_bone_pose_rotation(bone, Quaternion.from_euler(Vector3(x, y, z)))


func _apply() -> void:
	var w := _walk_w * (1.0 - _sit_w)
	var s := _sit_w
	var p := _phase
	var breathe := sin(_t * 1.7 + gesture_bias) * 0.025
	var sway := sin(_t * 0.6 + gesture_bias) * 0.04

	var thigh_l := sin(p) * 0.55 * w
	var thigh_r := -sin(p) * 0.55 * w
	var shin_l := -0.75 * maxf(0.0, sin(p + 1.3)) * w
	var shin_r := -0.75 * maxf(0.0, sin(p + PI + 1.3)) * w
	thigh_l = lerpf(thigh_l, PI / 2, s)
	thigh_r = lerpf(thigh_r, PI / 2, s)
	shin_l = lerpf(shin_l, -PI / 2, s)
	shin_r = lerpf(shin_r, -PI / 2, s)
	_rot(CharacterBuilder.THIGH_L, thigh_l)
	_rot(CharacterBuilder.THIGH_R, thigh_r)
	_rot(CharacterBuilder.SHIN_L, shin_l)
	_rot(CharacterBuilder.SHIN_R, shin_r)
	_rot(CharacterBuilder.SKIRT, lerpf((thigh_l + thigh_r) * 0.3, PI / 2 * 0.92, s))
	var lap: float = minf(1.0, (float(dims["thigh"]) + 0.1) / float(dims.get("skirt_len", 1.0)))
	skeleton.set_bone_pose_scale(CharacterBuilder.SKIRT, Vector3(1, lerpf(1.0, lap, s), 1))

	var bob := absf(cos(p)) * 0.035 * w
	var sit_drop := -float(dims["thigh"]) * s
	skeleton.set_bone_pose_position(CharacterBuilder.ROOT, Vector3(0, bob + sit_drop, 0))
	skeleton.set_bone_pose_position(CharacterBuilder.HIPS, skeleton.get_bone_rest(CharacterBuilder.HIPS).origin)

	_rot(CharacterBuilder.TORSO, breathe * 0.4 + 0.05 * w - 0.06 * s, sin(p) * 0.06 * w)
	var head_look := sin(_t * 0.37 + gesture_bias) * 0.25 * (1.0 - w) * (1.0 - _talk_w)
	_rot(CharacterBuilder.HEAD, -0.04 * w + sin(_t * 2.3) * 0.04 * _talk_w, head_look)

	var arm_l := -sin(p) * 0.45 * w + sway * (1.0 - w)
	var arm_r := sin(p) * 0.45 * w - sway * (1.0 - w)
	var fore_l := 0.15 + 0.25 * w
	var fore_r := 0.15 + 0.25 * w
	if str(look.get("prop", "none")) in ["staff", "staff_gold", "spear"]:
		arm_r = lerpf(arm_r, 0.1, 0.8)
		fore_r = 0.55
	elif str(look.get("prop", "none")) in ["tablet", "scroll", "amphora"]:
		fore_r = lerpf(fore_r, 0.9, 0.7)
	if look.get("shield") != null:
		fore_l = 0.9
		arm_l = lerpf(arm_l, 0.15, 0.8)
	# seated: forearms rest on the lap / armrests
	arm_l = lerpf(arm_l, 0.25, s)
	arm_r = lerpf(arm_r, 0.25, s)
	fore_l = lerpf(fore_l, 1.0, s)
	fore_r = lerpf(fore_r, 1.0, s)
	# talking: the free hand gestures
	var g := _talk_w
	arm_r = lerpf(arm_r, 0.55 + sin(_t * 2.1 + gesture_bias) * 0.25, g * (0.4 if str(look.get("prop", "none")) in ["staff", "staff_gold", "spear"] else 1.0))
	fore_r = lerpf(fore_r, 1.1 + sin(_t * 3.1) * 0.2, g * 0.8)
	var spread := 0.12 + 0.05 * sin(_t * 1.3)
	_rot(CharacterBuilder.ARM_L, arm_l, 0.0, -0.06 - spread * g * 0.5)
	_rot(CharacterBuilder.ARM_R, arm_r, 0.0, 0.06 + spread * g)
	_rot(CharacterBuilder.FORE_L, fore_l)
	_rot(CharacterBuilder.FORE_R, fore_r)

	_rot(CharacterBuilder.CLOAK, -(0.18 * w + 0.03 + 0.02 * sin(_t * 1.1 + gesture_bias)) * (1.0 - s) - 0.25 * s)
	_rot(CharacterBuilder.TAIL1, 0.12 * s, sin(p) * 0.25 * w + sin(_t * 0.8 + gesture_bias) * 0.12, 0.0)
	_rot(CharacterBuilder.TAIL2, -0.15 * s, sin(p - 0.8) * 0.3 * w + sin(_t * 0.8 + gesture_bias - 0.6) * 0.16, 0.0)
