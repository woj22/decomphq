class_name Palace
extends Node3D
## The Palatium Ardens: the primary rooms of the imperial palace, built entirely from code.
##
## Layout (metres; +X east, +Z south toward the camera, Y up):
##   Council Chamber        x -14..14   z -46..-18
##   Hall of Petitions      x -30..-18  z  -8..8      Peristyle of the Sun  x -18..18  z -18..18
##   Audience Chamber       x -54..-30  z -12..12     Hall of Kings         x  18..58  z -12..12
##   Gallery                x  -3..3    z  18..34
##   Royal Apartments       x -14..14   z  34..56
## Walls above the plinth, columns and architraves are separate "occluder" meshes, so the camera
## can cut them away when they hide the player.

const WALL_T := 0.6
const DOOR_W := 3.2
const DOOR_H := 4.6

const C := {
	"marble": "e9e2d0", "marble2": "d6ccb6", "plinth": "9a8a72", "gold": "d9a63e", "bronze": "b07a3a",
	"wall": "e6d8bc", "porphyry": "6a2e4a", "ochre": "a8483a", "serpentine": "3d5a48", "lapis": "2b4c7e",
	"grass": "6f8f45", "grass2": "62803c", "hedge": "4a6b34", "cypress": "35512c", "water": "4f97b3",
	"terracotta": "b3643c", "wood": "6b4a2e", "darkwood": "4a3020", "purple": "5a1f5c", "cream": "e4d6bf",
	"greytile": "c2ae95", "redtile": "8a3a2e", "blacktile": "3a3430", "flame": "ffb347", "ember": "ff7a2a",
	"bed": "e9e2d0", "parchment": "e6d9b8", "iron": "4a4a4e", "crimson": "8e1f24", "roof": "b5523a",
	"stone": "d8c8a8", "stone2": "c4b08e", "earth": "a8906a", "paving": "c9b38e",
}

var rooms: Array = []            # {id, name, subtitle, rect: Rect2(x, z, w, d)}
var waypoints: Dictionary = {}   # name -> Vector3
var seats: Dictionary = {}       # name -> {pos: Vector3 (floor under seat), yaw, top}
var occluders: Array = []        # MeshInstance3D (meta "aabb")
var astar := AStar3D.new()
var spawn := Vector3(-40, 0, 21.5)

var _mb: MeshBuilder             # static geometry of the room being built
var _glow: MeshBuilder           # unshaded flames / glow
var _water: MeshBuilder
var _body: StaticBody3D
var _room_id := ""
var _wp_ids: Dictionary = {}


func c(key: String) -> Color:
	return Color(C.get(key, key))


func build() -> void:
	_body = StaticBody3D.new()
	_body.name = "Collision"
	add_child(_body)
	_environment()
	_room("courtyard", "Peristyle of the Sun", "The heart of the Palatium. Every corridor of the palace crosses here.", Rect2(-18, -18, 36, 36), _build_courtyard)
	_room("council", "The Imperial Council Chamber", "Where the Emperor hears his ministers and the fate of provinces is argued.", Rect2(-14, -46, 28, 28), _build_council)
	_room("kings", "The Hall of Kings", "The six client kingdoms sit beneath their banners, in strict precedence.", Rect2(18, -12, 40, 24), _build_kings)
	_room("ante", "The Hall of Petitions", "Antechamber to the throne. Everyone waits; the Prefect decides how long.", Rect2(-30, -8, 12, 16), _build_ante)
	_room("audience", "The Emperor's Audience Chamber", "The Ardent Throne. Approach only when summoned.", Rect2(-54, -12, 24, 24), _build_audience)
	_room("gallery", "Gallery of the River Kings", "The corridor to your apartments, hung with the busts of Seravel's kings.", Rect2(-3, 18, 6, 16), _build_gallery)
	_room("apartments", "Royal Apartments of Seravel", "Your residence at court: study, map table and bedchamber.", Rect2(-14, 34, 28, 22), _build_apartments)
	_room("terrace", "The Imperial Terrace", "The palace's western belvedere. All Caelora lies below, gold in the evening light.", Rect2(-54, 12, 36, 18), _build_terrace)
	_room("roofs", "", "", Rect2(), _build_roofs)
	_build_city()
	_build_graph()


func room_at(p: Vector3) -> Dictionary:
	for r in rooms:
		if r["name"] != "" and (r["rect"] as Rect2).grow(0.2).has_point(Vector2(p.x, p.z)):
			return r
	return {}


const CAM_YAW := {"kings": -PI / 2, "ante": PI / 2, "audience": PI / 2}


func _room(id: String, title: String, subtitle: String, rect: Rect2, fn: Callable) -> void:
	_room_id = id
	_mb = MeshBuilder.new()
	_glow = MeshBuilder.new()
	_water = MeshBuilder.new()
	rooms.append({"id": id, "name": title, "subtitle": subtitle, "rect": rect, "cam_yaw": CAM_YAW.get(id, 0.0)})
	fn.call()
	var mi := _mb.instance()
	mi.name = "Room_" + id
	add_child(mi)
	if not _glow.is_empty():
		var g := _glow.instance(true)
		g.name = "Glow_" + id
		g.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(g)
	if id == "roofs":
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if not _water.is_empty():
		var w := MeshInstance3D.new()
		w.name = "Water_" + id
		w.mesh = _water.build()
		var wm := StandardMaterial3D.new()
		wm.vertex_color_use_as_albedo = true
		wm.vertex_color_is_srgb = true
		wm.roughness = 0.08
		wm.metallic_specular = 0.9
		wm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		w.mesh.surface_set_material(0, wm)
		w.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(w)


# ======================================================================== kit

func _collide_box(center: Vector3, size: Vector3, yaw := 0.0) -> void:
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = size
	cs.shape = sh
	cs.transform = Transform3D(Basis(Vector3.UP, yaw), center)
	_body.add_child(cs)


func _collide_cyl(base: Vector3, r: float, h: float) -> void:
	var cs := CollisionShape3D.new()
	var sh := CylinderShape3D.new()
	sh.radius = r
	sh.height = h
	cs.shape = sh
	cs.position = base + Vector3(0, h * 0.5, 0)
	_body.add_child(cs)


func _occluder(mb: MeshBuilder, nm: String) -> void:
	var mi := mb.instance()
	mi.name = nm
	add_child(mi)
	mi.set_meta("aabb", mi.mesh.get_aabb())
	mi.add_to_group("occluder")
	occluders.append(mi)


func _floor(x0: float, z0: float, x1: float, z1: float, tile: float, ca: Color, cb: Color, y := 0.0) -> void:
	var nx := int(ceil((x1 - x0) / tile))
	var nz := int(ceil((z1 - z0) / tile))
	for i in nx:
		for j in nz:
			var ax := x0 + i * tile
			var az := z0 + j * tile
			var bx := minf(ax + tile, x1)
			var bz := minf(az + tile, z1)
			var cc := ca if (i + j) % 2 == 0 else cb
			_mb.quad(Vector3(ax, y, bz), Vector3(bx, y, bz), Vector3(bx, y, az), Vector3(ax, y, az), cc)


## Axis-aligned wall from (ax, az) to (bx, bz). doors: [[offset_from_a, width, height], ...]
func _wall(ax: float, az: float, bx: float, bz: float, h: float, doors: Array = [], wall_col := "wall", band_col := "", nm := "Wall") -> void:
	var horizontal := absf(bz - az) < 0.01
	var length := absf(bx - ax) if horizontal else absf(bz - az)
	var sgn := signf(bx - ax) if horizontal else signf(bz - az)
	var cuts: Array = [[0.0, length]]
	for dr in doors:
		var o: float = dr[0]
		var w: float = dr[1]
		var nc: Array = []
		for seg in cuts:
			if o - w / 2 > seg[0] and o + w / 2 < seg[1]:
				nc.append([seg[0], o - w / 2])
				nc.append([o + w / 2, seg[1]])
			else:
				nc.append(seg)
		cuts = nc
	var wc := c(wall_col)
	var pos := func(t: float) -> Vector2:
		return Vector2(ax + sgn * t, az) if horizontal else Vector2(ax, az + sgn * t)
	var plinth_h := 0.9
	for seg in cuts:
		var t0: float = seg[0]
		var t1: float = seg[1]
		if t1 - t0 < 0.05:
			continue
		var p0: Vector2 = pos.call(t0)
		var p1: Vector2 = pos.call(t1)
		var mid := (p0 + p1) * 0.5
		var len_ := t1 - t0
		var size_xz := Vector2(len_, WALL_T) if horizontal else Vector2(WALL_T, len_)
		_mb.box(Vector3(mid.x, plinth_h * 0.5, mid.y), Vector3(size_xz.x + 0.08, plinth_h, size_xz.y + 0.08), c("plinth"))
		var up := MeshBuilder.new()
		up.box(Vector3(mid.x, (plinth_h + h) * 0.5, mid.y), Vector3(size_xz.x, h - plinth_h, size_xz.y), wc)
		if band_col != "":
			up.box(Vector3(mid.x, 2.1, mid.y), Vector3(size_xz.x + 0.06, 2.0, size_xz.y + 0.06), c(band_col))
			up.box(Vector3(mid.x, 3.16, mid.y), Vector3(size_xz.x + 0.1, 0.12, size_xz.y + 0.1), c("gold"))
		up.box(Vector3(mid.x, h - 0.2, mid.y), Vector3(size_xz.x + 0.24, 0.4, size_xz.y + 0.24), c("marble"))
		_occluder(up, nm)
		_collide_box(Vector3(mid.x, h * 0.5, mid.y), Vector3(size_xz.x, h, size_xz.y))
	var jambs := MeshBuilder.new()
	for dr in doors:
		var o2: float = dr[0]
		var w2: float = dr[1]
		var dh: float = dr[2]
		var dp: Vector2 = pos.call(o2)
		var lsize := Vector3(w2 + 0.9, h - dh, WALL_T + 0.1) if horizontal else Vector3(WALL_T + 0.1, h - dh, w2 + 0.9)
		var lin := MeshBuilder.new()
		lin.box(Vector3(dp.x, dh + (h - dh) * 0.5, dp.y), lsize, wc)
		lin.box(Vector3(dp.x, dh + 0.25, dp.y), lsize * Vector3(1, 0, 1) + Vector3(0.1, 0.5, 0.1) * Vector3(1, 1, 1), c("marble"))
		lin.box(Vector3(dp.x, h - 0.2, dp.y), Vector3(lsize.x + 0.14, 0.4, lsize.z + 0.14), c("marble"))
		_occluder(lin, nm + "Lintel")
		for s in [-1, 1]:
			var jp: Vector2 = pos.call(o2 + s * (w2 * 0.5 + 0.18))
			var js := Vector3(0.36, dh, WALL_T + 0.24) if horizontal else Vector3(WALL_T + 0.24, dh, 0.36)
			_mb.box(Vector3(jp.x, 0.45, jp.y), Vector3(js.x, 0.9, js.z), c("marble"))
			jambs.box(Vector3(jp.x, dh * 0.5 + 0.45, jp.y), Vector3(js.x, dh - 0.9, js.z), c("marble"))
	if not jambs.is_empty():
		_occluder(jambs, nm + "Jambs")


func _column(x: float, z: float, h: float, r: float, shaft := "marble", nm := "Column") -> void:
	var m := MeshBuilder.new()
	m.box(Vector3(x, 0.16, z), Vector3(r * 2.7, 0.32, r * 2.7), c("marble2"))
	m.tube(Vector3(x, 0.32, z), Vector2(r * 1.3, r * 1.3), Vector2(r * 1.12, r * 1.12), 0.14, 12, c("marble"), true, false)
	m.tube(Vector3(x, 0.46, z), Vector2(r * 1.12, r * 1.12), Vector2(r * 1.02, r * 1.02), 0.1, 12, c("marble"), true, false)
	# fluted shaft with a little entasis
	m.tube(Vector3(x, 0.56, z), Vector2(r, r), Vector2(r * 0.95, r * 0.95), (h - 1.2) * 0.4, 16, c(shaft), false, false, Basis.IDENTITY, 0.035)
	m.tube(Vector3(x, 0.56 + (h - 1.2) * 0.4, z), Vector2(r * 0.95, r * 0.95), Vector2(r * 0.86, r * 0.86), (h - 1.2) * 0.6, 16, c(shaft), false, false, Basis.IDENTITY, 0.035)
	# Ionic capital: echinus, volutes, abacus
	m.tube(Vector3(x, h - 0.64, z), Vector2(r * 0.88, r * 0.88), Vector2(r * 1.05, r * 1.05), 0.16, 12, c("gold"), false, false)
	m.box(Vector3(x, h - 0.4, z), Vector3(r * 2.5, 0.26, r * 1.5), c("marble"))
	for sx in [-1, 1]:
		m.cyl(Vector3(x + sx * r * 1.1, h - 0.4, z - r * 0.78), 0.17 * r / 0.42, 0.17 * r / 0.42, r * 1.56, 8, c("marble"), true, true, Basis(Vector3.RIGHT, PI / 2))
		m.cyl(Vector3(x + sx * r * 1.1, h - 0.4, z - r * 0.8), 0.07 * r / 0.42, 0.07 * r / 0.42, r * 1.6, 6, c("gold"), true, true, Basis(Vector3.RIGHT, PI / 2))
	m.box(Vector3(x, h - 0.13, z), Vector3(r * 2.7, 0.26, r * 2.7), c("marble"))
	_occluder(m, nm)
	_collide_cyl(Vector3(x, 0, z), r * 1.1, h)


