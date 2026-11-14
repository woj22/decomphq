class_name CharacterBuilder
extends RefCounted
## Builds a low-poly character as ONE skinned mesh (one draw call) on a 17-bone skeleton.
## Anatomy comes from the species' body table; clothing, headwear and props from the look.
## Bones never rotate at rest, so every part is authored in its bone's local frame
## (origin = joint, +Y up, -Z = the character's front, +X = the character's right).

enum { ROOT, HIPS, SKIRT, TORSO, HEAD, ARM_L, FORE_L, ARM_R, FORE_R,
	THIGH_L, SHIN_L, THIGH_R, SHIN_R, CLOAK, TAIL1, TAIL2, PROP, BONE_COUNT }
const BONE_NAMES := ["root", "hips", "skirt", "torso", "head", "arm_l", "fore_l", "arm_r", "fore_r",
	"thigh_l", "shin_l", "thigh_r", "shin_r", "cloak", "tail1", "tail2", "prop"]

const LONG_GARMENTS := ["toga", "robe", "stola"]
const LEATHER := "6b4a2e"
const SANDAL := "5c3d24"
const GOLD := "d9a63e"
const SILVER := "c7cdd8"
const IRON := "5f6266"
const WOOD := "6b4a2e"
const PARCHMENT := "e6d9b8"
const HORN := "d8caa4"
const MARBLE := "e9e4da"

var look: Dictionary
var d: Dictionary          # derived dimensions
var rest: Array = []       # global rest origin per bone
var parents: Array = []
var marble := false        # statues: every colour becomes marble
var mb := MeshBuilder.new()


static func build_rig(look_in: Dictionary) -> CharacterRig:
	var b := CharacterBuilder.new()
	b.look = look_in
	b._compute()
	b._build_geometry()
	var rig := CharacterRig.new()
	rig.setup(b, b.mb.build())
	return rig


## A static rest-pose mesh (statues, previews). Marble statues ignore every colour.
static func build_static_mesh(look_in: Dictionary, as_marble := false) -> ArrayMesh:
	var b := CharacterBuilder.new()
	b.look = look_in
	b.marble = as_marble
	b._compute()
	b._build_geometry()
	return b.mb.build()


func height() -> float:
	return d["leg"] + d["torso"] + d["neck"] + d["head_h"]


# ---------------------------------------------------------------- dimensions & skeleton

func _compute() -> void:
	var sp_id: String = look.get("species", "human")
	var body: Dictionary = Cast.species.get(sp_id, Cast.species["human"])["body"]
	var H: float = float(look.get("height", 1.0))
	var W: float = float(look.get("build", 1.0))
	var fem: bool = look.get("sex", "m") == "f"
	if fem and sp_id in ["human", "veyari"]:
		H *= 0.96
	d = {}
	d["sp"] = sp_id
	d["leg"] = body["leg"] * H
	d["thigh"] = d["leg"] * 0.5
	d["shin"] = d["leg"] * 0.5
	d["torso"] = body["torso"] * H
	d["neck"] = body["neck"] * H
	d["head_h"] = body["head_h"] * H
	d["head_w"] = body["head_w"] * H
	d["head_d"] = body["head_d"] * H
	d["shoulder"] = body["shoulder"] * W * (0.9 if fem else 1.0)
	d["hip"] = body["hip"] * W * (1.07 if fem else 1.0)
	d["arm"] = body["arm"] * H
	d["upper"] = d["arm"] * 0.46
	d["fore"] = d["arm"] * 0.54
	d["limb"] = body["limb"] * W * (0.92 if fem else 1.0)
	d["depth"] = body["depth"] * W
	d["foot_h"] = 0.06 * H
	d["hand"] = d["limb"] * 0.9 + 0.02

	var leg: float = d["leg"]
	var torso: float = d["torso"]
	var sh_x: float = d["shoulder"] * 0.5 - d["limb"] * 0.35
	var sh_y: float = leg + torso - 0.07
	var hip_x: float = d["hip"] * 0.27
	rest.resize(BONE_COUNT)
	parents.resize(BONE_COUNT)
	_bone(ROOT, -1, Vector3.ZERO)
	_bone(HIPS, ROOT, Vector3(0, leg, 0))
	_bone(SKIRT, HIPS, Vector3(0, leg, 0))
	_bone(TORSO, HIPS, Vector3(0, leg + 0.04, 0))
	_bone(HEAD, TORSO, Vector3(0, leg + torso + d["neck"], 0))
	_bone(ARM_L, TORSO, Vector3(-sh_x, sh_y, 0))
	_bone(FORE_L, ARM_L, Vector3(-sh_x, sh_y - d["upper"], 0))
	_bone(ARM_R, TORSO, Vector3(sh_x, sh_y, 0))
	_bone(FORE_R, ARM_R, Vector3(sh_x, sh_y - d["upper"], 0))
	_bone(THIGH_L, HIPS, Vector3(-hip_x, leg, 0))
	_bone(SHIN_L, THIGH_L, Vector3(-hip_x, leg - d["thigh"], 0))
	_bone(THIGH_R, HIPS, Vector3(hip_x, leg, 0))
	_bone(SHIN_R, THIGH_R, Vector3(hip_x, leg - d["thigh"], 0))
	_bone(CLOAK, TORSO, Vector3(0, leg + torso - 0.03, d["depth"] * 0.55 + 0.02))
	_bone(TAIL1, HIPS, Vector3(0, leg - 0.06, d["depth"] * 0.4))
	_bone(TAIL2, TAIL1, Vector3(0, leg - 0.06 - 0.2, d["depth"] * 0.4 + 0.5))
	_bone(PROP, FORE_R, Vector3(sh_x, sh_y - d["upper"] - d["fore"] + d["hand"] * 0.5, 0))


