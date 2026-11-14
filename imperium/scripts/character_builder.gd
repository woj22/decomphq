class_name CharacterBuilder
extends RefCounted
## Builds a faceted low-poly character as ONE skinned mesh (one draw call) on a 17-bone skeleton.
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
const MARBLE := "e3d8c4"

const S_LIMB := 6      # sides of limb tubes
const S_BODY := 10     # sides of torso and garments

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


## A static rest-pose mesh (statues). Marble statues ignore every colour.
static func build_static_mesh(look_in: Dictionary, as_marble := false) -> ArrayMesh:
	var b := CharacterBuilder.new()
	b.look = look_in
	b.marble = as_marble
	b.mb.jitter = 0.07 if as_marble else 0.05
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
	d["fem"] = fem
	d["leg"] = body["leg"] * H
	d["thigh"] = d["leg"] * 0.5
	d["shin"] = d["leg"] * 0.5
	d["torso"] = body["torso"] * H
	d["neck"] = body["neck"] * H
	d["head_h"] = body["head_h"] * H * 0.92
	d["head_w"] = body["head_w"] * H * 0.92
	d["head_d"] = body["head_d"] * H * 0.92
	d["shoulder"] = body["shoulder"] * W * (0.88 if fem else 1.04)
	d["hip"] = body["hip"] * W * (1.08 if fem else 1.0)
	d["arm"] = body["arm"] * H
	d["upper"] = d["arm"] * 0.46
	d["fore"] = d["arm"] * 0.54
	d["limb"] = body["limb"] * W * (0.88 if fem else 1.0)
	d["depth"] = body["depth"] * W
	d["foot_h"] = 0.06 * H
	d["hand"] = d["limb"] * 0.95 + 0.02
	d["skirt_len"] = d["thigh"] * 0.8

	var leg: float = d["leg"]
	var torso: float = d["torso"]
	var sh_x: float = d["shoulder"] * 0.5 - d["limb"] * 0.3
	var sh_y: float = leg + torso - 0.08
	var hip_x: float = d["hip"] * 0.26
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
	_bone(CLOAK, TORSO, Vector3(0, leg + torso - 0.02, 0))
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
	if hex == null or str(hex) == "" or str(hex) == "x":
		return Color(0.5, 0.5, 0.5)
	return Color(str(hex))


func lk(key: String) -> Color:
	return col(look.get(key))


## Limb segment hanging down from the joint: length ln, radius r0 (bottom) .. r1 (top).
func _limb(ln: float, r0: float, r1: float, c: Color, depth_k := 1.0, y0 := 0.0) -> void:
	mb.tube(Vector3(0, y0 - ln, 0), Vector2(r0, r0 * depth_k), Vector2(r1, r1 * depth_k), ln, S_LIMB, c)


# ---------------------------------------------------------------- geometry