func _beam(a: Vector3, b: Vector3, w := 0.9, hgt := 0.7) -> void:
	var up := MeshBuilder.new()
	var mid := (a + b) * 0.5
	var size := Vector3(absf(b.x - a.x) + w, hgt, absf(b.z - a.z) + w)
	up.box(mid, size, c("marble"))
	up.box(mid + Vector3(0, -hgt * 0.5 + 0.08, 0), size + Vector3(0.06, -hgt + 0.16, 0.06), c("gold"))
	_occluder(up, "Architrave")


func _steps(rect: Rect2, h: float, col := "marble2", top := "marble", collide := true) -> void:
	var center := Vector3(rect.position.x + rect.size.x * 0.5, h * 0.5, rect.position.y + rect.size.y * 0.5)
	_mb.box(center, Vector3(rect.size.x, h, rect.size.y), c(col))
	_mb.box(Vector3(center.x, h - 0.01, center.z), Vector3(rect.size.x + 0.04, 0.04, rect.size.y + 0.04), c(top))
	if collide:
		_collide_box(center + Vector3(0, 0.5, 0), Vector3(rect.size.x, h + 1.0, rect.size.y))


func _rug(rect: Rect2, col: String, border: String, y := 0.012) -> void:
	var p := rect.position
	var s := rect.size
	_mb.quad(Vector3(p.x, y, p.y + s.y), Vector3(p.x + s.x, y, p.y + s.y), Vector3(p.x + s.x, y, p.y), Vector3(p.x, y, p.y), c(border))
	var i := rect.grow(-0.3)
	_mb.quad(Vector3(i.position.x, y + 0.004, i.end.y), Vector3(i.end.x, y + 0.004, i.end.y), Vector3(i.end.x, y + 0.004, i.position.y), Vector3(i.position.x, y + 0.004, i.position.y), c(col))


func _brazier(x: float, z: float, base_y := 0.0, light := false, scale := 1.0) -> void:
	var b := Vector3(x, base_y, z)
	var k := scale
	for i in 3:
		var a := TAU * i / 3.0
		_mb.box(b + Vector3(cos(a) * 0.24 * k, 0.45 * k, sin(a) * 0.24 * k), Vector3(0.06, 0.9, 0.06) * k, c("bronze").darkened(0.2), Basis(Vector3(sin(a), 0, -cos(a)), 0.2))
	_mb.tube(b + Vector3(0, 0.82 * k, 0), Vector2(0.18, 0.18) * k, Vector2(0.5, 0.5) * k, 0.34 * k, 10, c("bronze"), true, true)
	_mb.tube(b + Vector3(0, 1.14 * k, 0), Vector2(0.5, 0.5) * k, Vector2(0.53, 0.53) * k, 0.05 * k, 10, c("gold"), false, false)
	for i in 5:
		var a2 := TAU * i / 5.0
		var fp := b + Vector3(cos(a2) * 0.2 * k, 1.12 * k, sin(a2) * 0.2 * k)
		_glow.tube(fp, Vector2(0.16, 0.16) * k, Vector2.ZERO, (0.5 + 0.25 * (i % 2)) * k, 4, c("flame"), false, false, Basis(Vector3(sin(a2), 0, -cos(a2)), 0.25))
	_glow.tube(b + Vector3(0, 1.12 * k, 0), Vector2(0.26, 0.26) * k, Vector2.ZERO, 0.95 * k, 5, Color("ffd36b"), false, false)
	_glow.tube(b + Vector3(0, 1.12 * k, 0), Vector2(0.14, 0.14) * k, Vector2.ZERO, 0.6 * k, 4, Color("fff1b0"), false, false, Basis(Vector3.UP, 0.4))
	_collide_cyl(b, 0.4 * k, 1.2 * k)
	if light:
		var l := OmniLight3D.new()
		l.position = b + Vector3(0, 1.7 * k, 0)
		l.light_color = Color("ffa555")
		l.light_energy = 1.6
		l.omni_range = 8.0
		add_child(l)


func _banner(x: float, z: float, facing: Vector3, faction: String, top_y := 6.2, length := 3.6, width := 1.4) -> void:
	var bn := MeshBuilder.new()
	var yaw := atan2(facing.x, facing.z)
	var bs := Basis(Vector3.UP, yaw)
	var off := facing.normalized() * (WALL_T * 0.5 + 0.08)
	bn.box(Vector3(x, top_y + 0.05, z) + off * 1.4, Vector3(width + 0.5, 0.1, 0.1), c("gold"), bs)
	for sx in [-1, 1]:
		bn.sphere(Vector3(x, top_y + 0.05, z) + off * 1.4 + bs * Vector3(sx * (width * 0.5 + 0.3), 0, 0), 0.09, c("gold"), 6, 4)
	_banner_cloth(bn, Vector3(x, top_y, z) + off, bs, faction, length, width)
	_occluder(bn, "Banner")


## The cloth itself, hanging from `top` (centre of its upper edge), facing bs * +Z.
func _banner_cloth(bn: MeshBuilder, top: Vector3, bs: Basis, faction: String, length: float, width: float) -> void:
	var k: Dictionary = Cast.kingdoms.get(faction, Cast.kingdoms["imperium"])
	var c1 := Color(k["colors"][0])
	var c2 := Color(k["colors"][1])
	var tail := width * 0.45
	var body := length - tail
	var hw := width * 0.5
	var pts := [Vector3(-hw, 0, 0), Vector3(hw, 0, 0), Vector3(hw, -body, 0), Vector3(0, -length, 0), Vector3(-hw, -body, 0)]
	for side in [1.0, -1.0]:
		var o := Vector3(0, 0, 0.025 * side)
		var p0: Vector3 = top + bs * (pts[0] + o)
		var p1: Vector3 = top + bs * (pts[1] + o)
		var p2: Vector3 = top + bs * (pts[2] + o)
		var p3: Vector3 = top + bs * (pts[3] + o)
		var p4: Vector3 = top + bs * (pts[4] + o)
		if side > 0:
			bn.quad(p4, p2, p1, p0, c1)
			bn.tri(p4, p3, p2, c1.darkened(0.08))
		else:
			bn.quad(p0, p1, p2, p4, c1.darkened(0.2))
			bn.tri(p2, p3, p4, c1.darkened(0.25))
	# gold border and emblem on the front face
	var f := bs * Vector3(0, 0, 0.035)
	bn.box(top + bs * Vector3(0, -0.12, 0) + f, Vector3(width, 0.08, 0.012), c2, bs)
	for sx in [-1, 1]:
		bn.box(top + bs * Vector3(sx * (hw - 0.05), -body * 0.5, 0) + f, Vector3(0.06, body - 0.1, 0.012), c2, bs)
		var a := atan2(tail, hw)
		bn.box(top + bs * Vector3(sx * hw * 0.5, -body - tail * 0.5 + 0.04, 0) + f, Vector3(Vector2(hw, tail).length(), 0.06, 0.012), c2, bs * Basis(Vector3.BACK, sx * a))
	_emblem(bn, top + bs * Vector3(0, -body * 0.48, 0) + f * 1.2, bs, str(k.get("emblem", "sun")), c2, width * 0.62)
	bn.box(top + bs * Vector3(0, -body + 0.05, 0) + f, Vector3(0.12, 0.12, 0.012), c2, bs * Basis(Vector3.BACK, PI / 4))


func _emblem(m: MeshBuilder, p: Vector3, bs: Basis, kind: String, col: Color, s: float) -> void:
	var flat := bs * Basis(Vector3.RIGHT, PI / 2)
	match kind:
		"laurel":
			for sx in [-1, 1]:
				for i in 7:
					var a := lerpf(-1.25, 1.35, i / 6.0)
					var lp := Vector3(sx * sin(a + PI / 2) * s * 0.42, -cos(a + PI / 2) * s * 0.42 - s * 0.05, 0)
					var lb := bs * Basis(Vector3.BACK, sx * (a + 0.5))
					m.sphere(p + bs * lp, s * 0.1, col, 4, 3, Vector3(0.55, 1.3, 0.12), lb)
			m.box(p + bs * Vector3(0, -s * 0.5, 0), Vector3(s * 0.12, s * 0.08, 0.02), col, bs)
		"sun":
			m.cyl(p, s * 0.32, s * 0.32, 0.02, 10, col, true, true, flat)
			for i in 8:
				var a := TAU * i / 8.0
				m.box(p + bs * Vector3(cos(a) * s * 0.5, sin(a) * s * 0.5, 0.01), Vector3(s * 0.08, s * 0.24, 0.02), col, bs * Basis(Vector3.BACK, a - PI / 2))
		"river":
			for i in 3:
				for j in 3:
					m.box(p + bs * Vector3((j - 1) * s * 0.3, (i - 1) * s * 0.3 + (0.05 if j == 1 else -0.03) * s, 0), Vector3(s * 0.3, s * 0.08, 0.02), col, bs * Basis(Vector3.BACK, 0.4 if j != 1 else -0.4))
		"lamp":
			m.box(p + bs * Vector3(0, -s * 0.2, 0), Vector3(s * 0.6, s * 0.2, 0.02), col, bs)
			m.box(p + bs * Vector3(0, s * 0.15, 0), Vector3(s * 0.16, s * 0.4, 0.02), col, bs * Basis(Vector3.BACK, PI / 4))
		"horns":
			for sx in [-1, 1]:
				m.box(p + bs * Vector3(sx * s * 0.22, 0, 0), Vector3(s * 0.12, s * 0.7, 0.02), col, bs * Basis(Vector3.BACK, sx * 0.45))
			m.box(p + bs * Vector3(0, -s * 0.25, 0), Vector3(s * 0.5, s * 0.15, 0.02), col, bs)
		"spear":
			m.box(p, Vector3(s * 0.08, s * 0.9, 0.02), col, bs)
			m.box(p + bs * Vector3(0, s * 0.42, 0), Vector3(s * 0.22, s * 0.22, 0.02), col, bs * Basis(Vector3.BACK, PI / 4))
		"wave":
			for i in 3:
				m.box(p + bs * Vector3(0, (i - 1) * s * 0.28, 0), Vector3(s * 0.8, s * 0.09, 0.02), col, bs * Basis(Vector3.BACK, 0.25 * (1 if i % 2 == 0 else -1)))
		"hammer":
			m.box(p + bs * Vector3(0, -s * 0.1, 0), Vector3(s * 0.1, s * 0.7, 0.02), col, bs)
			m.box(p + bs * Vector3(0, s * 0.28, 0), Vector3(s * 0.55, s * 0.22, 0.02), col, bs)


func _statue(x: float, z: float, yaw: float, look: Dictionary, pedestal := 1.4, base_y := 0.0) -> void:
	_mb.box(Vector3(x, base_y + pedestal * 0.5, z), Vector3(1.1, pedestal, 1.1), c("marble2"))
	_mb.box(Vector3(x, base_y + pedestal - 0.06, z), Vector3(1.25, 0.12, 1.25), c("marble"))
	_mb.box(Vector3(x, base_y + 0.08, z), Vector3(1.3, 0.16, 1.3), c("marble"))
	var m := MeshInstance3D.new()
	m.mesh = CharacterBuilder.build_static_mesh(look, true)
	m.position = Vector3(x, base_y + pedestal, z)
	m.rotation.y = yaw
	m.scale = Vector3.ONE * 1.25
	add_child(m)
	_collide_box(Vector3(x, 1.0, z), Vector3(1.2, 2.0, 1.2))


func _cypress(x: float, z: float, h := 4.5) -> void:
	_tree(_mb, Vector3(x, 0, z), h)
	_collide_cyl(Vector3(x, 0, z), 0.5, 2.0)


func _pot_plant(x: float, z: float) -> void:
	_mb.cyl(Vector3(x, 0, z), 0.32, 0.42, 0.6, 7, c("terracotta"))
	_mb.sphere(Vector3(x, 1.0, z), 0.55, c("hedge"), 6, 4, Vector3(1, 0.9, 1))
	_collide_cyl(Vector3(x, 0, z), 0.45, 1.2)


