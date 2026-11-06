import { test } from 'node:test';
import assert from 'node:assert/strict';
import { blankDraft, replacePick, reviewedPick } from '../src/review';
import { compare } from '../src/math';

const time = '2026-11-06T19:00:00Z';
const draft = () => ({ ...blankDraft(), label: 'Synthetic home win', event: 'Synthetic away at home', odds: '+100' });

test('Manual entry can omit context without manufacturing a forecast', () => {
  const p = reviewedPick(draft(), '1', time);
  assert.equal(p.source, 'Manual entry (unverified)');
  assert.equal(p.fairPercent, '');
  assert.equal(p.kind, 'manual');
  assert.equal(p.confirmed, true);
  assert.equal(p.capturedAt, time);
  assert.equal(compare([p], '10', false)[0].estimatedChance, null);
});

test('Required selection, game and price are checked before review', () => {
  for (const key of ['label', 'event', 'odds'] as const) {
    assert.throws(() => reviewedPick({ ...draft(), [key]: '' }, '1', time));
  }
});

test('Editing replaces the reviewed selection instead of duplicating it', () => {
  const p = reviewedPick(draft(), '1', time);
  const edited = reviewedPick({ ...draft(), odds: '-110' }, '1', time);
  const result = replacePick([p], edited);
  assert.equal(result.length, 1);
  assert.equal(result[0].odds, '-110');
  assert.equal(compare(result, '10', false)[0].gross, '$19.09');
});

test('An edit at capacity succeeds, but a ninth selection is rejected', () => {
  const picks = Array.from({ length: 8 }, (_, i) => reviewedPick(draft(), String(i), time));
  assert.equal(replacePick(picks, { ...picks[0], odds: '+150' }).length, 8);
  assert.throws(() => replacePick(picks, reviewedPick(draft(), '9', time)));
});

test('Zero and certain win assumptions are supported without changing payout', () => {
  const losses = compare([reviewedPick({ ...draft(), fairPercent: '0' }, '1', time)], '10', false)[0];
  assert.equal(losses.estimatedChance, '0.00%');
  assert.equal(losses.expectedNet, '-$10.00');
  const wins = compare([reviewedPick({ ...draft(), fairPercent: '100' }, '1', time)], '10', false)[0];
  assert.equal(wins.estimatedChance, '100.00%');
  assert.equal(wins.expectedNet, '$10.00');
});

test('Combination scenario distinguishes price threshold from assumed chance', () => {
  const a = reviewedPick({ ...draft(), event: 'A', fairPercent: '60' }, '1', time);
  const b = reviewedPick({ ...draft(), event: 'B', fairPercent: '60' }, '2', time);
  const combined = compare([a, b], '10', true).find(r => r.legs === 2)!;
  assert.equal(combined.breakEven, '25.00%');
  assert.equal(combined.estimatedChance, '36.00%');
  assert.equal(combined.gross, '$40.00');
  assert.equal(combined.net, '$30.00');
  assert.equal(combined.expectedNet, '$4.40');
});

test('Same event normalization blocks a misleading independence product', () => {
  const a = reviewedPick({ ...draft(), event: 'Away  AT Home' }, '1', time);
  const b = reviewedPick({ ...draft(), event: ' away at home ' }, '2', time);
  assert.equal(compare([a, b], '10', true).length, 2);
});
