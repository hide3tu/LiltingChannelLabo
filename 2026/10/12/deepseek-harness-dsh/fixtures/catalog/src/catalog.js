export function buildCatalog(records, { now }) {
  return records
    .filter((record) => record.draft !== true)
    .filter((record) => Date.parse(record.publishedAt) < Date.parse(now))
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .map((record) => {
      const slug = record.source.split('/').at(-1).replace(/\.md$/, '');
      return {
        title: record.title,
        slug,
        url: `/articles/${slug}`,
        publishedAt: record.publishedAt,
      };
    });
}
