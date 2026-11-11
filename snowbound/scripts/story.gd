class_name Story
extends RefCounted
## The truth of one game, decided at the start and never by the language model: who the culprit is, who dies each
## night, which clues are left where, what witnesses saw. The AI guests only get the parts they could know.

const LAST_NIGHT := 3

var rng := RandomNumberGenerator.new()
var culprit := ""
var night := 1                       # the night we are in or have just woken from
var phase := "night"                 # night | morning | tribunal | day | ending
var guests := {}                     # id -> {status, trust, suspicion, notes, heard: [], convo: []}
var victims: Array = []              # [{id, night}]
var locked: Array = []
var stove_tonight := ""
var clues: Array = []                # {id, text, owner, pos, night, found, public}
var public_log: Array = []           # things everyone knows: announcements, tribunal speeches, votes
var journal: Array = []              # what you have found and been told
var patrol_note := ""                # what the conductor saw last night
var steward_note := ""
var player_locked := false
var player_suspicion := 10           # how much the carriage as a whole suspects you (from found clues)


func start() -> void:
	rng.randomize()
	culprit = Cast.ids()[rng.randi() % Cast.ids().size()]
	for id in Cast.ids():
		guests[id] = {"status": "aboard", "trust": 40, "suspicion": 15,
			"notes": "", "heard": [], "convo": []}
	announce("Midnight approaches. The night train has stopped dead in a blizzard somewhere in the mountains; the conductor says the snowplough cannot reach you for three days.")


func announce(t: String) -> void:
	public_log.append(t)


func alive_guests() -> Array:
	return Cast.ids().filter(func(i): return guests[i]["status"] == "aboard" or guests[i]["status"] == "stove")


func free_guests() -> Array:   # alive and not locked away
	return Cast.ids().filter(func(i): return guests[i]["status"] in ["aboard", "stove"])


func status(id: String) -> String:
	if id == Cast.PLAYER:
		return "locked" if player_locked else "aboard"
	return guests[id]["status"]


# ------------------------------------------------------------------ the night
## Resolves the night when you go to sleep. Returns a dictionary describing the morning.
func resolve_night() -> Dictionary:
	var out := {"night": night, "victim": "", "quiet_reason": ""}
	var culprit_free: bool = guests[culprit]["status"] == "aboard"
	var candidates := Cast.ids().filter(func(i): return i != culprit and guests[i]["status"] == "aboard")
	if not culprit_free:
		out["quiet_reason"] = "stove" if guests[culprit]["status"] == "stove" else "locked"
	elif candidates.is_empty():
		out["quiet_reason"] = "none"
	else:
		# the culprit prefers whoever has been closest to the truth (high suspicion of the culprit is unknowable to
		# us, so: those who trust Confucius most are a danger to a framing, and are chosen more often)
		var weights := candidates.map(func(i): return 1.0 + guests[i]["trust"] / 50.0)
		var total: float = weights.reduce(func(a, b): return a + b, 0.0)
		var roll := rng.randf() * total
		var victim: String = candidates[0]
		for k in candidates.size():
			roll -= weights[k]
			if roll <= 0:
				victim = candidates[k]
				break
		guests[victim]["status"] = "dead"
		victims.append({"id": victim, "night": night})
		out["victim"] = victim
		_leave_clues(victim)
		_witnesses(victim)
	# whoever slept by the stove goes back to their compartment tonight
	for id in Cast.ids():
		if guests[id]["status"] == "stove":
			guests[id]["status"] = "aboard"
	stove_tonight = ""
	return out