func _bench(x: float, z: float, length: float, along_x: bool, seat_name := "", seat_yaw := 0.0, n_seats := 0) -> void:
	var size := Vector3(length, 0.45, 0.6) if along_x else Vector3(0.6, 0.45, length)
	_mb.box(Vector3(x, 0.38, z), size + Vector3(0.1, -0.31, 0.1), c("marble"))
	for s in [-1, 1]:
		var lp := Vector3(x + s * (length * 0.4 if along_x else 0.0), 0.16, z + (0.0 if along_x else s * length * 0.4))
		_mb.box(lp, Vector3(0.4, 0.32, 0.5) if along_x else Vector3(0.5, 0.32, 0.4), c("marble2"))
	_collide_box(Vector3(x, 0.3, z), size)
	for i in n_seats:
		var t := (float(i) + 0.5) / n_seats - 0.5
		var p := Vector3(x + (t * length if along_x else 0.0), 0, z + (0.0 if along_x else t * length))
		_seat(seat_name + str(i + 1), p, seat_yaw, 0.45)


func _seat(nm: String, floor_pos: Vector3, yaw: float, top: float) -> void:
	seats[nm] = {"pos": floor_pos, "yaw": yaw, "top": top}


func _chair(x: float, z: float, yaw: float, col := "darkwood", cushion := "purple", nm := "") -> void:
	var bs := Basis(Vector3.UP, yaw)
	var p := Vector3(x, 0, z)
	_mb.box(p + Vector3(0, 0.4, 0), Vector3(0.6, 0.08, 0.6), c(col), bs)
	_mb.box(p + Vector3(0, 0.46, 0), Vector3(0.52, 0.05, 0.52), c(cushion), bs)
	_mb.box(p + bs * Vector3(0, 0.82, 0.27), Vector3(0.6, 0.8, 0.07), c(col), bs)
	for sx in [-1, 1]:
		for sz in [-1, 1]:
			_mb.box(p + bs * Vector3(sx * 0.25, 0.2, sz * 0.25), Vector3(0.06, 0.4, 0.06), c(col), bs)
	if nm != "":
		_seat(nm, p, yaw, 0.48)


## yaw: rotation.y the seated character uses (0 faces -Z).
func _throne(x: float, z: float, yaw: float, base_y: float, main: String, accent: String, nm: String, grand := false) -> void:
	var bs := Basis(Vector3.UP, yaw)
	var p := Vector3(x, base_y, z)
	var w := 1.2 if grand else 0.95
	var back_h := 2.6 if grand else 1.8
	_mb.box(p + Vector3(0, 0.25, 0), Vector3(w + 0.2, 0.5, 1.0), c(main), bs)
	_mb.box(p + Vector3(0, 0.53, 0), Vector3(w - 0.1, 0.06, 0.8), c(accent), bs)
	_mb.box(p + bs * Vector3(0, back_h * 0.5 + 0.3, 0.45), Vector3(w + 0.2, back_h, 0.16), c(main), bs)
	_mb.box(p + bs * Vector3(0, back_h * 0.5 + 0.4, 0.36), Vector3(w - 0.2, back_h - 0.4, 0.04), c(accent), bs)
	for sx in [-1, 1]:
		_mb.box(p + bs * Vector3(sx * (w * 0.5 + 0.05), 0.75, 0.0), Vector3(0.14, 0.12, 0.95), c("gold"), bs)
		_mb.box(p + bs * Vector3(sx * (w * 0.5 + 0.05), 0.5, -0.4), Vector3(0.14, 0.5, 0.14), c("gold"), bs)
	if grand:
		var top := p + bs * Vector3(0, back_h + 0.45, 0.45)
		_emblem(_mb, top + bs * Vector3(0, 0, -0.1), bs * Basis(Vector3.UP, PI), "sun", c("gold"), 1.3)
	_collide_box(p + Vector3(0, 0.9, 0), Vector3(w + 0.3, 1.8, 1.1), yaw)
	_seat(nm, p, yaw, 0.56)


func _table(rect: Rect2, h := 0.8, col := "darkwood") -> void:
	var cx := rect.position.x + rect.size.x * 0.5
	var cz := rect.position.y + rect.size.y * 0.5
	_mb.box(Vector3(cx, h - 0.05, cz), Vector3(rect.size.x, 0.1, rect.size.y), c(col))
	_mb.box(Vector3(cx, h - 0.12, cz), Vector3(rect.size.x - 0.1, 0.05, rect.size.y - 0.1), c("gold"))
	for sx in [-1, 1]:
		for sz in [-1, 1]:
			_mb.box(Vector3(cx + sx * (rect.size.x * 0.5 - 0.15), (h - 0.1) * 0.5, cz + sz * (rect.size.y * 0.5 - 0.15)), Vector3(0.12, h - 0.1, 0.12), c(col))
	_collide_box(Vector3(cx, h * 0.5, cz), Vector3(rect.size.x, h, rect.size.y))


func _scroll_shelf(x: float, z: float, length: float, along_x: bool) -> void:
	var size := Vector3(length, 2.4, 0.5) if along_x else Vector3(0.5, 2.4, length)
	_mb.box(Vector3(x, 1.2, z), size, c("darkwood"))
	var n := int(length / 0.22)
	for row in 4:
		var y := 0.35 + row * 0.55
		_mb.box(Vector3(x, y - 0.17, z), size * Vector3(1, 0, 1) + Vector3(0.02, 0.04, 0.04), c("wood"))
		for i in n:
			var t := -length * 0.5 + 0.11 + i * 0.22
			var p := Vector3(x + (t if along_x else 0.0), y, z + (0.0 if along_x else t))
			var off := Vector3(0, 0, 0.27) if along_x else Vector3(0.27, 0, 0)
			if (i * 7 + row * 3) % 5 != 0:
				_mb.cyl(p - off * 0.1, 0.07, 0.07, 0.04, 5, c("parchment").darkened(0.05 * ((i + row) % 3)), true, false, Basis(Vector3.RIGHT, PI / 2) if along_x else Basis(Vector3.BACK, PI / 2))
	_collide_box(Vector3(x, 1.2, z), size)


# ======================================================================== environment

func _environment() -> void:
	var we := WorldEnvironment.new()
	var env := Environment.new()
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color("3e3478")
	sm.sky_horizon_color = Color("f2a26a")
	sm.sky_curve = 0.11
	sm.ground_horizon_color = Color("e7a27c")
	sm.ground_bottom_color = Color("5e4a6e")
	sm.ground_curve = 0.05
	sm.sun_angle_max = 12.0
	sm.sun_curve = 0.08
	sm.energy_multiplier = 1.0
	sky.sky_material = sm
	env.sky = sky
	env.background_mode = Environment.BG_SKY
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("9a84b4")
	env.ambient_light_energy = 0.62
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 0.92
	env.fog_enabled = not OS.get_cmdline_user_args().has("--nofog")
	env.fog_light_color = Color("c99a9c")
	env.fog_density = 0.0011
	env.fog_sun_scatter = 0.12
	env.fog_sky_affect = 0.0
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_strength = 1.0
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 0.95
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SOFTLIGHT
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.12
	env.adjustment_contrast = 1.05
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	# low evening sun from the west-south-west
	sun.rotation_degrees = Vector3(-17, -72, 0)
	sun.light_color = Color("ffb877")
	sun.light_energy = 1.35
	sun.shadow_enabled = true
	sun.shadow_bias = 0.12
	sun.shadow_normal_bias = 2.5
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 70.0
	add_child(sun)


# ======================================================================== rooms

func _build_courtyard() -> void:
	# portico paving, garden (four L-shaped beds), cross paths, square fountain plaza
	_floor(-18, -18, 18, 18, 2.0, c("cream"), c("greytile"))
	_mb.box(Vector3(0, 0.04, 0), Vector3(27.6, 0.08, 27.6), c("marble2"))
	for sx in [-1, 1]:
		for sz in [-1, 1]:
			for b in [Rect2(6.0, 2.25, 7.55, 11.3), Rect2(2.25, 6.0, 3.75, 7.55)]:
				var r: Rect2 = b
				var cx: float = sx * (r.position.x + r.size.x * 0.5)
				var cz: float = sz * (r.position.y + r.size.y * 0.5)
				_mb.box(Vector3(cx, 0.1, cz), Vector3(r.size.x, 0.12, r.size.y), c("grass"))
				for e in 4:
					var hz := e < 2
					var off: float = (r.size.y if hz else r.size.x) * 0.5 * (1 if e % 2 == 0 else -1)
					var hs := Vector3(r.size.x, 0.5, 0.4) if hz else Vector3(0.4, 0.5, r.size.y)
					_mb.box(Vector3(cx + (0.0 if hz else off), 0.35, cz + (off if hz else 0.0)), hs, c("hedge"))
				_collide_box(Vector3(cx, 0.5, cz), Vector3(r.size.x, 1.0, r.size.y))
	_mb.box(Vector3(0, 0.08, 0), Vector3(12.0, 0.16, 12.0), c("cream"))
	_mb.box(Vector3(0, 0.165, 0), Vector3(11.0, 0.01, 11.0), c("gold").darkened(0.15))
	_mb.box(Vector3(0, 0.17, 0), Vector3(10.6, 0.01, 10.6), c("cream"))
	for sx in [-1, 1]:
		_mb.box(Vector3(sx * 10.0, 0.12, 0), Vector3(8.0, 0.08, 4.5), c("cream"))
		_mb.box(Vector3(0, 0.12, sx * 10.0), Vector3(4.5, 0.08, 8.0), c("cream"))
	# fountain
	_mb.cyl(Vector3(0, 0.16, 0), 3.4, 3.3, 0.7, 12, c("marble"))
	_mb.cyl(Vector3(0, 0.86, 0), 3.5, 3.5, 0.12, 12, c("marble2"), true, false)
	_water.cyl(Vector3(0, 0.6, 0), 3.0, 3.0, 0.32, 12, Color(c("water"), 0.85), true, false)
	_mb.cyl(Vector3(0, 0.16, 0), 0.55, 0.45, 2.0, 8, c("marble"))
	_mb.cyl(Vector3(0, 2.0, 0), 0.4, 1.4, 0.4, 10, c("marble"))
	_water.cyl(Vector3(0, 2.3, 0), 1.25, 1.25, 0.08, 10, Color(c("water"), 0.85), true, false)
	_mb.cyl(Vector3(0, 2.4, 0), 0.25, 0.2, 0.9, 6, c("marble"))
	_emblem(_mb, Vector3(0, 3.7, 0), Basis.IDENTITY, "sun", c("gold"), 1.4)
	_emblem(_mb, Vector3(0, 3.7, 0), Basis(Vector3.UP, PI / 2), "sun", c("gold"), 1.4)
	for i in 6:
		var a := TAU * i / 6.0
		_water.box(Vector3(cos(a) * 1.6, 1.4, sin(a) * 1.6), Vector3(0.1, 1.6, 0.1), Color(c("water").lightened(0.3), 0.55), Basis(Vector3(-sin(a), 0, cos(a)), 0.35))
	_collide_cyl(Vector3.ZERO, 3.5, 1.0)
	# statues of past emperors in the garden corners
	var emperors := [
		{"species": "human", "sex": "m", "outfit": "toga", "headwear": "laurel", "prop": "scroll", "hair_style": "short", "beard": "full", "cloak": "x"},
		{"species": "human", "sex": "m", "outfit": "armour", "headwear": "none", "prop": "spear", "hair_style": "curly", "beard": "short", "cloak": "x", "shield": "x"},
		{"species": "human", "sex": "f", "outfit": "stola", "headwear": "diadem", "prop": "staff", "hair_style": "bun", "beard": "none"},
		{"species": "human", "sex": "m", "outfit": "toga", "headwear": "radiate", "prop": "staff_gold", "hair_style": "short", "beard": "none", "cloak": "x"},
	]
	var corners := [Vector2(-9.5, -9.5), Vector2(9.5, -9.5), Vector2(-9.5, 9.5), Vector2(9.5, 9.5)]
	for i in 4:
		var cp: Vector2 = corners[i]
		_statue(cp.x, cp.y, atan2(cp.x, cp.y), Cast.resolve_look("human", emperors[i], emperors[i]["sex"]), 1.6, 0.16)
	for p in [Vector2(-12.5, -5), Vector2(-5, -12.5), Vector2(12.5, -5), Vector2(5, -12.5), Vector2(-12.5, 5), Vector2(-5, 12.5), Vector2(12.5, 5), Vector2(5, 12.5)]:
		_cypress(p.x, p.y, 4.8)
	# peristyle colonnade + architraves
	for t in [-14.0, -10.0, -6.0, -2.0, 2.0, 6.0, 10.0, 14.0]:
		_column(t, -14, 6.6, 0.42)
		_column(t, 14, 6.6, 0.42)
		if absf(t) < 13.9:
			_column(-14, t, 6.6, 0.42)
			_column(14, t, 6.6, 0.42)
	for s in [-14.0, 14.0]:
		_beam(Vector3(-14, 6.95, s), Vector3(14, 6.95, s))
		_beam(Vector3(s, 6.95, -14), Vector3(s, 6.95, 14))
	# walls with the four great doors
	var dw := [[18.0, DOOR_W, DOOR_H]]
	_wall(-18, -18, 18, -18, 8.0, dw, "wall", "ochre", "WallCourtN")
	_wall(-18, 18, 18, 18, 8.0, dw, "wall", "ochre", "WallCourtS")
	_wall(-18, -18, -18, 18, 8.0, [[18.0, DOOR_W, DOOR_H], [33.0, 3.0, 4.2]], "wall", "ochre", "WallCourtW")
	_wall(18, -18, 18, 18, 8.0, dw, "wall", "ochre", "WallCourtE")
	# banners between the doors, braziers and benches in the portico
	for t in [-10.0, 10.0]:
		_banner(t, -18, Vector3(0, 0, 1), "imperium", 7.0)
		_banner(t, 18, Vector3(0, 0, -1), "imperium", 7.0)
		_banner(-18, t, Vector3(1, 0, 0), "imperium", 7.0)
		_banner(18, t, Vector3(-1, 0, 0), "imperium", 7.0)
	for p in [Vector2(-3.4, -16.2), Vector2(3.4, -16.2), Vector2(16.2, -3.4), Vector2(16.2, 3.4), Vector2(-16.2, -3.4), Vector2(-16.2, 3.4), Vector2(-3.4, 16.2), Vector2(3.4, 16.2)]:
		_brazier(p.x, p.y)
	_bench(-17.3, 12.0, 3.0, false, "court_bench_w", -PI / 2, 2)
	_bench(17.3, -12.0, 3.0, false, "court_bench_e", PI / 2, 2)
	_bench(-12.0, -17.3, 3.0, true, "court_bench_n", PI, 2)
	_bench(12.0, 17.3, 3.0, true, "court_bench_s", 0, 2)
	for p in [Vector2(-16.6, -16.6), Vector2(16.6, -16.6), Vector2(-16.6, 16.6), Vector2(16.6, 16.6)]:
		_pot_plant(p.x, p.y)
	# waypoints
	_wp("c_n", 0, -11); _wp("c_s", 0, 11); _wp("c_e", 11, 0); _wp("c_w", -11, 0)
	_wp("c_mid_n", 0, -5); _wp("c_mid_s", 0, 5); _wp("c_mid_e", 5, 0); _wp("c_mid_w", -5, 0)
	_wp("c_pl_ne", 5, -5); _wp("c_pl_se", 5, 5); _wp("c_pl_sw", -5, 5); _wp("c_pl_nw", -5, -5)
	_wp("p_n", 0, -16); _wp("p_s", 0, 16); _wp("p_e", 16, 0); _wp("p_w", -16, 0)
	_wp("p_nw", -16, -16); _wp("p_ne", 16, -16); _wp("p_sw", -16, 16); _wp("p_se", 16, 16)
	_wp("d_council", 0, -18); _wp("d_kings", 18, 0); _wp("d_ante", -18, 0); _wp("d_gallery", 0, 18); _wp("d_terrace", -18, 15)


