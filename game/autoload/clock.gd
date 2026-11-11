extends Node
## Action-driven game clock (PROJECT §2, ruling C07). No real-time tick.

var day := 1
var minutes := 480
var running := false
var total_minutes := 0


func reset() -> void:
	day = 1
	minutes = Content.cfg_i("clock_start", 480)
	running = false
	total_minutes = 0


func start_shift(d: int) -> void:
	day = d
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
	EventBus.clock_ticked.emit(day, minutes)
