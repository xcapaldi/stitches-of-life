import test from 'node:test';
import assert from 'node:assert/strict';

import { CROWN_FINAL_STITCHES, computeHatPlan, fixedCellValue } from '../src/hat.js';

test('worksheet arithmetic matches the form', () => {
  const plan = computeHatPlan({
    headCircumference: 22,
    earToEar: 14,
    stitchGauge: 5,
    rowGauge: 7,
    ease: 1,
    cuffStyle: 'hemmed',
  });

  // 22 - 1 = 21 inches around; 21 x 5 = 105 stitches.
  assert.equal(plan.derived.inchesAround, 21);
  assert.equal(plan.derived.bodyStitches, 105);
  // C less 10% of C.
  assert.equal(plan.derived.cuffStitches, 95);
  // 14 / 4 = 3.5, + 1 = 4.5 inches of body.
  assert.equal(plan.derived.crownLength, 3.5);
  assert.equal(plan.derived.bodyLength, 4.5);
  assert.equal(plan.derived.workedBodyInches, 4.5);
});

test('a ribbed cuff loses an inch of body and divides by the rib repeat', () => {
  const plan = computeHatPlan({ cuffStyle: 'ribbed', ribKnit: 2, ribPurl: 2 });
  assert.equal(plan.derived.cuffStitches % 4, 0);
  assert.equal(plan.derived.workedBodyInches, plan.derived.bodyLength - 1);
});

test('rounds run cast-on first and the crown ends on eight stitches', () => {
  for (const crownStyle of ['square', 'pointed', 'round']) {
    const plan = computeHatPlan({ crownStyle });
    const rows = plan.rows;
    assert.equal(rows[0].kind, 'cast-on');
    assert.equal(rows[0].width, plan.derived.cuffStitches);
    assert.equal(rows[rows.length - 1].width, CROWN_FINAL_STITCHES);

    const sections = [...new Set(rows.map((row) => row.section))];
    assert.deepEqual(sections, ['cuff', 'body', 'crown'], 'sections stay contiguous');

    // Widths never grow inside the crown and never fall below the finish count.
    const crown = rows.filter((row) => row.section === 'crown');
    for (let i = 1; i < crown.length; i += 1) {
      assert.ok(crown[i].width <= crown[i - 1].width);
      assert.ok(crown[i].width >= CROWN_FINAL_STITCHES);
    }
    assert.equal(crown[0].width % plan.crown.multiple, 0);
  }
});

test('the body starts with an increase round to C', () => {
  const plan = computeHatPlan({ cuffStyle: 'hemmed' });
  const body = plan.rows.filter((row) => row.section === 'body');
  assert.equal(body[0].kind, 'increase');
  assert.equal(body[0].width, plan.derived.bodyStitches);
  assert.equal(body[1].kind, 'turn', 'a hemmed cuff gets a purl fold round');
});

test('decrease counts add up to the stitches removed', () => {
  const plan = computeHatPlan({ crownStyle: 'square' });
  const crown = plan.rows.filter((row) => row.section === 'crown');
  const removed = crown.reduce((sum, row) => sum + row.decreases, 0);
  assert.equal(plan.derived.bodyStitches - removed, CROWN_FINAL_STITCHES);
});

test('silly measurements still produce a knittable hat', () => {
  const plan = computeHatPlan({ headCircumference: 0, earToEar: 0, stitchGauge: 0, rowGauge: 0 });
  assert.ok(plan.derived.bodyStitches >= 16);
  assert.ok(plan.rows.length > 3);
  assert.equal(plan.rows[plan.rows.length - 1].width, CROWN_FINAL_STITCHES);
});

test('fixed cuff cells follow the rib repeat', () => {
  const plan = computeHatPlan({ cuffStyle: 'ribbed', ribKnit: 2, ribPurl: 2 });
  assert.equal(fixedCellValue(plan, 0, 0), 0);
  assert.equal(fixedCellValue(plan, 0, 1), 0);
  assert.equal(fixedCellValue(plan, 0, 2), 1);
  assert.equal(fixedCellValue(plan, 0, 3), 1);
  const bodyRow = plan.derived.cuffRows;
  assert.equal(fixedCellValue(plan, bodyRow, 3), 0, 'only the cuff is ribbed');
});