func _build_council() -> void:
	_floor(-14, -46, 14, -18, 2.0, c("redtile"), c("cream"))
	# sun mosaic on the speaker's floor
	_mb.cyl(Vector3(0, 0, -33), 6.6, 6.6, 0.03, 20, c("marble"), true, false)
	_mb.cyl(Vector3(0, 0, -33), 2.4, 2.4, 0.05, 16, c("gold"), true, false)
	for i in 12:
		var a := TAU * i / 12.0
		_mb.box(Vector3(cos(a) * 4.0, 0.035, -33 + sin(a) * 4.0), Vector3(2.2, 0.03, 0.35), c("gold").darkened(0.1), Basis(Vector3.UP, -a))
	# horseshoe of tiers (open to the north, aisle at the south)
	var ctr := Vector3(0, 0, -33)
	var tiers := [[8.0, 9.5, 0.45], [9.5, 11.0, 0.9], [11.0, 12.6, 1.35]]
	var spans := [[deg_to_rad(-12), deg_to_rad(80)], [deg_to_rad(100), deg_to_rad(192)]]
	for sp in spans:
		for t in tiers:
			_mb.ring_sector(ctr, t[0], t[1], sp[0], sp[1], t[2], 14, c("marble"), c("marble2"))
			_mb.ring_sector(ctr + Vector3(0, t[2], 0), t[0] + 0.15, t[0] + 0.75, sp[0], sp[1], 0.07, 14, c("ochre"))
		var steps := 10
		for i in steps:
			var a := lerpf(sp[0], sp[1], (i + 0.5) / steps)
			var mid := ctr + Vector3(cos(a), 0, sin(a)) * 10.3
			_collide_box(mid + Vector3(0, 0.8, 0), Vector3(4.8, 1.6, 10.3 * (sp[1] - sp[0]) / steps + 0.2), -a)
	var n := 0
	for sp in spans:
		for k in 2:
			var r: float = 8.45 if k == 0 else 9.95
			var top: float = 0.45 if k == 0 else 0.9
			var floor_y: float = 0.0 if k == 0 else 0.45
			for i in 6:
				var a := lerpf(sp[0] + 0.12, sp[1] - 0.12, (i + 0.5) / 6.0)
				var p := ctr + Vector3(cos(a), 0, sin(a)) * r
				p.y = floor_y
				n += 1
				_seat("council_tier" + str(n), p, atan2(cos(a), sin(a)), top - floor_y)
	# the dais and the Emperor's council throne
	_steps(Rect2(-6, -46, 12, 6), 0.8)
	_steps(Rect2(-5, -40, 10, 0.8), 0.4, "marble2", "marble", false)
	_collide_box(Vector3(0, 0.5, -39.6), Vector3(10, 1.0, 0.8))
	_rug(Rect2(-1.6, -45.4, 3.2, 5.0), "purple", "gold", 0.815)
	_throne(0, -44.4, PI, 0.8, "marble", "purple", "council_throne", true)
	_chair(-3.4, -43.2, PI, "darkwood", "purple", "council_chair_w")
	_chair(3.4, -43.2, PI, "darkwood", "purple", "council_chair_e")
	# columns flanking the dais, banners
	_column(-7.2, -40.6, 8.6, 0.55, "porphyry")
	_column(7.2, -40.6, 8.6, 0.55, "porphyry")
	_brazier(-5.4, -38.8, 0.0, true)
	_brazier(5.4, -38.8, 0.0, true)
	# lectern
	_mb.taper(Vector3(0, 0, -29.5), Vector2(0.6, 0.5), Vector2(0.5, 0.4), 1.1, c("darkwood"))
	_mb.box(Vector3(0, 1.15, -29.5), Vector3(0.8, 0.08, 0.6), c("darkwood"), Basis(Vector3.RIGHT, 0.3))
	_collide_box(Vector3(0, 0.6, -29.5), Vector3(0.7, 1.2, 0.6))
	# walls
	_wall(-14, -46, 14, -46, 9.0, [], "wall", "porphyry", "WallCouncilN")
	_wall(-14, -46, -14, -18, 9.0, [], "wall", "porphyry", "WallCouncilW")
	_wall(14, -46, 14, -18, 9.0, [], "wall", "porphyry", "WallCouncilE")
	_banner(-3.0, -46, Vector3(0, 0, 1), "imperium", 8.2, 5.0, 1.8)
	_banner(3.0, -46, Vector3(0, 0, 1), "imperium", 8.2, 5.0, 1.8)
	var side := ["seravel", "lucerna", "velithra"]
	var side2 := ["tor_ilun", "karst_odun", "khar_dumeth"]
	for i in 3:
		_banner(-14, -24 - i * 7.0, Vector3(1, 0, 0), side[i], 8.0, 3.2, 1.3)
		_banner(14, -24 - i * 7.0, Vector3(-1, 0, 0), side2[i], 8.0, 3.2, 1.3)
	_wp("cu_entry", 0, -20.5); _wp("cu_aisle", 0, -24.0); _wp("cu_floor", 0, -30.4)
	_wp("cu_floor_w", -4.6, -33.6); _wp("cu_floor_e", 4.6, -33.6); _wp("cu_front", 0, -37.6)


func _build_kings() -> void:
	_floor(18, -12, 58, 12, 2.0, c("cream"), c("greytile"))
	_rug(Rect2(18.5, -1.6, 33.0, 3.2), "purple", "gold")
	for x in [24.0, 29.0, 34.0, 39.0, 44.0, 49.0]:
		_column(x, -6, 8.0, 0.5, "serpentine")
		_column(x, 6, 8.0, 0.5, "serpentine")
	_beam(Vector3(24, 8.35, -6), Vector3(49, 8.35, -6))
	_beam(Vector3(24, 8.35, 6), Vector3(49, 8.35, 6))
	# the long table of kings
	_table(Rect2(29.6, -1.2, 9.0, 2.4), 0.82, "darkwood")
	for i in 5:
		var x := 30.6 + i * 1.75
		_chair(x, -2.05, PI, "darkwood", "ochre", "kh_table_n" + str(i + 1))
		_chair(x, 2.05, 0.0, "darkwood", "ochre", "kh_table_s" + str(i + 1))
	_chair(28.6, 0, -PI / 2, "darkwood", "purple", "kh_table_w")
	_chair(39.6, 0, PI / 2, "darkwood", "purple", "kh_table_e")
	for i in 4:
		var x2 := 31.0 + i * 2.4
		_mb.cyl(Vector3(x2, 0.82, 0.3 * (1 if i % 2 == 0 else -1)), 0.08, 0.1, 0.22, 6, c("gold"))
		_mb.box(Vector3(x2 + 0.6, 0.85, -0.3), Vector3(0.4, 0.04, 0.3), c("parchment"))
	# the six thrones, by precedence: nearest the imperial seat is highest
	var north := [["seravel", 30.0], ["velithra", 37.0], ["lucerna", 44.0]]
	var south := [["tor_ilun", 30.0], ["karst_odun", 37.0], ["khar_dumeth", 44.0]]
	for e in north:
		var k: Dictionary = Cast.kingdoms[e[0]]
		_throne(e[1], -10.9, PI, 0.0, "darkwood", k["colors"][0], "kh_throne_" + e[0])
		_banner(e[1], -12, Vector3(0, 0, 1), e[0], 7.2, 3.6, 1.6)
		_rug(Rect2(e[1] - 1.3, -11.6, 2.6, 2.6), k["colors"][0], k["colors"][1])
	for e in south:
		var k2: Dictionary = Cast.kingdoms[e[0]]
		_throne(e[1], 10.9, 0.0, 0.0, "darkwood", k2["colors"][0], "kh_throne_" + e[0])
		_banner(e[1], 12, Vector3(0, 0, -1), e[0], 7.2, 3.6, 1.6)
		_rug(Rect2(e[1] - 1.3, 9.0, 2.6, 2.6), k2["colors"][0], k2["colors"][1])
	# the imperial seat on the east dais, statue of the dynasty's founder
	_steps(Rect2(52, -7, 6, 14), 0.9)
	_steps(Rect2(51.2, -4, 0.8, 8), 0.45, "marble2", "marble", false)
	_collide_box(Vector3(51.6, 0.5, 0), Vector3(0.8, 1.0, 8))
	_throne(55.6, 0, PI / 2, 0.9, "marble", "purple", "kh_imperial_seat", true)
	_banner(58, -3.4, Vector3(-1, 0, 0), "imperium", 8.0, 5.0, 1.8)
	_banner(58, 3.4, Vector3(-1, 0, 0), "imperium", 8.0, 5.0, 1.8)
	var founder := Cast.resolve_look("human", {"outfit": "armour", "headwear": "radiate", "prop": "spear", "cloak": "x", "shield": "x", "hair_style": "curly", "beard": "full"}, "m")
	_statue(56.2, -9.4, 3 * PI / 4, founder, 1.8)
	_statue(56.2, 9.4, PI / 4, founder, 1.8)
	for p in [Vector2(20.6, -10.6), Vector2(20.6, 10.6)]:
		_pot_plant(p.x, p.y)
	for p in [Vector2(51.0, -6.0), Vector2(51.0, 6.0), Vector2(26.5, -10.6), Vector2(26.5, 10.6)]:
		_brazier(p.x, p.y, 0.0, p.x > 50)
	_wall(18, -12, 58, -12, 9.0, [], "wall", "serpentine", "WallKingsN")
	_wall(18, 12, 58, 12, 9.0, [], "wall", "serpentine", "WallKingsS")
	_wall(58, -12, 58, 12, 9.0, [], "wall", "serpentine", "WallKingsE")
	_wp("kh_entry", 21, 0)
	_wp("kh_a_n", 26.5, -3.6); _wp("kh_a_s", 26.5, 3.6); _wp("kh_b_n", 41.6, -3.6); _wp("kh_b_s", 41.6, 3.6)
	_wp("kh_n1", 26.5, -8.6); _wp("kh_n2", 41.6, -8.6); _wp("kh_s1", 26.5, 8.6); _wp("kh_s2", 41.6, 8.6)
	_wp("kh_apse", 48.5, 0)


