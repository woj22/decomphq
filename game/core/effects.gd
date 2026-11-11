class_name Effects
extends RefCounted
## Effect mini-language (CONTRACTS §3.2). One small function per op.

const OPS: PackedStringArray = ["set_flag", "add_stat", "set_objective", "start_dialogue", "advance_clock", "give_docket", "start_shift",
	"end_shift", "call_soul", "give_archive", "give_archive_one", "reopen_case", "snapshot_stats", "restore_stats", "reset_cases",
	"start_incident", "resolve_incident", "unlock_area", "set_rank", "show_card", "set_npc_line_flag", "buy_item", "teleport",
	"end_prototype", "set_stat", "clear_flag"]

static var unknown_logged := {}


static func apply(effects: Variant, ctx: Dictionary = {}) -> void:
	if effects == null:
		return
	if effects is Dictionary:
		apply_one(effects, ctx)
		return
	if not (effects is Array):
		return
	for e: Variant in effects:
		if e is Dictionary:
			apply_one(e, ctx)


static func apply_one(e: Dictionary, ctx: Dictionary = {}) -> void:
	var op := str(e.get("op", ""))
	if e.has("conditions") and not Conditions.check(e["conditions"], ctx):
		return
	match op:
		"set_flag":
			GameState.set_flag(str(e.get("id", "")), e.get("value", true))
		"clear_flag":
			GameState.set_flag(str(e.get("id", "")), false)
		"add_stat":
			GameState.add_stat(str(e.get("id", "")), float(e.get("value", 0)))
		"set_stat":
			GameState.set_stat(str(e.get("id", "")), float(e.get("value", 0)))
		"set_objective":
			GameState.set_objective(str(e.get("id", "")))
		"start_dialogue":
			Dialogue.request(str(e.get("id", "")))
		"advance_clock":
			Clock.advance(int(e.get("minutes", 0)), "effect")
		"give_docket":
			GameState.give_docket(int(e.get("day", Clock.day)))
		"start_shift":
			GameState.start_shift(int(e.get("day", Clock.day)))
		"end_shift":
			GameState.end_shift()
		"call_soul":
			GameState.call_soul(str(e.get("case", "")))
		"give_archive":
			if e.has("id"):
				GameState.give_archive_one(Conditions.resolve_case(e.get("case"), ctx), str(e["id"]))
			else:
				GameState.give_archive(Conditions.resolve_case(e.get("case"), ctx))
		"give_archive_one":
			GameState.give_archive_one(Conditions.resolve_case(e.get("case"), ctx), str(e.get("id", "")))
		"reopen_case":
			GameState.reopen_case(Conditions.resolve_case(e.get("case"), ctx))
		"snapshot_stats":
			GameState.snapshot_stats(str(e.get("tag", "default")))
		"restore_stats":
			GameState.restore_stats(str(e.get("tag", "default")))
		"reset_cases":
			var ids: Array = []
			for c: Variant in e.get("ids", []):
				ids.append(Conditions.resolve_case(c, ctx))
			GameState.reset_cases(ids)
		"start_incident":
			GameState.set_incident(str(e.get("id", "")), "active")
		"resolve_incident":
			GameState.set_incident(str(e.get("id", "")), "resolved" if bool(e.get("resolved", true)) else "unresolved")
		"unlock_area":
			GameState.unlock_area(str(e.get("id", "")))
		"set_rank":
			GameState.set_rank(int(e.get("value", GameState.rank + 1)))
		"show_card":
			Dialogue.request_modal("card", {"title": str(e.get("title", "")), "text": str(e.get("text", ""))})
		"set_npc_line_flag":
			GameState.set_flag(str(e.get("id", "")), true)
		"buy_item":
			GameState.buy_item(str(e.get("id", "")), int(e.get("price", 0)))
		"teleport":
			World.request_teleport(str(e.get("area", "")), str(e.get("spawn", "default")))
		"end_prototype":
			Dialogue.request_modal("summary", {})
		_:
			if not unknown_logged.has(op):
				unknown_logged[op] = true
				push_warning("Unknown effect op '%s'" % op)
