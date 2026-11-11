class_name TriggerRunner
extends RefCounted
## Runs data triggers (CONTRACTS §3): [{id, on, match{arg:value}, conditions, effects, once}].

const SIGNAL_ARGS := {
	"area_entered": ["area_id"],
	"case_scored": ["case_id", "result"],
	"case_called": ["case_id"],
	"discovery_made": ["case_id", "discovery_id"],
	"dialogue_ended": ["dlg_id"],
	"shift_started": ["day"],
	"shift_ended": ["day", "summary"],
	"new_game_started": [],
	"rank_changed": ["rank"],
	"incident_changed": ["incident_id", "state"],
	"objective_changed": ["objective_id"],
	"case_seated": ["case_id"],
	"case_judged": ["case_id", "verdict"],
}

var enabled := true
var log_fired: Array = []


func connect_bus() -> void:
	for sig: String in SIGNAL_ARGS:
		var names: Array = SIGNAL_ARGS[sig]
		match names.size():
			0:
				EventBus.connect(sig, func() -> void: fire(sig, {}))
			1:
				EventBus.connect(sig, func(a: Variant) -> void: fire(sig, {names[0]: a}))
			2:
				EventBus.connect(sig, func(a: Variant, b: Variant) -> void: fire(sig, {names[0]: a, names[1]: b}))


func fire(sig: String, args: Dictionary) -> void:
	if not enabled:
		return
	var ctx := {}
	if args.has("case_id"):
		ctx["case"] = str(args["case_id"])
	for t: Variant in Content.triggers:
		if not (t is Dictionary):
			continue
		var tr: Dictionary = t
		if str(tr.get("on", "")) != sig:
			continue
		var tid := str(tr.get("id", ""))
		if bool(tr.get("once", true)) and GameState.triggers_fired.has(tid):
			continue
		var m: Variant = tr.get("match", {})
		var ok := true
		if m is Dictionary:
			for k: String in (m as Dictionary):
				var want: Variant = (m as Dictionary)[k]
				if not args.has(k) or str(args[k]) != str(want):
					# allow numeric equality 1 == 1.0
					if args.has(k) and (want is float or want is int) and (args[k] is float or args[k] is int) and float(want) == float(args[k]):
						continue
					ok = false
					break
		if not ok:
			continue
		if not Conditions.check(tr.get("conditions", []), ctx):
			continue
		GameState.triggers_fired[tid] = true
		log_fired.append(tid)
		Effects.apply(tr.get("effects", []), ctx)
