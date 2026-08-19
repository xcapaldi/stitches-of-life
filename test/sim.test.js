import test from 'node:test';
import assert from 'node:assert/strict';

import { computeHatPlan } from '../src/hat.js';
import { buildLayout, cellIndex, population } from '../src/grid.js';
import { buildLineage, buildTopology } from '../src/topology.js';
import { Simulation } from '../src/sim.js';
import { uniformPlan } from './helpers.js';

function makeSim(plan, options) {
  const layout = buildLayout(plan);
  const topology = buildTopology(layout);
  const lineage = buildLineage(layout);
  const sim = new Simulation({ plan, layout, topology, lineage, options });
  return { sim, layout };
}

test('a blinker blinks', () => {
  const plan = uniformPlan(9, 9);
  const { sim, layout } = makeSim(plan, { mode: '2d', seedType: 'clear' });
  for (const i of [3, 4, 5]) sim.state[cellIndex(layout, 4, i)] = 1;
  sim.refreshCurrent();

  sim.stepForward();
  assert.deepEqual(
    [3, 4, 5].map((r) => sim.state[cellIndex(layout, r, 4)]),
    [1, 1, 1],
    'the row becomes a column',
  );
  assert.equal(population(sim.state), 3);

  sim.stepForward();
  assert.deepEqual(
    [3, 4, 5].map((i) => sim.state[cellIndex(layout, 4, i)]),
    [1, 1, 1],
    'and back again',
  );
  assert.deepEqual(sim.cycle, { start: 0, period: 2 });
});

test('history walks forwards and backwards', () => {
  const plan = uniformPlan(12, 12);
  const { sim } = makeSim(plan, { mode: '2d', seedType: 'random', seedDensity: 0.4, rngSeed: 7 });
  const first = Uint8Array.from(sim.state);

  for (let i = 0; i < 6; i += 1) sim.stepForward();
  assert.equal(sim.generation, 6);
  const sixth = Uint8Array.from(sim.state);

  while (sim.stepBackward());
  assert.equal(sim.generation, 0);
  assert.deepEqual(Array.from(sim.state), Array.from(first));
  assert.equal(sim.stepBackward(), false, 'cannot step before the first generation');

  sim.goto(6);
  assert.deepEqual(Array.from(sim.state), Array.from(sixth), 'stepping back does not change history');
  assert.equal(sim.lastGeneration, 6, 'no generations were recomputed');
});

test('the same seed number gives the same design', () => {
  const options = { mode: '2d', seedType: 'random', seedDensity: 0.3, rngSeed: 99 };
  const a = makeSim(uniformPlan(10, 10), options).sim;
  const b = makeSim(uniformPlan(10, 10), options).sim;
  for (let i = 0; i < 5; i += 1) {
    a.stepForward();
    b.stepForward();
  }
  assert.deepEqual(Array.from(a.state), Array.from(b.state));

  const c = makeSim(uniformPlan(10, 10), { ...options, rngSeed: 100 }).sim;
  assert.notDeepEqual(Array.from(c.state), Array.from(a.history[0]));
});

test('editing a stitch discards the generations after it', () => {
  const plan = uniformPlan(8, 8);
  const { sim } = makeSim(plan, { mode: '2d', seedType: 'random', rngSeed: 3 });
  for (let i = 0; i < 5; i += 1) sim.stepForward();
  sim.goto(2);
  sim.editCell(10);
  assert.equal(sim.lastGeneration, 2);
  assert.equal(sim.generation, 2);
});

test('rounds that are not in the map hold still', () => {
  const plan = uniformPlan(6, 8, { inMap: (index) => index > 1 });
  const { sim, layout } = makeSim(plan, { mode: '2d', seedType: 'random', seedDensity: 0.5, rngSeed: 5 });
  const before = Array.from(sim.state.slice(0, layout.offsets[2]));
  for (let i = 0; i < 4; i += 1) sim.stepForward();
  assert.deepEqual(Array.from(sim.state.slice(0, layout.offsets[2])), before);
});

test('the 1D automaton fills one round per generation, upwards', () => {
  const plan = uniformPlan(6, 16);
  const { sim, layout } = makeSim(plan, {
    mode: '1d',
    rule1d: 90,
    direction: 'up',
    seedType: 'single',
  });

  assert.equal(sim.maxGeneration, 5);
  assert.equal(population(sim.state), 1, 'one lit stitch to start');

  sim.stepForward();
  const row1 = Array.from(sim.state.slice(layout.offsets[1], layout.offsets[2]));
  const lit = row1.map((v, i) => (v ? i : -1)).filter((i) => i >= 0);
  assert.deepEqual(lit, [7, 9], 'rule 90 splits the single stitch in two');
  assert.equal(sim.state[layout.offsets[2]], 0, 'later rounds are still empty');

  while (sim.stepForward());
  assert.equal(sim.generation, 5);
  assert.equal(sim.stepForward(), false, 'the map is full');
});

test('the 1D automaton can start at the crown instead', () => {
  const plan = uniformPlan(5, 12);
  const { sim, layout } = makeSim(plan, {
    mode: '1d',
    rule1d: 90,
    direction: 'down',
    seedType: 'single',
  });
  assert.equal(population(sim.state.slice(layout.offsets[4])), 1, 'the seed is the top round');
  sim.stepForward();
  assert.equal(population(sim.state.slice(layout.offsets[3], layout.offsets[4])), 2, 'it grows downwards');
});

test('a real hat runs without falling over', () => {
  const plan = computeHatPlan({ cuffStyle: 'ribbed', crownStyle: 'round', cuffInMap: false });
  const { sim, layout } = makeSim(plan, { mode: '2d', seedType: 'random', rngSeed: 11 });
  assert.equal(sim.state.length, layout.total);
  for (let i = 0; i < 20; i += 1) sim.stepForward();
  assert.equal(sim.generation, 20);
  assert.ok(sim.status().includes('Generation 20'));

  // The fixed ribbed cuff keeps its stripes.
  const width = layout.widths[0];
  for (let i = 0; i < width; i += 1) {
    assert.equal(sim.state[layout.offsets[0] + i], i % 4 < 2 ? 0 : 1);
  }
});

test('1D on a hat fills every round of the map', () => {
  const plan = computeHatPlan({ cuffStyle: 'ribbed', cuffInMap: false, crownInMap: true });
  const { sim } = makeSim(plan, { mode: '1d', rule1d: 30, direction: 'up', seedType: 'inherit' });
  assert.ok(population(sim.state) > 0, 'the cuff seeds the first round');
  while (sim.stepForward());
  assert.equal(sim.generation, sim.maxGeneration);
});
