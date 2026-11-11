class_name Cast
## Who is aboard: the five AI guests (each played by its own language-model calls), the two scripted staff and you.
## Signature items are what a guest can leave behind at a crime scene; colour is what a witness glimpses at night.

const PLAYER := "confucius"

const GUESTS := {
	"napoleon": {
		"name": "Napoleon Bonaparte", "short": "Napoleon", "compartment": 2,
		"persona": "Emperor of the French (1769-1821). Strategic, proud, impatient, used to command; speaks of campaigns and destiny. Short temper when doubted.",
		"secret": "You are carrying sealed dispatches you will not show anyone; you suspect someone aboard is an agent of your enemies.",
		"items": ["a gilt coat button stamped with an eagle", "a scrap of a military map"],
		"colour": "a dark blue coat with gold", "voice": "commanding",
	},
	"nightingale": {
		"name": "Florence Nightingale", "short": "Nightingale", "compartment": 3,
		"persona": "Nurse and statistician (1820-1910). Exacting, compassionate, unafraid of authority; counts, records and notices.",
		"secret": "You carry a vial of laudanum in your bag, more than a nurse should, and one dose is missing.",
		"items": ["an empty laudanum vial", "a page of tallies in neat columns"],
		"colour": "a dark grey dress and a white apron", "voice": "precise",
	},
	"tesla": {
		"name": "Nikola Tesla", "short": "Tesla", "compartment": 4,
		"persona": "Inventor (1856-1943). Brilliant, eccentric, obsessive about numbers divisible by three, germs and pigeons; visionary about electricity.",
		"secret": "You tampered with the carriage's electric lamps to test a device; the flickering is your doing.",
		"items": ["a coil of fine copper wire", "a sketch of a wireless apparatus"],
		"colour": "a black tailcoat", "voice": "intense",
	},
	"cleopatra": {
		"name": "Cleopatra", "short": "Cleopatra", "compartment": 5,
		"persona": "Last pharaoh of Ptolemaic Egypt (69-30 BC). Shrewd, multilingual, theatrical, charming when it serves her; regal and unhurried.",
		"secret": "You are not travelling alone in spirit: you have been bribing the steward for information about everyone aboard.",
		"items": ["a gold hairpin shaped like a cobra", "a smear of kohl on a handkerchief"],
		"colour": "white linen and gold", "voice": "regal",
	},
	"machiavelli": {
		"name": "Niccolò Machiavelli", "short": "Machiavelli", "compartment": 6,
		"persona": "Florentine diplomat and author of The Prince (1469-1527). Calculating, witty, cynical about virtue, enjoys watching others manoeuvre.",
		"secret": "You have been writing notes on each passenger's weaknesses, to sell to whoever pays most.",
		"items": ["a folded note in Italian listing names", "a red wool thread"],
		"colour": "a long red robe", "voice": "sly",
	},
}

const PLAYER_INFO := {
	"name": "Confucius", "compartment": 1,
	"items": ["a jade hairpin", "a strip of bamboo with characters on it"],
	"colour": "an indigo robe",
}

const STAFF := {
	"conductor": {"name": "Mr Albert Hale", "role": "conductor"},
	"steward": {"name": "Mrs Ilse Brandt", "role": "dining-car steward"},
}

## Historical and personal stances between guests (-2 hostile .. +2 warm), seeding relationships.
const STANCE := {
	"napoleon": {"nightingale": 1, "tesla": 0, "cleopatra": 1, "machiavelli": -1},
	"nightingale": {"napoleon": -1, "tesla": 1, "cleopatra": 0, "machiavelli": -1},
	"tesla": {"napoleon": 0, "nightingale": 1, "cleopatra": 0, "machiavelli": -1},
	"cleopatra": {"napoleon": 2, "nightingale": 0, "tesla": 0, "machiavelli": 1},
	"machiavelli": {"napoleon": 1, "nightingale": -1, "tesla": 0, "cleopatra": 1},
}


static func ids() -> Array:
	return GUESTS.keys()


static func display(id: String) -> String:
	if id == PLAYER:
		return "Confucius"
	if GUESTS.has(id):
		return GUESTS[id]["short"]
	if STAFF.has(id):
		return STAFF[id]["name"]
	return id


static func compartment_of(id: String) -> int:
	return PLAYER_INFO["compartment"] if id == PLAYER else int(GUESTS[id]["compartment"])
