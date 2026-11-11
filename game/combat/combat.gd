extends Node
## Combat (owner request): player HP/mana, two spells with tap and held (charged) forms, jump i-frames, demons,
## guard allies, demon breakouts. Lives beside World; all actors are children of the current AreaView.
##
## Buttons (FaceButtons UI / keyboard):  X = jump · TRIANGLE = Gilt Lance · CIRCLE = Ember Brand · SQUARE = interact.
## A press shorter than HOLD_S casts the quick form; holding longer charges the strong form (released to cast).

signal hp_changed(hp: float, max_hp: float)
signal mana_changed(mana: float, max_mana: float)
signal hostiles_changed(count: int)
signal charge_changed(button: String, t: float) # 0..1 while a spell button is held

const HOLD_S := 0.35

var hp := 100.0
var mana := 60.0
var enemies: Array = []
var defenders: Array = []
var _cooldown := {"triangle": 0.0, "circle": 0.0}
var _held := {} # button -> seconds held
var _breakout_t := 0.0
var _hostile_cfg: Dictionary = {}
var invuln := 0.0
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	rng.randomize()
	World.area_loaded.connect(func(_id: String) -> void: _on_area())


# ---------------------------------------------------------------- stats (upgrades are GameState stats)
func level(id: String) -> int:
	return GameState.get_stat_i("up_" + id)


func max_hp() -> float:
	return Content.cfg_f("combat_hp", 100.0) + 20.0 * level("vitality")


func max_mana() -> float:
	return Content.cfg_f("combat_mana", 60.0) + 20.0 * level("focus")


func mana_regen() -> float:
	return 6.0 + 2.0 * level("focus")


func spell_mult(id: String) -> float:
	return 1.0 + 0.3 * level(id)


func spell_cost(id: String, charged: bool) -> float:
	var base: float = {"lance": 8.0, "brand": 12.0}[id] if not charged else {"lance": 20.0, "brand": 25.0}[id]
	return base * pow(0.9, level(id))


## Sorcery room: prices per grade come from config "upgrades".<id>.prices.
func upgrade_prices(id: String) -> Array:
	var u: Variant = Content.cfg("upgrades", {})
	if u is Dictionary and (u as Dictionary).get(id) is Dictionary:
		return ((u as Dictionary)[id] as Dictionary).get("prices", [])
	return []


func buy_upgrade(id: String) -> void:
	var prices := upgrade_prices(id)
	var lv := level(id)
	var nm := str(((Content.cfg("upgrades", {}) as Dictionary).get(id, {}) as Dictionary).get("name", id))
	if lv >= prices.size():
		EventBus.notify.emit("%s is already at its highest grade." % nm)
		return
	var price := int(prices[lv])
	if GameState.get_stat_i("purse") < price:
		EventBus.notify.emit("%s grade %d costs %d obols. You have %d." % [nm, lv + 2, price, GameState.get_stat_i("purse")])
		return
	GameState.add_stat("purse", -price)
	GameState.add_stat("up_" + id, 1)
	Audio.sfx("sfx_stamp")
	EventBus.notify.emit("%s raised to grade %d (-%d obols)." % [nm, lv + 2, price])
	heal_full()


func heal_full() -> void:
	hp = max_hp()
	mana = max_mana()
	hp_changed.emit(hp, max_hp())
	mana_changed.emit(mana, max_mana())


func in_hostile_area() -> bool:
	return not _hostile_cfg.is_empty()


# ---------------------------------------------------------------- buttons
func press(button: String) -> void:
	if World.player == null or World.input_locked():
		return
	match button:
		"cross":
			jump()
		"square":
			World.interact_focused()
		"triangle", "circle":
			_held[button] = 0.0


func release(button: String) -> void:
	if not _held.has(button):
		return
	var t: float = _held[button]
	_held.erase(button)
	charge_changed.emit(button, 0.0)
	if World.player == null or World.input_locked():
		return
	var charged := t >= HOLD_S
	if button == "triangle":
		cast_lance(charged)
	elif button == "circle":
		cast_brand(charged)


func jump() -> void:
	var p := World.player
	if p == null or p.jumping:
		return
	invuln = maxf(invuln, 0.45)
	Audio.sfx("sfx_jump")
	p.jump()


# ---------------------------------------------------------------- spells
func _spend(id: String, charged: bool, button: String) -> bool:
	if float(_cooldown[button]) > 0.0:
		return false
	var cost := spell_cost(id, charged)
	if mana < cost:
		EventBus.notify.emit("Not enough mana.")
		return false
	mana -= cost
	mana_changed.emit(mana, max_mana())
	_cooldown[button] = 0.55 if charged else 0.3
	return true


## Gilt Lance (TRIANGLE): a gold bolt toward the nearest demon (or where you face). Charged: bigger, pierces.
func cast_lance(charged: bool) -> void:
	var p := World.player
	if p == null or not _spend("lance", charged, "triangle"):
		return
	var dir := _aim(p, 8.0)
	var pr := Projectile.new()
	World.view.sorted.add_child(pr)
	pr.launch(World.model, p.gpos + dir * 0.4, dir, 9.0 if not charged else 11.0,
		(10.0 if not charged else 26.0) * spell_mult("lance"), charged, "spell_lance_charged" if charged else "spell_lance")
	Audio.sfx("sfx_lance_charged" if charged else "sfx_lance")


