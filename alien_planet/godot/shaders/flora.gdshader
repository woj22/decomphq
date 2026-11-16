// Alien plants: vertex colour + wind sway. UV.x = sway weight (0 at the root), UV.y = per-plant phase.
shader_type spatial;
render_mode cull_disabled, specular_disabled;

uniform float sway_amount = 0.22;
uniform float sway_speed = 1.1;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float w = UV.x;
	float t = TIME * sway_speed + UV.y * 6.2831 + wp.x * 0.04 + wp.z * 0.03;
	VERTEX.x += (sin(t) + 0.35 * sin(t * 2.7)) * w * sway_amount;
	VERTEX.z += cos(t * 0.8) * w * sway_amount * 0.6;
}

void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 1.0;
	BACKLIGHT = COLOR.rgb * 0.6;   // leaves glow through instead of turning black from behind
}
