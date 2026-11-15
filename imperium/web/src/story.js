// One evening at the Imperial Palace. You are Cassian Arvel, King of Seravel, a client king of the Empire.
// Petitioners seek you out on the terrace; every decision moves your standing and moves the evening on.

export const STATS = [
  { id: 'favour', label: 'Imperial Favour', icon: '♛', start: 45 },
  { id: 'treasury', label: 'Treasury', icon: '⚖', start: 55 },
  { id: 'influence', label: 'Influence', icon: '✦', start: 30 },
  { id: 'loyalty', label: 'Seravel', icon: '⚑', start: 60 },
];

// Each petition: who brings it, where they wait on the terrace, the text, and the choices.
export const PETITIONS = [
  {
    id: 'tribute', who: 'aldric',
    title: 'The Tribute Assessment',
    text: "Majesty, the Imperial assessors have raised Seravel's tribute by a fifth. The Count of the Treasury signed it himself. Our granaries can bear it — barely. How shall I answer them?",
    choices: [
      { label: 'Pay in full, and promptly. Let the Throne see our loyalty.', fx: { favour: 10, treasury: -15 }, reply: "It will be done before the next moon. The Emperor's clerks will note our punctuality." },
      { label: 'Pay, but petition the Count for a reduction next year.', fx: { treasury: -10, influence: 4, favour: 2 }, reply: 'A measured answer. I shall draft the petition in your most courteous hand.' },
      { label: 'Delay. Plead a poor harvest in the hill provinces.', fx: { favour: -10, loyalty: 6 }, reply: 'Our farmers will bless your name. The assessors will remember it too.' },
    ],
  },
  {
    id: 'loan', who: 'treasurer',
    title: 'A Generous Offer',
    text: 'King Cassian. The Treasury could extend Seravel a loan at a most agreeable rate — in exchange for your voice in council when the grain levies are debated. A small thing between friends.',
    choices: [
      { label: 'Accept the loan, and the obligation that comes with it.', fx: { treasury: 18, influence: -6, favour: 3 }, reply: 'Splendid. My notary will call upon you. Do remember our little understanding.' },
      { label: 'Decline politely. Seravel keeps its own counsel.', fx: { influence: 5 }, reply: 'Independence. How… provincial. As you wish.' },
      { label: 'Accept — then tell the Prefect of the Palace about the bargain.', fx: { treasury: 18, favour: 8, influence: -12 }, reply: 'I see. I will remember the shape of this evening, Majesty.' },
    ],
  },
  {
    id: 'levies', who: 'thane',
    title: 'The Frontier Levies',
    text: "The Khar border is restless. The Legions need auxiliaries and the Emperor expects his kings to answer. Two cohorts from Seravel, by the spring thaw. Can I count on you?",
    choices: [
      { label: 'Two cohorts, fully equipped. Seravel stands with the Legions.', fx: { favour: 12, loyalty: -8, treasury: -6 }, reply: 'Good. I will see your men are placed where glory can find them.' },
      { label: 'Send gold for the war chest instead of men.', fx: { treasury: -14, favour: 6 }, reply: 'Gold does not hold a line, but it buys those who do. Acceptable.' },
      { label: 'Refuse. My people need their sons for the harvest.', fx: { favour: -12, loyalty: 8 }, reply: 'The Emperor will hear of it. I would not want to be the one who tells him.' },
    ],
  },
  {
    id: 'compact', who: 'thrask',
    title: "The Kings' Compact",
    text: 'Cassian. We kings carry the Empire on our backs and the assessors bleed us white. Stand with me and Queen Vashka — a joint petition to lower the tribute. Together they cannot ignore us.',
    choices: [
      { label: 'Join the Compact. The client kings must speak as one.', fx: { influence: 15, favour: -8 }, reply: 'Ha! Now we are a power in this palace. Tell no one until the council sits.' },
      { label: 'Wish him well, but keep Seravel out of it.', fx: { influence: -3 }, reply: 'Caution. It has kept smaller kings than you alive. Not always the bolder ones.' },
      { label: "Warn the Emperor's Praetorians of the plot.", fx: { favour: 14, influence: -16, loyalty: -2 }, reply: '…I see. Remember this night when you need a friend among the kings.' },
    ],
  },
  {
    id: 'audience', who: 'chancellor',
    title: 'A Summons',
    text: 'His Imperial Majesty has taken note of the King of Seravel this evening. The Prefecture will consider whether to grant you a private audience. Is there anything you would have me convey?',
    choices: [
      { label: "Only Seravel's devotion to the Throne.", fx: { favour: 5 }, reply: 'Simple, and therefore rare. I will convey it.' },
      { label: 'That Seravel asks for a seat on the Council of Kings.', fx: { influence: 8, favour: -3 }, reply: 'Ambition. The Emperor admires it in moderation. We shall see.' },
      { label: 'Ask what the Prefecture would want for a favourable word.', fx: { treasury: -8, favour: 9, influence: 3 }, reply: 'A practical king. The Prefecture appreciates practicality.' },
    ],
  },
];

export function verdict(s) {
  if (s.favour >= 70) return ["The Emperor's Confidant", 'The Throne has noticed you. A private audience is granted at dawn.'];
  if (s.influence >= 55) return ['Voice of the Kings', 'The client kings look to Seravel now. The Palace watches you, warily.'];
  if (s.loyalty >= 75) return ['Beloved of Seravel', 'Your people would follow you anywhere. The Palace is less sure of you.'];
  if (s.treasury <= 20) return ['A Poor Crown', 'Seravel is loyal and empty-handed. The creditors are already at the gate.'];
  if (s.favour <= 25) return ['Under Suspicion', 'The Praetorians have started to note your visitors. Tread carefully.'];
  return ['A Careful King', 'You end the evening as you began it: secure, if unremarkable.'];
}
