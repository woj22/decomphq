// Terrain, rocks and ruins: flat-shaded vertex colour, no textures, no specular (cheap on mobile).
shader_type spatial;
render_mode cull_back, specular_disabled;

uniform float brightness = 1.0;

void fragment() {
	ALBEDO = COLOR.rgb * brightness;
	ROUGHNESS = 1.0;
}
