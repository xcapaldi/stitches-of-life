import test from 'node:test';
import assert from 'node:assert/strict';

import { elementaryTable, formatRule, parseRule } from '../src/rules.js';

test('B/S notation is read both ways round', () => {
  const life = parseRule('B3/S23');
  assert.equal(life.text, 'B3/S23');
  assert.equal(life.birth[3], 1);
  assert.equal(life.birth[2], 0);
  assert.equal(life.survive[2], 1);
  assert.equal(life.survive[3], 1);
  assert.equal(life.survive[4], 0);

  assert.equal(parseRule('S23/B3').text, 'B3/S23');
  assert.equal(parseRule('b3/s23').text, 'B3/S23');
  assert.equal(parseRule(' B3 / S23 ').text, 'B3/S23');
  // The older survive/birth form.
  assert.equal(parseRule('23/3').text, 'B3/S23');
});

test('rules with no survival counts are still valid', () => {
  const seeds = parseRule('B2/S');
  assert.equal(seeds.text, 'B2/S');
  assert.equal(seeds.survive.reduce((a, b) => a + b, 0), 0);
});

test('nonsense rules are rejected', () => {
  for (const input of ['', 'hello', 'B3/Sx', 'B3-S23', null, 42]) {
    assert.equal(parseRule(input), null, `${input} should not parse`);
  }
});

test('formatRule round-trips', () => {
  const rule = parseRule('B36/S23');
  assert.equal(formatRule(rule.birth, rule.survive), 'B36/S23');
});

test('elementary rule numbers become lookup tables', () => {
  const rule30 = elementaryTable(30);
  // Rule 30: 111->0, 110->0, 101->0, 100->1, 011->1, 010->1, 001->1, 000->0
  assert.deepEqual(Array.from(rule30), [0, 1, 1, 1, 1, 0, 0, 0]);

  const rule90 = elementaryTable(90);
  for (let i = 0; i < 8; i += 1) {
    const left = (i >> 2) & 1;
    const right = i & 1;
    assert.equal(rule90[i], left ^ right, 'rule 90 is left xor right');
  }

  assert.deepEqual(Array.from(elementaryTable(0)), [0, 0, 0, 0, 0, 0, 0, 0]);
  assert.deepEqual(Array.from(elementaryTable(255)), [1, 1, 1, 1, 1, 1, 1, 1]);
  assert.deepEqual(Array.from(elementaryTable(300)), Array.from(elementaryTable(255)), 'clamped');
});
