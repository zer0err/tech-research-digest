import assert from 'node:assert/strict';
import {test} from 'node:test';
import {legacyReferenceCount, strictHttps} from '../docs/assets/article-reading.mjs';

const row = (text, ...urls) => ({text, urls});
const a = 'https://doi.org/10.64823/ijter.2611001';
const b = 'https://developer.nvidia.com/blog/example';
const c = 'https://arxiv.org/abs/2611.17334';

test('accepts only contiguous and unique section-local reference rows', () => {
  assert.equal(legacyReferenceCount([row('[1] notice', a), row('[2] paper', b)], false), 2);
  assert.equal(legacyReferenceCount([row('notice', a), row('paper', b)], true), 2);
  assert.equal(legacyReferenceCount([row('[2] swapped', b), row('[1] swapped', a)], true), 0);
  assert.equal(legacyReferenceCount([row('[1] notice', a), row('[2] duplicate', a)], false), 0);
  assert.equal(legacyReferenceCount([row('[1] notice', a, b), row('[2] paper', c)], false), 0);
  assert.equal(legacyReferenceCount([row('[1] notice', a), row('missing number', c)], false), 0);
  assert.equal(legacyReferenceCount([row('missing link')], true), 0);
});

test('parser rejects credentials, non-HTTPS, and relative links', () => {
  for (const bad of ['https://u:p@e.example', '/paper', 'javascript:void(0)', 'http://e.example', ' https://e.example ']) {
    assert.equal(strictHttps(bad), false);
  }
  assert.equal(strictHttps(a), true);
});