func _build_ante() -> void:
	_floor(-30, -8, -18, 8, 1.6, c("blacktile"), c("cream"))
	_rug(Rect2(-29.6, -1.3, 11.2, 2.6), "purple", "gold")
	_bench(-24.5, -7.25, 5.0, true, "ante_bench_n", PI, 2)
	_bench(-24.5, 7.25, 5.0, true, "ante_bench_s", 0.0, 2)
	# the Prefect's writing desk
	_table(Rect2(-29.2, -5.4, 1.6, 1.0), 1.05, "darkwood")
	_mb.box(Vector3(-28.4, 1.08, -4.9), Vector3(0.5, 0.05, 0.35), c("parchment"))
	_mb.cyl(Vector3(-28.9, 1.05, -5.1), 0.05, 0.06, 0.14, 6, c("iron"))
	_pot_plant(-20.8, -6.8)
	_pot_plant(-20.8, 6.8)
	_wall(-30, -8, -18, -8, 8.0, [], "wall", "ochre", "WallAnteN")
	_wall(-30, 8, -18, 8, 8.0, [], "wall", "ochre", "WallAnteS")
	_banner(-24, -8, Vector3(0, 0, 1), "imperium", 6.6, 3.0, 1.3)
	_banner(-24, 8, Vector3(0, 0, -1), "imperium", 6.6, 3.0, 1.3)
	_wp("an_entry", -20.6, 0); _wp("an_mid", -24, 0); _wp("an_n", -24, -4.6); _wp("an_s", -24, 4.6); _wp("an_inner", -28.4, 0)


func _build_audience() -> void:
	_floor(-54, -12, -30, 12, 2.0, c("porphyry"), c("cream"))
	_rug(Rect2(-47.2, -1.4, 17.0, 2.8), "purple", "gold")
	for x in [-35.0, -40.0, -45.0]:
		_column(x, -7, 9.0, 0.55, "porphyry")
		_column(x, 7, 9.0, 0.55, "porphyry")
	_beam(Vector3(-45, 9.35, -7), Vector3(-35, 9.35, -7))
	_beam(Vector3(-45, 9.35, 7), Vector3(-35, 9.35, 7))
	# the Ardent Throne on its three-step dais
	_steps(Rect2(-54, -6, 5.4, 12), 1.2)
	_steps(Rect2(-48.6, -5, 0.8, 10), 0.8, "marble2", "marble", false)
	_steps(Rect2(-47.8, -4, 0.8, 8), 0.4, "marble2", "marble", false)
	_collide_box(Vector3(-48.0, 0.6, 0), Vector3(1.6, 1.2, 10))
	_rug(Rect2(-53.4, -1.6, 4.8, 3.2), "purple", "gold", 1.215)
	_throne(-51.6, 0, -PI / 2, 1.2, "marble", "purple", "audience_throne", true)
	# the great sun on the west wall, drapes
	var sun_b := Basis(Vector3.UP, PI / 2)
	_emblem(_mb, Vector3(-53.55, 6.4, 0), sun_b, "sun", c("gold"), 4.2)
	for sz in [-1, 1]:
		_banner(-54, sz * 4.6, Vector3(1, 0, 0), "imperium", 9.0, 6.4, 2.2)
	for p in [Vector2(-46.0, -5.4), Vector2(-46.0, 5.4)]:
		_brazier(p.x, p.y, 0.0, true)
	for p in [Vector2(-33.0, -10.6), Vector2(-33.0, 10.6)]:
		_pot_plant(p.x, p.y)
	_wall(-54, -12, -30, -12, 10.0, [], "wall", "purple", "WallAudN")
	_wall(-54, 12, -30, 12, 10.0, [], "wall", "purple", "WallAudS")
	_wall(-54, -12, -54, 12, 10.0, [], "wall", "purple", "WallAudW")
	_wall(-30, -12, -30, 12, 10.0, [[12.0, DOOR_W, DOOR_H + 0.6]], "wall", "purple", "WallAudE")
	_wp("au_entry", -32.6, 0); _wp("au_mid", -39, 0); _wp("au_front", -44.8, 0)


func _build_gallery() -> void:
	_floor(-3, 18, 3, 34, 1.5, c("lapis"), c("cream"))
	_wall(-3, 18, -3, 34, 7.0, [], "wall", "lapis", "WallGalW")
	_wall(3, 18, 3, 34, 7.0, [], "wall", "lapis", "WallGalE")
	var kings := [
		{"outfit": "toga", "headwear": "crown_silver", "beard": "full", "hair_style": "short"},
		{"outfit": "armour", "headwear": "crown_silver", "beard": "short", "hair_style": "curly"},
		{"outfit": "toga", "headwear": "crown_silver", "beard": "none", "hair_style": "short", "sex": "f"},
		{"outfit": "toga", "headwear": "crown_silver", "beard": "full", "hair_style": "bald"},
	]
	for i in 4:
		var z := 21.5 + i * 3.6
		var sx := -1 if i % 2 == 0 else 1
		var lk: Dictionary = kings[i]
		_statue(sx * 2.05, z, sx * PI / 2, Cast.resolve_look("human", lk, lk.get("sex", "m")), 1.0)
	_banner(-3, 25.4, Vector3(1, 0, 0), "seravel", 6.2, 3.0, 1.2)
	_banner(3, 29.0, Vector3(-1, 0, 0), "seravel", 6.2, 3.0, 1.2)
	_wp("g_n", 0, 20.6); _wp("g_mid", 0, 26); _wp("g_s", 0, 31.6)


func _build_apartments() -> void:
	_floor(-14, 34, 4, 56, 2.0, c("cream"), c("greytile"))
	_floor(4, 34, 14, 56, 1.0, c("wood"), c("wood").darkened(0.08))
	_rug(Rect2(-9.2, 42.6, 8.4, 6.8), "lapis", "cream")
	_rug(Rect2(6.0, 46.0, 6.0, 7.0), "ochre", "gold")
	# study: desk, chair, shelves
	_table(Rect2(-10.4, 38.1, 2.8, 1.1), 0.82, "darkwood")
	_mb.box(Vector3(-9.6, 0.86, 38.6), Vector3(0.6, 0.03, 0.45), c("parchment"))
	_mb.box(Vector3(-8.8, 0.86, 38.4), Vector3(0.45, 0.03, 0.35), c("parchment").darkened(0.08))
	_mb.cyl(Vector3(-10.2, 0.85, 38.3), 0.07, 0.08, 0.16, 6, c("iron"))
	_chair(-9.0, 37.1, PI, "darkwood", "lapis", "ap_desk_chair")
	_scroll_shelf(-13.4, 40.5, 5.0, false)
	_scroll_shelf(-13.4, 48.5, 5.0, false)
	_banner(-9.0, 34, Vector3(0, 0, 1), "seravel", 6.2, 3.2, 1.4)
	_banner(-4.0, 34, Vector3(0, 0, 1), "imperium", 6.2, 3.2, 1.2)
	# the map table: a relief model of Seravel
	_map_table(Vector3(-5.0, 0, 46.0))
	_brazier(-1.8, 40.0, 0.0, true)
	_pot_plant(2.6, 54.6)
	_pot_plant(-12.6, 54.6)
	# bedchamber
	_bed(Vector3(11.4, 0, 50.0))
	_table(Rect2(12.6, 46.6, 1.0, 1.0), 0.7, "darkwood")
	_mb.box(Vector3(9.0, 0.5, 54.9), Vector3(2.6, 1.0, 0.9), c("darkwood"))
	_mb.box(Vector3(9.0, 1.02, 54.9), Vector3(2.7, 0.06, 1.0), c("gold"))
	_collide_box(Vector3(9.0, 0.5, 54.9), Vector3(2.6, 1.0, 0.9))
	_banner(14, 50.0, Vector3(-1, 0, 0), "seravel", 6.0, 2.6, 1.6)
	# walls
	_wall(-14, 34, 14, 34, 7.5, [[14.0, 2.6, 4.0]], "wall", "lapis", "WallAptN")
	_wall(-14, 56, 14, 56, 7.5, [], "wall", "lapis", "WallAptS")
	_wall(-14, 34, -14, 56, 7.5, [], "wall", "lapis", "WallAptW")
	_wall(14, 34, 14, 56, 7.5, [], "wall", "lapis", "WallAptE")
	_wall(4, 34, 4, 56, 7.5, [[9.5, 2.2, 3.6]], "wall", "lapis", "WallAptMid")
	_wp("ap_entry", 0, 36.6); _wp("ap_mid", 0, 43.5); _wp("ap_office", -6.0, 40.6); _wp("ap_map", -1.4, 46.0)
	_wp("ap_bed_door", 4, 43.5); _wp("ap_bed", 8.0, 46.5)


func _map_table(p: Vector3) -> void:
	_table(Rect2(p.x - 1.8, p.z - 1.3, 3.6, 2.6), 0.85, "darkwood")
	var y0 := p.y + 0.86
	var land := c("8a9a52")
	var nx := 12
	var nz := 8
	var cell := 3.2 / nx
	var hgt := func(i: int, j: int) -> float:
		var hx := float(i) / nx
		var hz := float(j) / nz
		var hill := maxf(0.0, 0.18 - Vector2(hx - 0.8, hz - 0.25).length() * 0.5) * 1.6
		return 0.02 + hill + 0.015 * sin(i * 1.7 + j * 2.3)
	for i in nx:
		for j in nz:
			var ax := p.x - 1.6 + i * cell
			var az := p.z - 1.1 + j * (2.2 / nz)
			var bx := ax + cell
			var bz := az + 2.2 / nz
			var h00: float = hgt.call(i, j)
			var h10: float = hgt.call(i + 1, j)
			var h01: float = hgt.call(i, j + 1)
			var h11: float = hgt.call(i + 1, j + 1)
			var col := land if (h00 + h11) * 0.5 < 0.12 else c("a08a5a")
			if (h00 + h11) * 0.5 > 0.2:
				col = c("cfc5ae")
			_mb.tri(Vector3(ax, y0 + h01, bz), Vector3(bx, y0 + h11, bz), Vector3(bx, y0 + h10, az), col)
			_mb.tri(Vector3(ax, y0 + h01, bz), Vector3(bx, y0 + h10, az), Vector3(ax, y0 + h00, az), col.darkened(0.04))
	# the river Sera, cities and roads
	for i in 10:
		var t := float(i) / 9.0
		var x := p.x - 1.6 + t * 3.2
		var z := p.z + 0.5 * sin(t * 4.0) - 0.1
		_mb.box(Vector3(x, y0 + 0.05, z), Vector3(0.38, 0.03, 0.12), c("water"), Basis(Vector3.UP, -0.5 * cos(t * 4.0) * 1.5))
	for cp in [Vector2(-0.6, 0.0), Vector2(0.7, -0.5), Vector2(-1.2, -0.6), Vector2(1.1, 0.6)]:
		var cpos := Vector3(p.x + cp.x, y0 + 0.08, p.z + cp.y)
		_mb.box(cpos, Vector3(0.14, 0.12, 0.14), c("cream"))
		_mb.taper(cpos + Vector3(0, 0.06, 0), Vector2(0.16, 0.16), Vector2(0.16, 0.01), 0.07, c("terracotta"))
	_mb.cyl(Vector3(p.x - 0.6, y0 + 0.14, p.z), 0.03, 0.03, 0.25, 4, c("gold"))
	_mb.box(Vector3(p.x - 0.53, y0 + 0.34, p.z), Vector3(0.14, 0.09, 0.01), c("lapis"))


func _bed(p: Vector3) -> void:
	_mb.box(p + Vector3(0, 0.3, 0), Vector3(3.0, 0.6, 2.2), c("darkwood"))
	_mb.box(p + Vector3(-0.1, 0.68, 0), Vector3(2.8, 0.18, 2.0), c("bed"))
	_mb.box(p + Vector3(-0.4, 0.8, 0), Vector3(1.9, 0.08, 2.08), c("lapis"))
	_mb.box(p + Vector3(1.1, 0.86, 0), Vector3(0.5, 0.18, 1.6), c("cream"))
	_mb.box(p + Vector3(1.45, 1.1, 0), Vector3(0.12, 1.6, 2.3), c("darkwood"))
	_mb.box(p + Vector3(1.48, 1.95, 0), Vector3(0.14, 0.12, 2.4), c("gold"))
	_collide_box(p + Vector3(0, 0.5, 0), Vector3(3.0, 1.0, 2.2))


# ======================================================================== shared props

func _tree(m: MeshBuilder, p: Vector3, h: float, pine := false) -> void:
	if pine:
		m.tube(p, Vector2(0.25, 0.25), Vector2(0.16, 0.16), h * 0.75, 5, c("wood"), false, false, Basis(Vector3.BACK, 0.1))
		m.sphere(p + Vector3(0.3, h * 0.82, 0), h * 0.32, c("hedge").darkened(0.1), 7, 4, Vector3(1.0, 0.38, 1.0))
		m.sphere(p + Vector3(-0.6, h * 0.76, 0.4), h * 0.22, c("hedge"), 6, 3, Vector3(1.0, 0.4, 1.0))
		return
	m.tube(p, Vector2(0.14, 0.14), Vector2(0.1, 0.1), 0.5, 5, c("wood"), false, false)
	m.tube(p + Vector3(0, 0.4, 0), Vector2(h * 0.11, h * 0.11), Vector2(h * 0.15, h * 0.15), h * 0.3, 7, c("cypress"), false, true, Basis.IDENTITY, 0.12)
	m.tube(p + Vector3(0, 0.4 + h * 0.3, 0), Vector2(h * 0.15, h * 0.15), Vector2(0, 0), h * 0.72, 7, c("cypress").lightened(0.04), false, false, Basis.IDENTITY, 0.12)


