class_name Settings
extends RefCounted
## Player settings (PROJECT §9.4): text speed, hold/tap stamp, joystick, haptics, screen shake.

const PATH := "user://settings.cfg"
static var text_speed := 1 # 0 slow, 1 normal, 2 instant
static var tap_stamp := false
static var joystick := true
static var haptics := true
static var shake := true
static var loaded := false


static func load_settings() -> void:
	if loaded:
		return
	loaded = true
	var cf := ConfigFile.new()
	if cf.load(PATH) != OK:
		return
	text_speed = int(cf.get_value("s", "text_speed", 1))
	tap_stamp = bool(cf.get_value("s", "tap_stamp", false))
	joystick = bool(cf.get_value("s", "joystick", true))
	haptics = bool(cf.get_value("s", "haptics", true))
	shake = bool(cf.get_value("s", "shake", true))


static func save_settings() -> void:
	var cf := ConfigFile.new()
	cf.set_value("s", "text_speed", text_speed)
	cf.set_value("s", "tap_stamp", tap_stamp)
	cf.set_value("s", "joystick", joystick)
	cf.set_value("s", "haptics", haptics)
	cf.set_value("s", "shake", shake)
	cf.save(PATH)


static func chars_per_second() -> float:
	return [20.0, 40.0, 100000.0][clampi(text_speed, 0, 2)]
