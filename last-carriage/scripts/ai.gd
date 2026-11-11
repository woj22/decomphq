class_name AIClient
extends Node
## OpenAI-compatible Chat Completions client with the player's own key (kept only in user://settings.cfg).
## Reasoning-era models (gpt-5*, gpt-6*, o*) reject a custom temperature, so they get reasoning effort none/minimal
## and a token budget instead; on a 400 about an unsupported parameter the request is retried once with only
## model + messages.

const CFG := "user://settings.cfg"

var api_key := ""
var model := "gpt-6-luna"
var base_url := "https://api.openai.com/v1"
var remember := false
var demo := false


func load_settings() -> void:
	var c := ConfigFile.new()
	if c.load(CFG) == OK:
		api_key = str(c.get_value("openai", "api_key", ""))
		model = str(c.get_value("openai", "model", model))
		base_url = str(c.get_value("openai", "base_url", base_url))
		remember = api_key != ""
	var env := OS.get_environment("LC_BASE_URL")  # tests point this at a local mock server
	if env != "":
		base_url = env
		api_key = "test-key"


func save_settings() -> void:
	var c := ConfigFile.new()
	c.set_value("openai", "api_key", api_key if remember else "")
	c.set_value("openai", "model", model)
	c.set_value("openai", "base_url", base_url)
	c.save(CFG)


func body_for(messages: Array) -> Dictionary:
	var b := {"model": model, "messages": messages}
	var m := model.to_lower()
	if m.begins_with("gpt-6") or m.begins_with("gpt-5") or (m.begins_with("o") and m.length() > 1 and m[1].is_valid_int()):
		b["max_completion_tokens"] = 900
		b["reasoning_effort"] = "none" if m.begins_with("gpt-6") else "minimal"
	else:
		b["max_completion_tokens"] = 350
		b["temperature"] = 0.9
	return b


## Returns {"ok": bool, "text": String, "error": String}
func chat(messages: Array) -> Dictionary:
	var res := await _post(body_for(messages))
	if res["code"] == 400:
		var t := String(res["body"]).to_lower()
		if t.contains("temperature") or t.contains("reasoning") or t.contains("unsupported") or t.contains("max_completion_tokens"):
			res = await _post({"model": model, "messages": messages})
	if res["result"] != HTTPRequest.RESULT_SUCCESS:
		return {"ok": false, "text": "", "error": "Could not reach %s (network error %d)." % [base_url, res["result"]]}
	var code: int = res["code"]
	var parsed: Variant = JSON.parse_string(res["body"])
	if code < 200 or code >= 300:
		var msg := "HTTP %d" % code
		if parsed is Dictionary and parsed.get("error") is Dictionary:
			msg += ": " + str(parsed["error"].get("message", ""))
		if code == 401:
			msg = "The API key was refused (401). Check it on the start screen."
		return {"ok": false, "text": "", "error": msg}
	var text := ""
	if parsed is Dictionary and parsed.get("choices") is Array and not parsed["choices"].is_empty():
		var ch: Variant = parsed["choices"][0]
		if ch is Dictionary and ch.get("message") is Dictionary:
			var c: Variant = ch["message"].get("content", "")
			text = str(c) if c != null else ""
	if text.strip_edges() == "":
		return {"ok": false, "text": "", "error": "Empty reply from the model."}
	return {"ok": true, "text": text, "error": ""}


func _post(body: Dictionary) -> Dictionary:
	var http := HTTPRequest.new()
	http.timeout = 60.0
	add_child(http)
	var headers := PackedStringArray(["Content-Type: application/json", "Authorization: Bearer " + api_key.strip_edges()])
	var err := http.request(base_url.trim_suffix("/") + "/chat/completions", headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		return {"result": HTTPRequest.RESULT_CANT_CONNECT, "code": 0, "body": ""}
	var r: Array = await http.request_completed
	http.queue_free()
	return {"result": r[0], "code": r[1], "body": (r[3] as PackedByteArray).get_string_from_utf8()}


## Pulls the first {...} object out of a reply (models sometimes wrap JSON in prose or code fences).
static func parse_json(text: String) -> Dictionary:
	var s := text.find("{")
	var e := text.rfind("}")
	if s >= 0 and e > s:
		var v: Variant = JSON.parse_string(text.substr(s, e - s + 1))
		if v is Dictionary:
			return v
	return {"speech": text.replace("{", "").replace("}", "").replace("\"", "").strip_edges()}