func _build_geometry() -> void:
	var outfit: String = str(look.get("outfit", "tunic"))
	var skin := lk("skin")
	var long := outfit in LONG_GARMENTS
	var armoured := outfit in ["armour", "scale"]
	var primary := lk("primary")
	var secondary := lk("secondary")
	var trim := lk("trim")
	var under := secondary if outfit == "toga" else primary
	var metal := primary
	var limb: float = d["limb"]
	var depth: float = d["depth"]
	var hip: float = d["hip"]
	var sh: float = d["shoulder"]
	var th: float = d["torso"] - 0.04
	var kh: bool = d["sp"] == "kharad"

	# --- legs
	for side in [-1, 1]:
		var thigh_b := THIGH_L if side < 0 else THIGH_R
		var shin_b := SHIN_L if side < 0 else SHIN_R
		var thigh_col := primary if long else skin
		var shin_col := primary if long else skin
		if armoured:
			thigh_col = skin
			shin_col = skin
		_on(thigh_b)
		_limb(d["thigh"] + 0.02, limb * 0.4, limb * 0.56, thigh_col)
		_on(shin_b)
		var shin_len: float = d["shin"] - d["foot_h"]
		_limb(shin_len, limb * 0.33, limb * 0.45, shin_col)
		if armoured and not kh:
			mb.tube(Vector3(0, -shin_len * 0.92, -0.01), Vector2(limb * 0.4, limb * 0.42), Vector2(limb * 0.48, limb * 0.5), shin_len * 0.7, S_LIMB, metal.darkened(0.05), true, false, Basis.IDENTITY, 0.0, -0.4, PI + 0.4)
		elif not long and not kh:
			# sandal laces
			for k in 3:
				mb.tube(Vector3(0, -shin_len + 0.03 + k * 0.06, 0), Vector2(limb * 0.36, limb * 0.36), Vector2(limb * 0.37, limb * 0.37), 0.018, S_LIMB, col(SANDAL), false, false)
		var fy: float = -d["shin"]
		if kh:
			mb.taper(Vector3(0, fy, -limb * 0.35), Vector2(limb * 1.0, limb * 2.0), Vector2(limb * 0.8, limb * 1.2), d["foot_h"] * 1.2, skin.darkened(0.12), Vector2(0, 0.02))
			for c in [-1, 0, 1]:
				mb.cone(Vector3(c * limb * 0.3, fy + 0.01, -limb * 1.3), 0.022, 0.08, 4, col(HORN), Basis(Vector3.RIGHT, -PI / 2))
		else:
			mb.taper(Vector3(0, fy, -limb * 0.32), Vector2(limb * 0.82, limb * 1.85), Vector2(limb * 0.7, limb * 1.0), d["foot_h"], col(SANDAL), Vector2(0, 0.03))

	# --- pelvis & skirt (own bone: it folds onto the lap when seated)
	_on(HIPS)
	mb.tube(Vector3(0, -0.12, 0), Vector2(hip * 0.5, depth * 0.48), Vector2(hip * 0.52, depth * 0.5), 0.2, S_BODY, under if not armoured else secondary)
	_on(SKIRT)
	if long:
		var ln: float = d["leg"] * 0.9
		d["skirt_len"] = ln
		mb.tube(Vector3(0, -ln, 0), Vector2(hip * 0.86, depth * 0.84), Vector2(hip * 0.53, depth * 0.51), ln + 0.05, 14, primary, false, true, Basis.IDENTITY, 0.07)
		mb.tube(Vector3(0, -ln - 0.005, 0), Vector2(hip * 0.89, depth * 0.87), Vector2(hip * 0.87, depth * 0.85), 0.07, 14, trim if outfit != "toga" else secondary, false, false, Basis.IDENTITY, 0.07)
	elif armoured:
		var ln2: float = d["thigh"] * 0.72
		d["skirt_len"] = ln2
		mb.tube(Vector3(0, -ln2, 0), Vector2(hip * 0.68, depth * 0.68), Vector2(hip * 0.53, depth * 0.5), ln2 + 0.04, S_BODY, secondary, false, true, Basis.IDENTITY, 0.05)
		for i in 10:
			var a := TAU * (i + 0.5) / 10.0
			var p := Vector3(cos(a) * hip * 0.62, -ln2 * 0.55, -sin(a) * depth * 0.62)
			mb.box(p, Vector3(0.075, ln2 * 0.8, 0.025), col(LEATHER), Basis(Vector3.UP, a + PI / 2) * Basis(Vector3.RIGHT, 0.12))
			mb.box(p + Vector3(0, -ln2 * 0.4, 0), Vector3(0.078, 0.025, 0.03), trim, Basis(Vector3.UP, a + PI / 2) * Basis(Vector3.RIGHT, 0.12))
	else:
		var ln3: float = d["thigh"] * 0.82
		d["skirt_len"] = ln3
		mb.tube(Vector3(0, -ln3, 0), Vector2(hip * 0.72, depth * 0.72), Vector2(hip * 0.53, depth * 0.5), ln3 + 0.05, 12, primary, false, true, Basis.IDENTITY, 0.06)
		mb.tube(Vector3(0, -ln3 - 0.005, 0), Vector2(hip * 0.74, depth * 0.74), Vector2(hip * 0.73, depth * 0.73), 0.05, 12, trim, false, false, Basis.IDENTITY, 0.06)

	# --- torso: waist -> chest -> shoulders
	_on(TORSO)
	var torso_col := metal if armoured else under
	var chest_y := th * 0.66
	mb.tube(Vector3(0, -0.08, 0), Vector2(hip * 0.5, depth * 0.48), Vector2(sh * 0.5, depth * 0.58), chest_y + 0.08, S_BODY, torso_col, false, true)
	mb.tube(Vector3(0, chest_y, 0), Vector2(sh * 0.5, depth * 0.58), Vector2(sh * 0.36, depth * 0.44), th - chest_y + 0.02, S_BODY, torso_col)
	if armoured:
		var band := metal.darkened(0.2)
		for i in 3:
			var y := th * (0.08 + 0.18 * i)
			var k := (y + 0.08) / (chest_y + 0.08)
			var rw := lerpf(hip * 0.5, sh * 0.5, k) + 0.012
			var rd := lerpf(depth * 0.48, depth * 0.58, k) + 0.012
			mb.tube(Vector3(0, y, 0), Vector2(rw, rd), Vector2(rw, rd), 0.035, S_BODY, band if outfit == "armour" else metal.darkened(0.3), false, false)
		# sculpted pectorals and a gold gorget
		for sx in [-1, 1]:
			mb.sphere(Vector3(sx * sh * 0.17, chest_y - 0.02, -depth * 0.42), sh * 0.15, metal.lightened(0.06), 6, 4, Vector3(1.0, 0.75, 0.45))
		mb.tube(Vector3(0, th - 0.03, 0), Vector2(sh * 0.3, depth * 0.38), Vector2(sh * 0.26, depth * 0.32), 0.06, S_BODY, trim)
	else:
		mb.tube(Vector3(0, 0.02, 0), Vector2(hip * 0.52, depth * 0.5), Vector2(hip * 0.53, depth * 0.51), 0.05, S_BODY, trim if outfit != "stola" else secondary, false, false)
	match outfit:
		"toga":
			# the sinus: a heavy diagonal fold from the right hip over the left shoulder
			var hp := Vector3(hip * 0.36, -0.08, 0)
			var shp := Vector3(-sh * 0.3, th - 0.04, 0)
			var sv := shp - hp
			var sb := Basis(Vector3.BACK, atan2(-sv.x, sv.y))
			mb.tube(hp, Vector2(0.1, depth * 0.6), Vector2(0.12, depth * 0.62), sv.length() + 0.06, 8, primary, true, true, sb, 0.08)
			mb.tube(hp + sb * Vector3(0.09, 0, 0), Vector2(0.025, depth * 0.61), Vector2(0.025, depth * 0.63), sv.length() + 0.06, 8, secondary if secondary != primary else trim, false, false, sb)
			# the drape hanging down the back from the left shoulder
			mb.taper(Vector3(-sh * 0.28, -0.6, depth * 0.38), Vector2(0.26, 0.06), Vector2(0.2, 0.08), th + 0.62, primary, Vector2(0, 0.02))
		"robe":
			mb.box(Vector3(0, th * 0.42, -depth * 0.55), Vector3(0.07, th * 0.95, 0.012), secondary)
			mb.tube(Vector3(0, th - 0.02, 0), Vector2(sh * 0.42, depth * 0.52), Vector2(sh * 0.3, depth * 0.4), 0.07, S_BODY, secondary)
		"stola":
			# the palla: a shawl over the shoulders
			mb.tube(Vector3(0, chest_y - 0.06, 0), Vector2(sh * 0.56, depth * 0.64), Vector2(sh * 0.4, depth * 0.48), th - chest_y + 0.1, S_BODY, secondary, true, false, Basis.IDENTITY, 0.06)
		"tunic":
			for sx in [-1, 1]:
				mb.box(Vector3(sx * sh * 0.16, th * 0.4, -depth * 0.55), Vector3(0.04, th * 0.92, 0.012), secondary, Basis(Vector3.BACK, sx * 0.08))
	# neck
	mb.tube(Vector3(0, th - 0.02, 0), Vector2(limb * 0.48, limb * 0.48), Vector2(limb * 0.44, limb * 0.44), d["neck"] + 0.06, S_LIMB, skin)

	# --- arms
	for side in [-1, 1]:
		var arm_b := ARM_L if side < 0 else ARM_R
		var fore_b := FORE_L if side < 0 else FORE_R
		var upper_col := skin
		var fore_col := skin
		var sleeve := Color(0, 0, 0, 0)
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
		mb.sphere(Vector3(side * 0.005, -0.03, 0), limb * 0.6, upper_col if sleeve.a == 0.0 else sleeve, 6, 4, Vector3(1.0, 0.9, 1.0))
		_limb(d["upper"] + 0.02, limb * 0.4, limb * 0.5, upper_col)
		if sleeve.a > 0.0:
			mb.tube(Vector3(0, -d["upper"] * 0.5, 0), Vector2(limb * 0.56, limb * 0.56), Vector2(limb * 0.6, limb * 0.6), d["upper"] * 0.5 + 0.02, S_LIMB, sleeve, false, false, Basis.IDENTITY, 0.05)
		if armoured:
			for k in 2:
				mb.tube(Vector3(0, -0.13 + k * 0.07, 0), Vector2(limb * 0.75 - k * 0.04, limb * 0.75 - k * 0.04), Vector2(limb * 0.6, limb * 0.62), 0.09, S_LIMB, metal.darkened(0.05 + k * 0.08), true, false)
		_on(fore_b)
		var fl: float = d["fore"] - d["hand"]
		_limb(fl + 0.02, limb * 0.32, limb * 0.4, fore_col)
		if long_sleeve:
			mb.tube(Vector3(0, -fl, 0), Vector2(limb * 0.6, limb * 0.6), Vector2(limb * 0.44, limb * 0.44), fl * 0.5, S_LIMB, fore_col.darkened(0.05), false, false, Basis.IDENTITY, 0.06)
			mb.tube(Vector3(0, -fl - 0.002, 0), Vector2(limb * 0.62, limb * 0.62), Vector2(limb * 0.61, limb * 0.61), 0.035, S_LIMB, trim, false, false)
		elif armoured:
			mb.tube(Vector3(0, -fl * 0.98, 0), Vector2(limb * 0.4, limb * 0.4), Vector2(limb * 0.45, limb * 0.45), fl * 0.6, S_LIMB, col(LEATHER), false, false)
		var hand_y: float = -d["fore"] + d["hand"] * 0.55
		mb.sphere(Vector3(0, hand_y, -0.01), d["hand"] * 0.5, skin, 6, 4, Vector3(0.8, 1.0, 0.62))
		mb.box(Vector3(-side * limb * 0.25, hand_y + 0.01, -0.035), Vector3(0.025, 0.06, 0.025), skin, Basis(Vector3.BACK, -side * 0.4))
		if kh:
			for c in [-1, 1]:
				mb.cone(Vector3(c * limb * 0.16, hand_y - d["hand"] * 0.45, -0.02), 0.016, 0.055, 4, col(HORN), Basis(Vector3.RIGHT, PI))

	# --- cloak: a shell wrapping the back, with a mantle and a gold V at the front
	if look.get("cloak") != null and str(look.get("cloak")) != "":
		var cloak := lk("cloak")
		var lining := secondary.darkened(0.15) if secondary != cloak else cloak.darkened(0.35)
		_on(CLOAK)
		var cl: float = d["torso"] + d["leg"] * 0.78
		mb.tube(Vector3(0, -cl, 0.02), Vector2(sh * 0.95, depth * 1.25), Vector2(sh * 0.56, depth * 0.66), cl, 12, cloak,
			false, false, Basis.IDENTITY, 0.05, -PI / 2 - 1.7, -PI / 2 + 1.7, Vector3(0, 0, -0.02), true, lining)
		mb.tube(Vector3(0, -cl - 0.004, 0.02), Vector2(sh * 0.97, depth * 1.27), Vector2(sh * 0.95, depth * 1.25), 0.045, 12, trim,
			false, false, Basis.IDENTITY, 0.05, -PI / 2 - 1.7, -PI / 2 + 1.7, Vector3.ZERO, true)
		_on(TORSO)
		mb.tube(Vector3(0, th - 0.16, 0), Vector2(sh * 0.6, depth * 0.72), Vector2(sh * 0.3, depth * 0.4), 0.22, S_BODY, cloak, true, false)
		for sx in [-1, 1]:
			mb.box(Vector3(sx * sh * 0.14, th - 0.12, -depth * 0.6), Vector3(0.05, 0.3, 0.03), trim, Basis(Vector3.BACK, sx * 0.55) * Basis(Vector3.RIGHT, -0.25))
		mb.sphere(Vector3(0, th - 0.24, -depth * 0.6), 0.035, col(GOLD), 6, 3)

	# --- tail
	if kh:
		var tail_col := skin.darkened(0.05)
		_on(TAIL1)
		mb.tube(Vector3.ZERO, Vector2(limb * 0.72, limb * 0.78), Vector2(limb * 0.52, limb * 0.55), 0.54, 7, tail_col, true, true, Basis(Vector3.RIGHT, deg_to_rad(112)))
		_on(TAIL2)
		mb.tube(Vector3.ZERO, Vector2(limb * 0.52, limb * 0.55), Vector2(0.015, 0.015), 0.64, 7, tail_col, true, true, Basis(Vector3.RIGHT, deg_to_rad(100)))
		for i in 4:
			mb.cone(Vector3(0, 0.03 - i * 0.03, 0.08 + i * 0.13), 0.03, 0.07, 4, skin.darkened(0.3), Basis(Vector3.RIGHT, deg_to_rad(20)))

	# --- head
	_on(HEAD)
	match d["sp"]:
		"veyari": _head_veyari(skin)
		"kharad": _head_kharad(skin)
		"othari": _head_othari(skin)
		_: _head_human(skin)
	_headwear()
	_props()


