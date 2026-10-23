import { searchBlogArticles } from './blog-search.mjs';

(() => {
  const controls = document.querySelector('.blog-filter');
  const select = document.getElementById('blog-theme');
  const query = document.getElementById('blog-query');
  const clear = document.getElementById('blog-clear');
  const noResults = document.getElementById('blog-no-results');
  const status = document.getElementById('blog-filter-status');
  const items = [...document.querySelectorAll('#blog-post-list > .post-item')];
  if (!controls || !select || !query || !clear || !noResults || !status || !items.length) return;
  const records = items.map(item => ({
    href: item.querySelector('.post-item-link').getAttribute('href'), axis: item.dataset.axis,
    title: item.querySelector('.post-item-title').textContent,
    category: item.querySelector('.post-axis')?.textContent || '',
    synonyms: [], lead: item.querySelector('.post-item-desc')?.textContent || '',
  }));

  function applyFromUrl() {
    const url = new URL(window.location.href);
    let theme = url.searchParams.get('theme') || '';
    let term = url.searchParams.get('q') || '';
    if (![...select.options].some(option => option.value === theme)) theme = '';
    let matches = searchBlogArticles(records, term, theme);
    // A shared article anchor must remain visible, even with different filters.
    const target = document.getElementById(url.hash.slice(1));
    if (target?.matches('.post-item') && !matches.some(item => item.href === target.querySelector('a').getAttribute('href'))) {
      theme = target.dataset.axis;
      term = '';
      matches = searchBlogArticles(records, term, theme);
    }
    select.value = theme;
    query.value = term;
    const hrefs = new Set(matches.map(item => item.href));
    items.forEach((item, index) => { item.hidden = !hrefs.has(records[index].href); });
    const label = theme ? select.selectedOptions[0].textContent.replace(/（\d+件）$/, '') + '：' : '';
    status.textContent = `${term ? `「${term}」・` : ''}${label}${matches.length}件の記事を表示`;
    clear.hidden = !theme && !term;
    noResults.hidden = matches.length !== 0;
  }

  function updateUrl() {
    const url = new URL(window.location.href);
    if (select.value) url.searchParams.set('theme', select.value);
    else url.searchParams.delete('theme');
    if (query.value.trim()) url.searchParams.set('q', query.value.trim());
    else url.searchParams.delete('q');
    url.hash = '';
    if (url.href !== window.location.href) window.history.pushState(null, '', url);
    applyFromUrl();
  }
  controls.querySelector('form').addEventListener('submit', event => { event.preventDefault(); updateUrl(); });
  select.addEventListener('change', updateUrl);
  clear.addEventListener('click', () => { select.value = ''; query.value = ''; updateUrl(); query.focus(); });
  window.addEventListener('popstate', applyFromUrl);
  window.addEventListener('hashchange', applyFromUrl);
  applyFromUrl();
  controls.hidden = false;
  const fallback = document.querySelector('.blog-topics');
  if (fallback) fallback.hidden = true;
})();
