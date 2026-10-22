import { searchTopics } from './search-core.mjs';

// Rank each content type separately so articles do not displace procedure guides.
export function searchSite(items, query) {
  const guides = items.filter(item => item.kind !== 'blog');
  const articles = items.filter(item => item.kind === 'blog');
  let result = { guides: searchTopics(guides, query), articles: searchTopics(articles, query, { limit: 4 }) };
  if (!result.guides.length && !result.articles.length) {
    const tokens = query.trim().split(/[\s　]+/).filter(Boolean);
    if (tokens.length > 1) {
      result = { guides: searchTopics(guides, tokens[0]), articles: searchTopics(articles, tokens[0], { limit: 4 }) };
    }
  }
  return result;
}
