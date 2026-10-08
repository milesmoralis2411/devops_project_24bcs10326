import assert from 'node:assert/strict';
import { test } from 'node:test';

import { errorMessage } from './api.js';
import { shortSha, signed, stockFill, timeAgo } from './format.js';

test('stockFill is empty when out of stock and capped at 100', () => {
  assert.equal(stockFill(0, 10), 0);
  assert.equal(stockFill(10, 10), 40); // reorder level sits at 40% of the bar
  assert.equal(stockFill(1000, 10), 100);
});

test('signed prefixes positive numbers', () => {
  assert.equal(signed(5), '+5');
  assert.equal(signed(-3), '-3');
});

test('timeAgo produces human friendly durations', () => {
  const now = Date.parse('2026-01-01T12:00:00Z');
  assert.equal(timeAgo('2026-01-01T11:59:50Z', now), 'just now');
  assert.equal(timeAgo('2026-01-01T11:30:00Z', now), '30 min ago');
  assert.equal(timeAgo('2026-01-01T09:00:00Z', now), '3 hrs ago');
  assert.equal(timeAgo('2025-12-30T12:00:00Z', now), '2 days ago');
});

test('shortSha shortens commit hashes', () => {
  assert.equal(shortSha('0123456789abcdef'), '0123456');
  assert.equal(shortSha(undefined), 'dev');
});

test('errorMessage flattens FastAPI validation errors', () => {
  const body = { detail: [{ loc: ['body', 'sku'], msg: 'String should match pattern' }] };
  assert.equal(errorMessage(body, 422), 'sku: String should match pattern');
  assert.equal(errorMessage({ detail: 'Product not found' }, 404), 'Product not found');
  assert.equal(errorMessage(null, 502), 'Request failed (HTTP 502)');
});