func _balustrade(ax: float, az: float, bx: float, bz: float, y := 0.0) -> void:
	var a := Vector3(ax, y, az)
	var b := Vector3(bx, y, bz)
	var v := b - a
	var ln := v.length()
	var bs := Basis(Vector3.UP, atan2(-v.z, v.x))
	var mid := (a + b) * 0.5
	_mb.box(mid + Vector3(0, 0.12, 0), Vector3(ln + 0.4, 0.24, 0.62), c("marble2"), bs)
	_mb.box(mid + Vector3(0, 1.08, 0), Vector3(ln + 0.4, 0.16, 0.66), c("marble"), bs)
	_mb.box(mid + Vector3(0, 0.98, 0), Vector3(ln + 0.3, 0.06, 0.5), c("gold").darkened(0.1), bs)
	var n := int(ln / 0.42)
	for i in n:
		var p := a + v * ((i + 0.5) / n)
		if i % 9 == 4:
			_mb.box(p + Vector3(0, 0.6, 0), Vector3(0.5, 0.95, 0.5), c("marble"), bs)
			continue
		_mb.tube(p + Vector3(0, 0.24, 0), Vector2(0.07, 0.07), Vector2(0.15, 0.15), 0.32, 6, c("marble"), false, false)
		_mb.tube(p + Vector3(0, 0.56, 0), Vector2(0.15, 0.15), Vector2(0.07, 0.07), 0.28, 6, c("marble"), false, false)
		_mb.tube(p + Vector3(0, 0.84, 0), Vector2(0.07, 0.07), Vector2(0.11, 0.11), 0.16, 6, c("marble"), false, false)
	_collide_box(mid + Vector3(0, 0.8, 0), Vector3(ln + 0.4, 1.6, 0.66), atan2(-v.z, v.x))


## A banner hanging from a gilded pole and crossbar (free-standing, as on the terrace).
func _pole_banner(x: float, z: float, yaw: float, faction := "imperium", h := 7.5, base_y := 0.0) -> void:
	var bs := Basis(Vector3.UP, yaw)
	var p := Vector3(x, base_y, z)
	var m := MeshBuilder.new()
	m.box(p + Vector3(0, 0.2, 0), Vector3(0.8, 0.4, 0.8), c("marble2"))
	m.tube(p + Vector3(0, 0.4, 0), Vector2(0.07, 0.07), Vector2(0.06, 0.06), h, 6, c("gold").darkened(0.15))
	m.sphere(p + Vector3(0, h + 0.5, 0), 0.14, c("gold"), 6, 4)
	m.tube(p + Vector3(0, h + 0.55, 0), Vector2(0.06, 0.06), Vector2.ZERO, 0.4, 4, c("gold"))
	m.box(p + Vector3(0, h + 0.15, 0) + bs * Vector3(0, 0, 0.12), Vector3(2.1, 0.08, 0.08), c("gold"), bs)
	_banner_cloth(m, p + Vector3(0, h + 0.1, 0) + bs * Vector3(0, 0, 0.14), bs, faction, h * 0.62, 1.7)
	_occluder(m, "PoleBanner")
	_collide_cyl(p, 0.45, 2.0)


# ======================================================================== the terrace

func _build_terrace() -> void:
	_floor(-54, 12, -18, 30, 2.0, c("cream"), c("greytile"))
	_rug(Rect2(-50, 13.9, 32, 2.4), "crimson", "gold")
	_wall(-30, 12, -18, 12, 8.0, [], "wall", "ochre", "WallTerrN")
	# loggia: a colonnade along the north side with a tiled lean-to roof
	for x in [-50.0, -46.0, -42.0, -38.0, -34.0, -30.0, -26.0, -22.0]:
		_column(x, 17.0, 7.0, 0.42)
	_beam(Vector3(-50, 7.35, 17.0), Vector3(-22, 7.35, 17.0))
	_balustrade(-53.6, 12.4, -53.6, 29.6)
	_balustrade(-53.6, 29.6, -18.4, 29.6)
	_balustrade(-18.4, 29.6, -18.4, 18.4)
	_pole_banner(-52.0, 28.0, -PI / 4 + PI, "imperium", 7.0)
	_pole_banner(-52.0, 14.0, PI / 2, "imperium", 7.0)
	_pole_banner(-20.0, 28.0, PI, "imperium", 7.0)
	var lk := Cast.resolve_look("human", {"outfit": "toga", "headwear": "laurel", "prop": "spear", "cloak": "x", "hair_style": "short", "beard": "full"}, "m")
	_statue(-38.0, 26.2, PI * 0.75, lk, 1.8)
	_brazier(-47.5, 27.6, 0.0, true, 1.3)
	_brazier(-24.0, 27.6, 0.0, false, 1.3)
	_brazier(-51.6, 20.0, 0.0, false, 1.3)
	_bench(-44.0, 22.0, 3.2, false, "terr_bench", -PI / 2, 2)
	_bench(-30.0, 22.0, 3.2, false, "terr_bench_e", -PI / 2, 2)
	for p in [Vector2(-20.4, 13.0), Vector2(-53.0, 13.0)]:
		_pot_plant(p.x, p.y)
	_wp("t_door", -20.6, 15.0); _wp("t_mid", -34.0, 20.2); _wp("t_view", -48.0, 24.5); _wp("t_south", -32.0, 27.4)


# ======================================================================== ceilings and roofs

func _cover(rect: Rect2, h: float, accent: String) -> void:
	var p := rect.position
	var sz := rect.size
	var cx := p.x + sz.x * 0.5
	var cz := p.y + sz.y * 0.5
	# coffered ceiling seen from below
	_mb.box(Vector3(cx, h + 0.2, cz), Vector3(sz.x, 0.4, sz.y), c("marble"))
	var step := 3.0
	var nx := int(sz.x / step)
	var nz := int(sz.y / step)
	for i in nx + 1:
		var x := p.x + sz.x * float(i) / nx
		_mb.box(Vector3(x, h - 0.12, cz), Vector3(0.36, 0.3, sz.y), c("marble2"))
	for j in nz + 1:
		var z := p.y + sz.y * float(j) / nz
		_mb.box(Vector3(cx, h - 0.12, z), Vector3(sz.x, 0.3, 0.36), c("marble2"))
	for i in nx:
		for j in nz:
			var x0 := p.x + sz.x * float(i) / nx + 0.3
			var x1 := p.x + sz.x * float(i + 1) / nx - 0.3
			var z0 := p.y + sz.y * float(j) / nz + 0.3
			var z1 := p.y + sz.y * float(j + 1) / nz - 0.3
			var y := h - 0.005
			_mb.quad(Vector3(x0, y, z0), Vector3(x1, y, z0), Vector3(x1, y, z1), Vector3(x0, y, z1), c(accent).darkened(0.2))
			var g := 0.32
			var mx := (x0 + x1) * 0.5
			var mz := (z0 + z1) * 0.5
			_mb.quad(Vector3(mx - g, y - 0.01, mz - g), Vector3(mx + g, y - 0.01, mz - g), Vector3(mx + g, y - 0.01, mz + g), Vector3(mx - g, y - 0.01, mz + g), c("gold"))
	# hipped terracotta roof above
	var ov := 0.9
	var along_x := sz.x >= sz.y
	var bw := sz.x + ov * 2
	var bd := sz.y + ov * 2
	var rh := minf(sz.x, sz.y) * 0.28
	var top := Vector2(maxf(bw - bd, 0.2), 0.05) if along_x else Vector2(0.05, maxf(bd - bw, 0.2))
	_mb.box(Vector3(cx, h + 0.5, cz), Vector3(bw, 0.2, bd), c("marble"))
	_mb.taper(Vector3(cx, h + 0.6, cz), Vector2(bw, bd), top, rh, c("roof"))
	_mb.taper(Vector3(cx, h + 0.6 + rh - 0.02, cz), top + Vector2(0.25, 0.25), top + Vector2(0.15, 0.15), 0.18, c("roof").darkened(0.15))


func _lean_to(a: Vector3, b: Vector3, out: Vector3, depth: float, rise: float) -> void:
	# a tiled roof strip from the line a-b (low edge) running `depth` along `out` and up by `rise`
	var o := out.normalized() * depth + Vector3(0, rise, 0)
	_mb.quad(a, b, b + o, a + o, c("roof"))
	_mb.quad(b + Vector3(0, -0.12, 0), a + Vector3(0, -0.12, 0), a + o + Vector3(0, -0.12, 0), b + o + Vector3(0, -0.12, 0), c("wood"))
	var n := int(a.distance_to(b) / 0.6)
	for i in n + 1:
		var p := a.lerp(b, float(i) / n)
		_mb.box(p + o * 0.5 + Vector3(0, 0.06, 0), Vector3(0.12, 0.1, 0.12) + Vector3(absf(o.x), absf(o.y), absf(o.z)) * Vector3(1, 0, 1), c("roof").darkened(0.12))


func _build_roofs() -> void:
	_cover(Rect2(-14, -46, 28, 28), 9.0, "porphyry")
	_cover(Rect2(18, -12, 40, 24), 9.0, "serpentine")
	_cover(Rect2(-30, -8, 12, 16), 8.0, "ochre")
	_cover(Rect2(-54, -12, 24, 24), 10.0, "purple")
	_cover(Rect2(-3, 18, 6, 16), 7.0, "lapis")
	_cover(Rect2(-14, 34, 28, 22), 7.5, "lapis")
	# courtyard portico roofs, sloping up to the walls
	var y0 := 7.3
	_lean_to(Vector3(-13.4, y0, -13.4), Vector3(13.4, y0, -13.4), Vector3(0, 0, -1), 4.9, 1.2)
	_lean_to(Vector3(13.4, y0, 13.4), Vector3(-13.4, y0, 13.4), Vector3(0, 0, 1), 4.9, 1.2)
	_lean_to(Vector3(-13.4, y0, 13.4), Vector3(-13.4, y0, -13.4), Vector3(-1, 0, 0), 4.9, 1.2)
	_lean_to(Vector3(13.4, y0, -13.4), Vector3(13.4, y0, 13.4), Vector3(1, 0, 0), 4.9, 1.2)
	_lean_to(Vector3(-50.5, 7.7, 17.6), Vector3(-21.5, 7.7, 17.6), Vector3(0, 0, -1), 5.8, 1.0)


# ======================================================================== the city of Caelora

const CITY_Y := -16.0
var _chunks := {}


func _chunk(p: Vector3) -> MeshBuilder:
	var k := Vector2i(floori(p.x / 160.0), floori(p.z / 160.0))
	if not _chunks.has(k):
		_chunks[k] = MeshBuilder.new()
	return _chunks[k]


func _house(m: MeshBuilder, p: Vector3, w: float, dp: float, h: float, wall: Color, detail: bool, rng: RandomNumberGenerator) -> void:
	m.box(p + Vector3(0, h * 0.5, 0), Vector3(w, h, dp), wall)
	m.box(p + Vector3(0, h - 0.15, 0), Vector3(w + 0.3, 0.3, dp + 0.3), wall.lightened(0.12))
	var along_x := w >= dp
	var rh := minf(w, dp) * rng.randf_range(0.28, 0.4)
	var top := Vector2(maxf(w - dp, 0.2), 0.05) if along_x else Vector2(0.05, maxf(dp - w, 0.2))
	m.taper(p + Vector3(0, h, 0), Vector2(w + 0.9, dp + 0.9), top, rh, c("roof").darkened(rng.randf_range(-0.05, 0.12)))
	if not detail:
		return
	# windows on the faces turned toward the palace
	var floors := int(h / 3.2)
	var dark := Color("4a3a40")
	var fx := -signf(p.x) if absf(p.x) > 1.0 else 1.0
	var fz := -signf(p.z) if absf(p.z) > 1.0 else 1.0
	var nwx := int(w / 2.6)
	var nwz := int(dp / 2.6)
	for f in floors:
		var y := 1.6 + f * 3.2
		var ww := 0.8
		var wh := 1.3 if f > 0 else 2.0
		if f == 0 and rng.randf() < 0.5:
			ww = 1.4
		for i in nwx:
			var x := p.x - w * 0.5 + (i + 0.5) * w / nwx
			var z := p.z + fz * (dp * 0.5 + 0.02)
			var a := Vector3(x - ww * 0.5, p.y + y - wh * 0.5, z)
			var b := Vector3(x + ww * 0.5, p.y + y - wh * 0.5, z)
			if fz > 0:
				m.quad(a, b, b + Vector3(0, wh, 0), a + Vector3(0, wh, 0), dark)
			else:
				m.quad(b, a, a + Vector3(0, wh, 0), b + Vector3(0, wh, 0), dark)
		for i in nwz:
			var z2 := p.z - dp * 0.5 + (i + 0.5) * dp / nwz
			var x2 := p.x + fx * (w * 0.5 + 0.02)
			var a2 := Vector3(x2, p.y + y - wh * 0.5, z2 + ww * 0.5)
			var b2 := Vector3(x2, p.y + y - wh * 0.5, z2 - ww * 0.5)
			if fx > 0:
				m.quad(a2, b2, b2 + Vector3(0, wh, 0), a2 + Vector3(0, wh, 0), dark)
			else:
				m.quad(b2, a2, a2 + Vector3(0, wh, 0), b2 + Vector3(0, wh, 0), dark)


