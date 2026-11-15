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
var boss_flag := ""
var boss_kind := "" # "", "brute", "thrace", "glut", "vael"
var boss_name := ""
var _skill_t := 3.0
var _summon_t := 10.0
var _phase := 1
var self_modulate_base := Color.WHITE


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
	if Clock.is_night():
		max_hp *= Content.cfg_f("night_demon_hp_mult", 1.6)
		damage *= Content.cfg_f("night_demon_dmg_mult", 1.5)
		speed *= 1.15
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
	if boss_kind != "":
		Combat.boss_hp.emit(boss_name, clampf(hp / max_hp, 0.0, 1.0))
		if boss_kind == "thrace" and _phase == 1 and hp < max_hp * 0.5:
			_phase = 2
			_blink()
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
	var best: Actor = null if Combat.downed else World.player
	var bd := INF if best == null else gpos.distance_to(best.gpos)
	for g: Variant in Combat.defenders:
		if is_instance_valid(g) and not (g as Defender).down and (best == null or gpos.distance_to((g as Actor).gpos) < bd - 1.5):
			best = g
			bd = gpos.distance_to((g as Actor).gpos)
	target = best


func _process(delta: float) -> void:
	if dead:
		return
	if boss_kind != "" and boss_kind != "brute":
		_boss_skills(delta)
	if _hit_t > 0.0:
		_hit_t -= delta
		if _hit_t <= 0.0:
			modulate = self_modulate_base
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


# ---------------------------------------------------------------- boss skills
func _boss_skills(delta: float) -> void:
	_skill_t -= delta
	_summon_t -= delta
	var p := World.player
	if p == null or Combat.downed:
		return
	match boss_kind:
		"thrace":
			# keeps his distance and fires violet ink; summons ink-wraiths; re-files himself when hurt
			if gpos.distance_to(p.gpos) < 3.0 and path.is_empty():
				var away := (gpos - p.gpos).normalized() * 3.0
				go_to(model.nearest_walkable(Vector2i(roundi(gpos.x + away.x), roundi(gpos.y + away.y)), cell()))
			if _skill_t <= 0.0:
				_skill_t = 1.6 if _phase == 1 else 1.0
				set_anim("cast" if Assets.has_anim(sprite_id, "cast") else "attack")
				for spread: float in ([0.0] if _phase == 1 else [-0.25, 0.0, 0.25]):
					var b := BossBolt.new()
					get_parent().add_child(b)
					var to := p.gpos + (p.gpos - gpos).orthogonal().normalized() * spread * 3.0
					b.launch(model, gpos, to, 6.5, damage * 0.7, "violet_bolt")
			if _summon_t <= 0.0:
				_summon_t = 14.0
				Combat.summon("chr_ink_wraith", gpos, 2, false)
		"glut":
			if _skill_t <= 0.0:
				_skill_t = 6.0 if _phase == 1 else 4.0
				_hellfire()
			if _summon_t <= 0.0:
				_summon_t = 16.0
				Combat.summon("chr_demon", gpos, 2, false)
			if _phase == 1 and hp < max_hp * 0.5:
				_phase = 2
				speed *= 1.3
		"vael":
			if _skill_t <= 0.0:
				_skill_t = 2.2 if _phase == 1 else 1.4
				_holy_beam(p.gpos)
			if _phase == 1 and hp < max_hp * 0.5:
				_phase = 2
				speed *= 1.25
				Combat.summon("chr_soul_0", gpos, 0, false)


func _blink() -> void:
	var c := model.nearest_walkable(Vector2i(randi_range(1, model.size.x - 2), randi_range(1, model.size.y - 2)), cell())
	Fx.burst(get_parent(), "ink_puddle", gpos)
	path.clear()
	set_gpos(Vector2(c))
	EventBus.notify.emit("Thrace re-files himself across the room.")


## Telegraphed ring of hellfire around Glut: get out of the circle.
func _hellfire() -> void:
	var at := gpos
	Fx.burst(get_parent(), "ink_puddle", at)
	EventBus.notify.emit("The floor glows around Glut...")
	await get_tree().create_timer(0.9).timeout
	if dead or not is_inside_tree():
		return
	Fx.burst(get_parent(), "hellfire_burst", at)
	Audio.sfx("sfx_nova")
	if World.player != null and World.player.gpos.distance_to(at) < 2.4:
		Combat.damage_player(damage * 1.2)
	for g: Variant in Combat.defenders:
		if is_instance_valid(g) and (g as Defender).gpos.distance_to(at) < 2.4:
			(g as Defender).take_hit(damage)


## Vael marks the player's position; a beam strikes it a second later. Keep moving.
func _holy_beam(target: Vector2) -> void:
	Fx.burst(get_parent(), "select_ring", target)
	await get_tree().create_timer(1.0).timeout
	if dead or not is_inside_tree():
		return
	Fx.burst(get_parent(), "holy_beam", target)
	Audio.sfx("sfx_lance_charged")
	if World.player != null and World.player.gpos.distance_to(target) < 0.9:
		Combat.damage_player(damage * 1.4)
