extends Node
## One autosave slot (PROJECT §8.5): atomic write, previous kept as .bak. Autosave on area change, verdict,
## app pause and shift sign.

const VERSION := 1
var path := "user://save_0.json"
var enabled := true
var last_reason := ""
var save_count := 0


func _ready() -> void:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--save="):
			path = a.substr(7)


func has_save() -> bool:
	return FileAccess.file_exists(path)


func delete_save() -> void:
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))


func snapshot() -> Dictionary:
	return {"version": VERSION, "saved_at": Time.get_datetime_string_from_system(true), "clock": Clock.to_dict(),
		"player": World.to_dict(), "sim": Sim.to_dict(), "state": GameState.to_dict()}


func autosave(reason: String = "") -> bool:
	if not enabled or not GameState.in_game:
		return false
	last_reason = reason
	var ok := JsonUtil.save_file(path, snapshot(), true)
	if ok:
		save_count += 1
		EventBus.game_saved.emit()
	return ok


func read() -> Dictionary:
	var d: Variant = JsonUtil.load_file(path)
	if not (d is Dictionary):
		var bak: Variant = JsonUtil.load_file(path + ".bak")
		if bak is Dictionary:
			return migrate(bak)
		return {}
	return migrate(d)


func migrate(d: Dictionary) -> Dictionary:
	var v := int(d.get("version", 1))
	while v < VERSION:
		v += 1 # future: call migrate_vN_to_vN+1
	d["version"] = v
	return d


## Restores state only (no scene work). Returns the player dict.
func restore(d: Dictionary) -> Dictionary:
	Dialogue.clear()
	GameState.from_dict(d.get("state", {}))
	Clock.from_dict(d.get("clock", {}))
	Sim.from_dict(d.get("sim", {}))
	GameState.recompute_derived()
	EventBus.game_loaded.emit()
	return d.get("player", {})


## Full continue: restore and rebuild the world where the player was.
func continue_game() -> bool:
	var d := read()
	if d.is_empty():
		return false
	var p := restore(d)
	var area := str(p.get("area", ""))
	if area == "" or Content.area(area).is_empty():
		area = Content.area_ids()[0] if Content.area_ids().size() > 0 else ""
	World.load_area(area, "default", JsonUtil.to_vec2i(p.get("cell"), Vector2i(-1, -1)), str(p.get("facing", "s")))
	GameState.flush_pending_scored()
	return true


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if what != NOTIFICATION_APPLICATION_FOCUS_OUT:
			autosave("pause")
