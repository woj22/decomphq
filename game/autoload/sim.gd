extends Node
## Prototype simulation counters (PROJECT §6). Advanced by game minutes; a 4 Hz real-time tick drives presentation only.

signal presentation_tick()

var arrival := 16 # A
var bench := 8 # J
var acc_arrival := 0.0
var acc_registrar := 0.0
var acc_adjudicator := 0.0
var heaven_out := 0
var hell_out := 0
var rng := SeededRng.new(991)
var _tick_accum := 0.0


func _ready() -> void:
	reset()


func reset() -> void:
	arrival = Content.cfg_i("queue_arrival_start", 16)
	bench = Content.cfg_i("queue_bench_start", 8)
	acc_arrival = 0.0
	acc_registrar = 0.0
	acc_adjudicator = 0.0
	heaven_out = 0
	hell_out = 0
	rng = SeededRng.new(Content.cfg_i("sim_seed", 991))


func queue_total() -> int:
	return arrival + bench


## Advances counters minute by minute from the clock's current time (called by Clock.advance before minutes is final).
func advance_game(m: int) -> void:
	var start: int = Clock.minutes - m
	var early := Content.cfg_f("arrival_rate_early", 3.0)
	var late := Content.cfg_f("arrival_rate_late", 2.0)
	var switch_at := Content.cfg_i("arrival_rate_switch", 600)
	var reg := Content.cfg_f("registrar_rate", 2.4)
	var adj := Content.cfg_f("adjudicator_rate", 1.2)
	var cap := Content.cfg_i("queue_bench_cap", 12)
	var hell_share := Content.cfg_f("adjudicator_hell_share", 0.6)
	for i in m:
		var t := start + i
		var h := (t / 60) % 24
		if h >= Content.cfg_i("night_from_hour", 22) or h < Content.cfg_i("night_to_hour", 6):
			continue # the fortress sleeps
		acc_arrival += (early if t < switch_at else late) / 60.0
		while acc_arrival >= 1.0:
			acc_arrival -= 1.0
			arrival += 1
		if arrival > 0 and bench < cap:
			acc_registrar += reg / 60.0
			if acc_registrar >= 1.0:
				acc_registrar -= 1.0
				arrival -= 1
				bench += 1
				EventBus.sim_soul_registered.emit()
		if bench > 0:
			acc_adjudicator += adj / 60.0
			if acc_adjudicator >= 1.0:
				acc_adjudicator -= 1.0
				bench -= 1
				var side := "hell" if rng.randf() < hell_share else "heaven"
				if side == "hell":
					hell_out += 1
				else:
					heaven_out += 1
				EventBus.sim_soul_adjudicated.emit(side)
	GameState.recompute_derived()


## The player calls a docket soul: Queue -1.
func take_arrival() -> void:
	if arrival > 0:
		arrival -= 1
	elif bench > 0:
		bench -= 1


func _process(delta: float) -> void:
	_tick_accum += delta
	if _tick_accum >= 0.25:
		_tick_accum -= 0.25
		presentation_tick.emit()


func to_dict() -> Dictionary:
	return {"arrival": arrival, "bench": bench, "acc_arrival": acc_arrival, "acc_registrar": acc_registrar,
		"acc_adjudicator": acc_adjudicator, "heaven_out": heaven_out, "hell_out": hell_out, "rng": str(rng.get_state())}


func from_dict(d: Dictionary) -> void:
	arrival = int(d.get("arrival", 16))
	bench = int(d.get("bench", 8))
	acc_arrival = float(d.get("acc_arrival", 0.0))
	acc_registrar = float(d.get("acc_registrar", 0.0))
	acc_adjudicator = float(d.get("acc_adjudicator", 0.0))
	heaven_out = int(d.get("heaven_out", 0))
	hell_out = int(d.get("hell_out", 0))
	rng.set_state(str(d.get("rng", str(rng.get_state()))).to_int())
