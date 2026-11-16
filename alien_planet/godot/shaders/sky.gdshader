// Alien dusk sky: gradient, sun, stars and a huge ringed gas giant, all analytic (no textures).
// Static (no TIME), so Godot only builds the radiance/ambient once.
shader_type sky;

uniform vec3 sun_dir = vec3(0.44, 0.36, 0.82);
uniform vec3 planet_dir = vec3(0.83, 0.47, -0.30);
uniform vec3 ring_axis = vec3(0.2, 0.95, 0.25);
uniform vec3 planet_light = vec3(0.0, 0.5, 0.86);
uniform vec3 moon_dir = vec3(-0.5, 0.55, -0.67);
uniform float planet_size = 0.26;
uniform vec3 zenith_col : source_color = vec3(0.09, 0.11, 0.27);
uniform vec3 mid_col : source_color = vec3(0.40, 0.27, 0.52);
uniform vec3 horizon_col : source_color = vec3(1.0, 0.60, 0.47);
uniform vec3 ground_col : source_color = vec3(0.30, 0.20, 0.36);
uniform vec3 planet_a : source_color = vec3(0.96, 0.84, 0.66);
uniform vec3 planet_b : source_color = vec3(0.80, 0.45, 0.36);
uniform vec3 planet_c : source_color = vec3(0.55, 0.42, 0.62);
uniform vec3 ring_col : source_color = vec3(0.93, 0.80, 0.66);

float hash(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

vec3 sky_grad(vec3 d) {
	float y = d.y;
	vec3 col = mix(horizon_col, mid_col, smoothstep(0.0, 0.28, y));
	col = mix(col, zenith_col, smoothstep(0.25, 0.95, y));
	float sd = max(dot(d, sun_dir), 0.0);
	col += vec3(1.0, 0.5, 0.3) * pow(sd, 5.0) * 0.45 * (1.0 - smoothstep(0.0, 0.7, y));
	return col;
}

void sky() {
	vec3 d = normalize(EYEDIR);
	vec3 col = sky_grad(d);
	float y = d.y;
	float sd = max(dot(d, sun_dir), 0.0);
	// stars and a faint nebula band (only at the screen pass, not in the radiance map)
	if (AT_CUBEMAP_PASS == false && y > 0.0) {
		vec3 g = floor(d * 260.0);
		float h = hash(g);
		float star = step(0.9972, h) * smoothstep(0.08, 0.55, y);
		col += vec3(0.9, 0.9, 1.0) * star * (0.4 + 0.6 * hash(g + 3.1));
		float neb = pow(max(0.0, 1.0 - abs(dot(d, normalize(vec3(0.3, 0.4, 0.86)))) * 3.0), 2.0);
		neb *= 0.5 + 0.5 * sin(d.x * 9.0 + sin(d.z * 7.0) * 2.0);
		col += vec3(0.55, 0.25, 0.6) * neb * 0.16 * smoothstep(0.1, 0.6, y);
	}
	// sun
	col += vec3(1.0, 0.8, 0.55) * pow(sd, 300.0) * 2.0;
	col += vec3(1.0, 0.95, 0.85) * smoothstep(0.9994, 0.9997, sd) * 3.0;

	// small pale moon
	float md = dot(d, normalize(moon_dir));
	if (md > 0.9993) {
		vec3 mn = normalize(d - normalize(moon_dir) * 0.9993);
		col = mix(col, vec3(0.75, 0.85, 0.95) * (0.3 + 0.7 * clamp(dot(d - normalize(moon_dir), sun_dir) * 40.0 + 0.5, 0.0, 1.0)), smoothstep(0.9993, 0.99945, md));
	}

	// ringed planet: sphere at distance 1 along planet_dir
	vec3 C = normalize(planet_dir);
	float R = planet_size;
	vec3 ax = normalize(ring_axis);
	float b = dot(d, C);
	float disc = b * b - (1.0 - R * R);
	float t_planet = 1e9;
	vec4 pl = vec4(0.0);
	if (disc > 0.0 && b > 0.0) {
		t_planet = b - sqrt(disc);
		vec3 p = d * t_planet;
		vec3 n = normalize(p - C);
		float lat = dot(n, ax);
		float bands = sin(lat * 22.0 + sin(lat * 9.0 + n.x * 3.0) * 1.3);
		float bands2 = sin(lat * 61.0 + bands * 2.0);
		vec3 pc = mix(planet_a, planet_b, smoothstep(-0.4, 0.9, bands));
		pc = mix(pc, planet_c, smoothstep(0.6, 1.0, bands2) * 0.35);
		vec3 pld = normalize(planet_light);
		float diff = smoothstep(-0.2, 0.5, dot(n, pld));
		float tr = dot(C - p, ax) / dot(pld, ax);
		if (tr > 0.0) {
			float rq = length(p + pld * tr - C) / R;
			if (rq > 1.35 && rq < 2.3) diff *= 0.55;
		}
		vec3 lit = pc * (diff * 1.05 + 0.10);
		float rim = pow(1.0 - clamp(dot(n, -d), 0.0, 1.0), 2.5);
		lit += vec3(1.0, 0.65, 0.75) * rim * 0.45 * (0.25 + diff);
		float edge = smoothstep(0.0, 0.0012, disc);
		pl = vec4(lit, edge);
	}
	vec4 rg = vec4(0.0);
	float t_ring = 1e9;
	float dn = dot(d, ax);
	if (abs(dn) > 1e-4) {
		t_ring = dot(C, ax) / dn;
		if (t_ring > 0.0) {
			vec3 q = d * t_ring;
			float rq = length(q - C) / R;
			if (rq > 1.3 && rq < 2.4) {
				float rb = (0.5 + 0.5 * sin(rq * 47.0)) * (0.55 + 0.45 * sin(rq * 13.0 + 1.0));
				float gap = smoothstep(1.76, 1.79, rq) * (1.0 - smoothstep(1.86, 1.89, rq));
				float a = (0.35 + 0.6 * rb) * (1.0 - gap * 0.92) * smoothstep(1.32, 1.42, rq) * (1.0 - smoothstep(2.2, 2.38, rq));
				vec3 oc = q - C;
				vec3 pl2 = normalize(planet_light);
				float bb = dot(oc, pl2);
				float sh = (bb < 0.0 && bb * bb - (dot(oc, oc) - R * R) > 0.0) ? 0.2 : 1.0;
				rg = vec4(ring_col * (0.35 + 0.8 * sh) * mix(0.8, 1.15, rb), a * 0.9);
			}
		}
	}
	vec3 res = col;
	if (t_ring > t_planet) {
		res = mix(res, rg.rgb, rg.a);
		res = mix(res, pl.rgb, pl.a);
	} else {
		res = mix(res, pl.rgb, pl.a);
		res = mix(res, rg.rgb, rg.a);
	}
	// thick lower atmosphere washes out the giant near the horizon
	res = mix(res, col, (1.0 - smoothstep(-0.02, 0.32, y)) * 0.7);
	if (y < 0.0) res = mix(sky_grad(vec3(d.x, 0.0, d.z)), ground_col, smoothstep(0.0, -0.2, y));
	COLOR = res;
}
