// Dusk sky: gradient, sun with halo, a small pale moon, faint stars high up. Analytic, no textures.
// Static (no TIME), so Godot only builds the radiance/ambient once.
shader_type sky;

uniform vec3 sun_dir = vec3(0.44, 0.36, 0.82);
uniform vec3 moon_dir = vec3(-0.5, 0.55, -0.67);
uniform vec3 zenith_col : source_color = vec3(0.16, 0.36, 0.78);
uniform vec3 mid_col : source_color = vec3(0.42, 0.64, 0.93);
uniform vec3 horizon_col : source_color = vec3(0.86, 0.91, 0.96);
uniform vec3 ground_col : source_color = vec3(0.38, 0.33, 0.36);
uniform float star_strength = 0.0;

float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

vec3 sky_grad(vec3 d) {
	float y = d.y;
	vec3 col = mix(horizon_col, mid_col, smoothstep(0.0, 0.32, y));
	col = mix(col, zenith_col, smoothstep(0.28, 0.95, y));
	float sd = max(dot(d, sun_dir), 0.0);
	// warm forward-scatter around the sun, strongest near the horizon
	col += vec3(1.0, 0.9, 0.7) * pow(sd, 8.0) * 0.25;
	col += vec3(1.0, 0.95, 0.85) * pow(sd, 60.0) * 0.35;
	return col;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	vec3 col = sky_grad(d);
	float y = d.y;
	float sd = max(dot(d, sun_dir), 0.0);
	if (AT_CUBEMAP_PASS == false && y > 0.0) {
		vec3 g = floor(d * 260.0);
		float h = hash(g);
		float star = step(0.9975, h) * smoothstep(0.35, 0.85, y);
		col += vec3(0.9, 0.92, 1.0) * star * (0.4 + 0.6 * hash(g + 3.1)) * star_strength;
	}
	// sun disc + glare
	col += vec3(1.0, 0.82, 0.6) * pow(sd, 350.0) * 1.6;
	col += vec3(1.0, 0.95, 0.88) * smoothstep(0.9994, 0.9997, sd) * 3.0;
	// small pale moon
	vec3 mdir = normalize(moon_dir);
	float md = dot(d, mdir);
	if (md > 0.9993) {
		float lit = clamp(dot(d - mdir, sun_dir) * 40.0 + 0.5, 0.0, 1.0);
		col = mix(col, vec3(0.86, 0.88, 0.92) * (0.45 + 0.55 * lit), smoothstep(0.9993, 0.99945, md));
	}
	if (y < 0.0) col = mix(sky_grad(vec3(d.x, 0.0, d.z)), ground_col, smoothstep(0.0, -0.2, y));
	COLOR = col;
}
