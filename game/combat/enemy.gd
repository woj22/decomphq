class_name Enemy
extends Actor
## A demon: chases the nearest target (player or a guard), claws in melee, can be knocked back. Not a saved entity.

var max_hp := 30.0
var hp := 30.0
var damage := 8.0
var reach := 0.95
var attack_cd := 1.1
var dead := false
var target: Actor
var _cd := 0.6
var _repath := 0.0
var _knock := Vector2.ZERO
var _hit_t := 0.0
var bar: ColorRect


func configure(brute: bool) -> void:
	if brute:
		max_hp = 80.0
		damage = 16.0
		speed = 1.5
		reach = 1.15
		attack_cd = 1.6
	else:
		max_hp = 30.0
		damage = 8.0
		speed = 2.3
	hp = max_hp
	bar = ColorRect.new()
	bar.color = Color("#e8552b")
	bar.size = Vector2(24, 2)
	bar.position = Vector2(-12, -58 if not brute else -78)
	bar.visible = false
	add_child(bar)


func take_hit(dmg: float, knock: Vector2 = Vector2.ZERO) -> void:
	if dead:
		return
	hp -= dmg
	_knock += knock
	_hit_t = 0.2
	set_anim("hit" if Assets.has_anim(sprite_id, "hit") else "idle")
	modulate = Color(2, 2, 2, 1)
	Fx.burst(get_parent(), "impact_spark", gpos)
	Audio.sfx("sfx_hit")
	bar.visible = true
	bar.size.x = 24.0 * clampf(hp / max_hp, 0.0, 1.0)
	if hp <= 0.0:
		_die()


func _die() -> void:
	dead = true
	path.clear()
	Audio.sfx("sfx_demon_die")
	Combat.enemy_died(self)
	var tw := create_tween()
	tw.tween_property(self, "modulate", Color(1, 0.3, 0.2, 0), 0.5)
	tw.tween_callback(queue_free)


func _pick_target() -> void:
	var best: Actor = World.player
	var bd := INF if best == null else gpos.distance_to(best.gpos)
	for g: Variant in Combat.defenders:
		if is_instance_valid(g) and not (g as Defender).down and gpos.distance_to((g as Actor).gpos) < bd - 1.5:
			best = g
			bd = gpos.distance_to((g as Actor).gpos)
	target = best


func _process(delta: float) -> void:
	if dead:
		return
	if _hit_t > 0.0:
		_hit_t -= delta
		if _hit_t <= 0.0:
			modulate = Color.WHITE
	if _knock.length() > 0.01:
		var step := _knock * minf(1.0, delta * 8.0)
		var ng := gpos + step
		if model.walkable(Vector2i(roundi(ng.x), roundi(ng.y))):
			set_gpos(ng)
		_knock -= step
	_cd -= delta
	_repath -= delta
	if _repath <= 0.0:
		_repath = 0.5
		_pick_target()
		if target != null and gpos.distance_to(target.gpos) > reach:
			go_to(target.cell())
	if target != null and is_instance_valid(target):
		var d := gpos.distance_to(target.gpos)
		if d <= reach:
			path.clear()
			face_towards(target.gpos)
			if _cd <= 0.0:
				_cd = attack_cd
				set_anim("attack" if Assets.has_anim(sprite_id, "attack") else "idle")
				Fx.burst(get_parent(), "demon_slash", target.gpos)
				if target == World.player:
					Combat.damage_player(damage)
				elif target is Defender:
					(target as Defender).take_hit(damage)
			elif anim != "attack" or _cd < attack_cd - 0.3:
				set_anim("idle")
	super._process(delta)
