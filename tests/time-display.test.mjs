import test from 'node:test';
import assert from 'node:assert/strict';
import {dateInZone, timeInZone, plannedInstant, localizedTitle} from '../docs/assets/time-display.mjs';

test('execution remains UTC+8 while plan is shown in reader timezone', () => {
  const instant = plannedInstant('2026-10-26', '09:07');
  assert.equal(instant, '2026-10-26T09:07:00+08:00');
  assert.equal(timeInZone(instant, 'Asia/Shanghai'), '09:07');
  assert.equal(timeInZone(instant, 'America/Los_Angeles'), '18:07');
  assert.equal(dateInZone(instant, 'America/Los_Angeles'), '2026-10-25');
  assert.equal(timeInZone(instant, 'Europe/London'), '01:07');
});
test('local date grouping is not the execution date', () => {
  const instant = plannedInstant('2026-10-26', '18:47');
  assert.equal(timeInZone(instant, 'America/Los_Angeles'), '03:47');
  assert.equal(dateInZone(instant, 'America/Los_Angeles'), '2026-10-26');
});
test('DST applies at each instant rather than using a fixed user offset', () => {
  assert.equal(timeInZone(plannedInstant('2026-10-26', '09:07'), 'America/New_York'), '21:07');
  assert.equal(timeInZone(plannedInstant('2026-11-02', '09:07'), 'America/New_York'), '20:07');
});
test('display title date follows actual publication in user timezone', () => {
  assert.equal(localizedTitle('简报（2026-10-26）', '2026-10-26T09:07:00+08:00', 'America/Los_Angeles'), '简报（2026-10-25）');
});
