shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, unshaded;
// Frosted carriage windows. Panes are centred every 2 m along z, 1.72 m wide, between y = 0.98 and 1.82, so the
// pane-local UV comes from the world position (the merged window mesh has no UVs).

uniform float time_scale = 1.0;
varying vec3 wpos;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int k = 0; k < 5; k++) { v += a * noise(p); p *= 2.07; a *= 0.5; } return v; }

void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float zc = wpos.z - round(wpos.z * 0.5) * 2.0;           // -1..1 around the pane centre
	vec2 uv = vec2(zc / 0.86, (wpos.y - 1.4) / 0.42);           // pane-local, -1..1
	float edge = max(abs(uv.x), abs(uv.y));
	edge = max(edge, length(uv * vec2(0.85, 1.0)) * 0.88);      // rounded corners fill first
	float n = fbm(vec2(wpos.z, wpos.y) * 7.0 + wpos.x * 3.0);
	float crystals = fbm(vec2(wpos.z, wpos.y) * 26.0);
	float frost = smoothstep(0.55, 1.02, edge + (n - 0.5) * 0.5);
	frost = max(frost, smoothstep(0.8, 1.0, uv.y * -0.5 + 0.5 + (n - 0.5) * 0.6) * 0.55);   // heavier along the bottom
	frost *= 0.75 + 0.25 * crystals;
	// melted streaks where condensation ran down
	float streak = smoothstep(0.86, 1.0, noise(vec2(wpos.z * 40.0, 0.0))) * smoothstep(0.2, -0.6, uv.y) * 0.25;
	ALBEDO = mix(vec3(0.62, 0.72, 0.85), vec3(0.9, 0.94, 1.0), frost);
	ALPHA = clamp(0.07 + frost * 0.85 + streak, 0.0, 0.95);
}
