/**
 * The simulation and its history.
 *
 * Every generation is kept, so the design can be walked forwards and backwards
 * and any generation can be exported. Editing a stitch while scrubbed back in
 * time discards the generations after the current one, the way an undo history
 * behaves.
 */

import { applyFixedRows, createState, hashState, population, simulationRows } from './grid.js';
import { elementaryTable, parseRule } from './rules.js';
import { applySeed } from './seeds.js';

export const DEFAULT_SIM_OPTIONS = {
  mode: '2d', // '2d' | '1d'
  rule2d: 'B3/S23',
  rule1d: 30,
  direction: 'up', // 1D only: which end of the hat holds the first generation
  seedType: 'random',
  seedDensity: 0.35,
  rngSeed: 1,
  maxHistory: 2000,
};

export class Simulation {
  constructor({ plan, layout, topology, lineage, options = {} }) {
    this.plan = plan;
    this.layout = layout;
    this.topology = topology;
    this.lineage = lineage;
    this.options = { ...DEFAULT_SIM_OPTIONS, ...options };
    this.rows = simulationRows(layout);
    this.reset();
  }

  /** Simulation rounds ordered so that index 0 holds the first generation. */
  get orderedRows() {
    if (this.options.mode === '1d' && this.options.direction === 'down') {
      return this.rows.slice().reverse();
    }
    return this.rows;
  }

  get state() {
    return this.history[this.pointer];
  }

  get generation() {
    return this.pointer;
  }

  get lastGeneration() {
    return this.history.length - 1;
  }

  /** The highest generation this configuration can ever reach. */
  get maxGeneration() {
    if (this.options.mode === '1d') return Math.max(0, this.orderedRows.length - 1);
    return Infinity;
  }

  setOptions(options) {
    this.options = { ...this.options, ...options };
  }

  reset() {
    const state = createState(this.layout);
    applySeed(state, {
      plan: this.plan,
      layout: this.layout,
      mode: this.options.mode,
      direction: this.options.direction,
      rows: this.orderedRows,
      type: this.options.seedType,
      density: this.options.seedDensity,
      rngSeed: this.options.rngSeed,
    });
    applyFixedRows(state, this.plan, this.layout);

    this.history = [state];
    this.populations = [population(state)];
    this.pointer = 0;
    this.hashes = new Map([[hashState(state), 0]]);
    this.cycle = null;
    this.exhausted = false;
    return state;
  }

  /** Work out the generation that follows `state`; null when there is none. */
  compute(state, generation) {
    if (this.options.mode === '1d') return this.compute1d(state, generation);
    return this.compute2d(state);
  }

  compute2d(state) {
    const rule = parseRule(this.options.rule2d) || parseRule(DEFAULT_SIM_OPTIONS.rule2d);
    const { start, list } = this.topology;
    const { widths, offsets, rowCount, inMap } = this.layout;
    const next = new Uint8Array(state);

    for (let r = 0; r < rowCount; r += 1) {
      if (!inMap[r]) continue; // fixed rounds keep their pattern
      const base = offsets[r];
      const width = widths[r];
      for (let i = 0; i < width; i += 1) {
        const cell = base + i;
        let live = 0;
        for (let k = start[cell]; k < start[cell + 1]; k += 1) live += state[list[k]];
        if (live > 8) live = 8;
        next[cell] = state[cell] ? rule.survive[live] : rule.birth[live];
      }
    }
    return next;
  }

  compute1d(state, generation) {
    const order = this.orderedRows;
    const target = order[generation + 1];
    if (target === undefined) return null;

    const table = elementaryTable(this.options.rule1d);
    const source = this.options.direction === 'up' ? this.lineage.below : this.lineage.above;
    const { widths, offsets } = this.layout;
    const next = new Uint8Array(state);
    const base = offsets[target];
    const width = widths[target];

    for (let i = 0; i < width; i += 1) {
      const cell = base + i;
      const l = source[cell * 3];
      const c = source[cell * 3 + 1];
      const r = source[cell * 3 + 2];
      if (l < 0 || c < 0 || r < 0) {
        next[cell] = state[cell];
        continue;
      }
      const key = (state[l] << 2) | (state[c] << 1) | state[r];
      next[cell] = table[key];
    }
    return next;
  }

  stepForward() {
    if (this.pointer < this.history.length - 1) {
      this.pointer += 1;
      return true;
    }
    if (this.history.length > this.options.maxHistory) {
      this.exhausted = true;
      return false;
    }
    const next = this.compute(this.state, this.pointer);
    if (!next) {
      this.exhausted = true;
      return false;
    }
    this.history.push(next);
    this.populations.push(population(next));
    this.pointer += 1;

    const hash = hashState(next);
    const seen = this.hashes.get(hash);
    if (seen !== undefined && this.cycle === null) {
      this.cycle = { start: seen, period: this.pointer - seen };
    } else if (seen === undefined) {
      this.hashes.set(hash, this.pointer);
    }
    return true;
  }

  stepBackward() {
    if (this.pointer === 0) return false;
    this.pointer -= 1;
    return true;
  }

  /** Move to generation n, computing the missing generations if needed. */
  goto(n) {
    const target = Math.max(0, Math.round(n));
    if (target <= this.lastGeneration) {
      this.pointer = target;
      return true;
    }
    this.pointer = this.lastGeneration;
    while (this.pointer < target) {
      if (!this.stepForward()) return false;
    }
    return true;
  }

  /** Run forward until the automaton settles or `limit` generations pass. */
  runAhead(limit = 100) {
    let steps = 0;
    while (steps < limit && this.cycle === null && this.stepForward()) steps += 1;
    return steps;
  }

  /** Drop every generation after the current one. */
  truncate() {
    if (this.history.length > this.pointer + 1) {
      this.history.length = this.pointer + 1;
      this.populations.length = this.pointer + 1;
    }
    this.cycle = null;
    this.exhausted = false;
    this.hashes = new Map([[hashState(this.state), this.pointer]]);
  }

  /** Re-read the current state after it has been written to directly. */
  refreshCurrent() {
    this.truncate();
    this.populations[this.pointer] = population(this.state);
    this.hashes = new Map([[hashState(this.state), this.pointer]]);
  }

  /** Hand-edit the current generation; later generations are discarded. */
  editCell(index, value) {
    if (index < 0 || index >= this.layout.total) return false;
    this.truncate();
    const state = this.state;
    const next = value === undefined ? (state[index] ? 0 : 1) : value ? 1 : 0;
    if (state[index] === next) return false;
    state[index] = next;
    this.populations[this.pointer] = population(state);
    this.hashes = new Map([[hashState(state), this.pointer]]);
    return true;
  }

  status() {
    const parts = [];
    const max = this.maxGeneration;
    parts.push(
      `Generation ${this.pointer}${Number.isFinite(max) ? ` of ${max}` : ''} (${this.lastGeneration} computed)`,
    );
    parts.push(`${this.populations[this.pointer].toLocaleString()} contrast stitches`);
    if (this.cycle) {
      parts.push(
        this.cycle.period === 1
          ? `settled at generation ${this.cycle.start}`
          : `period ${this.cycle.period} loop from generation ${this.cycle.start}`,
      );
    } else if (this.exhausted && this.options.mode === '1d') {
      parts.push('the map is full');
    }
    return parts.join(' · ');
  }
}
