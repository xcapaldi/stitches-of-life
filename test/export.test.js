import test from 'node:test';
import assert from 'node:assert/strict';

import { computeHatPlan } from '../src/hat.js';
import { buildLayout, cellIndex, createState } from '../src/grid.js';
import {
  asciiChart,
  buildInstructions,
  buildProject,
  decodeCells,
  describeRound,
  encodeCells,
  readProject,
  roundRuns,
} from '../src/export.js';
import { uniformPlan } from './helpers.js';

test('cells survive a round trip through the project format', () => {
  const state = new Uint8Array(50);
  for (const i of [0, 1, 2, 9, 30, 49]) state[i] = 1;
  const encoded = encodeCells(state);
  assert.deepEqual(Array.from(decodeCells(encoded, state.length)), Array.from(state));

  const empty = new Uint8Array(12);
  assert.deepEqual(Array.from(decodeCells(encodeCells(empty), 12)), Array.from(empty));

  const full = new Uint8Array(12).fill(1);
  assert.deepEqual(Array.from(decodeCells(encodeCells(full), 12)), Array.from(full));
});

test('a round is described in the order it is worked', () => {
  const plan = uniformPlan(2, 10);
  const layout = buildLayout(plan);
  const state = createState(layout);
  for (const i of [0, 1, 5]) state[cellIndex(layout, 0, i)] = 1;

  assert.deepEqual(roundRuns(state, layout, 0), [
    { value: 1, count: 2 },
    { value: 0, count: 3 },
    { value: 1, count: 1 },
    { value: 0, count: 4 },
  ]);
  assert.equal(describeRound(state, layout, 0, 'colorwork'), '2 CC, 3 MC, 1 CC, 4 MC');
  assert.equal(describeRound(state, layout, 0, 'texture'), 'P2, K3, P1, K4');
  assert.equal(describeRound(state, layout, 1, 'colorwork'), '10 MC', 'a plain round stays short');
  assert.equal(describeRound(state, layout, 1, 'texture'), 'K10');
});

test('the ascii chart is drawn top round first, read right to left', () => {
  const plan = uniformPlan(3, 6);
  const layout = buildLayout(plan);
  const state = createState(layout);
  state[cellIndex(layout, 0, 0)] = 1; // first stitch of round 1

  const lines = asciiChart(plan, layout, state).split('\n');
  assert.equal(lines.length, 3);
  assert.ok(lines[0].startsWith('3 '), 'the top round comes first');
  assert.ok(lines[2].endsWith('#'), 'stitch 0 sits at the right-hand edge');
});

test('the pattern reads like a pattern', () => {
  const plan = computeHatPlan({ cuffStyle: 'ribbed', crownStyle: 'round' });
  const layout = buildLayout(plan);
  const state = createState(layout);
  const text = buildInstructions({
    plan,
    layout,
    state,
    meta: { knitBy: 'Ada', knitFor: 'Grace', yarn: 'worsted' },
  });

  assert.ok(text.includes('# Hats That Fit'));
  assert.ok(text.includes('Ada'));
  assert.ok(text.includes(`Cast on **${plan.derived.cuffStitches} stitches**`));
  assert.ok(text.includes(`increase evenly to **${plan.derived.bodyStitches} stitches**`));
  assert.ok(text.includes('K2/P2 ribbing'));
  assert.ok(text.includes('until 8 stitches remain'));
  assert.ok(text.includes('## Round by round'));
  assert.ok(text.includes('## Chart'));
  // Plain rounds are collapsed rather than listed one at a time.
  assert.ok(/Rnds \d+–\d+/.test(text));
});

test('texture patterns talk about knits and purls', () => {
  const plan = computeHatPlan({ stitchMode: 'texture', cuffStyle: 'rolled' });
  const layout = buildLayout(plan);
  const state = createState(layout);
  const text = buildInstructions({ plan, layout, state });
  assert.ok(text.includes('knit and purl on one colour'));
  assert.ok(!text.includes('MC is the main colour'));
});

test('project files identify themselves', () => {
  const plan = computeHatPlan({});
  const layout = buildLayout(plan);
  const project = buildProject({
    plan,
    state: createState(layout),
    simOptions: { mode: '2d', rule2d: 'B3/S23' },
    generation: 4,
    meta: { knitFor: 'Grace' },
  });
  const parsed = readProject(JSON.stringify(project));
  assert.equal(parsed.generation, 4);
  assert.equal(parsed.hat.cuffStyle, plan.params.cuffStyle);
  assert.throws(() => readProject('{"format":"something else"}'), /Not a Stitches of Life project/);
});
