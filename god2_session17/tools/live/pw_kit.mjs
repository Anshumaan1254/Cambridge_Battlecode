// Ability slot kinds per champion for the pw_* power-usage tools (GameRules v3.0.4): unit spells (dmg, stun, dmgstun) target one tile,
// area spells (aoestun, aoe) radius 1, hordash = Heart of Ruin's dash with a radius-1 landing hit and stun, dash = 2-step move,
// reset / ereset (Marcella: next attack stuns) / shield = self, heal = ally.
export const KIT = {
  Ryth: ['aoestun', 'reset'], VesperVale: ['reset', 'dash'], Vendetta: ['reset', 'dash'], Cassi: ['dmg', 'stun'],
  Issac: ['reset', 'dash'], Stellar: ['dmg', 'aoe'], Prism: ['dmgstun', 'aoe'], Marcella: ['ereset', 'dmg'],
  Willow: ['heal', 'reset'], Ren: ['dmgstun', 'dash'], Varg: ['reset', 'shield'], Tavi: ['reset', 'dmgstun'],
  HeartOfRuin: ['shield', 'hordash'],
};
