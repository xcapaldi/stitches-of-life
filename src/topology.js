/**
 * Neighbourhoods on the hat's surface.
 *
 * The map is a tube: every round wraps around, so a stitch at the end of a
 * round is beside the stitch at the start. Rounds also change width — the
 * increase round after the cuff, and every decrease round in the crown — so
 * "the stitch above" is not simply the same index one row up.
 *
 * Each stitch is treated as an arc of the round it belongs to. Stitch i of a
 * round W stitches wide covers [i/W, (i+1)/W) of the circumference. Its
 * neighbours in an adjacent round are the stitches whose arcs overlap that
 * span widened by one stitch on each side, which gives the usual three
 * neighbours when both rounds are the same width and degrades sensibly when
 * they are not.
 */

import { wrap } from './grid.js';

const EPS = 1e-9;

/** Indices in a round of `targetWidth` that overlap the arc [a, b) of a circle. */
export function arcOverlap(a, b, targetWidth) {
  if (b - a >= 1) {
    const all = [];
    for (let j = 0; j < targetWidth; j += 1) all.push(j);
    return all;
  }
  const first = Math.floor(a * targetWidth + EPS);
  const last = Math.ceil(b * targetWidth - EPS) - 1;
  const out = [];
  const seen = new Set();
  for (let j = first; j <= last; j += 1) {
    const idx = wrap(j, targetWidth);
    if (seen.has(idx)) continue;
    seen.add(idx);
    out.push(idx);
  }
  return out;
}

/** Neighbours of stitch `i` (of `width`) inside an adjacent round. */
export function neighborsInRow(i, width, targetWidth) {
  const a = (i - 1) / width;
  const b = (i + 2) / width;
  return arcOverlap(a, b, targetWidth);
}

/**
 * The three cells of an adjacent round that feed a 1D automaton: left, centre
 * and right, sampled at the positions those stitches would sit at.
 */
export function parentsInRow(i, width, targetWidth) {
  const center = (i + 0.5) / width;
  return [center - 1 / width, center, center + 1 / width].map((angle) =>
    wrap(Math.floor(((angle % 1) + 1) % 1 * targetWidth), targetWidth),
  );
}

/**
 * Build neighbour lists for the whole map in compressed sparse row form:
 * the neighbours of cell c are `list[start[c] .. start[c + 1])`.
 */
export function buildTopology(layout) {
  const { rowCount, widths, offsets, total } = layout;
  const start = new Int32Array(total + 1);
  const chunks = new Array(total);
  const sets = new Array(total);

  for (let r = 0; r < rowCount; r += 1) {
    const width = widths[r];
    const base = offsets[r];
    for (let i = 0; i < width; i += 1) {
      const self = base + i;
      const found = [];
      const seen = new Set([self]);
      const add = (idx) => {
        if (seen.has(idx)) return;
        seen.add(idx);
        found.push(idx);
      };

      if (width > 1) {
        add(base + wrap(i - 1, width));
        add(base + wrap(i + 1, width));
      }
      for (const dr of [-1, 1]) {
        const other = r + dr;
        if (other < 0 || other >= rowCount) continue;
        const otherWidth = widths[other];
        const otherBase = offsets[other];
        for (const j of neighborsInRow(i, width, otherWidth)) add(otherBase + j);
      }

      chunks[self] = found;
      sets[self] = seen;
    }
  }

  // Where two rounds have different stitch counts the overlap test is not
  // symmetric on its own. Adding the missing reverse links keeps "touching"
  // mutual, so a stitch always influences whatever influences it.
  for (let c = 0; c < total; c += 1) {
    for (const other of chunks[c]) {
      if (sets[other].has(c)) continue;
      sets[other].add(c);
      chunks[other].push(c);
    }
  }

  for (let c = 0; c < total; c += 1) start[c + 1] = chunks[c].length;
  for (let c = 0; c < total; c += 1) start[c + 1] += start[c];
  const list = new Int32Array(start[total]);
  for (let c = 0; c < total; c += 1) {
    const chunk = chunks[c];
    const at = start[c];
    for (let k = 0; k < chunk.length; k += 1) list[at + k] = chunk[k];
  }

  return { start, list, total };
}

/**
 * For every cell, the three cells directly below and the three directly above
 * it, used by the 1D automaton. Stored as flat triples; -1 where the adjacent
 * round does not exist.
 */
export function buildLineage(layout) {
  const { rowCount, widths, offsets, total } = layout;
  const below = new Int32Array(total * 3).fill(-1);
  const above = new Int32Array(total * 3).fill(-1);

  for (let r = 0; r < rowCount; r += 1) {
    const width = widths[r];
    const base = offsets[r];
    for (let i = 0; i < width; i += 1) {
      const self = base + i;
      if (r > 0) {
        const src = parentsInRow(i, width, widths[r - 1]);
        for (let k = 0; k < 3; k += 1) below[self * 3 + k] = offsets[r - 1] + src[k];
      }
      if (r < rowCount - 1) {
        const src = parentsInRow(i, width, widths[r + 1]);
        for (let k = 0; k < 3; k += 1) above[self * 3 + k] = offsets[r + 1] + src[k];
      }
    }
  }

  return { below, above };
}
