extends Node
## Game clock. Actions still cost time (PROJECT §2), and (owner request) the 24-hour day also runs in real time:
## `clock_realtime_minutes_per_second` game minutes per real second while the player is free in the world.
## Night = 22:00-06:00: the fortress sleeps (see World / AmbientLife / area door conditions).

var day := 1
var minutes := 480
var running := false
var total_minutes := 0


func reset() -> void:
	day = 1
	minutes = Content.cfg_i("clock_start", 480)
	running = false
	total_minutes = 0
	_was_night = false


func start_shift(d: int) -> void:
	# Same calendar day if it is still morning; otherwise the shift starts the next morning.
	if d > day:
		day = d
	elif hour() >= 12:
		day += 1
	minutes = Content.cfg_i("clock_start", 480)
	running = true
	EventBus.clock_ticked.emit(day, minutes)


func stop_shift() -> void:
	running = false


## Advances game time for an action. Ignored while the clock is frozen (before the docket / after the ledger).
func advance(m: int, _reason: String = "") -> void:
	if m <= 0 or not running:
		return
	minutes += m
	total_minutes += m
	Sim.advance_game(m)
	EventBus.clock_ticked.emit(day, minutes)


signal night_changed(night: bool)

var _rt_acc := 0.0
var _was_night := false


func is_night() -> bool:
	var h := (minutes / 60) % 24
	return h >= Content.cfg_i("night_from_hour", 22) or h < Content.cfg_i("night_to_hour", 6)


## Hour of day 0..23.
func hour() -> int:
	return (minutes / 60) % 24


func _process(delta: float) -> void:
	if not GameState.in_game or World.player == null or World.input_locked():
		return
	if Playtest.active and not Playtest.realtime_clock:
		return
	_rt_acc += delta * Content.cfg_f("clock_realtime_minutes_per_second", 1.0)
	if _rt_acc >= 1.0:
		var m := int(_rt_acc)
		_rt_acc -= m
		tick(m)


## Real-time passage: always runs (even outside a shift), rolls over midnight, flags night changes.
func tick(m: int) -> void:
	minutes += m
	total_minutes += m
	while minutes >= 1440:
		minutes -= 1440
		day += 1
	if running:
		Sim.advance_game(m)
	EventBus.clock_ticked.emit(day, minutes)
	_check_night()


func _check_night() -> void:
	var n := is_night()
	if n != _was_night:
		_was_night = n
		night_changed.emit(n)


## Sleep until the next 06:00 (dormitory beds).
func sleep_until_morning() -> void:
	var wake := Content.cfg_i("night_to_hour", 6) * 60
	var add := wake - minutes
	if add <= 0:
		add += 1440
	tick(add)


func overtime() -> bool:
	return minutes >= Content.cfg_i("overtime_after", 1080)


func time_text() -> String:
	var h := (minutes / 60) % 24
	var m := minutes % 60
	return "%02d:%02d" % [h, m]


func label() -> String:
	return "Day %d - %s%s" % [day, time_text(), " (overtime)" if overtime() else ""]


func to_dict() -> Dictionary:
	return {"day": day, "minutes": minutes, "running": running, "total": total_minutes}


func from_dict(d: Dictionary) -> void:
	day = int(d.get("day", 1))
	minutes = int(d.get("minutes", 480))
	running = bool(d.get("running", false))
	total_minutes = int(d.get("total", 0))
	_was_night = is_night()
	EventBus.clock_ticked.emit(day, minutes)
