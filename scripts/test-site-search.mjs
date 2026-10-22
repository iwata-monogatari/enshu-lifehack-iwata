import assert from 'node:assert/strict';
import fs from 'node:fs';
import { searchSite } from '../assets/site-search.mjs';
import { searchTopics } from '../assets/search-core.mjs';

const read = path => JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8').replace(/^\uFEFF/, ''));
const guides = read('../search-index.json');
const articles = read('../blog/search-index.json');
const posts = read('../data/blog-posts.json').posts;
const cases = read('../data/test-cases.json');
const items = [...guides, ...articles];
assert.equal(articles.length, posts.length, 'Every published article must be searchable');
assert.equal(new Set(items.map(item => item.href)).size, items.length, 'No duplicate results');
for (const post of posts) {
  const item = articles.find(item => item.href === `/blog/${post.slug}/`);
  assert.equal(item?.title, post.title);
  assert.equal(item?.lead, post.description);
  assert.ok(fs.existsSync(new URL(`../blog/${post.slug}/index.html`, import.meta.url)));
}
for (const test of cases) {
  assert.deepEqual(searchSite(items, test.query).guides.map(item => item.href), searchTopics(guides, test.query).map(item => item.href), `Guide rankings changed: ${test.query}`);
}
for (const [query, slug] of [
  ['文化財フェスティバル', '20261021-iwata-cultural-festival'],
  ['リサイクルステーション', '20261018-iwata-recycling-station-comparison'],
  ['空き家バンク', '20260829-akiya-bank-vs-okoshi-project'],
  ['二十歳の集い', '20261019-iwata-hatachi-no-postcard'],
]) {
  assert.ok(searchSite(items, query).articles.some(item => item.href === `/blog/${slug}/`), `Article not found: ${query}`);
}
assert.deepEqual(searchSite(items, 'zxqvzzxxx'), { guides: [], articles: [] });
assert.deepEqual(searchSite(items, ''), { guides: [], articles: [] });
console.log(`PASS: ${posts.length} article records, ${cases.length} guide ranking regressions, 4 article queries, empty/no-hit searches`);
