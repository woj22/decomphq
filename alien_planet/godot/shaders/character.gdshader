// Characters: flat-shaded vertex colour like the world, plus a soft rim so they read against busy scenery.
shader_type spatial;
render_mode cull_back, specular_disabled;

uniform float rim = 0.35;

void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 0.9;
	RIM = rim;
	RIM_TINT = 0.6;
}
