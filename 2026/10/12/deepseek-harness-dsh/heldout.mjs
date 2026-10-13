import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const { buildCatalog } = await import(pathToFileURL(resolve(process.argv[2])));
const make = (overrides = {}) => ({ source: 'entry.md', title: 'Entry', publishedAt: '2026-10-11T12:00:00Z', ...overrides });
const cases = [
  ['UTC day transition', () => {
    const records = [
      make({ title: 'Older', publishedAt: '2026-10-12T00:30:00+09:00' }),
      make({ title: 'Newer', publishedAt: '2026-10-11T17:00:00Z' }),
    ];
    assert.deepEqual(buildCatalog(records, { now: '2026-10-13T00:00:00Z' }).map((r) => r.title), ['Newer', 'Older']);
  }],
  ['Windows filename with a dot', () => {
    assert.equal(buildCatalog([make({ source: 'C:\\articles\\v2.notes.md' })], { now: '2026-10-13T00:00:00Z' })[0].url, '/articles/v2.notes');
  }],
  ['Same instant with a different offset', () => {
    assert.equal(buildCatalog([make({ publishedAt: '2026-10-13T03:00:00Z' })], { now: '2026-10-13T12:00:00+09:00' }).length, 1);
  }],
];
let passed = 0;
for (const [name, check] of cases) {
  try { check(); passed++; console.log(JSON.stringify({ name, pass: true })); }
  catch (e) { console.log(JSON.stringify({ name, pass: false, error: e.message })); }
}
console.log(JSON.stringify({ passed, total: cases.length }));
process.exitCode = passed === cases.length ? 0 : 1;