# ---------------------------------------------------------------- heads

func _eyes(y: float, sep: float, size: Vector2, front: float, white := true) -> void:
	var ec := col(look.get("eye", "222222"))
	for sx in [-1, 1]:
		if white:
			mb.box(Vector3(sx * sep, y, front - 0.002), Vector3(size.x * 1.25, size.y, 0.01), col("efe8dc"))
		mb.box(Vector3(sx * sep + sx * 0.002, y, front - 0.006), Vector3(size.x * 0.6, size.y * 1.05, 0.01), ec)


func _skull(hw: float, hd: float, hh: float, skin: Color, back := 0.0) -> void:
	# cranium and a tapered jaw: two faceted pieces
	mb.sphere(Vector3(0, hh * 0.6, back), hw * 0.5, skin, 8, 6, Vector3(1.0, hh / hw * 0.82, hd / hw))
	mb.tube(Vector3(0, hh * 0.04, -hd * 0.06), Vector2(hw * 0.3, hd * 0.34), Vector2(hw * 0.47, hd * 0.47), hh * 0.5, 8, skin)


func _hair_cap(hw: float, hd: float, hh: float, hair: Color, low := 0.55, back := 0.0) -> void:
	# a faceted cap over the cranium, open at the face
	mb.tube(Vector3(0, hh * low, back + hd * 0.02), Vector2(hw * 0.54, hd * 0.55), Vector2(hw * 0.46, hd * 0.47), hh * (0.86 - low), 9, hair,
		false, false, Basis.IDENTITY, 0.04, -PI / 2 - 2.3, -PI / 2 + 2.3)
	mb.sphere(Vector3(0, hh * 0.72, back + hd * 0.03), hw * 0.52, hair, 8, 4, Vector3(1.0, 0.62, hd / hw * 1.02))