## Ember Brand (CIRCLE): a burning ring around you. Charged: wider, stronger, hurls demons back.
func cast_brand(charged: bool) -> void:
	var p := World.player
	if p == null or not _spend("brand", charged, "circle"):
		return
	var radius := 1.7 if not charged else 2.7
	var dmg := (8.0 if not charged else 18.0) * spell_mult("brand")
	Fx.burst(World.view.decal_layer, "spell_nova_charged" if charged else "spell_nova", p.gpos)
	for e: Variant in enemies.duplicate():
		var en: Enemy = e
		if is_instance_valid(en) and en.gpos.distance_to(p.gpos) <= radius:
			en.take_hit(dmg, (en.gpos - p.gpos).normalized() * (1.6 if charged else 0.6))
	Audio.sfx("sfx_nova")


func _aim(p: Actor, max_range: float) -> Vector2:
	var best: Enemy = null
	var bd := max_range
	for e: Variant in enemies:
		var en: Enemy = e
		if is_instance_valid(en) and not en.dead:
			var d := en.gpos.distance_to(p.gpos)
			if d < bd:
				bd = d
				best = en
	if best != null:
		return (best.gpos - p.gpos).normalized()
	return Iso.grid_dir(p.facing)


# ---------------------------------------------------------------- damage
func damage_player(n: float) -> void:
	if invuln > 0.0 or World.player == null:
		return
	hp -= n
	invuln = 0.6
	Audio.sfx("sfx_player_hurt")
	World.player.flash()
	hp_changed.emit(hp, max_hp())
	if hp <= 0.0:
		_fall()


## Falling in combat: dragged back to the Court by the Watch, a fine docked from the purse, healed.
func _fall() -> void:
	var fine := mini(GameState.get_stat_i("purse"), Content.cfg_i("combat_fall_fine", 5))
	GameState.add_stat("purse", -fine)
	hp = max_hp()
	hp_changed.emit(hp, max_hp())
	World.escort_lost()
	Dialogue.request_modal("card", {"title": "Dragged Back", "text": "The Watch hauls you out by the collar. The infirmary bills you %d obols." % fine})
	World.request_teleport("area_clerks_court", "default")


func enemy_died(e: Enemy) -> void:
	enemies.erase(e)
	hostiles_changed.emit(enemies.size())
	GameState.add_stat("purse", Content.cfg_i("demon_bounty", 2))
	GameState.add_stat("demons_banished", 1)


# ---------------------------------------------------------------- area hookup
func _on_area() -> void:
	enemies.clear()
	defenders.clear()
	_held.clear()
	var m := World.model
	_hostile_cfg = {}
	if m == null:
		return
	var h: Variant = m.data.get("hostiles")
	if h is Dictionary:
		_hostile_cfg = h
		_spawn_defenders()
		var ev: Array = _hostile_cfg.get("breakout_every", [30, 50])
		_breakout_t = rng.randf_range(float(ev[0]) * 0.4, float(ev[1]) * 0.6)
	hostiles_changed.emit(0)


func _spawn_defenders() -> void:
	var night := Clock.is_night()
	for d: Variant in _hostile_cfg.get("defenders", []):
		var dd: Dictionary = d
		if bool(dd.get("night_only", false)) and not night:
			continue
		var g := Defender.new()
		World.view.sorted.add_child(g)
		g.setup(str(dd.get("night_sprite", "chr_guard_night")) if night else str(dd.get("sprite", "chr_guard")), World.model,
			Vector2(JsonUtil.to_vec2i(dd.get("cell"))), str(dd.get("facing", "ne")))
		g.post = JsonUtil.to_vec2i(dd.get("cell"))
		defenders.append(g)


## Demons break out of the Gate. More of them at night, and more while you escort a soul.
func breakout(count: int = -1) -> void:
	if World.model == null or _hostile_cfg.is_empty():
		return
	var spawns: Array = _hostile_cfg.get("spawn_cells", [])
	if spawns.is_empty():
		return
	var n := count if count > 0 else rng.randi_range(1, 2) + (1 if Clock.is_night() else 0) + (1 if World.escort != null else 0)
	n = mini(n, int(_hostile_cfg.get("max_enemies", 6)) - enemies.size())
	for i in n:
		var brute := rng.randf() < float(_hostile_cfg.get("brute_chance", 0.2))
		var e := Enemy.new()
		World.view.sorted.add_child(e)
		var c := JsonUtil.to_vec2i(spawns[rng.randi_range(0, spawns.size() - 1)])
		e.setup("chr_demon_brute" if brute else "chr_demon", World.model, Vector2(c), "sw")
		e.configure(brute)
		enemies.append(e)
	if n > 0:
		Audio.sfx("sfx_demon_roar")
		EventBus.notify.emit("Demons break from the Gate!")
		hostiles_changed.emit(enemies.size())


func clear_enemies() -> void:
	for e: Variant in enemies:
		if is_instance_valid(e):
			(e as Node).queue_free()
	enemies.clear()
	hostiles_changed.emit(0)


func _process(delta: float) -> void:
	if Playtest.active and not Playtest.combat_enabled:
		return
	invuln = maxf(0.0, invuln - delta)
	for b: String in _cooldown:
		_cooldown[b] = maxf(0.0, float(_cooldown[b]) - delta)
	for b: String in _held.keys():
		_held[b] = float(_held[b]) + delta
		charge_changed.emit(b, clampf(float(_held[b]) / HOLD_S, 0.0, 1.0))
	if mana < max_mana():
		mana = minf(max_mana(), mana + mana_regen() * delta)
		mana_changed.emit(mana, max_mana())
	if not _hostile_cfg.is_empty() and not World.input_locked() and World.player != null:
		_breakout_t -= delta
		if _breakout_t <= 0.0:
			var ev: Array = _hostile_cfg.get("breakout_every", [30, 50])
			var mult := 0.6 if World.escort != null else 1.0
			_breakout_t = rng.randf_range(float(ev[0]), float(ev[1])) * mult
			breakout()
