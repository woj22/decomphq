// Alien wheat: gusts roll across the fields as travelling waves; stalks bend with the wind and the
// grain heads catch a brighter sheen where the gust passes. UV.x = bend weight (0 at the root), UV.y = phase.
shader_type spatial;
render_mode cull_disabled, specular_disabled;

uniform vec2 wind_dir = vec2(0.8, 0.6);
uniform float gust_scale = 0.11;     // spatial frequency of gust bands (per metre)
uniform float gust_speed = 2.3;   // storm wind
uniform float bend = 0.42;
varying float v_gust;

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 wd = normalize(wind_dir);
	float along = dot(wp.xz, wd);
	float g1 = sin(along * gust_scale * 6.2831 - TIME * gust_speed);
	float g2 = sin(dot(wp.xz, vec2(-wd.y, wd.x)) * 0.05 + along * 0.31 - TIME * gust_speed * 1.7);
	float gust = clamp(0.55 + 0.45 * g1 + 0.2 * g2, 0.0, 1.0);
	float w = UV.x;
	float flutter = sin(TIME * 5.3 + UV.y * 6.2831 + wp.x * 1.7) * 0.035;
	float b = w * (bend * (0.25 + 0.75 * gust)) + w * flutter;
	VERTEX.x += wd.x * b;
	VERTEX.z += wd.y * b;
	VERTEX.y -= w * b * b * 0.6;
	v_gust = gust * w;
}

void fragment() {
	ALBEDO = COLOR.rgb * (0.85 + 0.3 * v_gust);
	ROUGHNESS = 1.0;
	BACKLIGHT = COLOR.rgb * 0.45;
}
