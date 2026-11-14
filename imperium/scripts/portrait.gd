class_name Portrait
extends SubViewport
## A small isolated 3D stage that renders one character: a head-and-shoulders portrait for
## dialogue, or a slowly turning full-length figure for the court roster.

var rig: CharacterRig
var turntable := false
var _cam: Camera3D


static func make(look: Dictionary, px: Vector2i, full_body := false, turn := false) -> Portrait:
	var p := Portrait.new()
	p.size = px
	p.own_world_3d = true
	p.transparent_bg = true
	p.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	p.msaa_3d = Viewport.MSAA_2X
	p.turntable = turn
	p._stage(look, full_body)
	return p


func _stage(look: Dictionary, full_body: bool) -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_CLEAR_COLOR
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("c9b79a")
	env.environment.ambient_light_energy = 0.7
	env.environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	add_child(env)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-30, 35, 0)
	key.light_energy = 1.2
	add_child(key)
	var rim := DirectionalLight3D.new()
	rim.rotation_degrees = Vector3(-20, 200, 0)
	rim.light_energy = 0.6
	rim.light_color = Color("ffd8a0")
	add_child(rim)
	rig = CharacterBuilder.build_rig(look)
	rig.rotation.y = PI + 0.3
	add_child(rig)
	_cam = Camera3D.new()
	var h := rig.height
	if full_body:
		_cam.fov = 30
		_cam.position = Vector3(0, h * 0.55, h * 1.95 + 0.9)
		_cam.transform = _cam.transform.looking_at(Vector3(0, h * 0.5, 0))
		add_child(_cam)
	else:
		_cam.fov = 26
		var head_y: float = h - float(rig.dims["head_h"]) * 0.45
		_cam.position = Vector3(0.12, head_y + 0.05, 1.35)
		_cam.transform = _cam.transform.looking_at(Vector3(0, head_y - 0.06, 0))
		add_child(_cam)


func _process(delta: float) -> void:
	if turntable and rig != null:
		rig.rotation.y += delta * 0.5
