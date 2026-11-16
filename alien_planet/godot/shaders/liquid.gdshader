// The glowing lake: opaque (no overdraw), animated bands, fresnel towards the sky colour.
shader_type spatial;
render_mode cull_back, specular_schlick_ggx;

uniform vec3 deep : source_color = vec3(0.03, 0.18, 0.28);
uniform vec3 shallow : source_color = vec3(0.10, 0.70, 0.68);
uniform vec3 sheen : source_color = vec3(0.95, 0.55, 0.75);
uniform vec3 glint : source_color = vec3(0.55, 1.0, 0.92);
varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += sin(wpos.x * 0.35 + TIME * 0.9) * 0.05 + sin(wpos.z * 0.29 - TIME * 0.7) * 0.05;
}

void fragment() {
	vec2 p = wpos.xz;
	float w = sin(p.x * 0.21 + TIME * 0.35) + sin(p.y * 0.26 - TIME * 0.45) + sin((p.x + p.y) * 0.13 + TIME * 0.2);
	float band = smoothstep(0.82, 0.98, fract(w * 0.6));
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	vec3 c = mix(deep, shallow, 0.35 + 0.25 * sin(w));
	ALBEDO = mix(c * 0.3, sheen * 0.3, fres * 0.3);
	EMISSION = c * 0.9 + glint * band * 0.45;
	ROUGHNESS = 0.35;
	SPECULAR = 0.08;
}
