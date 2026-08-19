/**
 * Flat storage for the stitch map.
 *
 * Rounds have different stitch counts, so cells live in one flat array with a
 * per-row offset table rather than a rectangular buffer.
 */

import { fixedCellValue } from './hat.js';

export function buildLayout(plan) {
  const rowCount = plan.rows.length;
  const widths = new Int32Array(rowCount);
  const offsets = new Int32Array(rowCount + 1);
  let total = 0;
  for (let r = 0; r < rowCount; r += 1) {
    widths[r] = plan.rows[r].width;
    offsets[r] = total;
    total += widths[r];
  }
  offsets[rowCount] = total;

  const inMap = new Uint8Array(rowCount);
  for (let r = 0; r < rowCount; r += 1) inMap[r] = plan.rows[r].inMap ? 1 : 0;

  return { rowCount, widths, offsets, total, inMap };
}

export const wrap = (i, width) => ((i % width) + width) % width;

export function cellIndex(layout, row, stitch) {
  if (row < 0 || row >= layout.rowCount) return -1;
  return layout.offsets[row] + wrap(stitch, layout.widths[row]);
}

export function rowOfCell(layout, index) {
  let lo = 0;
  let hi = layout.rowCount - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (layout.offsets[mid] <= index) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

export function createState(layout) {
  return new Uint8Array(layout.total);
}

/**
 * Write the fixed content (ribbing) into every round that is not part of the
 * simulation. Rounds that are in the map keep whatever the seed put there.
 */
export function applyFixedRows(state, plan, layout) {
  for (let r = 0; r < layout.rowCount; r += 1) {
    if (layout.inMap[r]) continue;
    const width = layout.widths[r];
    const base = layout.offsets[r];
    for (let i = 0; i < width; i += 1) state[base + i] = fixedCellValue(plan, r, i);
  }
  return state;
}

/** Rounds that take part in the simulation, in knitting order. */
export function simulationRows(layout) {
  const rows = [];
  for (let r = 0; r < layout.rowCount; r += 1) if (layout.inMap[r]) rows.push(r);
  return rows;
}

export function population(state) {
  let n = 0;
  for (let i = 0; i < state.length; i += 1) n += state[i];
  return n;
}

/** FNV-1a over the state, used to spot still lifes and oscillators. */
export function hashState(state) {
  let h = 0x811c9dc5;
  for (let i = 0; i < state.length; i += 1) {
    h ^= state[i];
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}
