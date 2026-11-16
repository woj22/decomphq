// Stylised low-poly lake water, matching the flat-shaded world:
// faceted gently rolling surface, clear turquoise shallows fading to deep blue (depth buffer),
// sparkling sun glints on the facets, a soft sky reflection, and crisp foam rings lapping the shore.
// Lighting is done here (unshaded) so the look is fully controlled and cheap. No textures.
shader_type spatial;
render_mode blend_mix, cull_back, depth_draw_always, unshaded, shadows_disabled;

uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;

uniform vec3 sun_dir = vec3(0.44, 0.36, 0.82);
uniform vec3 sun_col : source_color = vec3(1.0, 0.9, 0.75);
uniform vec3 shallow_col : source_color = vec3(0.30, 0.78, 0.74);
uniform vec3 mid_col : source_color = vec3(0.10, 0.50, 0.62);
uniform vec3 deep_col : source_color = vec3(0.05, 0.22, 0.42);
uniform vec3 sky_reflect : source_color = vec3(0.42, 0.58, 0.82);
uniform vec3 foam_col : source_color = vec3(0.95, 0.98, 1.0);
uniform float clarity = 0.2;           // how quickly the water tints with depth (per metre)
uniform float max_opacity = 0.62;      // never fully opaque: the lake bed always shows through
uniform float wave_height = 0.09;
uniform float wave_speed = 0.8;
uniform bool debug_depth = false;

varying vec3 wpos;

float wave(vec2 p, vec2 dir, float wl, float amp, float t) {
	float k = 6.2831 / wl;
	return amp * sin(dot(dir, p) * k - t * sqrt(9.8 * k));
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float t = TIME * wave_speed;
	float h = 0.0;
	h += wave(w.xz, normalize(vec2(1.0, 0.3)), 7.0, 1.0, t);
	h += wave(w.xz, normalize(vec2(-0.3, 1.0)), 4.6, 0.7, t);
	h += wave(w.xz, normalize(vec2(0.8, -0.7)), 3.1, 0.45, t);
	VERTEX.y += h * wave_height;
	wpos = w + vec3(0.0, h * wave_height, 0.0);
}

void fragment() {
	// faceted normal from screen-space derivatives (flat shading, like the rest of the world)
	vec3 n = normalize(cross(dFdy(wpos), dFdx(wpos)));
	if (n.y < 0.0) n = -n;
	vec3 v = normalize(CAMERA_POSITION_WORLD - wpos);

	// water depth along the view ray, from the depth buffer (Compatibility: NDC z in -1..1)
	float raw = texture(depth_tex, SCREEN_UV).r;
	vec4 view = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, raw * 2.0 - 1.0, 1.0);
	float depth = max(-view.z / view.w + VERTEX.z, 0.0);
	if (raw >= 0.99999) depth = 2.0;   // no depth info (or sky behind): assume a moderate depth

	float k = 1.0 - exp(-depth * clarity);
	vec3 col = mix(shallow_col, mid_col, smoothstep(0.0, 0.55, k));
	col = mix(col, deep_col, smoothstep(0.5, 1.0, k));

	// soft sky reflection (fresnel) and sun light on the facets
	float fres = 0.04 + 0.6 * pow(1.0 - clamp(dot(n, v), 0.0, 1.0), 5.0);
	col = mix(col, sky_reflect, fres);
	col *= 0.85 + 0.25 * clamp(dot(n, sun_dir), 0.0, 1.0);
	vec3 r = reflect(-v, n);
	float glint = pow(max(dot(r, sun_dir), 0.0), 120.0);
	float sparkle = step(0.985, max(dot(r, sun_dir), 0.0));   // crisp facet flashes

	// foam: a solid contact line plus rings that lap in towards the shore
	float t = TIME * wave_speed;
	float edge = 1.0 - smoothstep(0.03, 0.08, depth);
	float ring = fract(depth * 2.2 + t * 0.35);
	float rings = step(0.86, ring) * (1.0 - smoothstep(0.15, 0.75, depth));
	float breakup = step(0.35, fract(sin(dot(floor(wpos.xz * 1.5), vec2(12.9898, 78.233))) * 43758.5453));
	float foam = max(edge, rings * breakup) * smoothstep(0.0, 0.03, depth);

	vec3 outc = col + sun_col * (glint * 0.8 + sparkle * 0.6);
	outc = mix(outc, foam_col, foam * 0.9);
	ALBEDO = outc;
	ALPHA = clamp(mix(0.12, max_opacity, k) + fres * 0.3 + foam + glint, 0.0, 1.0);
	if (debug_depth) { ALBEDO = vec3(fract(depth), 0.0, depth / 10.0); ALPHA = 1.0; }
}
