class_name Defender
extends Actor
## A guard of the Ember Gate: holds a post, engages demons that come near, recovers when knocked down.

var post := Vector2i.ZERO
var hp := 60.0
var down := false
var _cd := 0.0
var _repath := 0.0
var _down_t := 0.0


func take_hit(dmg: float) -> void:
	if down:
		return
	hp -= dmg
	modulate = Color(2, 1.4, 1.4, 1)
	create_tween().tween_property(self, "modulate", Color.WHITE, 0.2)
	if hp <= 0.0:
		down = true
		_down_t = 8.0
		path.clear()
		modulate = Color(0.5, 0.5, 0.6, 0.7)


func _process(delta: float) -> void:
	if down:
		_down_t -= delta
		if _down_t <= 0.0:
			down = false
			hp = 60.0
			modulate = Color.WHITE
		_animate(delta)
		return
	_cd -= delta
	_repath -= delta
	var foe: Enemy = null
	var fd := 4.5
	for e: Variant in Combat.enemies:
		if is_instance_valid(e) and not (e as Enemy).dead:
			var d := (e as Enemy).gpos.distance_to(gpos)
			if d < fd:
				fd = d
				foe = e
	if foe != null:
		if fd <= 1.2:
			path.clear()
			face_towards(foe.gpos)
			if _cd <= 0.0:
				_cd = 1.3
				foe.take_hit(9.0, (foe.gpos - gpos).normalized() * 0.4)
		elif _repath <= 0.0:
			_repath = 0.5
			go_to(foe.cell())
	elif cell() != post and _repath <= 0.0:
		_repath = 1.0
		go_to(post)
	super._process(delta)
