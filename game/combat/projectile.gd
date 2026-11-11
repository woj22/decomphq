class_name Projectile
extends Node2D
## A spell bolt travelling in grid space; hits the first demon (or every demon when piercing); stops at walls.

var model: AreaModel
var gpos := Vector2.ZERO
var vel := Vector2.ZERO
var dmg := 10.0
var pierce := false
var life := 1.2
var hit: Array = []
var spr: Sprite2D
var _t := 0.0
var _f := 0
var _sid := ""


func launch(m: AreaModel, from: Vector2, dir: Vector2, spd: float, damage: float, piercing: bool, sid: String) -> void:
	model = m
	gpos = from
	vel = dir.normalized() * spd
	dmg = damage
	pierce = piercing
	_sid = sid
	spr = Sprite2D.new()
	spr.centered = false
	spr.texture = Assets.frame(sid, 0, "fx")
	spr.offset = -(Assets.info(sid, "fx").get("origin", Vector2(16, 8)) as Vector2)
	spr.position = Vector2(0, -20)
	spr.rotation = Iso.grid_delta_to_screen(dir).angle()
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	spr.material = mat
	add_child(spr)
	position = Iso.cell_to_local(gpos)


func _process(delta: float) -> void:
	life -= delta
	gpos += vel * delta
	position = Iso.cell_to_local(gpos)
	_t += delta
	if _t > 0.08:
		_t = 0.0
		_f = (_f + 1) % maxi(1, Assets.frame_count(_sid))
		spr.texture = Assets.frame(_sid, _f, "fx")
	var c := Vector2i(roundi(gpos.x), roundi(gpos.y))
	if life <= 0.0 or not model.in_bounds(c) or (model.cell_solid(c) and model.kind_at(c) in ["wall", "kerb", "door"]):
		_end()
		return
	for e: Variant in Combat.enemies.duplicate():
		var en: Enemy = e
		if is_instance_valid(en) and not en.dead and not hit.has(en) and en.gpos.distance_to(gpos) < 0.6:
			en.take_hit(dmg, vel.normalized() * 0.35)
			hit.append(en)
			if not pierce:
				_end()
				return


func _end() -> void:
	Fx.burst(get_parent(), "impact_spark", gpos)
	queue_free()