func _bone(i: int, parent: int, origin: Vector3) -> void:
	rest[i] = origin
	parents[i] = parent


func make_skeleton() -> Skeleton3D:
	var sk := Skeleton3D.new()
	for i in BONE_COUNT:
		sk.add_bone(BONE_NAMES[i])
	for i in BONE_COUNT:
		var p: int = parents[i]
		if p >= 0:
			sk.set_bone_parent(i, p)
		var local: Vector3 = rest[i] - (rest[p] if p >= 0 else Vector3.ZERO)
		sk.set_bone_rest(i, Transform3D(Basis.IDENTITY, local))
	sk.reset_bone_poses()
	return sk


# ---------------------------------------------------------------- helpers

func _on(bone: int) -> void:
	mb.bone = bone
	mb.xf = Transform3D(Basis.IDENTITY, rest[bone])


func col(hex) -> Color:
	if marble:
		return Color(MARBLE)
	if hex == null or str(hex) == "":
		return Color(0.5, 0.5, 0.5)
	return Color(str(hex))


func lk(key: String) -> Color:
	return col(look.get(key))


func _has(key: String) -> bool:
	var v = look.get(key)
	return v != null and str(v) != "" and str(v) != "none"


# ---------------------------------------------------------------- geometry

func _build_geometry() -> void:
	var outfit: String = str(look.get("outfit", "tunic"))
	var skin := lk("skin")
	var long := outfit in LONG_GARMENTS
	var armoured := outfit in ["armour", "scale"]
	var primary := lk("primary")
	var secondary := lk("secondary")
	var trim := lk("trim")
	var under := secondary if outfit == "toga" else primary   # colour of the torso garment
	var metal := primary if armoured else Color()
	var limb: float = d["limb"]
	var depth: float = d["depth"]
	var hip: float = d["hip"]

	# --- legs
	for side in [-1, 1]:
		var thigh_b := THIGH_L if side < 0 else THIGH_R
		var shin_b := SHIN_L if side < 0 else SHIN_R
		var thigh_col := primary if long else skin
		var shin_col := primary if long else skin
		if armoured:
			thigh_col = skin
			shin_col = col(LEATHER) if d["sp"] != "kharad" else skin
		_on(thigh_b)
		mb.taper(Vector3(0, -d["thigh"], 0), Vector2(limb * 0.85, limb * 0.85), Vector2(limb * 1.08, limb * 1.12), d["thigh"], thigh_col)
		_on(shin_b)
		var shin_len: float = d["shin"] - d["foot_h"]
		mb.taper(Vector3(0, -shin_len, 0), Vector2(limb * 0.7, limb * 0.72), Vector2(limb * 0.86, limb * 0.88), shin_len, shin_col)
		if armoured and d["sp"] != "kharad":
			mb.taper(Vector3(0, -shin_len * 0.9, -0.01), Vector2(limb * 0.8, limb * 0.8), Vector2(limb * 0.92, limb * 0.9), shin_len * 0.75, metal.darkened(0.1))
		var fy: float = -d["shin"] + d["foot_h"] * 0.5
		if d["sp"] == "kharad":
			mb.box(Vector3(0, fy, -limb * 0.4), Vector3(limb * 1.1, d["foot_h"], limb * 1.9), skin.darkened(0.15))
			for c in [-1, 0, 1]:
				mb.cone(Vector3(c * limb * 0.32, fy - d["foot_h"] * 0.3, -limb * 1.3), 0.022, 0.07, 4, col(HORN), Basis(Vector3.RIGHT, -PI / 2))
		else:
			mb.box(Vector3(0, fy, -limb * 0.35), Vector3(limb * 0.9, d["foot_h"], limb * 1.75), col(SANDAL))

	# --- pelvis
	_on(HIPS)
	mb.box(Vector3(0, -0.03, 0), Vector3(hip * 1.02, 0.2, depth * 0.95), under if not armoured else secondary)

	# --- skirt (own bone: it folds onto the lap when seated)
	_on(SKIRT)
	d["skirt_len"] = d["thigh"] * 0.8
	if long:
		d["skirt_len"] = d["leg"] * 0.9
		var ln: float = d["leg"] * 0.9
		mb.taper(Vector3(0, -ln, 0), Vector2(hip * 1.6, depth * 1.55), Vector2(hip * 1.06, depth * 1.02), ln + 0.04, primary)
		mb.taper(Vector3(0, -ln - 0.005, 0), Vector2(hip * 1.64, depth * 1.6), Vector2(hip * 1.6, depth * 1.56), 0.06, trim if outfit != "toga" else secondary)
	elif armoured:
		var ln2: float = d["thigh"] * 0.75
		mb.taper(Vector3(0, -ln2, 0), Vector2(hip * 1.3, depth * 1.3), Vector2(hip * 1.04, depth * 1.0), ln2 + 0.04, secondary)
		for i in 8:
			var a := TAU * (i + 0.5) / 8.0
			var p := Vector3(cos(a) * hip * 0.6, -ln2 * 0.62, sin(a) * depth * 0.62)
			mb.box(p, Vector3(0.07, ln2 * 0.75, 0.03), col(LEATHER), Basis(Vector3.UP, -a + PI / 2))
	else:
		var ln3: float = d["thigh"] * 0.8
		mb.taper(Vector3(0, -ln3, 0), Vector2(hip * 1.36, depth * 1.36), Vector2(hip * 1.05, depth * 1.0), ln3 + 0.04, primary)
		mb.taper(Vector3(0, -ln3 - 0.005, 0), Vector2(hip * 1.4, depth * 1.4), Vector2(hip * 1.37, depth * 1.37), 0.045, trim)

	# --- torso
	_on(TORSO)
	var th: float = d["torso"] - 0.04
	var torso_col := metal if armoured else under
	mb.taper(Vector3(0, -0.06, 0), Vector2(hip * 0.96, depth * 0.95), Vector2(d["shoulder"], depth * 1.05), th + 0.06, torso_col)
	if armoured:
		var band := metal.darkened(0.18) if outfit == "armour" else metal.darkened(0.3)
		for i in 3:
			var y := th * (0.12 + 0.2 * i)
			var wv := lerpf(hip * 0.98, d["shoulder"], (y + 0.06) / (th + 0.06))
			mb.taper(Vector3(0, y, 0), Vector2(wv + 0.02, depth * 1.08), Vector2(wv + 0.03, depth * 1.09), 0.045, band)
		mb.box(Vector3(0, th * 0.62, -depth * 0.54), Vector3(0.09, 0.09, 0.02), trim)
	else:
		mb.box(Vector3(0, 0.03, 0), Vector3(hip * 1.02, 0.05, depth * 1.02), trim if outfit != "stola" else secondary)
	match outfit:
		"toga":
			var sash_b := Basis(Vector3.BACK, deg_to_rad(-38))
			mb.box(Vector3(-d["shoulder"] * 0.08, th * 0.5, 0), Vector3(0.2, th * 1.45, depth * 1.12), primary, sash_b)
			mb.box(Vector3(-d["shoulder"] * 0.08 + 0.03, th * 0.5, 0), Vector3(0.035, th * 1.45, depth * 1.14), secondary if outfit == "toga" and secondary != primary else trim, sash_b)
		"robe":
			mb.box(Vector3(0, th * 0.45, -depth * 0.52), Vector3(0.07, th * 1.0, 0.012), secondary)
		"stola":
			mb.taper(Vector3(0, th * 0.62, 0), Vector2(d["shoulder"] * 0.98, depth * 1.12), Vector2(d["shoulder"] * 1.06, depth * 1.14), th * 0.42, secondary)
		"tunic":
			for sx in [-1, 1]:
				mb.box(Vector3(sx * d["shoulder"] * 0.2, th * 0.5, -depth * 0.52), Vector3(0.04, th * 0.95, 0.012), secondary)
	if look.get("cloak") != null:
		var cloak := lk("cloak")
		mb.taper(Vector3(0, th - 0.06, 0), Vector2(d["shoulder"] * 1.04, depth * 1.12), Vector2(d["shoulder"] * 0.9, depth * 1.0), 0.09, cloak)
		for sx in [-1, 1]:
			mb.box(Vector3(sx * d["shoulder"] * 0.36, th - 0.03, -depth * 0.55), Vector3(0.05, 0.05, 0.03), col(GOLD))
	# neck
	mb.box(Vector3(0, th + d["neck"] * 0.5, 0), Vector3(limb * 0.95, d["neck"] + 0.06, limb * 0.95), skin)

	# --- arms
	for side in [-1, 1]:
		var arm_b := ARM_L if side < 0 else ARM_R
		var fore_b := FORE_L if side < 0 else FORE_R
		var upper_col := skin
		var fore_col := skin
		var sleeve := Color()
		var long_sleeve := false
		match outfit:
			"robe", "stola":
				upper_col = primary
				fore_col = primary
				long_sleeve = true
			"toga":
				if side < 0:
					upper_col = primary
					fore_col = primary
					long_sleeve = true
				else:
					sleeve = under
			"tunic":
				sleeve = primary
			_:
				sleeve = secondary
		_on(arm_b)
		mb.taper(Vector3(0, -d["upper"], 0), Vector2(limb * 0.78, limb * 0.8), Vector2(limb * 0.95, limb * 0.98), d["upper"] + 0.02, upper_col)
		if sleeve.a > 0.0 and sleeve != Color():
			mb.taper(Vector3(0, -d["upper"] * 0.5, 0), Vector2(limb * 1.0, limb * 1.0), Vector2(limb * 1.08, limb * 1.08), d["upper"] * 0.5 + 0.03, sleeve)
		if armoured:
			mb.taper(Vector3(side * 0.01, -0.07, 0), Vector2(limb * 1.4, limb * 1.4), Vector2(limb * 1.1, limb * 1.2), 0.13, metal.darkened(0.08))
		_on(fore_b)
		var fl: float = d["fore"] - d["hand"]
		mb.taper(Vector3(0, -fl, 0), Vector2(limb * 0.68, limb * 0.7), Vector2(limb * 0.8, limb * 0.82), fl, fore_col)
		if long_sleeve:
			mb.taper(Vector3(0, -fl, 0), Vector2(limb * 1.08, limb * 1.08), Vector2(limb * 0.86, limb * 0.88), fl * 0.45, fore_col.darkened(0.06))
		elif armoured:
			mb.taper(Vector3(0, -fl * 0.95, 0), Vector2(limb * 0.82, limb * 0.84), Vector2(limb * 0.9, limb * 0.9), fl * 0.6, col(LEATHER))
		var hand_y: float = -d["fore"] + d["hand"] * 0.5
		mb.box(Vector3(0, hand_y, -0.01), Vector3(limb * 0.72, d["hand"], limb * 0.62), skin)
		if d["sp"] == "kharad":
			for c in [-1, 1]:
				mb.cone(Vector3(c * limb * 0.2, hand_y - d["hand"] * 0.45, -0.02), 0.016, 0.05, 4, col(HORN), Basis(Vector3.RIGHT, PI))

	# --- cloak
	if look.get("cloak") != null:
		_on(CLOAK)
		var cl: float = d["torso"] + d["leg"] * 0.72
		mb.taper(Vector3(0, -cl, 0.04), Vector2(d["shoulder"] * 1.35, 0.045), Vector2(d["shoulder"] * 0.98, 0.055), cl, lk("cloak"))

	# --- tail
	if d["sp"] == "kharad":
		var tail_col := skin.darkened(0.05)
		_on(TAIL1)
		mb.taper(Vector3.ZERO, Vector2(limb * 1.4, limb * 1.5), Vector2(limb * 1.0, limb * 1.05), 0.54, tail_col, Vector2.ZERO, Basis(Vector3.RIGHT, deg_to_rad(112)))
		_on(TAIL2)
		mb.taper(Vector3.ZERO, Vector2(limb * 1.0, limb * 1.05), Vector2(0.03, 0.03), 0.62, tail_col, Vector2.ZERO, Basis(Vector3.RIGHT, deg_to_rad(100)))
		for i in 4:
			mb.cone(Vector3(0, 0.02 - i * 0.03, 0.1 + i * 0.13), 0.03, 0.06, 4, skin.darkened(0.3), Basis(Vector3.RIGHT, deg_to_rad(20)))

	# --- head
	_on(HEAD)
	match d["sp"]:
		"veyari": _head_veyari(skin)
		"kharad": _head_kharad(skin)
		"othari": _head_othari(skin)
		_: _head_human(skin)
	_headwear()

	# --- props
	_props()


