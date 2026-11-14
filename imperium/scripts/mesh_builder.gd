class_name MeshBuilder
extends RefCounted
## Accumulates flat-shaded, vertex-coloured triangles and turns them into an ArrayMesh.
## Every model in Imperium (architecture, props, characters) is built through this class,
## so the whole look comes from code and can be regenerated at will.
##
## Convention: callers give polygon corners counter-clockwise as seen from the front;
## the builder emits them in Godot's clockwise front-face order.
## `xf` transforms every point added; `bone` (when >= 0) rigidly skins new vertices to that bone.

var xf := Transform3D.IDENTITY
var bone := -1

var _v := PackedVector3Array()
var _n := PackedVector3Array()
var _c := PackedColorArray()
var _b := PackedInt32Array()
var _w := PackedFloat32Array()

static var _mat: StandardMaterial3D
static var _mat_glow: StandardMaterial3D


static func material() -> StandardMaterial3D:
	if _mat == null:
		_mat = StandardMaterial3D.new()
		_mat.vertex_color_use_as_albedo = true
		_mat.vertex_color_is_srgb = true
		_mat.roughness = 0.82
		_mat.metallic_specular = 0.25
	return _mat


static func glow_material() -> StandardMaterial3D:
	if _mat_glow == null:
		_mat_glow = StandardMaterial3D.new()
		_mat_glow.vertex_color_use_as_albedo = true
		_mat_glow.vertex_color_is_srgb = true
		_mat_glow.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return _mat_glow


func is_empty() -> bool:
	return _v.is_empty()


func triangle_count() -> int:
	return _v.size() / 3


func tri(a: Vector3, b: Vector3, c: Vector3, col: Color) -> void:
	a = xf * a
	b = xf * b
	c = xf * c
	var n := (b - a).cross(c - a)
	if n.length_squared() < 1e-14:
		return
	n = n.normalized()
	_v.append(a)
	_v.append(c)
	_v.append(b)
	for i in 3:
		_n.append(n)
		_c.append(col)
		if bone >= 0:
			_b.append_array([bone, 0, 0, 0])
			_w.append_array([1.0, 0.0, 0.0, 0.0])


func quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3, col: Color) -> void:
	tri(a, b, c, col)
	tri(a, c, d, col)


## Eight corners indexed (x?1:0) + (y?2:0) + (z?4:0).
func hexa(p: Array, col: Color, skip_bottom := false) -> void:
	quad(p[6], p[7], p[3], p[2], col)          # +Y
	if not skip_bottom:
		quad(p[0], p[1], p[5], p[4], col)      # -Y
	quad(p[4], p[5], p[7], p[6], col)          # +Z
	quad(p[1], p[0], p[2], p[3], col)          # -Z
	quad(p[5], p[1], p[3], p[7], col)          # +X
	quad(p[0], p[4], p[6], p[2], col)          # -X


func box(center: Vector3, size: Vector3, col: Color, basis := Basis.IDENTITY) -> void:
	var h := size * 0.5
	var p: Array = []
	for i in 8:
		var o := Vector3(h.x if i & 1 else -h.x, h.y if i & 2 else -h.y, h.z if i & 4 else -h.z)
		p.append(center + basis * o)
	hexa(p, col)


## Box from a bottom rectangle (size_bot.x, size_bot.y = x, z) at `base` to a top rectangle of
## size_top, `h` higher and shifted by `top_off` (x, z).
func taper(base: Vector3, size_bot: Vector2, size_top: Vector2, h: float, col: Color,
		top_off := Vector2.ZERO, basis := Basis.IDENTITY) -> void:
	var p: Array = []
	for i in 8:
		var top := (i & 2) != 0
		var s := size_top if top else size_bot
		var o := Vector3(s.x * (0.5 if i & 1 else -0.5), h if top else 0.0, s.y * (0.5 if i & 4 else -0.5))
		if top:
			o += Vector3(top_off.x, 0.0, top_off.y)
		p.append(base + basis * o)
	hexa(p, col)


