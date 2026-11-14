# Imperium: World & Court Bible (v0.1)

Source of truth for the setting, cast and palace. The data files in `data/` carry the same content in a form the game reads; if this document and the data disagree, the data wins and this document is updated.

## The Empire

**The Ardent Imperium**: forty provinces and six client kingdoms, ruled for nine centuries by the human **Valerran dynasty** from the capital **Caelora**. Its emblem is the golden **eagle-sun**, and its colours are Tyrian purple and gold. The Empire is at the height of its power. It is wealthy, ordered and confident, and its frontier is quiet, perhaps too quiet. Its technology is that of classical antiquity: roads, sailing ships, horses, chariots, aqueducts, bronze and monumental engineering. There is nothing futuristic.

The political centre is the **Palatium Ardens**, the imperial palace complex in Caelora. This season the Emperor has summoned the client kings to court for a **Royal Session**, in a time of peace. Nobody is quite sure why.

## Species

| Species | Silhouette | Place in the Empire |
|---|---|---|
| **Humans** (the Imperial Kin) | Medium height, the familiar shape | They founded the dynasty and hold most high offices, the senior legions and the old aristocracy. |
| **Veyari** (the Long-Lived) | Tall and slender. Swept-back cranial crest fins, long pointed ears, cheek ridges, pale blue-lilac skin, golden eyes. Live 200–260 years. | Former merchant leagues. Now the Empire's scholars, envoys, bankers and translators: indispensable, and kept one step below the top. |
| **Kharad** (the Scaled Kingdoms) | Massive and scaled, with a snout, a crown of horns along the skull, a heavy tail and clawed hands and feet | A warrior culture conquered within living memory. Their auxiliary legions are the Empire's hammer, and they rarely command. |
| **Othari** (the Stoneborn) | Short and immensely broad, with stone-grey or clay skin, a heavy brow plate and braided jaw-plates instead of beards | Miners, smiths and builders. Valued for their skill, and often in debt to the treasury. |

There is a species hierarchy. Humans hold the throne and nearly every inner-council seat. The Treasurer, Nyssal Vey-Tamir, is the only non-human on the inner council, and Korrach Venn is the first Kharad to command the Auxilia. Every species has internal factions: Khar-Dumeth's old warrior king and Tor-Ilun's reformist queen are rivals within Kharad politics.

## The client kingdoms

| Kingdom | Ruler | Species | Colours / emblem | In one line |
|---|---|---|---|---|
| **Seravel** | **You**: King Cassian Arvel | Human | Deep blue & silver / river | A prosperous western river kingdom. Loyal, rarely noticed, never quite trusted with more. |
| **Lucerna** | Marcellan Dorr | Human | Crimson & gold / lamp | The Emperor's cousins. Controls the lower Sera and wants the upper river too. |
| **Khar-Dumeth** | Thrask Ur-Vashen | Kharad | Black-green & bronze / horns | The largest Kharad realm and the core of the auxiliary legions. |
| **Tor-Ilun** | Vashka Tor-Ilun | Kharad | Rust & bone / spear | A steppe kingdom that joined by treaty, ruled by a young reformer. |
| **Velithra** | Ilsaveth Anorai | Veyari | Teal & pale silver / wave | A banking and harbour kingdom that lends to half the court. |
| **Karst Odun** | Oduvar Brunnhak | Othari | Rust & iron / hammer | Its mines feed the mints. Owes eleven years of tribute. |

## The cast (18 notable characters)

Every notable has traits, an ambition, a current agenda, a biography, relationships with other characters (−100..100), an opinion of you, a home place in the palace, and authored lines (greetings by disposition, "who are you", "what occupies you", overheard remarks). These fields are the grounding that later AI-driven dialogue will draw on.

**The Imperial House**
- **Aurex IV Valerran**, Emperor (human, 56). Shrewd, generous in public, tests everyone. Wants to hand the Empire on stronger, and to keep any king from growing strong enough to object. *Seated on the Ardent Throne.*
- **Valen Valerran**, Crown Prince (26). Idealistic and impatient, served beside the Kharad, wants auxiliary officers to command. *Walks between the courtyard and the Hall of Kings.*
- **Sabine Valerran**, Empress (51). The only person who interrupts the Emperor; is building a circle of kings around her son. *In the gardens.*

