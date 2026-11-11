shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
// Wind-sculpted snow: soft drifts in the normal, faint sparkle.

varying vec3 wpos;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int k = 0; k < 4; k++) { v += a * noise(p); p *= 2.1; a *= 0.5; } return v; }
float h(vec2 p) { return fbm(p * vec2(0.15, 0.45)) * 1.6 + fbm(p * 2.5) * 0.08; }

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += h(wpos.xz) - 0.8;
}

void fragment() {
	vec2 p = wpos.xz;
	float e = 0.15;
	vec3 n = normalize(vec3(h(p - vec2(e, 0)) - h(p + vec2(e, 0)), 2.0 * e, h(p - vec2(0, e)) - h(p + vec2(0, e))));
	NORMAL = (VIEW_MATRIX * vec4(n, 0.0)).xyz;
	float tone = fbm(p * 0.6);
	ALBEDO = mix(vec3(0.42, 0.48, 0.62), vec3(0.58, 0.64, 0.78), tone);
	ROUGHNESS = 0.75;
	float sp = step(0.985, hash(floor(p * 60.0)));
	EMISSION = vec3(0.6, 0.7, 0.9) * sp * 0.25;
}
