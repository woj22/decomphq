extends TestBase


func test_cell_to_local() -> void:
	assert_eq(Iso.cell_to_local(Vector2(0, 0)), Vector2(32, 16))
	assert_eq(Iso.cell_to_local(Vector2(1, 0)), Vector2(64, 32))
	assert_eq(Iso.cell_to_local(Vector2(0, 1)), Vector2(0, 32))
	assert_eq(Iso.cell_to_local(Vector2(3, 2)), Vector2(64, 96))


func test_round_trip() -> void:
	for cx in range(-3, 15):
		for cy in range(-3, 15):
			var c := Vector2(cx, cy)
			var back := Iso.local_to_cell(Iso.cell_to_local(c))
			assert_near(back.x, c.x, 0.0001)
			assert_near(back.y, c.y, 0.0001)
			assert_eq(Iso.local_to_cell_i(Iso.cell_to_local(c) + Vector2(5, 3)), Vector2i(cx, cy))


func test_matches_tilemap() -> void:
	var ts := TileSet.new()
	ts.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	ts.tile_layout = TileSet.TILE_LAYOUT_DIAMOND_DOWN
	ts.tile_size = Vector2i(64, 32)
	var l := TileMapLayer.new()
	l.tile_set = ts
	for c: Vector2i in [Vector2i(0, 0), Vector2i(1, 0), Vector2i(0, 1), Vector2i(5, 7)]:
		assert_eq(l.map_to_local(c), Iso.cellv(c))
	l.free()


func test_facing() -> void:
	assert_eq(Iso.facing_from_screen(Vector2(1, 0)), "e")
	assert_eq(Iso.facing_from_screen(Vector2(0, 1)), "s")
	assert_eq(Iso.facing_from_screen(Vector2(-1, -1)), "nw")
	assert_eq(Iso.facing_from_grid(Vector2(1, 0)), "se")
	assert_eq(Iso.facing_from_grid(Vector2(0, 1)), "sw")
	assert_eq(Iso.facing_from_grid(Vector2(-1, 0)), "nw")
	assert_eq(Iso.facing_from_grid(Vector2(1, 1)), "s")
