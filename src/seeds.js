/**
 * First generations.
 *
 * A seed writes into the rounds that take part in the simulation. For a 2D run
 * that is the whole map; for a 1D run only the round the automaton starts from,
 * since every later round is derived from the one before it.
 */

import { fixedCellValue } from './hat.js';

export const SEED_TYPES = [
  { id: 'random', label: 'Random', modes: ['2d', '1d'], usesDensity: true },
  { id: 'rib', label: 'Ribbing', modes: ['2d', '1d'] },
  { id: 'alternating', label: 'Alternating stitches', modes: ['2d', '1d'] },
  { id: 'single', label: 'Single stitch', modes: ['2d', '1d'] },
  { id: 'sparse', label: 'Scattered stitches', modes: ['2d', '1d'], usesDensity: true },
  { id: 'inherit', label: 'Continue from the cuff', modes: ['1d'] },
  { id: 'glider', label: 'Glider', modes: ['2d'] },
  { id: 'blinker', label: 'Blinker', modes: ['2d'] },
  { id: 'clear', label: 'Empty', modes: ['2d', '1d'] },
];

/** Small deterministic PRNG so a design can be reproduced from its seed number. */
export function makeRng(seed) {
  let a = (Math.floor(Number(seed) || 0) || 1) >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seedRow(state, ctx, row, rng) {
  const { layout, plan, type, density } = ctx;
  const width = layout.widths[row];
  const base = layout.offsets[row];
  const { ribKnit, ribPurl } = plan.params;
  const repeat = ribKnit + ribPurl;

  for (let i = 0; i < width; i += 1) {
    let value = 0;
    switch (type) {
      case 'random':
        value = rng() < density ? 1 : 0;
        break;
      case 'sparse':
        value = rng() < density * 0.25 ? 1 : 0;
        break;
      case 'rib':
        value = i % repeat < ribKnit ? 0 : 1;
        break;
      case 'alternating':
        value = (i + row) % 2;
        break;
      case 'single':
        value = i === Math.floor(width / 2) ? 1 : 0;
        break;
      default:
        value = 0;
    }
    state[base + i] = value;
  }
}

/** Copy the round next to the starting round, resampled to its stitch count. */
function seedInherit(state, ctx, row) {
  const { layout, plan, direction } = ctx;
  const source = direction === 'up' ? row - 1 : row + 1;
  const width = layout.widths[row];
  const base = layout.offsets[row];
  if (source < 0 || source >= layout.rowCount) {
    seedRow(state, { ...ctx, type: 'rib' }, row, () => 0);
    return;
  }
  const sourceWidth = layout.widths[source];
  const sourceBase = layout.offsets[source];
  for (let i = 0; i < width; i += 1) {
    const j = Math.min(sourceWidth - 1, Math.floor(((i + 0.5) / width) * sourceWidth));
    // A fixed round may not have been written yet, so fall back to its pattern.
    const value = layout.inMap[source] ? state[sourceBase + j] : fixedCellValue(plan, source, j);
    state[base + i] = value;
  }
}

function placePattern(state, ctx, cells) {
  const { layout, rows } = ctx;
  const anchorRow = rows[Math.floor(rows.length / 2)];
  for (const [dr, di] of cells) {
    const row = anchorRow + dr;
    if (row < 0 || row >= layout.rowCount) continue;
    const width = layout.widths[row];
    const stitch = (Math.floor(width / 2) + di + width) % width;
    state[layout.offsets[row] + stitch] = 1;
  }
}

const GLIDER = [
  [0, 0],
  [1, 1],
  [2, -1],
  [2, 0],
  [2, 1],
];

const BLINKER = [
  [0, -1],
  [0, 0],
  [0, 1],
];

/**
 * Write a seed into `state`.
 *
 * ctx: { plan, layout, mode, direction, rows, type, density, rngSeed }
 * where `rows` are the simulation rounds in knitting order.
 */
export function applySeed(state, ctx) {
  const { mode, rows, type } = ctx;
  if (!rows.length) return state;

  const rng = makeRng(ctx.rngSeed);
  // `rows` arrives in generation order, so the first generation is always rows[0].
  const targets = mode === '1d' ? [rows[0]] : rows;

  // 1D fills the map round by round, so everything downstream starts empty.
  if (mode === '1d') {
    for (const row of rows) {
      const base = ctx.layout.offsets[row];
      state.fill(0, base, base + ctx.layout.widths[row]);
    }
  }

  if (type === 'glider' || type === 'blinker') {
    for (const row of rows) {
      const base = ctx.layout.offsets[row];
      state.fill(0, base, base + ctx.layout.widths[row]);
    }
    placePattern(state, ctx, type === 'glider' ? GLIDER : BLINKER);
    return state;
  }

  for (const row of targets) {
    if (type === 'inherit') seedInherit(state, ctx, row);
    else seedRow(state, ctx, row, rng);
  }
  return state;
}
