extends Node
## Autoload "Cast": the world's static data (species, kingdoms, notable characters, palace extras).

const GROUPS := [
	["imperial", "The Imperial House"],
	["ministers", "Ministers & Officers"],
	["kings", "The Client Kings"],
	["household", "Your Household"],
]

var species: Dictionary = {}
var kingdoms: Dictionary = {}
var characters: Dictionary = {}
var extras: Dictionary = {}
## Runtime opinion of the player (starts at the authored value; later systems will change it).
var opinion: Dictionary = {}


func _ready() -> void:
	species = _load("res://data/species.json")
	kingdoms = _load("res://data/kingdoms.json")
	characters = _load("res://data/characters.json")
	extras = _load("res://data/extras.json")
	for id in characters:
		characters[id]["id"] = id
		opinion[id] = int(characters[id].get("opinion", 0))


func _load(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("Cast: cannot open %s" % path)
		return {}
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		push_error("Cast: %s is not a JSON object" % path)
		return {}
	return data


func character(id: String) -> Dictionary:
	return characters.get(id, {})


func ids_in_group(group: String) -> Array:
	var out: Array = []
	for id in characters:
		if characters[id].get("group", "") == group and id != "player":
			out.append(id)
	return out


func kingdom_name(faction: String) -> String:
	return kingdoms.get(faction, {}).get("name", "")


func opinion_word(v: int) -> String:
	if v >= 60: return "Devoted"
	if v >= 30: return "Friendly"
	if v >= 10: return "Cordial"
	if v > -10: return "Neutral"
	if v > -30: return "Cool"
	return "Hostile"


## A complete look dictionary for the character builder: species defaults filled in,
## list-valued fields resolved with `rng` (extras), colours left as hex strings.
func resolve_look(species_id: String, look: Dictionary, sex := "m", rng: RandomNumberGenerator = null) -> Dictionary:
	var sp: Dictionary = species.get(species_id, species["human"])
	var out := {}
	for k in look:
		var v = look[k]
		if typeof(v) == TYPE_ARRAY:
			v = v[rng.randi() % v.size()] if rng != null else v[0]
		out[k] = v
	out["species"] = species_id
	out["sex"] = sex
	var r := rng if rng != null else RandomNumberGenerator.new()
	if not out.has("skin"):
		out["skin"] = sp["skin_tones"][r.randi() % sp["skin_tones"].size()]
	if not out.has("hair"):
		out["hair"] = sp["hair_tones"][r.randi() % sp["hair_tones"].size()]
	if not out.has("hair_style"):
		var styles := ["short", "cropped", "curly", "bald"] if sex == "m" else ["bun", "long", "braids"]
		if species_id == "kharad":
			styles = ["bald"]
		out["hair_style"] = styles[r.randi() % styles.size()]
	if not out.has("beard"):
		out["beard"] = "plates" if species_id == "othari" else ("none" if sex == "f" or species_id != "human" or r.randf() < 0.5 else "short")
	out["eye"] = sp.get("eye", "222222")
	for k in ["primary", "secondary", "trim"]:
		if not out.has(k):
			out[k] = "c9c2b0"
	for k in ["cloak", "headwear", "prop", "shield", "outfit"]:
		if not out.has(k):
			out[k] = null if k in ["cloak", "shield"] else ("tunic" if k == "outfit" else "none")
	if not out.has("height"):
		out["height"] = 1.0 if rng == null else r.randf_range(0.95, 1.05)
	if not out.has("build"):
		out["build"] = 1.0 if rng == null else r.randf_range(0.95, 1.06)
	return out


func look_for(id: String) -> Dictionary:
	var c := character(id)
	return resolve_look(c.get("species", "human"), c.get("look", {}), c.get("sex", "m"))
