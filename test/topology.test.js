import test from 'node:test';
import assert from 'node:assert/strict';

import { computeHatPlan } from '../src/hat.js';
import { buildLayout, cellIndex, rowOfCell } from '../src/grid.js';
import { arcOverlap, buildLineage, buildTopology, neighborsInRow, parentsInRow } from '../src/topology.js';
import { uniformPlan } from './helpers.js';

const neighborsOf = (topology, cell) =>
  Array.from(topology.list.slice(topology.start[cell], topology.start[cell + 1]));

test('equal width rounds give the usual eight neighbours', () => {
  const layout = buildLayout(uniformPlan(5, 10));
  const topology = buildTopology(layout);
  const cell = cellIndex(layout, 2, 4);
  const neighbors = neighborsOf(topology, cell);
  assert.equal(neighbors.length, 8);
  const expected = [];
  for (const dr of [-1, 0, 1]) {
    for (const di of [-1, 0, 1]) {
      if (dr === 0 && di === 0) continue;
      expected.push(cellIndex(layout, 2 + dr, 4 + di));
    }
  }
  assert.deepEqual(neighbors.slice().sort((a, b) => a - b), expected.sort((a, b) => a - b));
});

test('a round wraps around the hat', () => {
  const layout = buildLayout(uniformPlan(3, 10));
  const topology = buildTopology(layout);
  const first = cellIndex(layout, 1, 0);
  const last = cellIndex(layout, 1, 9);
  assert.ok(neighborsOf(topology, first).includes(last), 'stitch 0 touches the end of the round');
});

test('the top and bottom rounds have five neighbours', () => {
  const layout = buildLayout(uniformPlan(4, 12));
  const topology = buildTopology(layout);
  assert.equal(neighborsOf(topology, cellIndex(layout, 0, 5)).length, 5);
  assert.equal(neighborsOf(topology, cellIndex(layout, 3, 5)).length, 5);
});

test('neighbourhoods stay mutual across decrease rounds', () => {
  const plan = computeHatPlan({ crownStyle: 'round' });
  const layout = buildLayout(plan);
  const topology = buildTopology(layout);
  for (let cell = 0; cell < layout.total; cell += 1) {
    for (const other of neighborsOf(topology, cell)) {
      assert.ok(
        neighborsOf(topology, other).includes(cell),
        `cell ${cell} and ${other} disagree about touching`,
      );
      assert.notEqual(other, cell, 'a stitch is not its own neighbour');
    }
  }
});

test('every stitch of a hat has neighbours above and below where rounds exist', () => {
  const plan = computeHatPlan({});
  const layout = buildLayout(plan);
  const topology = buildTopology(layout);
  for (let cell = 0; cell < layout.total; cell += 1) {
    const row = rowOfCell(layout, cell);
    const neighbors = neighborsOf(topology, cell);
    assert.ok(neighbors.length >= 4, `cell ${cell} in round ${row} is too lonely`);
    assert.ok(neighbors.length <= 20, `cell ${cell} in round ${row} has too many neighbours`);
  }
});

test('arc overlap covers the whole round when the span is wide enough', () => {
  assert.equal(arcOverlap(0, 1.5, 6).length, 6);
  // Three stitches wide, the widened span already wraps the whole round.
  assert.deepEqual(neighborsInRow(0, 3, 3), [0, 1, 2]);
  assert.deepEqual(neighborsInRow(0, 4, 4), [3, 0, 1]);
});

test('parents sample left, centre and right of the round below', () => {
  assert.deepEqual(parentsInRow(5, 10, 10), [4, 5, 6]);
  assert.deepEqual(parentsInRow(0, 10, 10), [9, 0, 1], 'the round wraps');
  // Half as many stitches below: neighbouring stitches share parents.
  assert.deepEqual(parentsInRow(4, 10, 5), [1, 2, 2]);
});

test('lineage points at the physically adjacent rounds', () => {
  const layout = buildLayout(uniformPlan(3, 8));
  const lineage = buildLineage(layout);
  const cell = cellIndex(layout, 1, 3);
  assert.deepEqual(
    Array.from(lineage.below.slice(cell * 3, cell * 3 + 3)),
    [cellIndex(layout, 0, 2), cellIndex(layout, 0, 3), cellIndex(layout, 0, 4)],
  );
  assert.deepEqual(
    Array.from(lineage.above.slice(cell * 3, cell * 3 + 3)),
    [cellIndex(layout, 2, 2), cellIndex(layout, 2, 3), cellIndex(layout, 2, 4)],
  );
  const bottom = cellIndex(layout, 0, 3);
  assert.equal(lineage.below[bottom * 3], -1, 'nothing below the cast-on round');
});

test('the layout indexes rows and cells consistently', () => {
  const plan = computeHatPlan({});
  const layout = buildLayout(plan);
  assert.equal(layout.total, plan.derived.totalStitches);
  for (let row = 0; row < layout.rowCount; row += 1) {
    assert.equal(rowOfCell(layout, layout.offsets[row]), row);
    assert.equal(rowOfCell(layout, layout.offsets[row] + layout.widths[row] - 1), row);
    assert.equal(cellIndex(layout, row, layout.widths[row]), layout.offsets[row], 'indices wrap');
  }
});
