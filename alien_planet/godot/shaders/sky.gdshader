// Storm sky: a heavy overcast ceiling with slow-looking streaks, darker overhead, a pale gap near the
// horizon, and a hint of the hidden sun. Analytic, no textures; static so radiance is built once.
shader_type sky;

uniform vec3 sun_dir = vec3(0.44, 0.36, 0.82);
uniform vec3 moon_dir = vec3(-0.5, 0.55, -0.67);
uniform vec3 zenith_col : source_color = vec3(0.13, 0.15, 0.19);
uniform vec3 mid_col : source_color = vec3(0.24, 0.27, 0.32);
uniform vec3 horizon_col : source_color = vec3(0.42, 0.45, 0.5);
uniform vec3 ground_col : source_color = vec3(0.16, 0.16, 0.18);
uniform vec3 cloud_dark : source_color = vec3(0.10, 0.11, 0.14);
uniform vec3 cloud_light : source_color = vec3(0.36, 0.38, 0.44);

float hash2(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i + vec2(1, 0)), f.x), mix(hash2(i + vec2(0, 1)), hash2(i + vec2(1, 1)), f.x), f.y);
}

float fbm(vec2 p) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < 4; i++) {
		s += a * vnoise(p);
		p = p * 2.03 + vec2(1.7, 9.2);
		a *= 0.5;
	}
	return s;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float y = d.y;
	vec3 col = mix(horizon_col, mid_col, smoothstep(0.0, 0.3, y));
	col = mix(col, zenith_col, smoothstep(0.25, 0.9, y));
	if (y > -0.05) {
		// project onto a cloud plane and layer streaky noise
		vec2 uv = d.xz / (max(y, 0.0) + 0.12) * 1.6;
		float n = fbm(uv * vec2(1.0, 2.4) + vec2(3.0, 0.0));
		float n2 = fbm(uv * 3.1 + vec2(n * 1.5, 7.0));
		float c = smoothstep(0.35, 0.75, n * 0.7 + n2 * 0.45);
		vec3 cc = mix(cloud_dark, cloud_light, n2);
		col = mix(col, cc, c * smoothstep(-0.05, 0.25, y) * 0.85);
		// a faint glow where the sun hides behind the clouds
		float sd = max(dot(d, sun_dir), 0.0);
		col += vec3(0.5, 0.48, 0.42) * pow(sd, 12.0) * 0.25 * (1.0 - c * 0.6);
	}
	if (y < 0.0) col = mix(horizon_col, ground_col, smoothstep(0.0, -0.2, y));
	COLOR = col;
}
