/**
 * Automaton rules.
 *
 * 2D rules use the usual B/S notation over the neighbourhood built in
 * topology.js. Because rounds change width, a cell does not always have
 * exactly eight neighbours, so counts are compared against the rule directly
 * rather than assuming a Moore neighbourhood.
 *
 * 1D rules are Wolfram's elementary automata: each stitch is decided by the
 * three stitches of the previous round below (or above) it.
 */

export const RULE_PRESETS_2D = [
  { name: "Conway's Life", rule: 'B3/S23' },
  { name: 'HighLife', rule: 'B36/S23' },
  { name: 'Day & Night', rule: 'B3678/S34678' },
  { name: 'Maze', rule: 'B3/S12345' },
  { name: 'Mazectric', rule: 'B3/S1234' },
  { name: 'Coral', rule: 'B3/S45678' },
  { name: 'Seeds', rule: 'B2/S' },
  { name: 'Replicator', rule: 'B1357/S1357' },
  { name: 'Diamoeba', rule: 'B35678/S5678' },
  { name: 'Vote', rule: 'B5678/S45678' },
];

export const RULE_PRESETS_1D = [
  { name: 'Rule 30 (chaotic)', rule: 30 },
  { name: 'Rule 90 (Sierpinski)', rule: 90 },
  { name: 'Rule 110 (complex)', rule: 110 },
  { name: 'Rule 150 (nested)', rule: 150 },
  { name: 'Rule 54 (triangles)', rule: 54 },
  { name: 'Rule 60 (diagonals)', rule: 60 },
  { name: 'Rule 73 (blocks)', rule: 73 },
  { name: 'Rule 105 (dense nest)', rule: 105 },
  { name: 'Rule 22 (fractal)', rule: 22 },
  { name: 'Rule 45 (chaotic)', rule: 45 },
];

/**
 * Parse "B3/S23" into lookup tables. Also accepts "3/23" and "S23/B3".
 * Returns null when the string cannot be read.
 */
export function parseRule(text) {
  if (typeof text !== 'string') return null;
  const cleaned = text.trim().toUpperCase().replace(/\s+/g, '');
  if (!cleaned) return null;

  let birthDigits = null;
  let surviveDigits = null;

  if (cleaned.includes('B') || cleaned.includes('S')) {
    const parts = cleaned.split('/');
    for (const part of parts) {
      const digits = part.replace(/[^0-9]/g, '');
      if (part.startsWith('B')) birthDigits = digits;
      else if (part.startsWith('S')) surviveDigits = digits;
      else return null;
    }
  } else {
    const parts = cleaned.split('/');
    if (parts.length !== 2) return null;
    // Bare "3/23" is survive/birth in the older notation.
    surviveDigits = parts[0].replace(/[^0-9]/g, '');
    birthDigits = parts[1].replace(/[^0-9]/g, '');
  }

  if (birthDigits === null && surviveDigits === null) return null;
  if (/[^0-9]/.test(cleaned.replace(/[BS/]/g, ''))) return null;

  const birth = new Uint8Array(9);
  const survive = new Uint8Array(9);
  for (const ch of birthDigits || '') {
    const n = Number(ch);
    if (n <= 8) birth[n] = 1;
  }
  for (const ch of surviveDigits || '') {
    const n = Number(ch);
    if (n <= 8) survive[n] = 1;
  }
  return { birth, survive, text: formatRule(birth, survive) };
}

export function formatRule(birth, survive) {
  const digits = (table) =>
    Array.from(table)
      .map((on, n) => (on ? n : null))
      .filter((n) => n !== null)
      .join('');
  return `B${digits(birth)}/S${digits(survive)}`;
}

/** Elementary rule number to an 8 entry table indexed by (left<<2)|(centre<<1)|right. */
export function elementaryTable(ruleNumber) {
  const n = Math.max(0, Math.min(255, Math.round(Number(ruleNumber) || 0)));
  const table = new Uint8Array(8);
  for (let i = 0; i < 8; i += 1) table[i] = (n >> i) & 1;
  return table;
}