func _leave_clues(victim: String) -> void:
	var n := Cast.compartment_of(victim)
	var base := Layout.compartment_z(n)
	var items: Array = Cast.GUESTS[culprit]["items"]
	var true_item: String = items[(night - 1) % items.size()]
	clues.append({"id": "c%d_true" % night, "owner": culprit, "night": night, "found": false, "public": false,
		"text": "In %s's compartment, half under the bed: %s." % [Cast.display(victim), true_item],
		"pos": Vector3(-0.2, 0.05, base + 1.5)})
	# a red herring: someone else's belonging, sometimes yours
	var others := Cast.ids().filter(func(i): return i != culprit and i != victim and guests[i]["status"] != "dead")
	var framed: String = Cast.PLAYER if (rng.randf() < 0.4 or others.is_empty()) else others[rng.randi() % others.size()]
	var fitems: Array = Cast.PLAYER_INFO["items"] if framed == Cast.PLAYER else Cast.GUESTS[framed]["items"]
	clues.append({"id": "c%d_herring" % night, "owner": framed, "night": night, "found": false, "public": false,
		"text": "Outside %s's door, on the corridor runner: %s." % [Cast.display(victim), fitems[rng.randi() % fitems.size()]],
		"pos": Vector3(1.05, 0.02, base + 0.9 + rng.randf() * 0.6)})


func _witnesses(victim: String) -> void:
	# the conductor's patrol: usually the culprit's colours, sometimes a mistake
	var pool := [Cast.PLAYER] + Cast.ids().filter(func(i): return i != culprit and i != victim)
	var seen: String = culprit if rng.randf() < 0.62 else pool[rng.randi() % pool.size()]
	var colour: String = Cast.PLAYER_INFO["colour"] if seen == Cast.PLAYER else Cast.GUESTS[seen]["colour"]
	patrol_note = "On my two o'clock round I glimpsed someone in %s at the far end of the corridor, by the lamps. Only a glimpse, mind." % colour
	# the steward knows who came back to the bar after midnight
	var late := [culprit] if rng.randf() < 0.5 else []
	for id in free_guests():
		if id != culprit and id != victim and rng.randf() < 0.3:
			late.append(id)
	steward_note = ("After midnight %s came back for a drink. Nobody else." % " and ".join(late.map(Cast.display))) if not late.is_empty() \
		else "Nobody came back to the bar after midnight. I locked the spirits away at half past twelve."
	# neighbours heard which way the footsteps went (toward the culprit's compartment)
	var vn := Cast.compartment_of(victim)
	var cn := Cast.compartment_of(culprit)
	var dir := "toward the dining car" if cn > vn else "toward the front of the train"
	for id in free_guests():
		var gn := Cast.compartment_of(id)
		if absi(gn - vn) == 1 and id != culprit:
			guests[id]["heard"].append("Night %d: around two o'clock you heard %s's door slide, then soft footsteps going %s." % [night, Cast.display(victim), dir])
		elif id != culprit and rng.randf() < 0.3:
			guests[id]["heard"].append("Night %d: you slept badly and heard the lamps hum and flicker." % night)
	if guests[culprit]["status"] == "aboard":
		guests[culprit]["heard"].append("Night %d: you killed %s. You must not be found out." % [night, Cast.display(victim)])


## Clues nobody found by the time of the tribunal: the conductor finds some and tells everyone.
func sweep_clues() -> Array:
	var told := []
	for c in clues:
		if not c["found"] and not c["public"] and c["night"] == night and rng.randf() < 0.55:
			c["public"] = true
			told.append(c)
			if c["owner"] == Cast.PLAYER:
				player_suspicion += 20
	return told


# ------------------------------------------------------------------ votes
func tally(votes: Dictionary) -> String:
	## votes: voter -> target. Returns the target with a strict plurality, or "" on a tie.
	var count := {}
	for v in votes.values():
		if v != "":
			count[v] = count.get(v, 0) + 1
	var best := ""
	var top := 0
	var tie := false
	for k in count:
		if count[k] > top:
			best = k
			top = count[k]
			tie = false
		elif count[k] == top:
			tie = true
	return "" if tie else best


func lock_up(id: String) -> void:
	if id == Cast.PLAYER:
		player_locked = true
	else:
		guests[id]["status"] = "locked"
	locked.append(id)


func outcome() -> String:
	## "" while the game goes on; "won" / "lost" at the end.
	if night > LAST_NIGHT:
		return "won" if culprit in locked else "lost"
	if free_guests().filter(func(i): return i != culprit).is_empty() and culprit not in locked:
		return "lost"
	return ""
