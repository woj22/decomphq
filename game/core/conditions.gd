class_name Conditions
extends RefCounted
## Condition mini-language (CONTRACTS §3.1). A conditions array is AND.

const OPS: PackedStringArray = ["flag", "not_flag", "stat_gte", "stat_lte", "rank_gte", "day_eq", "verdict", "case_state",
	"discovered", "asked", "has_active_case", "active_case_eq", "docket_empty", "holds_archive", "archive_available", "any", "not",
	"all"]

static var unknown_logged := {}


static func check(conds: Variant, ctx: Dictionary = {}) -> bool:
	if conds == null:
		return true
	if conds is Dictionary:
		return check_one(conds, ctx)
	if not (conds is Array):
		return true
	for c: Variant in conds:
		if c is Dictionary and not check_one(c, ctx):
			return false
	return true


static func resolve_case(v: Variant, ctx: Dictionary = {}) -> String:
	var s := str(v) if v != null else ""
	if s == "" or s == "$active_case":
		if ctx.has("case") and str(ctx["case"]) != "":
			return str(ctx["case"])
		return GameState.active_case_id()
	return s


static func check_one(c: Dictionary, ctx: Dictionary = {}) -> bool:
	var op := str(c.get("op", ""))
	match op:
		"flag":
			if c.has("value"):
				return GameState.get_flag(str(c.get("id", ""))) == c["value"]
			return GameState.flag_true(str(c.get("id", "")))
		"not_flag":
			return not GameState.flag_true(str(c.get("id", "")))
		"stat_gte":
			return GameState.get_stat(str(c.get("id", ""))) >= float(c.get("value", 0))
		"stat_lte":
			return GameState.get_stat(str(c.get("id", ""))) <= float(c.get("value", 0))
		"rank_gte":
			return GameState.rank >= int(c.get("value", 0))
		"day_eq":
			return Clock.day == int(c.get("value", 0))
		"verdict":
			return GameState.case_verdict(resolve_case(c.get("case"), ctx)) == str(c.get("value", ""))
		"case_state":
			return GameState.case_state(resolve_case(c.get("case"), ctx)) == str(c.get("value", ""))
		"discovered":
			return GameState.is_discovered(resolve_case(c.get("case"), ctx), str(c.get("id", "")))
		"asked":
			return GameState.is_asked(resolve_case(c.get("case"), ctx), str(c.get("id", "")))
		"has_active_case":
			return GameState.active_case_id() != ""
		"active_case_eq":
			return GameState.active_case_id() == resolve_case(c.get("case"), ctx)
		"docket_empty":
			return GameState.docket_empty()
		"holds_archive":
			return GameState.holds_archive(resolve_case(c.get("case"), ctx), str(c.get("id", "")))
		"archive_available":
			return GameState.archive_available(resolve_case(c.get("case"), ctx))
		"any":
			for sub: Variant in c.get("of", []):
				if sub is Dictionary and check_one(sub, ctx):
					return true
				if sub is Array and check(sub, ctx):
					return true
			return false
		"all":
			return check(c.get("of", []), ctx)
		"not":
			var of: Variant = c.get("of", {})
			return not check(of, ctx)
		_:
			if not unknown_logged.has(op):
				unknown_logged[op] = true
				push_warning("Unknown condition op '%s'" % op)
			return false