## A columned temple in its own frame: front faces local -Z. w across the front, dp deep.
func _temple(m: MeshBuilder, p: Vector3, yaw: float, w: float, dp: float, colh: float, akroterion := true) -> void:
	var keep := m.xf
	m.xf = Transform3D(Basis(Vector3.UP, yaw), p)
	var pod := 1.8
	m.box(Vector3(0, pod * 0.5, 0), Vector3(w + 2.0, pod, dp + 2.0), c("stone"))
	for i in 4:
		m.box(Vector3(0, pod * (i + 0.5) / 4.0, -dp * 0.5 - 1.0 - (4 - i) * 0.5), Vector3(w * 0.8, pod * (i + 1) / 4.0, 0.5), c("marble2"))
	m.box(Vector3(0, pod + colh * 0.5, dp * 0.12), Vector3(w - 3.0, colh, dp * 0.7), c("wall"))
	var r := colh * 0.065
	var nf := maxi(4, int(w / (r * 5.0)))
	var ns := maxi(3, int(dp / (r * 5.0)))
	for i in nf:
		var x := -w * 0.5 + 0.8 + (w - 1.6) * float(i) / (nf - 1)
		for zz in [-dp * 0.5 + 0.8, dp * 0.5 - 0.8]:
			m.tube(Vector3(x, pod, zz), Vector2(r, r), Vector2(r * 0.85, r * 0.85), colh, 8, c("marble"), false, false, Basis.IDENTITY, 0.04)
	for j in range(1, ns - 1):
		var z := -dp * 0.5 + 0.8 + (dp - 1.6) * float(j) / (ns - 1)
		for xx in [-w * 0.5 + 0.8, w * 0.5 - 0.8]:
			m.tube(Vector3(xx, pod, z), Vector2(r, r), Vector2(r * 0.85, r * 0.85), colh, 8, c("marble"), false, false, Basis.IDENTITY, 0.04)
	var ey := pod + colh
	m.box(Vector3(0, ey + 0.5, 0), Vector3(w, 1.0, dp), c("marble"))
	m.box(Vector3(0, ey + 0.3, 0), Vector3(w + 0.1, 0.25, dp + 0.1), c("gold").darkened(0.1))
	var gh := w * 0.22
	m.gable(Vector3(0, ey + 1.0, 0), Vector2(dp + 0.8, w + 0.8), gh, c("roof"), c("marble"), Basis(Vector3.UP, PI / 2))
	if akroterion:
		m.tube(Vector3(0, ey + 1.0 + gh, -dp * 0.5 - 0.3), Vector2(0.4, 0.4), Vector2.ZERO, gh * 0.4, 5, c("gold"))
		for sx in [-1, 1]:
			m.sphere(Vector3(sx * (w * 0.5 + 0.2), ey + 1.2, -dp * 0.5 - 0.3), 0.4, c("gold"), 5, 3)
	m.xf = keep


func _colonnade(m: MeshBuilder, a: Vector3, b: Vector3, h: float, out: Vector3) -> void:
	var n := int(a.distance_to(b) / 4.0)
	for i in n + 1:
		var p := a.lerp(b, float(i) / n)
		m.tube(p, Vector2(0.45, 0.45), Vector2(0.4, 0.4), h, 8, c("marble"), false, false, Basis.IDENTITY, 0.04)
	var mid := (a + b) * 0.5
	var v := b - a
	var bs := Basis(Vector3.UP, atan2(-v.z, v.x))
	m.box(mid + Vector3(0, h + 0.4, 0), Vector3(v.length() + 1.0, 0.8, 1.2), c("marble"), bs)
	var o := out.normalized() * 6.0
	m.quad(a + Vector3(0, h + 0.8, 0), b + Vector3(0, h + 0.8, 0), b + o + Vector3(0, h + 2.2, 0), a + o + Vector3(0, h + 2.2, 0), c("roof"))
	m.box(mid + o + Vector3(0, (h + 2.2) * 0.5, 0), Vector3(v.length() + 1.0, h + 2.2, 0.8), c("wall"), bs)


func _build_city() -> void:
	var Y := CITY_Y
	_collide_box(Vector3(1, -0.5, 4), Vector3(128, 1.0, 118))   # the palace floor
	var base := MeshBuilder.new()
	base.jitter = 0.02
	# the plain, the paved city and its main streets
	base.quad(Vector3(-2200, Y - 0.3, 2200), Vector3(2200, Y - 0.3, 2200), Vector3(2200, Y - 0.3, -2200), Vector3(-2200, Y - 0.3, -2200), c("earth"))
	base.quad(Vector3(-380, Y, 380), Vector3(380, Y, 380), Vector3(380, Y, -380), Vector3(-380, Y, -380), c("paving"))
	for i in range(-7, 8):
		var t := i * 52.0 - 13.0
		base.quad(Vector3(t - 3, Y + 0.02, 380), Vector3(t + 3, Y + 0.02, 380), Vector3(t + 3, Y + 0.02, -380), Vector3(t - 3, Y + 0.02, -380), c("stone"))
		base.quad(Vector3(-380, Y + 0.03, t + 3), Vector3(380, Y + 0.03, t + 3), Vector3(380, Y + 0.03, t - 3), Vector3(-380, Y + 0.03, t - 3), c("stone"))
	# the palace podium (fitted to the buildings) and its buttressed retaining walls
	var pods := [Rect2(-54.7, -46.7, 113.4, 77.4), Rect2(-14.7, 30.0, 29.4, 26.7)]
	for pr in pods:
		var pd: Rect2 = pr
		var pc := Vector3(pd.position.x + pd.size.x * 0.5, 0, pd.position.y + pd.size.y * 0.5)
		base.box(pc + Vector3(0, (Y - 0.06) * 0.5, 0), Vector3(pd.size.x, -Y - 0.06, pd.size.y), c("stone2"))
		base.box(pc + Vector3(0, -0.7, 0), Vector3(pd.size.x + 0.8, 0.5, pd.size.y + 0.8), c("marble"))
		var nb := int(pd.size.x / 7.0)
		var nbz := int(pd.size.y / 7.0)
		for k in nb + 1:
			var bx := lerpf(pd.position.x, pd.end.x, float(k) / nb)
			for bz in [pd.position.y, pd.end.y]:
				base.box(Vector3(bx, (Y - 1.0) * 0.5, bz), Vector3(1.8, -Y - 1.0, 2.6), c("stone"))
		for k in nbz + 1:
			var bz2 := lerpf(pd.position.y, pd.end.y, float(k) / nbz)
			for bx2 in [pd.position.x, pd.end.x]:
				base.box(Vector3(bx2, (Y - 1.0) * 0.5, bz2), Vector3(2.6, -Y - 1.0, 1.8), c("stone"))
	var pod := Rect2(-54.7, -46.7, 113.4, 103.4)
	# a monumental stair down to the forum on the west
	for i in 16:
		var y := -1.0 - i * 0.94
		base.box(Vector3(-56.0 - i * 1.1, y * 0.5 + Y * 0.5, 8.0), Vector3(1.1, y - Y, 10.0), c("marble2"))
	_add_city_mesh(base, false)

	var rng := RandomNumberGenerator.new()
	var forum := Rect2(-170, 14, 86, 52)
	var acro := Rect2(-330, -95, 160, 150)
	var amph := Vector2(190, 170)
	var walls := [Color("e3d3b6"), Color("d9c09a"), Color("ece2cf"), Color("cfae86"), Color("e0c7a4"), Color("d4b48e")]
	for gx in range(-14, 15):
		for gz in range(-14, 15):
			var cx := gx * 26.0
			var cz := gz * 26.0
			var cp := Vector2(cx, cz)
			if pods[0].grow(14).has_point(cp) or pods[1].grow(14).has_point(cp) or (cp.x > -60 and cp.x < 60 and cp.y > -50 and cp.y < 30) or forum.grow(10).has_point(cp) or acro.grow(6).has_point(cp) or cp.distance_to(amph) < 62.0:
				continue
			if absf(cx - 13.0 + 13.0) < 1 and false:
				continue
			rng.seed = hash(Vector2i(gx, gz)) + 99
			var dist := cp.length()
			var m := _chunk(Vector3(cx, 0, cz))
			var roll := rng.randf()
			var gp := Vector3(cx, Y, cz)
			if roll < 0.06 and dist < 330:
				_temple(m, gp, rng.randi_range(0, 3) * PI / 2, rng.randf_range(12, 16), rng.randf_range(18, 22), rng.randf_range(7, 9))
			elif roll < 0.13:
				m.box(gp + Vector3(0, 0.1, 0), Vector3(20, 0.2, 20), c("grass"))
				for k in rng.randi_range(4, 8):
					_tree(m, gp + Vector3(rng.randf_range(-9, 9), 0.2, rng.randf_range(-9, 9)), rng.randf_range(6, 11), rng.randf() < 0.35)
			elif roll < 0.17 and dist < 300:
				m.box(gp + Vector3(0, 0.08, 0), Vector3(20, 0.16, 20), c("cream"))
				m.tube(gp + Vector3(0, 0.16, 0), Vector2(3.0, 3.0), Vector2(2.9, 2.9), 0.8, 10, c("marble"))
				m.tube(gp + Vector3(0, 0.9, 0), Vector2(2.5, 2.5), Vector2(2.5, 2.5), 0.05, 10, c("water"))
				m.tube(gp + Vector3(0, 0.16, 0), Vector2(0.6, 0.6), Vector2(0.5, 0.5), 3.5, 8, c("marble2"))
				for k in 4:
					_tree(m, gp + Vector3(8.5 * (1 if k % 2 else -1), 0.1, 8.5 * (1 if k < 2 else -1)), 8.0)
			else:
				var detail := dist < 240
				var n := rng.randi_range(2, 4) if detail else rng.randi_range(1, 2)
				var hk := clampf(1.3 - dist / 420.0, 0.6, 1.3)
				for k in n:
					var w := rng.randf_range(7, 12)
					var dp := rng.randf_range(7, 12)
					var off := Vector3(rng.randf_range(-11 + w * 0.5, 11 - w * 0.5), 0, rng.randf_range(-11 + dp * 0.5, 11 - dp * 0.5))
					var h := rng.randf_range(4.5, 10.0) * hk
					_house(m, gp + off, w, dp, h, walls[rng.randi() % walls.size()], detail, rng)
				if rng.randf() < 0.35:
					_tree(m, gp + Vector3(rng.randf_range(-11, 11), 0, 11.5), rng.randf_range(6, 10))

	# the forum below the terrace: colonnades, a fountain with a statue, temples, banners
	var fm := _chunk(Vector3(forum.position.x + 40, 0, forum.position.y))
	var fp := Vector3(forum.position.x + forum.size.x * 0.5, Y, forum.position.y + forum.size.y * 0.5)
	fm.box(fp + Vector3(0, 0.1, 0), Vector3(forum.size.x, 0.2, forum.size.y), c("cream"))
	_floor_on(fm, forum.grow(-6), 4.0, c("cream"), c("greytile"), Y + 0.21)
	_colonnade(fm, Vector3(forum.position.x + 6, Y, forum.position.y + 5), Vector3(forum.end.x - 6, Y, forum.position.y + 5), 7.0, Vector3(0, 0, -1))
	_colonnade(fm, Vector3(forum.end.x - 6, Y, forum.end.y - 5), Vector3(forum.position.x + 6, Y, forum.end.y - 5), 7.0, Vector3(0, 0, 1))
	fm.tube(fp + Vector3(0, 0.2, 0), Vector2(7, 7), Vector2(6.8, 6.8), 1.0, 14, c("marble"))
	fm.tube(fp + Vector3(0, 1.0, 0), Vector2(6.3, 6.3), Vector2(6.3, 6.3), 0.06, 14, c("water"))
	fm.tube(fp + Vector3(0, 0.2, 0), Vector2(1.6, 1.6), Vector2(1.3, 1.3), 4.5, 8, c("marble2"))
	var st := MeshInstance3D.new()
	st.mesh = CharacterBuilder.build_static_mesh(Cast.resolve_look("human", {"outfit": "armour", "headwear": "laurel", "prop": "spear", "cloak": "x", "hair_style": "curly", "beard": "short"}, "m"), true)
	st.position = fp + Vector3(0, 4.7, 0)
	st.rotation.y = -PI / 2
	st.scale = Vector3.ONE * 3.2
	add_child(st)
	_temple(fm, Vector3(forum.position.x - 4, Y, fp.z), PI / 2, 18, 26, 10)
	for k in 5:
		var bx := forum.position.x + 14 + k * 15.0
		for side in [-1, 1]:
			var bz: float = fp.z + side * (forum.size.y * 0.5 - 9.5)
			var pbm := MeshBuilder.new()
			pbm.tube(Vector3(bx, Y, bz), Vector2(0.12, 0.12), Vector2(0.1, 0.1), 10, 6, c("gold").darkened(0.15))
			pbm.box(Vector3(bx, Y + 9.6, bz), Vector3(0.1, 0.1, 2.6), c("gold"))
			_banner_cloth(pbm, Vector3(bx, Y + 9.5, bz), Basis(Vector3.UP, -PI / 2), "imperium", 6.5, 2.2)
			fm.append(pbm)

	# the acropolis on the western skyline: terraces, a great stair and the Temple of the Sun
	var am := MeshBuilder.new()
	var ac := Vector3(acro.position.x + acro.size.x * 0.5, Y, acro.position.y + acro.size.y * 0.5)
	var lv := [[Vector2(150, 140), 9.0], [Vector2(112, 100), 9.0], [Vector2(78, 66), 8.0]]
	var y0 := Y
	for l in lv:
		var sz: Vector2 = l[0]
		var hh: float = l[1]
		am.box(Vector3(ac.x, y0 + hh * 0.5, ac.z), Vector3(sz.x, hh, sz.y), c("stone"))
		am.box(Vector3(ac.x, y0 + hh - 0.3, ac.z), Vector3(sz.x + 1.0, 0.6, sz.y + 1.0), c("marble"))
		for k in 9:
			var bz2 := ac.z - sz.y * 0.5 + sz.y * (k + 0.5) / 9.0
			am.box(Vector3(ac.x + sz.x * 0.5 + 0.4, y0 + hh * 0.5, bz2), Vector3(0.8, hh, 1.6), c("stone2"))
		var gx2 := ac.x + sz.x * 0.5
		for k in 7:
			var bzz := ac.z - 30 + k * 10.0
			if absf(bzz - ac.z) > 8.0:
				_banner_cloth(am, Vector3(gx2 + 0.5, y0 + hh - 0.4, bzz), Basis(Vector3.UP, PI / 2), "imperium", hh * 0.75, 2.6)
		y0 += hh
	# the great stair up the east face
	var steps_n := 26
	for i in steps_n:
		var t3 := float(i) / steps_n
		am.box(Vector3(ac.x + 75.0 + 6.0 - t3 * 70.0, Y + (i + 0.5) * (26.0 / steps_n) * 0.5, ac.z), Vector3(70.0 / steps_n + 0.2, (i + 1) * (26.0 / steps_n), 16.0), c("marble2"))
	_temple(am, Vector3(ac.x - 4, y0, ac.z), -PI / 2, 30, 46, 14)
	_temple(am, Vector3(ac.x + 8, Y + 18.0, ac.z - 40), -PI / 2, 14, 20, 8, false)
	_temple(am, Vector3(ac.x + 8, Y + 18.0, ac.z + 40), -PI / 2, 14, 20, 8, false)
	for k in 12:
		var a2 := TAU * k / 12.0
		_tree(am, Vector3(ac.x + cos(a2) * 46.0, Y + 18.0, ac.z + sin(a2) * 40.0), 9.0)
	_add_city_mesh(am, false)

	# the aqueduct striding in from the hills
	var aq := MeshBuilder.new()
	var a0 := Vector3(-900, Y, -420)
	var a1 := Vector3(-70, Y, -70)
	var segs := int(a0.distance_to(a1) / 11.0)
	var dir := (a1 - a0).normalized()
	var ab := Basis(Vector3.UP, atan2(-dir.z, dir.x))
	for i in segs:
		var p := a0.lerp(a1, float(i) / segs)
		aq.box(p + Vector3(0, 7.5, 0), Vector3(2.2, 15.0, 3.0), c("stone2"), ab)
		aq.box(p + Vector3(0, 21.0, 0), Vector3(1.6, 9.0, 2.6), c("stone2"), ab)
	var mid := (a0 + a1) * 0.5
	aq.box(mid + Vector3(0, 15.6, 0), Vector3(a0.distance_to(a1), 1.4, 3.2), c("stone"), ab)
	aq.box(mid + Vector3(0, 26.0, 0), Vector3(a0.distance_to(a1), 1.6, 3.0), c("stone"), ab)
	_add_city_mesh(aq, false)

	# the amphitheatre
	var amx := MeshBuilder.new()
	var ap := Vector3(amph.x, Y, amph.y)
	amx.ring_sector(ap, 30, 50, 0, TAU, 18.0, 32, c("stone"), c("stone2"))
	amx.ring_sector(ap, 18, 30, 0, TAU, 6.0, 24, c("marble2"))
	for row in 3:
		for k in 32:
			var t4 := TAU * (k + 0.5) / 32.0
			var nrm := Vector3(cos(t4), 0, sin(t4))
			var tan := Vector3(-sin(t4), 0, cos(t4))
			var o := ap + nrm * 50.05 + Vector3(0, 2.0 + row * 5.6, 0)
			amx.quad(o - tan * 1.4, o + tan * 1.4, o + tan * 1.4 + Vector3(0, 3.6, 0), o - tan * 1.4 + Vector3(0, 3.6, 0), Color("5a4648"))
	_add_city_mesh(amx, false)

	for k in _chunks:
		_add_city_mesh(_chunks[k], false)
	_build_horizon()


