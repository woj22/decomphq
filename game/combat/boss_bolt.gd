class_name BossBolt
extends Node2D
## A boss projectile flying at the player (Thrace's violet ink). Dodge with CROSS (jump i-frames) or step aside.

var model: AreaModel
var gpos := Vector2.ZERO
var vel := Vector2.ZERO
var dmg := 12.0
var life := 2.5
var spr: Sprite2D


func launch(m: AreaModel, from: Vector2, to: Vector2, speed: float, damage: float, sid: String) -> void:
	model = m
	gpos = from
	vel = (to - from).normalized() * speed
	dmg = damage
	spr = Sprite2D.new()
	spr.centered = false
	spr.texture = Assets.frame(sid, 0, "fx")
	spr.offset = -(Assets.info(sid, "fx").get("origin", Vector2(16, 8)) as Vector2)
	spr.position = Vector2(0, -24)
	spr.rotation = Iso.grid_delta_to_screen(vel).angle()
	add_child(spr)
	position = Iso.cell_to_local(gpos)


func _process(delta: float) -> void:
	life -= delta
	gpos += vel * delta
	position = Iso.cell_to_local(gpos)
	var c := Vector2i(roundi(gpos.x), roundi(gpos.y))
	if life <= 0.0 or not model.in_bounds(c) or model.kind_at(c) in ["wall", "kerb", "door"]:
		queue_free()
		return
	if World.player != null and gpos.distance_to(World.player.gpos) < 0.55:
		Combat.damage_player(dmg)
		Fx.burst(get_parent(), "impact_spark", gpos)
		queue_free()
