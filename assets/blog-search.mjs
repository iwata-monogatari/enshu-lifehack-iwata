import { searchTopics } from './search-core.mjs';

// Reuse the site search's ranking and fallback, without truncating article matches.
export function searchBlogArticles(items, query, theme = '') {
  const scoped = theme ? items.filter(item => item.axis === theme) : items;
  const value = query.trim();
  if (!value) return scoped;
  let result = searchTopics(scoped, value, { limit: scoped.length });
  const tokens = value.split(/[\s　]+/).filter(Boolean);
  if (!result.length && tokens.length > 1) result = searchTopics(scoped, tokens[0], { limit: scoped.length });
  return result;
}
