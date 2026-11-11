shader_type sky;
// Blue-hour sky behind a blizzard: deep blue overhead, a pale violet-grey band at the horizon, a last warm glow in
// the west, and slow storm cloud.

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int k = 0; k < 5; k++) { v += a * noise(p); p *= 2.03; a *= 0.5; } return v; }

void sky() {
	vec3 d = EYEDIR;
	float h = max(d.y, 0.0);
	vec3 zenith = vec3(0.035, 0.05, 0.11);
	vec3 horizon = vec3(0.34, 0.36, 0.5);
	vec3 col = mix(horizon, zenith, pow(h, 0.45));
	float west = pow(max(dot(normalize(vec3(d.x, 0.0, d.z)), normalize(vec3(-1.0, 0.0, -0.4))), 0.0), 4.0);
	col += vec3(0.42, 0.22, 0.2) * west * exp(-h * 7.0) * 0.6;
	vec2 uv = d.xz / max(d.y + 0.15, 0.05);
	float c = fbm(uv * 0.8 + vec2(TIME * 0.01, TIME * 0.004));
	col = mix(col, vec3(0.2, 0.22, 0.3), smoothstep(0.45, 0.8, c) * 0.55 * (1.0 - h * 0.5));
	if (d.y < 0.0) { col = mix(horizon * 0.9, vec3(0.25, 0.28, 0.36), clamp(-d.y * 4.0, 0.0, 1.0)); }
	COLOR = col;
}
