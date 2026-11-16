// Bioluminescent parts (bulbs, crystals, ruin glyphs): unshaded, softly pulsing, sways like flora.
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform float intensity = 1.25;
uniform float pulse = 0.18;
uniform float sway_amount = 0.22;
uniform float sway_speed = 1.1;
varying float v_phase;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float w = UV.x;
	float t = TIME * sway_speed + UV.y * 6.2831 + wp.x * 0.04 + wp.z * 0.03;
	VERTEX.x += (sin(t) + 0.35 * sin(t * 2.7)) * w * sway_amount;
	VERTEX.z += cos(t * 0.8) * w * sway_amount * 0.6;
	v_phase = UV.y * 6.2831 + wp.x * 0.11 + wp.z * 0.07;
}

void fragment() {
	float p = 1.0 + pulse * sin(TIME * 1.7 + v_phase);
	ALBEDO = COLOR.rgb * intensity * p;
}
