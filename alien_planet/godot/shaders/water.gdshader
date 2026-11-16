// Lake water: transparent, Gerstner waves in the vertex shader, small ripples in the fragment shader,
// depth-based colour/clarity and shoreline foam (from the depth buffer), sky reflections + sun glints.
// No textures. Works in the Compatibility renderer (mobile).
shader_type spatial;
render_mode blend_mix, cull_back, depth_draw_always, specular_schlick_ggx;

uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

uniform vec3 shallow_col : source_color = vec3(0.16, 0.58, 0.62);
uniform vec3 deep_col : source_color = vec3(0.02, 0.15, 0.28);
uniform vec3 foam_col : source_color = vec3(0.92, 0.97, 1.0);
uniform float clarity = 0.32;          // how quickly the water gets opaque with depth (per metre)
uniform float wave_height = 0.11;
uniform float wave_speed = 1.0;
uniform bool debug_depth = false;

varying vec3 wpos;

// one Gerstner wave: dir (normalised), wavelength, steepness
vec3 gerstner(vec2 p, vec2 dir, float wl, float steep, float t, inout vec3 tangent, inout vec3 binormal) {
	float k = 6.2831 / wl;
	float c = sqrt(9.8 / k);
	float f = k * (dot(dir, p) - c * t);
	float a = steep / k;
	tangent += vec3(-dir.x * dir.x * steep * sin(f), dir.x * steep * cos(f), -dir.x * dir.y * steep * sin(f));
	binormal += vec3(-dir.x * dir.y * steep * sin(f), dir.y * steep * cos(f), -dir.y * dir.y * steep * sin(f));
	return vec3(dir.x * a * cos(f), a * sin(f), dir.y * a * cos(f));
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float t = TIME * wave_speed;
	vec3 tng = vec3(1.0, 0.0, 0.0);
	vec3 bin = vec3(0.0, 0.0, 1.0);
	vec3 off = vec3(0.0);
	float s = wave_height / 0.16;
	off += gerstner(w.xz, normalize(vec2(1.0, 0.35)), 9.0, 0.10 * s, t, tng, bin);
	off += gerstner(w.xz, normalize(vec2(-0.4, 1.0)), 5.5, 0.08 * s, t, tng, bin);
	off += gerstner(w.xz, normalize(vec2(0.7, -0.8)), 3.2, 0.06 * s, t, tng, bin);
	off += gerstner(w.xz, normalize(vec2(-1.0, -0.2)), 13.0, 0.05 * s, t, tng, bin);
	VERTEX += off;
	NORMAL = normalize(cross(bin, tng));
	wpos = w + off;
}

// cheap animated ripple normal (sum of sines in several directions)
vec2 ripples(vec2 p, float t) {
	vec2 g = vec2(0.0);
	vec2 d1 = vec2(0.8, 0.6), d2 = vec2(-0.5, 0.86), d3 = vec2(0.2, -0.98), d4 = vec2(-0.95, -0.3);
	g += d1 * cos(dot(p, d1) * 2.1 + t * 2.3) * 0.5;
	g += d2 * cos(dot(p, d2) * 2.9 - t * 2.9) * 0.35;
	g += d3 * cos(dot(p, d3) * 4.3 + t * 3.7) * 0.22;
	g += d4 * cos(dot(p, d4) * 6.1 - t * 4.1) * 0.12;
	return g;
}

void fragment() {
	float t = TIME * wave_speed;
	// ripple detail on top of the wave normal (in view space)
	vec2 r = ripples(wpos.xz, t) * 0.08;
	vec3 n_world = normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz + vec3(r.x, 0.0, r.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(n_world, 0.0)).xyz);

	// water depth below the surface along the view ray, from the depth buffer
	float raw = texture(depth_tex, SCREEN_UV).r;
	vec4 ndc = vec4(SCREEN_UV * 2.0 - 1.0, raw * 2.0 - 1.0, 1.0);   // Compatibility: GL depth range -1..1
	vec4 view = INV_PROJECTION_MATRIX * ndc;
	float scene_z = -view.z / view.w;
	float surf_z = -VERTEX.z;
	float depth = max(scene_z - surf_z, 0.0);

	float k = 1.0 - exp(-depth * clarity);
	vec3 col = mix(shallow_col, deep_col, k);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);

	// foam along the shore, broken up by the ripples
	float foam_line = 1.0 - smoothstep(0.0, 0.3, depth);
	float foam_noise = 0.5 + 0.5 * sin(wpos.x * 3.1 + sin(wpos.z * 2.3 + t) * 2.0 + t * 1.3);
	float foam = clamp(foam_line * (0.4 + 0.55 * foam_noise), 0.0, 1.0);
	foam *= smoothstep(0.02, 0.12, depth);   // fade at the exact contact line

	ALBEDO = mix(col, foam_col, foam);
	ROUGHNESS = mix(0.07, 0.6, foam);
	METALLIC = 0.0;
	SPECULAR = 0.32;
	ALPHA = clamp(mix(0.12, 0.9, k) + fres * 0.3 + foam * 0.8, 0.0, 1.0);
	if (debug_depth) { ALBEDO = vec3(fract(depth), raw > 0.9999 ? 1.0 : 0.0, depth / 10.0); ALPHA = 1.0; }
}
