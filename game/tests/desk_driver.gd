class_name DeskDriver
extends RefCounted
## Mirrors tools/scoring_ref.py's scripted desk actions on the real engine (GameState + JudgementSession).

const FULL := {
	"case_s001": [["pell"], ["ask_all"]],
	"case_s002": [["pell"], ["link", "r1", "arc_002a"], ["ask_all"]],
	"case_s003": [["pell"], ["ask_all"]],
	"case_s004": [["pell"], ["link", "r2", "arc_004a"], ["ask_all"]],
	"case_s007": [["pell"], ["link", "r4", "arc_007a"], ["ask_all"], ["pell"]],
	"case_s008": [["pell"], ["link", "r2", "arc_008a"], ["link", "r1", "arc_008b"], ["ask_all"]],
}
const ORDER := ["case_s001", "case_s002", "case_s003", "case_s004", "case_s007", "case_s008"]

var wrong_links := 0


static func profiles() -> Dictionary:
	var p := {}
	p["perfect"] = {}
	for c: String in ORDER:
		p["perfect"][c] = [FULL[c], "guideline", "auto"]
	p["attentive"] = {"case_s001": [[], "heaven", ""], "case_s002": [FULL["case_s002"], "hell", "auto"],
		"case_s003": [[["pell"]], "heaven", "auto"], "case_s004": [[["ask", "q2"]], "heaven", "auto"],
		"case_s007": [[["pell"], ["link", "r4", "arc_007a"]], "hell", "auto"], "case_s008": [FULL["case_s008"], "heaven", "auto"]}
	p["half_diligent"] = {"case_s001": [[], "heaven", ""], "case_s002": [FULL["case_s002"], "hell", "auto"],
		"case_s003": [[["pell"], ["ask", "q3"]], "heaven", "auto"], "case_s004": [[], "tally", ""],
		"case_s007": [[], "tally", ""], "case_s008": [FULL["case_s008"], "heaven", "auto"]}
	p["rubric_only"] = {}
	p["careless"] = {}
	for c: String in ORDER:
		p["rubric_only"][c] = [[["ask_all"]], "tally", "auto"]
		p["careless"][c] = [[], "tally", ""]
	return p


## Puts a case on the desk (seated) without the world.
static func seat(cid: String) -> JudgementSession:
	var rec := GameState.case_rec(cid)
	rec["state"] = "seated"
	if not GameState.docket.has(cid):
		GameState.docket.append(cid)
	return JudgementSession.new(cid)


func run_script(s: JudgementSession, script: Array) -> void:
	for step: Array in script:
		match str(step[0]):
			"pell":
				s.request_archive()
			"link":
				var r := s.link(str(step[1]), str(step[2]))
				if not r["ok"]:
					wrong_links += 1
			"ask":
				s.ask(str(step[1]))
			"ask_all":
				ask_all(s)


static func ask_all(s: JudgementSession) -> void:
	var progress := true
	while progress:
		progress = false
		for q: Dictionary in s.data.get("questions", []):
			var qid := str(q["id"])
			if s.asked().has(qid) or not s.question_available(q) or s.composure() <= 0:
				continue
			s.ask(qid)
			progress = true


static func best_ground(s: JudgementSession, verdict: String) -> String:
	var keyed := ""
	var any := ""
	for f: Dictionary in s.facts():
		if f["side"] == verdict:
			if f["key"] and keyed == "":
				keyed = f["id"]
			if any == "":
				any = f["id"]
	return keyed if keyed != "" else any


## Plays one case; returns the score result.
func play(cid: String, script: Array, verdict: String, ground: String) -> Dictionary:
	var s := seat(cid)
	run_script(s, script)
	if verdict == "guideline":
		verdict = Scoring.guideline(s.data)
	elif verdict == "tally":
		verdict = Scoring.side_of(s.known_tally())
	if ground == "auto":
		ground = best_ground(s, verdict)
	var r := s.stamp(verdict, ground)
	r["known_tally"] = s.known_tally()
	return r
