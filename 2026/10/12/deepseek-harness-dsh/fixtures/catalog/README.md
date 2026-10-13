# Article catalog fixture

This small Node.js project builds a public article catalog from metadata records.
It is an intentionally buggy fixture for a coding-agent experiment, not production code.
There are no external dependencies. Run the tests with `npm test`.

`buildCatalog(records, { now })` in `src/catalog.js` returns a new array containing
`title`, `slug`, `url`, and the original `publishedAt` string for each public record.

Expected behavior:

- Omit records whose `draft` value is boolean `true`.
- Include valid publication timestamps at or before `now`; omit future and invalid timestamps.
- Sort from newest to oldest by the actual instant, including timezone offsets.
- Derive the slug from the final `.md` filename, for either POSIX or Windows paths.
- Set `url` to `/articles/` followed by that slug. Fixture slugs use URL-safe ASCII.
- Do not mutate the input records or input array.

The tests include three regressions. Fix the implementation without changing or
deleting existing tests, removing assertions, or hardcoding fixture values.
