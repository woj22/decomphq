// Stylised low-poly clouds: unshaded vertex colour (sunlit tops, cool undersides baked in), no fog.
shader_type spatial;
render_mode unshaded, fog_disabled, shadows_disabled, cull_back;

void fragment() {
	ALBEDO = COLOR.rgb;
}