func _floor_on(m: MeshBuilder, r: Rect2, tile: float, ca: Color, cb: Color, y: float) -> void:
	var nx := int(r.size.x / tile)
	var nz := int(r.size.y / tile)
	for i in nx:
		for j in nz:
			var ax := r.position.x + i * tile
			var az := r.position.y + j * tile
			m.quad(Vector3(ax, y, az + tile), Vector3(ax + tile, y, az + tile), Vector3(ax + tile, y, az), Vector3(ax, y, az), ca if (i + j) % 2 == 0 else cb)


func _add_city_mesh(m: MeshBuilder, shadows: bool, mat: Material = null) -> MeshInstance3D:
	if m.is_empty():
		return null
	var mi := m.instance()
	if mat != null:
		mi.mesh.surface_set_material(0, mat)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	return mi


func _build_horizon() -> void:
	# mountains: lit by the sun, but kept out of the fog so they read as distant violet ranges
	var mm := MeshBuilder.new()
	mm.jitter = 0.06
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for i in 46:
		var a := TAU * float(i) / 46.0 + rng.randf_range(-0.05, 0.05)
		var r := rng.randf_range(1300, 1700)
		var p := Vector3(cos(a) * r, CITY_Y - 5.0, sin(a) * r)
		var h := rng.randf_range(45, 130)
		var west := clampf(-cos(a), 0.0, 1.0)
		var col := Color("a596c2").lerp(Color("8f86b8"), rng.randf()).lerp(Color("c2a2bc"), west * 0.5)
		mm.tube(p, Vector2(rng.randf_range(230, 400), rng.randf_range(160, 280)), Vector2.ZERO, h, 7, col, false, false,
			Basis(Vector3.UP, rng.randf() * TAU), 0.12, 0.0, TAU, Vector3(rng.randf_range(-40, 40), 0, rng.randf_range(-40, 40)))
	var mmat := MeshBuilder.material().duplicate() as StandardMaterial3D
	mmat.disable_fog = true
	_add_city_mesh(mm, false, mmat)
	# faceted evening clouds
	var cm := MeshBuilder.new()
	cm.jitter = 0.08
	for i in 34:
		var a2 := rng.randf_range(-PI * 0.8, PI * 0.8) + PI
		var r2 := rng.randf_range(800, 1300)
		var cp := Vector3(cos(a2) * r2, rng.randf_range(140, 300), sin(a2) * r2)
		var cb := Basis(Vector3.UP, a2 + PI / 2 + rng.randf_range(-0.3, 0.3))
		var ln := rng.randf_range(90, 220)
		for k in rng.randi_range(4, 7):
			var t := rng.randf_range(-0.5, 0.5)
			var lump := Vector3(rng.randf_range(0.25, 0.45) * ln, rng.randf_range(5, 12), rng.randf_range(12, 30))
			var lp := cp + cb * Vector3(t * ln, rng.randf_range(-6, 6), rng.randf_range(-15, 15))
			var lb := cb * Basis(Vector3.UP, rng.randf_range(-0.25, 0.25))
			cm.sphere(lp + Vector3(0, lump.y * 0.35, 0), 1.0, Color("f8c99a").lerp(Color("f4a982"), rng.randf()), 5, 3, lump, lb)
			cm.sphere(lp - Vector3(0, lump.y * 0.3, 0), 1.0, Color("b392bd").lerp(Color("d49aa8"), rng.randf()), 5, 3, lump * Vector3(0.95, 0.7, 0.95), lb)
	var cmat := StandardMaterial3D.new()
	cmat.vertex_color_use_as_albedo = true
	cmat.vertex_color_is_srgb = true
	cmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	cmat.disable_fog = true
	_add_city_mesh(cm, false, cmat)


# ======================================================================== navigation graph

func _wp(nm: String, x: float, z: float) -> void:
	waypoints[nm] = Vector3(x, 0, z)


func _build_graph() -> void:
	var edges := [
		# courtyard
		["c_n", "c_mid_n"], ["c_s", "c_mid_s"], ["c_e", "c_mid_e"], ["c_w", "c_mid_w"],
		["c_mid_n", "c_pl_ne"], ["c_pl_ne", "c_mid_e"], ["c_mid_e", "c_pl_se"], ["c_pl_se", "c_mid_s"],
		["c_mid_s", "c_pl_sw"], ["c_pl_sw", "c_mid_w"], ["c_mid_w", "c_pl_nw"], ["c_pl_nw", "c_mid_n"],
		["c_n", "p_n"], ["c_s", "p_s"], ["c_e", "p_e"], ["c_w", "p_w"],
		["p_n", "p_ne"], ["p_ne", "p_e"], ["p_e", "p_se"], ["p_se", "p_s"], ["p_s", "p_sw"], ["p_sw", "p_w"], ["p_w", "p_nw"], ["p_nw", "p_n"],
		["p_n", "d_council"], ["p_e", "d_kings"], ["p_w", "d_ante"], ["p_s", "d_gallery"], ["p_sw", "d_terrace"],
		["d_terrace", "t_door"], ["t_door", "t_mid"], ["t_mid", "t_view"], ["t_mid", "t_south"], ["t_view", "t_south"],
		# council
		["d_council", "cu_entry"], ["cu_entry", "cu_aisle"], ["cu_aisle", "cu_floor"], ["cu_floor", "cu_floor_w"], ["cu_floor", "cu_floor_e"],
		["cu_floor_w", "cu_front"], ["cu_floor_e", "cu_front"],
		# hall of kings
		["d_kings", "kh_entry"], ["kh_entry", "kh_a_n"], ["kh_entry", "kh_a_s"], ["kh_a_n", "kh_b_n"], ["kh_a_s", "kh_b_s"],
		["kh_a_n", "kh_n1"], ["kh_a_s", "kh_s1"], ["kh_b_n", "kh_n2"], ["kh_b_s", "kh_s2"], ["kh_n1", "kh_n2"], ["kh_s1", "kh_s2"],
		["kh_b_n", "kh_apse"], ["kh_b_s", "kh_apse"],
		# petitions & audience
		["d_ante", "an_entry"], ["an_entry", "an_mid"], ["an_mid", "an_n"], ["an_mid", "an_s"], ["an_mid", "an_inner"],
		["an_inner", "au_entry"], ["au_entry", "au_mid"], ["au_mid", "au_front"],
		# gallery & apartments
		["d_gallery", "g_n"], ["g_n", "g_mid"], ["g_mid", "g_s"], ["g_s", "ap_entry"], ["ap_entry", "ap_mid"],
		["ap_mid", "ap_office"], ["ap_mid", "ap_map"], ["ap_mid", "ap_bed_door"], ["ap_bed_door", "ap_bed"], ["ap_entry", "ap_office"],
	]
	var i := 0
	for nm in waypoints:
		_wp_ids[nm] = i
		astar.add_point(i, waypoints[nm])
		i += 1
	for e in edges:
		if not (_wp_ids.has(e[0]) and _wp_ids.has(e[1])):
			push_error("Palace: bad edge %s" % [e])
			continue
		astar.connect_points(_wp_ids[e[0]], _wp_ids[e[1]])


func nearest_waypoint(p: Vector3) -> String:
	var id := astar.get_closest_point(Vector3(p.x, 0, p.z))
	for nm in _wp_ids:
		if _wp_ids[nm] == id:
			return nm
	return ""


func path_between(from_wp: String, to_wp: String) -> PackedVector3Array:
	if not (_wp_ids.has(from_wp) and _wp_ids.has(to_wp)):
		return PackedVector3Array()
	return astar.get_point_path(_wp_ids[from_wp], _wp_ids[to_wp])
