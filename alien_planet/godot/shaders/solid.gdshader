// Terrain, rocks and ruins: flat-shaded vertex colour, no textures. `wet` darkens the albedo and adds a
// rain-soaked sheen that catches the sky (and the lightning).
shader_type spatial;
render_mode cull_back;

uniform float brightness = 1.0;
uniform float wet = 0.75;

void fragment() {
	ALBEDO = COLOR.rgb * brightness * (1.0 - 0.25 * wet);
	ROUGHNESS = mix(1.0, 0.32, wet * smoothstep(0.3, 0.9, NORMAL.y * 0.5 + 0.5));
	SPECULAR = 0.45 * wet;
}
