class_name Fx
extends RefCounted
## One-shot animated effect sprites (spell rings, sparks, claw slashes).

static func burst(parent: Node, sid: String, at: Vector2) -> void:
	if parent == null:
		return
	var s := Sprite2D.new()
	s.centered = false
	s.texture = Assets.frame(sid, 0, "fx")
	var info := Assets.info(sid, "fx")
	s.offset = -(info.get("origin", Vector2(16, 16)) as Vector2)
	s.position = Iso.cell_to_local(at)
	if bool(info.get("additive", false)) or sid.begins_with("spell_nova"):
		var mat := CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		s.material = mat
	s.z_index = 5
	parent.add_child(s)
	var n := maxi(1, Assets.frame_count(sid))
	var tw := s.create_tween()
	for f in range(1, n):
		tw.tween_interval(0.07)
		tw.tween_callback(func() -> void: s.texture = Assets.frame(sid, f, "fx"))
	tw.tween_interval(0.07)
	tw.tween_property(s, "modulate:a", 0.0, 0.15)
	tw.tween_callback(s.queue_free)
