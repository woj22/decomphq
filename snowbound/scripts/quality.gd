class_name Quality
## Graphics quality (chosen on the start screen, saved on the device). 0 = Low, 1 = Balanced, 2 = High.

const NAMES := ["Low", "Balanced", "High"]
const CFG := "user://snowbound_quality.cfg"
static var level := 1


static func load_setting() -> void:
	var c := ConfigFile.new()
	if c.load(CFG) == OK:
		level = clampi(int(c.get_value("gfx", "level", 1)), 0, 2)


static func save_setting() -> void:
	var c := ConfigFile.new()
	c.set_value("gfx", "level", level)
	c.save(CFG)


static func pick(low: Variant, balanced: Variant, high: Variant) -> Variant:
	return [low, balanced, high][level]


## Render the 3D at a fraction of the screen's resolution and upscale (the UI stays sharp).
static func apply_viewport(vp: Viewport) -> void:
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR if level == 0 else Viewport.SCALING_3D_MODE_FSR
	vp.scaling_3d_scale = pick(0.5, 0.67, 0.85)
	vp.fsr_sharpness = 0.4
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if level == 2 else Viewport.SCREEN_SPACE_AA_DISABLED
