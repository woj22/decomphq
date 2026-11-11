shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;
// A billboarded snowflake that is never drawn inside the carriage (|x| < 1.75 along the train), whatever the
// particle simulation does on a given phone's GPU.

uniform vec4 colour : source_color = vec4(0.85, 0.9, 1.0, 0.9);
varying float inside;

void vertex() {
	vec3 centre = MODEL_MATRIX[3].xyz;
	inside = (abs(centre.x) < 1.75 && centre.z > -2.5 && centre.z < 33.5 && centre.y < 3.0) ? 1.0 : 0.0;
	float s = length(MODEL_MATRIX[0].xyz);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0] * s, INV_VIEW_MATRIX[1] * s, INV_VIEW_MATRIX[2] * s, vec4(centre, 1.0));
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	if (inside > 0.5) { discard; }
	float d = length(UV - 0.5) * 2.0;
	ALBEDO = colour.rgb;
	ALPHA = colour.a * smoothstep(1.0, 0.0, d) * COLOR.a;
}