**Ministers & officers**
- **Severa Ostian**, Prefect of the Palace (human). Controls access to the Emperor. Incorruptible, and keeps a list of everyone who has offered a bribe. *Stands in the Hall of Petitions.*
- **Nyssal Vey-Tamir**, Count of the Sacred Treasury (Veyari, 162). Has noticed that Seravel's river tolls were assessed low. *In the Council Chamber.*
- **Decimar Thane**, Marshal of the Legions (human). Wants twenty thousand men and a triumph. *Council Chamber ↔ courtyard.*
- **Korrach Venn**, Legate of the Auxilia (Kharad). Held the Basalt Gate for nine days, then watched Thane take the triumph. *Talking with Thrask in the Hall of Kings.*
- **Ulda Karrask**, Master of Imperial Works (Othari). Her Western Aqueduct would run through Seravel. *Inspecting the fountain.*
- **Halvana Pryce**, Governor of Meridia (human). Drought, three days waiting on a bench; Seravel's neighbour. *Hall of Petitions.*
- **Sethiel Aurn**, Imperial Herald (Veyari). Decides the seating chart and hears every rumour first. *At the door of the Hall of Kings.*
- **Cassia Varro**, Praetorian Prefect (human). "Step back from the dais." *Beside the throne.*

**The client kings**: Marcellan of Lucerna (your rival, walking the Hall of Kings), Thrask of Khar-Dumeth, Vashka of Tor-Ilun, Ilsaveth of Velithra (in the gardens), and Oduvar of Karst Odun (seated on his throne).

**Your household**: **Aldric Fenn**, Royal Steward (human), and **Hessa Durn**, Captain of the Seravel Guard (Othari). Both are in your apartments.

The opening tensions are seeded deliberately: the river-toll audit (Treasurer, Marcellan), Meridia's drought (Halvana, Aldric), the Basalt Gate grievance (Korrach, Thrask, the Prince, against Thane), the Western Aqueduct (Ulda), Vashka's trade road, the Lucernan precedence dispute (the Herald), and Velithran money behind all of it.

**Extras** (`data/extras.json`) fill the palace: Praetorian guards, Kharad auxiliaries, Seravel guards, scribes, servants, couriers and courtiers. Their looks are randomised from templates with a fixed seed, so the population is the same every run. All of them speak overheard lines about the politics above.

## The palace: primary rooms

| Room | Size | Contents |
|---|---|---|
| **Peristyle of the Sun** (courtyard hub) | 36×36 m | A colonnade of 28 columns, four L-shaped garden beds, statues of four past emperors, cypresses, and a two-tier fountain topped by the eagle-sun. Four great doors lead to the other rooms. |
| **Imperial Council Chamber** | 28×28 m | Three-tier horseshoe seating (24 seats), a sun mosaic on the speaker's floor, a lectern, a dais with the council throne and two ministers' chairs, porphyry columns, and the six kingdoms' banners. |
| **Hall of Kings** | 40×24 m | A basilica nave with serpentine columns, a long table of kings, and six thrones under six banners in precedence order (nearer the imperial seat is higher; Seravel sits nearest the door). The imperial seat stands on the east dais, flanked by statues of the dynasty's founder. |
| **Hall of Petitions** | 12×16 m | The antechamber: waiting benches, the Prefect's writing desk, and Praetorians at the inner door. |
| **Emperor's Audience Chamber** | 24×24 m | A purple carpet up to a three-step dais, the Ardent Throne, a great golden sun on the west wall, braziers, and the Praetorian guard. |
| **Gallery of the River Kings** | 6×16 m | The corridor to your rooms, lined with marble busts of Seravel's kings. |
| **Royal Apartments of Seravel** | 28×22 m | A study (desk, scroll shelves, and a **relief map table of Seravel**, where kingdom management will go) and a bedchamber. |

Still to build, as listed in the concept: the Imperial Treasury, military command chambers, diplomatic reception halls, ministers' offices, and the other kings' residences.
