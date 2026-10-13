import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCatalog } from '../src/catalog.js';

const now = '2026-10-13T12:00:00+09:00';
const make = (overrides = {}) => ({
  source: 'hello.md',
  title: 'Hello',
  publishedAt: '2026-10-12T08:00:00+09:00',
  ...overrides,
});

test('creates a catalog entry from a published article', () => {
  assert.deepEqual(buildCatalog([make()], { now }), [{
    title: 'Hello', slug: 'hello', url: '/articles/hello',
    publishedAt: '2026-10-12T08:00:00+09:00',
  }]);
});

test('uses the basename of a nested POSIX path', () => {
  assert.equal(buildCatalog([make({ source: 'tech/2026/10/nested.md' })], { now })[0].slug, 'nested');
});

test('uses the basename of a Windows path', () => {
  const result = buildCatalog([make({ source: 'tech\\2026\\10\\windows.md' })], { now });
  assert.equal(result[0].slug, 'windows');
  assert.equal(result[0].url, '/articles/windows');
});

test('omits draft records', () => {
  assert.deepEqual(buildCatalog([make({ draft: true })], { now }), []);
});

test('omits future publication timestamps', () => {
  assert.deepEqual(buildCatalog([make({ publishedAt: '2026-10-14T00:00:00+09:00' })], { now }), []);
});

test('includes an article published exactly at now', () => {
  assert.equal(buildCatalog([make({ publishedAt: now })], { now }).length, 1);
});

test('sorts actual instants rather than timestamp strings', () => {
  const input = [
    make({ title: 'Older', publishedAt: '2026-10-12T10:00:00+09:00' }),
    make({ title: 'Newer', publishedAt: '2026-10-12T02:00:00Z' }),
  ];
  assert.deepEqual(buildCatalog(input, { now }).map((r) => r.title), ['Newer', 'Older']);
});

test('omits invalid publication timestamps', () => {
  assert.deepEqual(buildCatalog([make({ publishedAt: 'not-a-date' })], { now }), []);
});

test('does not mutate input arrays or records', () => {
  const input = [make(), make({ title: 'Earlier', publishedAt: '2026-10-11T00:00:00Z' })];
  const before = structuredClone(input);
  buildCatalog(input, { now });
  assert.deepEqual(input, before);
});