func cyl(base: Vector3, r_bot: float, r_top: float, h: float, sides: int, col: Color,
		cap_top := true, cap_bot := true, basis := Basis.IDENTITY, phase := 0.0) -> void:
	var bot: Array = []
	var top: Array = []
	for i in sides + 1:
		var t := TAU * float(i) / sides + phase
		var d := Vector3(cos(t), 0.0, -sin(t))
		bot.append(base + basis * (d * r_bot))
		top.append(base + basis * (d * r_top + Vector3(0, h, 0)))
	var ct := base + basis * Vector3(0, h, 0)
	for i in sides:
		quad(bot[i], bot[i + 1], top[i + 1], top[i], col)
		if cap_top and r_top > 0.0:
			tri(ct, top[i], top[i + 1], col)
		if cap_bot and r_bot > 0.0:
			tri(base, bot[i + 1], bot[i], col)


func cone(base: Vector3, r: float, h: float, sides: int, col: Color, basis := Basis.IDENTITY) -> void:
	cyl(base, r, 0.0, h, sides, col, false, true, basis)


func sphere(center: Vector3, r: float, col: Color, segs := 6, rings := 4, scale := Vector3.ONE,
		basis := Basis.IDENTITY) -> void:
	var grid: Array = []
	for j in rings + 1:
		var phi := PI * float(j) / rings
		var row: Array = []
		for i in segs + 1:
			var t := TAU * float(i) / segs
			var d := Vector3(sin(phi) * cos(t), cos(phi), -sin(phi) * sin(t)) * r * scale
			row.append(center + basis * d)
		grid.append(row)
	for j in rings:
		for i in segs:
			quad(grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1], grid[j][i], col)


## Horizontal annulus sector (for tiered seating, apse floors, rings) from angle a0 to a1 (radians,
## measured from +X toward +Z), extruded `h` upward from `y`.
func ring_sector(center: Vector3, r_in: float, r_out: float, a0: float, a1: float, h: float,
		steps: int, col: Color, col_side := Color(0, 0, 0, 0)) -> void:
	var side := col if col_side.a == 0.0 else col_side
	for i in steps:
		var t0 := lerpf(a0, a1, float(i) / steps)
		var t1 := lerpf(a0, a1, float(i + 1) / steps)
		var d0 := Vector3(cos(t0), 0, sin(t0))
		var d1 := Vector3(cos(t1), 0, sin(t1))
		var i0 := center + d0 * r_in
		var i1 := center + d1 * r_in
		var o0 := center + d0 * r_out
		var o1 := center + d1 * r_out
		var up := Vector3(0, h, 0)
		# Angle grows toward +Z, so (o0, o1, i1, i0) is clockwise from above; flip for the top face.
		quad(i0 + up, i1 + up, o1 + up, o0 + up, col)
		quad(o1, o0, o0 + up, o1 + up, side)          # outer wall
		quad(i0, i1, i1 + up, i0 + up, side)          # inner wall
		if i == 0:
			quad(o0, i0, i0 + up, o0 + up, side)
		if i == steps - 1:
			quad(i1, o1, o1 + up, i1 + up, side)


func append(other: MeshBuilder) -> void:
	_v.append_array(other._v)
	_n.append_array(other._n)
	_c.append_array(other._c)
	_b.append_array(other._b)
	_w.append_array(other._w)


func build(glow := false) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	if _v.is_empty():
		return mesh
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = _v
	arrays[Mesh.ARRAY_NORMAL] = _n
	arrays[Mesh.ARRAY_COLOR] = _c
	if _b.size() == _v.size() * 4:
		arrays[Mesh.ARRAY_BONES] = _b
		arrays[Mesh.ARRAY_WEIGHTS] = _w
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, glow_material() if glow else material())
	return mesh


func instance(glow := false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = build(glow)
	return mi
