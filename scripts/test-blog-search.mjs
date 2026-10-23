import assert from 'node:assert/strict';
import fs from 'node:fs';
import { searchBlogArticles } from '../assets/blog-search.mjs';
import { searchSite } from '../assets/site-search.mjs';
const read = path => JSON.parse(fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/^\uFEFF/,''));
const indexed=read('../blog/search-index.json');
const posts=read('../data/blog-posts.json').posts;
const items=indexed.map(item=>({...item,axis:posts.find(p=>item.href===`/blog/${p.slug}/`).axis}));
for (const query of ['相続','空き家','子育て']) {
  const all=searchBlogArticles(items,query);
  const first=searchSite(items,query).articles;
  assert.ok(all.length>4,`${query} must expose matches beyond the first four`);
  assert.deepEqual(all.slice(0,4).map(x=>x.href),first.map(x=>x.href));
  assert.equal(new Set(all.map(x=>x.href)).size,all.length);
}
const omitted='/blog/20260829-akiya-bank-vs-okoshi-project/';
assert.ok(!searchSite(items,'空き家').articles.some(x=>x.href===omitted));
assert.ok(searchBlogArticles(items,'空き家').some(x=>x.href===omitted));
for (const axis of ['mon','tue','wed','thu','fri','sat','sun']) {
  assert.equal(searchBlogArticles(items,'',axis).length,posts.filter(p=>p.axis===axis).length);
  assert.ok(searchBlogArticles(items,'相続',axis).every(p=>p.axis===axis));
}
assert.equal(searchBlogArticles(items,'').length,posts.length);
assert.ok(searchBlogArticles(items,'ひとり親','thu').some(p=>p.href==='/blog/20261022-iwata-single-parent-cafe/'));
assert.equal(searchBlogArticles(items,'zxqvzzxxx').length,0);
assert.equal(searchBlogArticles(items,'<script>alert("x")</script>').length,0);
console.log('PASS: full result continuation, previously omitted article, 7 themes, combined filters, empty/no-hit/special input');