func _eyes(y: float, sep: float, size: Vector2, front: float) -> void:
	var ec := col(look.get("eye", "222222"))
	for sx in [-1, 1]:
		mb.box(Vector3(sx * sep, y, front - 0.004), Vector3(size.x, size.y, 0.012), ec)


func _hair_cap(hw: float, hd: float, hh: float, hair: Color, from_y: float) -> void:
	mb.taper(Vector3(0, hh * from_y, 0.005), Vector2(hw * 1.08, hd * 1.08), Vector2(hw * 0.86, hd * 0.9), hh * (1.0 - from_y) + 0.035, hair)
	mb.taper(Vector3(0, hh * 0.25, hd * 0.24), Vector2(hw * 1.04, hd * 0.6), Vector2(hw * 1.08, hd * 0.64), hh * (from_y - 0.25) + 0.01, hair)


func _head_human(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var hair := lk("hair")
	mb.taper(Vector3.ZERO, Vector2(hw * 0.78, hd * 0.84), Vector2(hw, hd), hh * 0.62, skin)
	mb.taper(Vector3(0, hh * 0.62, 0), Vector2(hw, hd), Vector2(hw * 0.8, hd * 0.84), hh * 0.38, skin)
	mb.box(Vector3(0, hh * 0.42, -hd * 0.5 - 0.014), Vector3(0.032, 0.065, 0.03), skin.darkened(0.08))
	for sx in [-1, 1]:
		mb.box(Vector3(sx * hw * 0.52, hh * 0.5, 0.0), Vector3(0.03, 0.06, 0.05), skin.darkened(0.05))
		mb.box(Vector3(sx * hw * 0.22, hh * 0.66, -hd * 0.5 - 0.006), Vector3(0.055, 0.014, 0.012), hair.darkened(0.1))
	_eyes(hh * 0.56, hw * 0.22, Vector2(0.034, 0.024), -hd * 0.5)
	var helmet := str(look.get("headwear", "")) == "helmet"
	var style := str(look.get("hair_style", "short"))
	if not helmet:
		match style:
			"short": _hair_cap(hw, hd, hh, hair, 0.74)
			"cropped": _hair_cap(hw * 0.98, hd * 0.98, hh, hair, 0.8)
			"curly":
				_hair_cap(hw, hd, hh, hair, 0.72)
				for i in 6:
					var a := TAU * i / 6.0
					mb.box(Vector3(cos(a) * hw * 0.3, hh + 0.02, sin(a) * hd * 0.3), Vector3(0.06, 0.05, 0.06), hair.darkened(0.08))
			"long":
				_hair_cap(hw, hd, hh, hair, 0.72)
				mb.box(Vector3(0, hh * 0.32, hd * 0.44), Vector3(hw * 1.05, hh * 0.95, 0.07), hair)
			"bun":
				_hair_cap(hw, hd, hh, hair, 0.72)
				mb.sphere(Vector3(0, hh * 0.8, hd * 0.55), 0.07, hair, 6, 4)
			"braids":
				_hair_cap(hw, hd, hh, hair, 0.72)
				for sx in [-1, 1]:
					mb.box(Vector3(sx * hw * 0.4, hh * 0.1, hd * 0.3), Vector3(0.05, hh * 0.9, 0.05), hair)
	var beard := str(look.get("beard", "none"))
	if beard == "short":
		mb.box(Vector3(0, hh * 0.17, -hd * 0.16), Vector3(hw * 0.86, hh * 0.36, hd * 0.74), hair)
		mb.box(Vector3(0, hh * 0.36, -hd * 0.5 - 0.006), Vector3(hw * 0.45, 0.03, 0.02), hair)
	elif beard == "full":
		mb.taper(Vector3(0, -0.07, -hd * 0.14), Vector2(hw * 0.7, hd * 0.6), Vector2(hw * 0.94, hd * 0.8), hh * 0.46 + 0.07, hair)
		mb.box(Vector3(0, hh * 0.36, -hd * 0.5 - 0.01), Vector3(hw * 0.5, 0.035, 0.03), hair)
	else:
		mb.box(Vector3(0, hh * 0.26, -hd * 0.5 - 0.003), Vector3(0.06, 0.012, 0.01), skin.darkened(0.3))


func _head_veyari(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var hair := lk("hair")
	mb.taper(Vector3.ZERO, Vector2(hw * 0.64, hd * 0.72), Vector2(hw, hd * 0.95), hh * 0.58, skin)
	mb.taper(Vector3(0, hh * 0.58, 0), Vector2(hw, hd * 0.95), Vector2(hw * 0.62, hd * 0.92), hh * 0.42, skin, Vector2(0, hd * 0.38))
	for sx in [-1, 1]:
		# swept crest fins
		mb.taper(Vector3(sx * hw * 0.26, hh * 0.78, hd * 0.12), Vector2(0.028, 0.14), Vector2(0.012, 0.06), 0.27, hair, Vector2.ZERO, Basis(Vector3.RIGHT, deg_to_rad(58)))
		# cheek ridges
		mb.box(Vector3(sx * hw * 0.34, hh * 0.38, -hd * 0.44), Vector3(0.018, 0.07, 0.03), skin.darkened(0.18))
		# long pointed ears
		mb.taper(Vector3(sx * hw * 0.5, hh * 0.52, 0.02), Vector2(0.02, 0.05), Vector2(0.008, 0.01), 0.12, skin.darkened(0.06), Vector2(sx * 0.03, 0.04))
	mb.taper(Vector3(0, hh * 0.8, hd * 0.1), Vector2(0.03, 0.18), Vector2(0.012, 0.08), 0.22, hair.darkened(0.12), Vector2.ZERO, Basis(Vector3.RIGHT, deg_to_rad(62)))
	mb.box(Vector3(0, hh * 0.4, -hd * 0.47 - 0.006), Vector3(0.022, 0.06, 0.02), skin.darkened(0.06))
	_eyes(hh * 0.58, hw * 0.24, Vector2(0.05, 0.03), -hd * 0.47)
	mb.box(Vector3(0, hh * 0.24, -hd * 0.36 - 0.003), Vector3(0.045, 0.01, 0.01), skin.darkened(0.35))
	if str(look.get("hair_style", "")) == "long":
		mb.taper(Vector3(0, -0.14, hd * 0.42), Vector2(hw * 0.95, 0.06), Vector2(hw * 0.8, 0.07), hh * 0.95, hair)


func _head_kharad(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var dark := skin.darkened(0.25)
	mb.taper(Vector3(0, 0, 0.02), Vector2(hw * 0.9, hd * 0.86), Vector2(hw, hd * 0.92), hh * 0.78, skin)
	mb.taper(Vector3(0, hh * 0.78, 0.02), Vector2(hw, hd * 0.92), Vector2(hw * 0.7, hd * 0.75), hh * 0.22, skin)
	# snout
	mb.taper(Vector3(0, hh * 0.14 + hh * 0.26, -hd * 0.38), Vector2(hw * 0.8, hh * 0.56), Vector2(hw * 0.58, hh * 0.4), hd * 0.62, skin.lightened(0.04), Vector2(0, -0.02), Basis(Vector3.RIGHT, -PI / 2))
	mb.box(Vector3(0, hh * 0.15, -hd * 0.7), Vector3(hw * 0.56, 0.02, hd * 0.5), dark)  # mouth line
	for sx in [-1, 1]:
		mb.box(Vector3(sx * hw * 0.13, hh * 0.44, -hd * 1.0 - 0.002), Vector3(0.02, 0.015, 0.012), dark)
	# brow ridge and eyes
	mb.box(Vector3(0, hh * 0.7, -hd * 0.46), Vector3(hw * 1.06, 0.06, 0.08), dark)
	_eyes(hh * 0.6, hw * 0.33, Vector2(0.045, 0.026), -hd * 0.42)
	# horn crown
	var horn := col(HORN)
	for i in 3:
		for sx in [-1, 1]:
			var p := Vector3(sx * hw * (0.36 - i * 0.04), hh * (0.86 - i * 0.05), -hd * 0.1 + i * hd * 0.24)
			mb.cone(p, 0.04 - i * 0.006, 0.17 - i * 0.03, 5, horn, Basis(Vector3.RIGHT, deg_to_rad(62)) * Basis(Vector3.BACK, deg_to_rad(-18 * sx)))
	# scale ridge down the back of the skull
	for i in 4:
		mb.box(Vector3(0, hh * (0.95 - i * 0.2), hd * 0.42), Vector3(0.05, 0.05, 0.05), dark, Basis(Vector3.RIGHT, PI / 4))


func _head_othari(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var hair := lk("hair")
	mb.taper(Vector3.ZERO, Vector2(hw, hd * 0.92), Vector2(hw * 0.8, hd * 0.86), hh, skin)
	mb.box(Vector3(0, hh * 0.68, -hd * 0.46), Vector3(hw * 1.08, 0.075, 0.08), skin.darkened(0.2))
	mb.box(Vector3(0, hh * 0.44, -hd * 0.47 - 0.012), Vector3(0.07, 0.06, 0.04), skin.darkened(0.1))
	_eyes(hh * 0.56, hw * 0.22, Vector2(0.03, 0.02), -hd * 0.46)
	for sx in [-1, 1]:
		mb.box(Vector3(sx * hw * 0.5, hh * 0.5, 0.0), Vector3(0.035, 0.05, 0.05), skin.darkened(0.08))
	if str(look.get("beard", "plates")) == "plates":
		for i in 3:
			var x := (i - 1) * hw * 0.27
			var ln := 0.2 if i == 1 else 0.15
			mb.box(Vector3(x, hh * 0.22 - ln * 0.4, -hd * 0.42), Vector3(hw * 0.24, ln + hh * 0.2, 0.06), hair)
			mb.box(Vector3(x, hh * 0.22 - ln * 0.85, -hd * 0.42), Vector3(hw * 0.26, 0.03, 0.07), col(GOLD) if look.get("group", "") == "kings" else col(IRON).lightened(0.2))
	var style := str(look.get("hair_style", "braids"))
	if str(look.get("headwear", "")) != "helmet" and style != "bald":
		_hair_cap(hw, hd, hh, hair, 0.8)
		if style == "braids":
			for sx in [-1, 1]:
				mb.box(Vector3(sx * hw * 0.3, hh * 0.15, hd * 0.44), Vector3(0.06, hh * 0.95, 0.06), hair)


func _headwear() -> void:
	var hw_t := str(look.get("headwear", "none"))
	if hw_t == "none" or hw_t == "":
		return
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var r := maxf(hw, hd) * 0.56
	var yb := hh * 0.8
	if d["sp"] == "veyari":
		yb = hh * 0.68
	if d["sp"] == "kharad":
		yb = hh * 0.74
	match hw_t:
		"radiate":
			var g := col(GOLD)
			mb.cyl(Vector3(0, yb, 0.0), r, r * 0.97, 0.05, 10, g, false, false)
			for i in 9:
				var a := lerpf(PI * 0.15, PI * 0.85, i / 8.0)
				var p := Vector3(cos(a) * r, yb + 0.03, -sin(a) * r)
				mb.box(p + Vector3(0, 0.06, 0), Vector3(0.025, 0.13, 0.012), g, Basis(Vector3.UP, a - PI / 2) * Basis(Vector3.RIGHT, -0.25))
		"crown_gold", "crown_silver", "crown_iron":
			var c := col(GOLD if hw_t == "crown_gold" else (SILVER if hw_t == "crown_silver" else IRON))
			mb.cyl(Vector3(0, yb, 0), r * 1.02, r * 1.04, 0.075, 8, c, false, false)
			for i in 6:
				var a := TAU * i / 6.0 + PI / 2
				mb.cone(Vector3(cos(a) * r, yb + 0.07, -sin(a) * r), 0.03, 0.08, 4, c)
			mb.box(Vector3(0, yb + 0.04, -r - 0.01), Vector3(0.04, 0.04, 0.02), lk("secondary") if hw_t != "crown_iron" else col("9b2226"))
		"diadem", "diadem_silver":
			var c2 := col(GOLD if hw_t == "diadem" else SILVER)
			mb.cyl(Vector3(0, yb, 0), r * 0.98, r * 0.98, 0.032, 10, c2, false, false)
			mb.box(Vector3(0, yb + 0.03, -r * 0.98 - 0.008), Vector3(0.045, 0.06, 0.02), c2)
			mb.box(Vector3(0, yb + 0.03, -r * 0.98 - 0.02), Vector3(0.025, 0.03, 0.012), lk("secondary"))
		"circlet", "circlet_gold":
			mb.cyl(Vector3(0, yb, 0), r * 0.98, r * 0.98, 0.025, 10, col(GOLD if hw_t == "circlet_gold" else SILVER), false, false)
		"laurel":
			var leaf := col("4f7a3a")
			for i in 12:
				var a := TAU * i / 12.0
				mb.box(Vector3(cos(a) * r, yb + 0.02, -sin(a) * r), Vector3(0.05, 0.022, 0.03), leaf, Basis(Vector3.UP, a) * Basis(Vector3.BACK, 0.5))
		"helmet":
			var m := lk("primary") if str(look.get("outfit", "")) in ["armour", "scale"] else col("aeb4bc")
			var crest := lk("secondary")
			mb.cyl(Vector3(0, hh * 0.52, 0.01), r * 1.12, r * 0.6, hh * 0.5, 8, m, true, false)
			mb.box(Vector3(0, hh * 1.06, 0.01), Vector3(0.05, 0.12, hd * 1.05), crest)
			mb.box(Vector3(0, hh * 0.42, hd * 0.52), Vector3(hw * 1.1, 0.12, 0.05), m.darkened(0.1))
			mb.box(Vector3(0, hh * 0.72, -hd * 0.55), Vector3(hw * 1.0, 0.035, 0.04), col(GOLD))
			for sx in [-1, 1]:
				mb.box(Vector3(sx * hw * 0.52, hh * 0.38, -hd * 0.1), Vector3(0.025, hh * 0.42, hd * 0.45), m.darkened(0.05))


func _props() -> void:
	var p := str(look.get("prop", "none"))
	_on(PROP)
	match p:
		"staff", "staff_gold":
			mb.cyl(Vector3(0, -0.85, 0), 0.022, 0.022, 1.75, 6, col(WOOD) if p == "staff" else col(GOLD).darkened(0.15))
			mb.sphere(Vector3(0, 0.95, 0), 0.05, col(GOLD), 6, 4)
			if p == "staff_gold":
				for i in 8:
					var a := TAU * i / 8.0
					mb.box(Vector3(cos(a) * 0.08, 0.98, -sin(a) * 0.08), Vector3(0.02, 0.02, 0.07), col(GOLD), Basis(Vector3.UP, a))
		"spear":
			mb.cyl(Vector3(0, -0.85, 0), 0.02, 0.02, 2.15, 5, col(WOOD))
			mb.cone(Vector3(0, 1.3, 0), 0.04, 0.2, 4, col(SILVER))
		"scroll":
			mb.cyl(Vector3(0.12, 0, -0.02), 0.035, 0.035, 0.24, 6, col(PARCHMENT), true, true, Basis(Vector3.BACK, PI / 2))
			for sx in [-0.135, 0.135]:
				mb.box(Vector3(sx, 0, -0.02), Vector3(0.02, 0.06, 0.06), col(WOOD))
		"tablet":
			mb.box(Vector3(0, -0.02, -0.07), Vector3(0.025, 0.24, 0.17), col(WOOD))
			mb.box(Vector3(0.014, -0.02, -0.07), Vector3(0.006, 0.2, 0.13), col("3a2a1e"))
		"amphora":
			var tc := col("b3643c")
			mb.sphere(Vector3(0, -0.2, -0.05), 0.12, tc, 7, 5, Vector3(1, 1.35, 1))
			mb.cyl(Vector3(0, -0.05, -0.05), 0.04, 0.05, 0.14, 6, tc)
			mb.sphere(Vector3(0, -0.38, -0.05), 0.04, tc, 5, 3)
	if p == "sword":
		_on(HIPS)
		var sb := Basis(Vector3.BACK, deg_to_rad(-12)) * Basis(Vector3.RIGHT, deg_to_rad(-20))
		mb.box(Vector3(-d["hip"] * 0.72, -0.22, -0.04), Vector3(0.06, 0.5, 0.03), col(LEATHER).darkened(0.2), sb)
		mb.box(Vector3(-d["hip"] * 0.68, 0.05, -0.1), Vector3(0.12, 0.03, 0.04), col(GOLD), sb)
		mb.box(Vector3(-d["hip"] * 0.67, 0.11, -0.12), Vector3(0.03, 0.1, 0.03), col(LEATHER), sb)
	if look.get("shield") != null:
		_on(FORE_L)
		var hy: float = -d["fore"] + d["hand"] * 0.5
		var sh_b := Basis(Vector3.BACK, PI / 2) * Basis.from_scale(Vector3(1.45, 1.0, 1.0))
		var sc := lk("shield")
		mb.cyl(Vector3(-d["limb"] * 0.55 - 0.05, hy + 0.12, -0.02), 0.3, 0.3, 0.05, 10, sc, true, true, sh_b)
		mb.cyl(Vector3(-d["limb"] * 0.55 - 0.055, hy + 0.12, -0.02), 0.32, 0.32, 0.03, 10, col(GOLD).darkened(0.2), false, false, sh_b)
		mb.sphere(Vector3(-d["limb"] * 0.55 - 0.1, hy + 0.12, -0.02), 0.06, col(GOLD), 6, 3)
