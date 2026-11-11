extends Node
## Ambience per area + SFX pool. Silently does nothing for missing files.

var _amb: AudioStreamPlayer
var _sfx: Array = []
var _cache := {}
var _amb_id := ""
var muted := false


func _ready() -> void:
	_amb = AudioStreamPlayer.new()
	_amb.volume_db = -12.0
	add_child(_amb)
	for i in 4:
		var p := AudioStreamPlayer.new()
		p.volume_db = -6.0
		add_child(p)
		_sfx.append(p)
	muted = DisplayServer.get_name() == "headless"


func _stream(id: String) -> AudioStream:
	if _cache.has(id):
		return _cache[id]
	var s: AudioStream = null
	for ext: String in [".wav", ".ogg"]:
		var p := "res://assets/audio/" + id + ext
		if ResourceLoader.exists(p):
			s = load(p) as AudioStream
		elif ext == ".wav" and FileAccess.file_exists(p):
			s = AudioStreamWAV.load_from_file(ProjectSettings.globalize_path(p))
		if s != null:
			break
	_cache[id] = s
	return s


func sfx(id: String) -> void:
	if muted:
		return
	var s := _stream(id)
	if s == null:
		return
	for p: AudioStreamPlayer in _sfx:
		if not p.playing:
			p.stream = s
			p.play()
			return


func set_ambience(id: String) -> void:
	if muted or id == _amb_id:
		return
	_amb_id = id
	var s := _stream(id)
	if s == null:
		_amb.stop()
		return
	if s is AudioStreamWAV:
		var w: AudioStreamWAV = s
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_end = int(w.get_length() * w.mix_rate)
	_amb.stream = s
	_amb.play()
