# The Purgatory Border — Owner's Brief (condensed, authoritative)

Visual target: `docs/reference/concept-mockup.png` (gothic isometric pixel art; fortress between golden Heaven on the left and red Hell on the right; HUD with location/day/time, souls/coin/order stats, objective card, minimap, bottom bar Map/Staff/Reports/Upgrades/Settings).

## Concept
Mobile game. The player is a civil servant in the afterlife's administration, working in an enormous gothic fortress between Heaven and Hell. Every dead human passes through it. Start as a low-ranking clerk judging individual souls (Heaven or Hell); grow into management, exploration, politics and narrative; end as one of the most powerful figures in the afterlife, liaising directly with God and the Devil.

## Setting
A gigantic explorable gothic fortress — a medieval administrative city of interconnected buildings, courtyards, corridors, bridges, towers, undercrofts.
- Heaven: gold/white celestial architecture, clouds, radiant light.
- Hell: dark red/black gothic, infernal towers, fire, volcanic.
- Purgatory: the fortress and administrative territory between.
Locations: Arrival Hall (souls arrive/register); Records Department (archive of human life histories); Judgement Chambers (investigate and assign); Border Guard HQ (security, prisoners); Diplomatic Quarter (Heaven/Hell envoys); Administrative Offices (departments, hundreds of workers); High Chancellor's Office (eventual player HQ). More unlock with progress.

## Gameplay — NOT a menu-based management game
The player physically controls a character and walks the fortress: isometric exploration, interconnected environments, interactable buildings/rooms/characters/objects, conversations with employees/superiors/visitors, locations with distinct gameplay functions, areas unlocking with progress, a populated living world that expands and changes as the player gains influence.

## Career ranks
1 Junior Processing Clerk → 2 Senior Adjudicator → 3 Department Supervisor → 4 Chief Commissioner of the Border → 5 High Chancellor of Purgatory. Each promotion adds responsibilities, locations, privileges, mechanics. Early: individual souls. Later: teams, departments, budgets, staffing, diplomacy, the whole fortress. Finally: advising the highest authorities.

## Soul judgement (central mechanic)
Each soul has a unique history, personality, biography, moral record. Player investigates and decides. Mechanics: read histories, find inconsistencies, interview souls, consult records, hear appeals, weigh mitigating circumstances, final judgement. Decisions have consequences. Morally complicated cases without an obvious right answer.

## Workforce & management
Many NPC employees: receptionists, investigators, adjudicators, archivists, guards, transporters, auditors, supervisors. Player eventually recruits, promotes, dismisses, reassigns. Mechanics: morale, competence, department efficiency, corruption, finances, backlogs, disputes. Employees have personalities, ambitions, secrets.

## Politics & narrative
Heaven and Hell are political entities with bureaucracies, factions and agendas; Heaven not wholly benevolent, Hell not wholly evil. Rising rank brings ambassadors, soul disputes, corruption investigations, summits, and eventually God and the Devil. Overarching story: an administrative crisis — growing backlogs, political disputes, powerful figures manipulating the system.

## Visual direction
Atmospheric gothic pixel art, isometric. References: Papers, Please; classic isometric RPGs; medieval gothic architecture; dark fantasy; management sims. Enormous, detailed, populated by hundreds of small characters. Restrained palette: charcoal, grey, muted purple, golden light, infernal red.

## Process
Seven specialist roles (Director/Systems, World/Narrative, Environment/Art, Technical, UI/UX Mobile, Management/Sim, QA/Producer). Independent proposals → cross-review for contradictions/dependencies → one central project document → small playable prototype first.

Prototype must include: a small section of the fortress; a controllable player character; walking between several rooms; interacting with NPCs; a basic soul judgement system; a simple progression mechanic. Then expand.

Priority: genuinely explorable, atmospheric, engaging. Ambitious vision, realistic scope, mobile.

## Fixed constraints (set by owner / verified in this environment)
- Engine: **Godot 4.6** (`godot` on PATH), mobile target (Android/iOS), GDScript.
- Asset tool: **Blender 5.3** via the `bpy` Python module (`python3 -c "import bpy"`). Headless, no GPU: **Cycles CPU works; EEVEE crashes** (no EGL). A 128px Cycles render takes ~0.3 s.
- Godot can run and screenshot under `xvfb-run -a godot --path <proj> --rendering-driver opengl3` (Compatibility renderer, software GL).
- No human artist: every asset must be generated procedurally/by script and be reproducible from the repo.