func _head_human(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var hair := lk("hair")
	_skull(hw, hd, hh, skin)
	var front := -hd * 0.5
	# nose, brow, mouth, ears
	mb.taper(Vector3(0, hh * 0.36, front + 0.005), Vector2(0.036, 0.03), Vector2(0.018, 0.012), hh * 0.24, skin.darkened(0.05), Vector2(0, 0.012))
	mb.box(Vector3(0, hh * 0.64, front + 0.012), Vector3(hw * 0.78, 0.028, 0.03), skin.darkened(0.1))
	for sx in [-1, 1]:
		mb.box(Vector3(sx * hw * 0.21, hh * 0.67, front + 0.004), Vector3(0.055, 0.016, 0.014), hair.darkened(0.1))
		mb.sphere(Vector3(sx * hw * 0.5, hh * 0.5, 0.01), 0.032, skin.darkened(0.06), 5, 3, Vector3(0.5, 1.1, 0.8))
	_eyes(hh * 0.56, hw * 0.2, Vector2(0.032, 0.02), front + 0.006)
	var helmet := str(look.get("headwear", "")) == "helmet"
	var style := str(look.get("hair_style", "short"))
	if not helmet:
		match style:
			"short": _hair_cap(hw, hd, hh, hair, 0.55)
			"cropped": _hair_cap(hw * 0.97, hd * 0.97, hh, hair, 0.62)
			"curly":
				_hair_cap(hw, hd, hh, hair, 0.52)
				for i in 8:
					var a := TAU * i / 8.0
					mb.sphere(Vector3(cos(a) * hw * 0.34, hh * 0.92 + 0.02 * (i % 2), -sin(a) * hd * 0.34 + 0.01), 0.04, hair.darkened(0.06), 5, 3)
			"long":
				_hair_cap(hw, hd, hh, hair, 0.5)
				mb.tube(Vector3(0, -0.1, hd * 0.12), Vector2(hw * 0.52, hd * 0.3), Vector2(hw * 0.54, hd * 0.42), hh * 0.85, 8, hair, false, true,
					Basis.IDENTITY, 0.06, -PI / 2 - 1.6, -PI / 2 + 1.6, Vector3.ZERO, true)
			"bun":
				_hair_cap(hw, hd, hh, hair, 0.5)
				mb.sphere(Vector3(0, hh * 0.72, hd * 0.55), 0.065, hair.darkened(0.05), 7, 5)
			"braids":
				_hair_cap(hw, hd, hh, hair, 0.5)
				for sx in [-1, 1]:
					mb.tube(Vector3(sx * hw * 0.42, -0.08, hd * 0.2), Vector2(0.025, 0.025), Vector2(0.035, 0.035), hh * 0.75, 5, hair)
	var beard := str(look.get("beard", "none"))
	if beard == "short" or beard == "full":
		var bl := 0.0 if beard == "short" else 0.08
		mb.tube(Vector3(0, hh * 0.02 - bl, -hd * 0.06), Vector2(hw * 0.3, hd * 0.34), Vector2(hw * 0.5, hd * 0.5), hh * 0.38 + bl, 9, hair,
			false, true, Basis.IDENTITY, 0.05, PI / 2 - 1.75, PI / 2 + 1.75, Vector3.ZERO, true)
		mb.box(Vector3(0, hh * 0.31, front - 0.004), Vector3(hw * 0.46, 0.028, 0.02), hair.darkened(0.08))
		for sx in [-1, 1]:
			mb.box(Vector3(sx * hw * 0.45, hh * 0.45, -hd * 0.05), Vector3(0.03, hh * 0.3, hd * 0.4), hair)
	else:
		mb.box(Vector3(0, hh * 0.24, front + 0.002), Vector3(0.055, 0.012, 0.01), skin.darkened(0.3))


func _head_veyari(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var hair := lk("hair")
	# an elongated, swept-back skull
	mb.sphere(Vector3(0, hh * 0.68, hd * 0.12), hw * 0.5, skin, 8, 6, Vector3(1.0, hh / hw * 0.7, hd / hw * 1.3))
	mb.tube(Vector3(0, hh * 0.04, -hd * 0.08), Vector2(hw * 0.24, hd * 0.28), Vector2(hw * 0.47, hd * 0.46), hh * 0.55, 8, skin)
	for sx in [-1, 1]:
		mb.taper(Vector3(sx * hw * 0.22, hh * 0.8, hd * 0.1), Vector2(0.022, 0.12), Vector2(0.008, 0.04), 0.2, hair, Vector2.ZERO, Basis(Vector3.RIGHT, deg_to_rad(60)) * Basis(Vector3.BACK, sx * -0.12))
		mb.box(Vector3(sx * hw * 0.33, hh * 0.36, -hd * 0.38), Vector3(0.016, 0.08, 0.03), skin.darkened(0.2), Basis(Vector3.BACK, sx * 0.3))
		mb.taper(Vector3(sx * hw * 0.48, hh * 0.5, 0.02), Vector2(0.02, 0.05), Vector2(0.006, 0.01), 0.14, skin.darkened(0.06), Vector2(sx * 0.05, 0.05))
	mb.taper(Vector3(0, hh * 0.84, 0.0), Vector2(0.026, 0.15), Vector2(0.01, 0.06), 0.17, hair.darkened(0.1), Vector2.ZERO, Basis(Vector3.RIGHT, deg_to_rad(64)))
	mb.taper(Vector3(0, hh * 0.38, -hd * 0.49), Vector2(0.026, 0.022), Vector2(0.012, 0.01), hh * 0.2, skin.darkened(0.05))
	_eyes(hh * 0.56, hw * 0.21, Vector2(0.046, 0.024), -hd * 0.47, false)
	mb.box(Vector3(0, hh * 0.22, -hd * 0.42), Vector3(0.045, 0.01, 0.01), skin.darkened(0.35))
	if str(look.get("hair_style", "")) == "long":
		mb.tube(Vector3(0, -0.18, hd * 0.32), Vector2(hw * 0.48, 0.05), Vector2(hw * 0.4, 0.06), hh * 0.95, 8, hair, true, true, Basis.IDENTITY, 0.08)


func _head_kharad(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var dark := skin.darkened(0.25)
	mb.sphere(Vector3(0, hh * 0.55, hd * 0.06), hw * 0.5, skin, 8, 6, Vector3(1.0, hh / hw * 0.85, hd / hw * 0.9))
	# heavy snout and jaw
	mb.tube(Vector3(0, hh * 0.42, -hd * 0.25), Vector2(hw * 0.36, hh * 0.28), Vector2(hw * 0.25, hh * 0.2), hd * 0.6, 7, skin.lightened(0.03), true, true, Basis(Vector3.RIGHT, -PI / 2), 0.0, 0.0, TAU, Vector3(0, 0, 0.02))
	mb.tube(Vector3(0, hh * 0.24, -hd * 0.2), Vector2(hw * 0.32, hh * 0.16), Vector2(hw * 0.22, hh * 0.1), hd * 0.5, 7, skin.darkened(0.08), true, true, Basis(Vector3.RIGHT, -PI / 2))
	mb.box(Vector3(0, hh * 0.33, -hd * 0.5), Vector3(hw * 0.5, 0.015, hd * 0.5), dark)
	for sx in [-1, 1]:
		mb.box(Vector3(sx * hw * 0.1, hh * 0.5, -hd * 0.84), Vector3(0.022, 0.016, 0.012), dark)
		for k in 3:
			mb.cone(Vector3(sx * hw * (0.2 - k * 0.04), hh * 0.31, -hd * (0.55 + k * 0.1)), 0.012, 0.03, 3, col(HORN), Basis(Vector3.RIGHT, PI))
	mb.box(Vector3(0, hh * 0.72, -hd * 0.38), Vector3(hw * 1.0, 0.07, 0.1), dark, Basis(Vector3.RIGHT, -0.2))
	_eyes(hh * 0.62, hw * 0.3, Vector2(0.044, 0.024), -hd * 0.36, false)
	var horn := col(HORN)
	for i in 3:
		for sx in [-1, 1]:
			var p := Vector3(sx * hw * (0.34 - i * 0.05), hh * (0.86 - i * 0.04), -hd * 0.1 + i * hd * 0.24)
			mb.cone(p, 0.042 - i * 0.006, 0.2 - i * 0.035, 5, horn, Basis(Vector3.RIGHT, deg_to_rad(64)) * Basis(Vector3.BACK, deg_to_rad(-20 * sx)))
	for i in 5:
		mb.box(Vector3(0, hh * (1.0 - i * 0.17), hd * 0.42 - i * 0.02), Vector3(0.05, 0.05, 0.05), dark, Basis(Vector3.RIGHT, PI / 4))


func _head_othari(skin: Color) -> void:
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var hair := lk("hair")
	mb.sphere(Vector3(0, hh * 0.6, 0), hw * 0.48, skin, 8, 5, Vector3(1.0, hh / hw * 0.75, hd / hw))
	mb.tube(Vector3(0, 0.0, -hd * 0.04), Vector2(hw * 0.5, hd * 0.44), Vector2(hw * 0.47, hd * 0.46), hh * 0.52, 8, skin)
	mb.box(Vector3(0, hh * 0.66, -hd * 0.45), Vector3(hw * 1.0, 0.08, 0.09), skin.darkened(0.22), Basis(Vector3.RIGHT, -0.15))
	mb.taper(Vector3(0, hh * 0.36, -hd * 0.5), Vector2(0.075, 0.05), Vector2(0.05, 0.03), hh * 0.24, skin.darkened(0.08))
	_eyes(hh * 0.55, hw * 0.21, Vector2(0.03, 0.018), -hd * 0.47, false)
	for sx in [-1, 1]:
		mb.sphere(Vector3(sx * hw * 0.5, hh * 0.48, 0.0), 0.035, skin.darkened(0.08), 5, 3)
	if str(look.get("beard", "plates")) == "plates":
		for i in 3:
			var x := (i - 1) * hw * 0.27
			var ln := 0.22 if i == 1 else 0.16
			mb.tube(Vector3(x, hh * 0.28 - ln, -hd * 0.42), Vector2(hw * 0.1, 0.026), Vector2(hw * 0.13, 0.035), ln + hh * 0.06, 5, hair, true, true)
			mb.tube(Vector3(x, hh * 0.28 - ln * 0.78, -hd * 0.42), Vector2(hw * 0.12, 0.035), Vector2(hw * 0.12, 0.035), 0.03, 5, col(GOLD).darkened(0.1))
	var style := str(look.get("hair_style", "braids"))
	if str(look.get("headwear", "")) != "helmet" and style != "bald":
		_hair_cap(hw * 0.98, hd * 0.98, hh, hair, 0.6)
		if style == "braids":
			for sx in [-1, 1]:
				mb.tube(Vector3(sx * hw * 0.3, -0.04, hd * 0.42), Vector2(0.03, 0.03), Vector2(0.042, 0.042), hh * 0.85, 5, hair)


func _headwear() -> void:
	var hw_t := str(look.get("headwear", "none"))
	if hw_t == "none" or hw_t == "":
		return
	var hw: float = d["head_w"]
	var hd: float = d["head_d"]
	var hh: float = d["head_h"]
	var r := maxf(hw, hd) * 0.53
	var yb := hh * 0.76
	if d["sp"] == "veyari":
		yb = hh * 0.68
	if d["sp"] == "kharad":
		yb = hh * 0.74
	match hw_t:
		"radiate", "laurel_gold", "laurel":
			var leaf := col(GOLD) if hw_t != "laurel" else col("4f7a3a")
			mb.tube(Vector3(0, yb, 0.01), Vector2(r, r * 1.05), Vector2(r * 0.98, r * 1.03), 0.025, 10, leaf.darkened(0.1), false, false)
			for i in 18:
				var a := lerpf(-PI * 0.42, PI * 1.42, i / 17.0)
				var p := Vector3(cos(a) * r * 1.02, yb + 0.03 + 0.012 * (i % 2), -sin(a) * r * 1.07 + 0.01)
				var lb := Basis(Vector3.UP, a) * Basis(Vector3.BACK, 0.9 if i % 2 == 0 else -0.6)
				mb.sphere(p, 0.03, leaf if i % 3 else leaf.lightened(0.15), 4, 3, Vector3(0.45, 1.0, 0.25), lb)
			if hw_t == "radiate":
				for i in 7:
					var a2 := lerpf(PI * 0.2, PI * 0.8, i / 6.0)
					mb.box(Vector3(cos(a2) * r, yb + 0.1, -sin(a2) * r), Vector3(0.022, 0.13, 0.01), col(GOLD), Basis(Vector3.UP, a2 - PI / 2) * Basis(Vector3.RIGHT, -0.25))
		"crown_gold", "crown_silver", "crown_iron":
			var c := col(GOLD if hw_t == "crown_gold" else (SILVER if hw_t == "crown_silver" else IRON))
			mb.tube(Vector3(0, yb, 0.01), Vector2(r * 1.04, r * 1.08), Vector2(r * 1.08, r * 1.12), 0.075, 10, c, false, false)
			for i in 7:
				var a3 := TAU * i / 7.0 + PI / 2
				mb.cone(Vector3(cos(a3) * r * 1.06, yb + 0.07, -sin(a3) * r * 1.1 + 0.01), 0.03, 0.085, 4, c)
			mb.sphere(Vector3(0, yb + 0.04, -r * 1.12), 0.022, lk("secondary") if hw_t != "crown_iron" else col("9b2226"), 5, 3)
		"diadem", "diadem_silver":
			var c2 := col(GOLD if hw_t == "diadem" else SILVER)
			mb.tube(Vector3(0, yb, 0.01), Vector2(r, r * 1.05), Vector2(r, r * 1.05), 0.03, 10, c2, false, false)
			mb.taper(Vector3(0, yb, -r * 1.05), Vector2(0.06, 0.02), Vector2(0.01, 0.01), 0.08, c2)
			mb.sphere(Vector3(0, yb + 0.03, -r * 1.07), 0.016, lk("secondary"), 5, 3)
		"circlet", "circlet_gold":
			mb.tube(Vector3(0, yb, 0.01), Vector2(r, r * 1.05), Vector2(r, r * 1.05), 0.025, 10, col(GOLD if hw_t == "circlet_gold" else SILVER), false, false)
		"helmet":
			var m := lk("primary") if str(look.get("outfit", "")) in ["armour", "scale"] else col("aeb4bc")
			var crest := lk("secondary")
			mb.sphere(Vector3(0, hh * 0.62, 0.01), r * 1.12, m, 8, 6, Vector3(1.0, 0.95, 1.08))
			mb.tube(Vector3(0, hh * 0.5, 0.01), Vector2(r * 1.14, r * 1.2), Vector2(r * 1.12, r * 1.18), 0.06, 10, col(GOLD), false, false)
			# transverse plume of the officer, longitudinal for the ranks
			mb.tube(Vector3(0, hh * 1.12, 0.0), Vector2(0.03, hd * 0.5), Vector2(0.045, hd * 0.6), 0.14, 8, crest, true, true, Basis.IDENTITY, 0.12)
			mb.box(Vector3(0, hh * 0.38, hd * 0.55), Vector3(hw * 1.0, 0.1, 0.06), m.darkened(0.1), Basis(Vector3.RIGHT, 0.4))
			for sx in [-1, 1]:
				mb.box(Vector3(sx * hw * 0.5, hh * 0.32, -hd * 0.12), Vector3(0.025, hh * 0.38, hd * 0.42), m.darkened(0.05))


func _props() -> void:
	var p := str(look.get("prop", "none"))
	_on(PROP)
	match p:
		"staff", "staff_gold":
			mb.tube(Vector3(0, -0.85, 0), Vector2(0.02, 0.02), Vector2(0.02, 0.02), 1.75, 6, col(WOOD) if p == "staff" else col(GOLD).darkened(0.15))
			mb.sphere(Vector3(0, 0.95, 0), 0.05, col(GOLD), 7, 5)
			if p == "staff_gold":
				for i in 8:
					var a := TAU * i / 8.0
					mb.box(Vector3(cos(a) * 0.08, 0.98, -sin(a) * 0.08), Vector3(0.02, 0.02, 0.07), col(GOLD), Basis(Vector3.UP, a))
		"spear":
			mb.tube(Vector3(0, -0.85, 0), Vector2(0.018, 0.018), Vector2(0.018, 0.018), 2.15, 5, col(WOOD))
			mb.tube(Vector3(0, 1.3, 0), Vector2(0.045, 0.012), Vector2(0.0, 0.0), 0.26, 4, col(SILVER))
			mb.tube(Vector3(0, 1.26, 0), Vector2(0.025, 0.025), Vector2(0.025, 0.025), 0.05, 5, col(GOLD))
		"scroll":
			mb.cyl(Vector3(0.12, 0, -0.02), 0.035, 0.035, 0.24, 6, col(PARCHMENT), true, true, Basis(Vector3.BACK, PI / 2))
			for sx in [-0.135, 0.135]:
				mb.sphere(Vector3(sx, 0, -0.02), 0.03, col(WOOD), 5, 3)
		"tablet":
			mb.box(Vector3(0, -0.02, -0.07), Vector3(0.025, 0.24, 0.17), col(WOOD))
			mb.box(Vector3(0.014, -0.02, -0.07), Vector3(0.006, 0.2, 0.13), col("3a2a1e"))
		"amphora":
			var tc := col("b3643c")
			mb.sphere(Vector3(0, -0.2, -0.05), 0.12, tc, 8, 6, Vector3(1, 1.35, 1))
			mb.cyl(Vector3(0, -0.05, -0.05), 0.04, 0.05, 0.14, 6, tc)
			mb.sphere(Vector3(0, -0.38, -0.05), 0.04, tc, 5, 3)
	if p == "sword":
		_on(HIPS)
		var sb := Basis(Vector3.BACK, deg_to_rad(-12)) * Basis(Vector3.RIGHT, deg_to_rad(-20))
		mb.box(Vector3(-d["hip"] * 0.72, -0.22, -0.04), Vector3(0.06, 0.5, 0.03), col(LEATHER).darkened(0.2), sb)
		mb.box(Vector3(-d["hip"] * 0.68, 0.05, -0.1), Vector3(0.12, 0.03, 0.04), col(GOLD), sb)
		mb.box(Vector3(-d["hip"] * 0.67, 0.11, -0.12), Vector3(0.03, 0.1, 0.03), col(LEATHER), sb)
	if look.get("shield") != null and str(look.get("shield")) != "":
		_on(FORE_L)
		var hy: float = -d["fore"] + d["hand"] * 0.5
		var sh_b := Basis(Vector3.BACK, PI / 2) * Basis.from_scale(Vector3(1.45, 1.0, 1.0))
		var sc := lk("shield")
		var cx: float = -d["limb"] * 0.55 - 0.05
		mb.cyl(Vector3(cx, hy + 0.12, -0.02), 0.3, 0.3, 0.05, 12, sc, true, true, sh_b)
		mb.cyl(Vector3(cx - 0.005, hy + 0.12, -0.02), 0.32, 0.32, 0.03, 12, col(GOLD).darkened(0.2), false, false, sh_b)
		mb.sphere(Vector3(cx - 0.05, hy + 0.12, -0.02), 0.06, col(GOLD), 6, 4)
