import {test} from 'node:test';
import assert from 'node:assert/strict';
import {slotStatus} from '../docs/assets/slot-status.mjs';
const planned = '2026-10-25T09:07:00+08:00';
const now = new Date('2026-10-25T12:00:00+08:00');
test('historical empty rows never promise future publication', () => {
  assert.match(slotStatus(undefined, planned, now, true), /无可核验/);
  assert.equal(slotStatus({status:'already_published'}, planned, now, true), '今日无新增');
  assert.match(slotStatus({status:'analysis_rejected',attempts:1}, planned, now, true), /本次未发布/);
});
test('future, delayed, retrying and exhausted are distinct', () => {
  assert.equal(slotStatus(undefined, planned, new Date('2026-10-25T00:00Z')), '未到执行时间');
  assert.match(slotStatus(undefined, planned, now), /执行延迟/);
  assert.match(slotStatus({status:'source_failure',attempts:1}, planned, now), /等待重试/);
  assert.match(slotStatus({status:'source_failure',attempts:3}, planned, now), /本次未发布/);
});
