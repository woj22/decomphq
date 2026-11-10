extends Node2D
const TW := 32
const TH := 16
const HPX := 8
var world: Node2D
var player: Node2D
var astar := AStarGrid2D.new()
var ground: TileMapLayer
var path: PackedVector2Array
var got_tap := false
var frames := 0

func diamond(img: Image, ox: int, oy: int, col: Color) -> void:
	for y in TH:
		for x in TW:
			var dx: float = abs(x + 0.5 - TW / 2.0) / (TW / 2.0)
			var dy: float = abs(y + 0.5 - TH / 2.0) / (TH / 2.0)
			if dx + dy <= 1.0:
				var c := col
				if dx + dy > 0.85: c = col.darkened(0.3)
				img.set_pixel(ox + x, oy + y, c)

func make_atlas() -> ImageTexture:
	var img := Image.create(TW * 3, 48, false, Image.FORMAT_RGBA8)
	diamond(img, 0, 32, Color("3a3644"))          # floor
	for h in range(32, -1, -1):                    # wall cube 32px tall
		diamond(img, TW, h, Color("5a5468") if h == 0 else Color("2a2632").lightened(0.004 * (32 - h)))
	for h in range(4, -1, -1):                     # deck slab
		diamond(img, TW * 2, 28 + h, Color("8a6a3a") if h == 0 else Color("4a3a20"))
	return ImageTexture.create_from_image(img)

func make_layer(ts: TileSet, elev: int, sorted: bool) -> TileMapLayer:
	var l := TileMapLayer.new()
	l.tile_set = ts
	l.y_sort_enabled = sorted
	l.position.y = -elev * HPX
	l.y_sort_origin = elev * HPX
	l.z_index = (elev / 6) * 10
	world.add_child(l)
	return l

func _ready() -> void:
	var ts := TileSet.new()
	ts.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	ts.tile_layout = TileSet.TILE_LAYOUT_DIAMOND_DOWN
	ts.tile_size = Vector2i(TW, TH)
	var src := TileSetAtlasSource.new()
	src.texture = make_atlas()
	src.texture_region_size = Vector2i(TW, 48)
	for i in 3:
		src.create_tile(Vector2i(i, 0))
		src.get_tile_data(Vector2i(i, 0), 0).texture_origin = Vector2i(0, 16)
	ts.add_source(src, 0)
	world = Node2D.new(); world.y_sort_enabled = true; add_child(world)
	ground = make_layer(ts, 0, false); ground.z_index = -1
	var walls := make_layer(ts, 0, true)
	var deck := make_layer(ts, 6, true)
	var walls1 := make_layer(ts, 6, true)
	walls1.set_cell(Vector2i(12, 9), 0, Vector2i(1, 0))
	astar.region = Rect2i(0, 0, 16, 16)
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.update()
	for y in 16:
		for x in 16:
			ground.set_cell(Vector2i(x, y), 0, Vector2i(0, 0))
			if (x == 8 and y != 12 and y > 2) or (y == 3 and x > 3 and x < 8):
				walls.set_cell(Vector2i(x, y), 0, Vector2i(1, 0))
				astar.set_point_solid(Vector2i(x, y))
	for x in range(2, 15): deck.set_cell(Vector2i(x, 9), 0, Vector2i(2, 0))  # bridge over ground
	print("map_to_local(0,0)=", ground.map_to_local(Vector2i(0, 0)), " (1,0)=", ground.map_to_local(Vector2i(1, 0)), " (0,1)=", ground.map_to_local(Vector2i(0, 1)))
	print("local_to_map(48,24)=", ground.local_to_map(Vector2(48, 24)))
	# characters: one behind wall, one in front, one under bridge, one on bridge
	var pimg := Image.create(12, 22, false, Image.FORMAT_RGBA8); pimg.fill(Color("d8c070"))
	var ptex := ImageTexture.create_from_image(pimg)
	var spots := [[Vector2i(7, 6), 0, Color.WHITE], [Vector2i(9, 6), 0, Color.CYAN], [Vector2i(5, 7), 0, Color.RED], [Vector2i(11, 9), 6, Color.GREEN], [Vector2i(6, 9), 6, Color.YELLOW]]
	for s in spots:
		var n := Node2D.new(); n.position = ground.map_to_local(s[0]) ; n.z_index = (s[1] / 6) * 10
		var sp := Sprite2D.new(); sp.texture = ptex; sp.offset = Vector2(0, -11); sp.position.y = -s[1] * HPX; sp.modulate = s[2]
		n.add_child(sp); world.add_child(n)
		if s[2] == Color.WHITE: player = n
	# crowd: 400 sprites
	var rng := RandomNumberGenerator.new(); rng.seed = 1
	var cimg := Image.create(6, 12, false, Image.FORMAT_RGBA8); cimg.fill(Color(0.8, 0.8, 0.9, 0.8))
	var ctex := ImageTexture.create_from_image(cimg)
	for i in 400:
		var sp := Sprite2D.new(); sp.texture = ctex; sp.offset = Vector2(0, -6)
		sp.position = ground.map_to_local(Vector2i(rng.randi_range(0, 7), rng.randi_range(10, 15))) + Vector2(rng.randf_range(-8, 8), rng.randf_range(-4, 4))
		world.add_child(sp)
	var cam := Camera2D.new(); cam.position = ground.map_to_local(Vector2i(8, 8)); add_child(cam)
	print("viewport visible rect=", get_viewport().get_visible_rect(), " window=", get_window().size, " xform=", get_viewport().get_final_transform())
	# scripted tap -> path
	var ev := InputEventScreenTouch.new(); ev.pressed = true; ev.position = Vector2(100, 100)
	Input.parse_input_event(ev)
	var t := Time.get_ticks_usec()
	for i in 200: astar.get_id_path(Vector2i(0, 0), Vector2i(15, 15))
	print("200 A* 16x16 usec=", Time.get_ticks_usec() - t)
	path = astar.get_point_path(Vector2i(7, 6), Vector2i(9, 6))
	print("path 7,6 -> 9,6 len=", path.size())

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventScreenTouch and e.pressed:
		got_tap = true
		var wp: Vector2 = get_canvas_transform().affine_inverse() * e.position
		print("tap screen=", e.position, " world=", wp, " cell=", ground.local_to_map(ground.to_local(wp)))

func _process(_d: float) -> void:
	frames += 1
	if frames == 10:
		get_viewport().get_texture().get_image().save_png("res://shot.png")
		print("fps=", Engine.get_frames_per_second(), " draw_calls=", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME), " got_tap=", got_tap)
		get_tree().quit()
