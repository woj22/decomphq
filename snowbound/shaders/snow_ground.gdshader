shader_type spatial;
render_mode diffuse_lambert, specular_disabled;
// Wind-sculpted snow, cheap enough for phones: height and normal are computed per vertex; per pixel only a tone.

varying vec3 wpos;
varying float tone;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float h(vec2 p) { return noise(p * vec2(0.15, 0.45)) * 1.2 + noise(p * vec2(0.6, 0.9)) * 0.3; }

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float e = 0.6;
	float c = h(wpos.xz);
	VERTEX.y += c - 0.8;
	NORMAL = normalize(vec3(h(wpos.xz - vec2(e, 0)) - h(wpos.xz + vec2(e, 0)), 2.0 * e, h(wpos.xz - vec2(0, e)) - h(wpos.xz + vec2(0, e))));
	tone = noise(wpos.xz * 0.6);
}

void fragment() {
	ALBEDO = mix(vec3(0.42, 0.48, 0.62), vec3(0.58, 0.64, 0.78), tone);
	ROUGHNESS = 0.8;
}
