// SGRS portal data. Edit this file to fill in profiles; the page reads it on load.
//
// Profile fields (all optional, leave "" or [] until you have something):
//   id        case number shown on the file, e.g. "SGRS-0001"
//   alias     in-game name or callsign
//   discord   Discord username
//   nationality  in-game nationality or country, e.g. "Belgian", "Dutch", "French"
//   status    "wanted" | "at-large" | "in-custody" | "cleared"
//   threat    "low" | "medium" | "high" | "extreme"
//   charges   list of in-game charges, e.g. ["Treason against the Crown"]
//   lastSeen  province or region key from the atlas: antwerp, east-flanders, west-flanders,
//             flemish-brabant, limburg, hainaut, liege, luxembourg, namur, walloon-brabant,
//             brussels, flanders, wallonia
//   reward    bounty text, e.g. "5,000 coins"
//   issued    date the notice went out, e.g. "2026-11-23"
//   issuedBy  who signed the notice
//   photo     image URL (a Discord avatar link works), or "" for the silhouette
//   summary   one or two sentences for the card
//   notes     longer case notes for the dossier
//
// Keep it to in-game roleplay details. No real names, addresses or other real-life info.

window.SGRS_DATA = {
  agency: "SGRS",
  agencyLong: "Service Général du Renseignement et de la Sécurité",
  server: "Kingdom of Belgium",
  mapUrl: "../belgium-map/index.html",

  profiles: [
    { id: "SGRS-0001", alias: "", discord: "", nationality: "", status: "", threat: "", charges: [], lastSeen: "", reward: "", issued: "", issuedBy: "", photo: "", summary: "", notes: "" },
    { id: "SGRS-0002", alias: "", discord: "", nationality: "", status: "", threat: "", charges: [], lastSeen: "", reward: "", issued: "", issuedBy: "", photo: "", summary: "", notes: "" },
    { id: "SGRS-0003", alias: "", discord: "", nationality: "", status: "", threat: "", charges: [], lastSeen: "", reward: "", issued: "", issuedBy: "", photo: "", summary: "", notes: "" },
    { id: "SGRS-0004", alias: "", discord: "", nationality: "", status: "", threat: "", charges: [], lastSeen: "", reward: "", issued: "", issuedBy: "", photo: "", summary: "", notes: "" },
    { id: "SGRS-0005", alias: "", discord: "", nationality: "", status: "", threat: "", charges: [], lastSeen: "", reward: "", issued: "", issuedBy: "", photo: "", summary: "", notes: "" },
    { id: "SGRS-0006", alias: "", discord: "", nationality: "", status: "", threat: "", charges: [], lastSeen: "", reward: "", issued: "", issuedBy: "", photo: "", summary: "", notes: "" },
  ],

  // Short notices shown on the Bulletins tab: { date: "2026-11-23", title: "", body: "" }
  bulletins: [],
};
