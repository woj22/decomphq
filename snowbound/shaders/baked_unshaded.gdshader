shader_type spatial;
render_mode unshaded;
// Train interior surfaces: light comes from the Blender bake (UV2, stored as sRGB of light/scale) and is added as
// emission; real-time lamps contribute a little diffuse plus the specular glints on varnished wood and brass.

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool use_albedo = false;
uniform vec4 tint : source_color = vec4(1.0);
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool use_normal = false;
uniform float normal_depth = 1.0;
uniform sampler2D rough_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform bool use_rough = false;
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform float specular : hint_range(0.0, 1.0) = 0.5;
uniform sampler2D lightmap : source_color, filter_linear;
uniform float lightmap_scale = 1.6;
uniform float direct = 0.22;
uniform vec3 glow_color : source_color = vec3(0.0);
uniform float glow_energy = 0.0;

void fragment() {
	vec3 a = tint.rgb;
	if (use_albedo) { a *= texture(albedo_tex, UV).rgb; }
	vec3 lm = texture(lightmap, UV2).rgb * lightmap_scale;
	ALBEDO = a * direct;
	EMISSION = a * lm * (1.0 - metallic * 0.5) + glow_color * glow_energy;
	float r = roughness;
	if (use_rough) { r = clamp(texture(rough_tex, UV).r * roughness * 1.6, 0.04, 1.0); }
	ROUGHNESS = r;
	METALLIC = metallic;
	SPECULAR = specular;
	if (use_normal) { NORMAL_MAP = texture(normal_tex, UV).rgb; NORMAL_MAP_DEPTH = normal_depth; }
}
