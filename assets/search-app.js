import { searchTopics } from '/assets/search-core.mjs';

let indexPromise = null;
function loadIndex() {
  if (!indexPromise) {
    indexPromise = fetch('/search-index.json').then((res) => res.json());
  }
  return indexPromise;
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

const ANALYTICS_ENDPOINT = 'https://fujigaoka-analytics-worker.hiroyukio0122.workers.dev/api/click';
const ANALYTICS_SITE_ID = 'iwata-lifehack';
let searchTrackTimer = null;

function trackSearch(term) {
  const value = (term || '').trim().slice(0, 60);
  if (!value) return;
  clearTimeout(searchTrackTimer);
  searchTrackTimer = setTimeout(() => {
    try {
      fetch(ANALYTICS_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_id: ANALYTICS_SITE_ID,
          path: window.location.pathname + window.location.search,
          url: window.location.href,
          referrer: document.referrer || '',
          event_name: `search:${value}`,
        }),
        mode: 'cors',
        credentials: 'omit',
        keepalive: true,
      }).catch(() => {});
    } catch (e) {
      /* noop */
    }
  }, 700);
}

async function runSearch(query) {
  const resultsEl = document.getElementById('search-results');
  if (!resultsEl) return;
  const value = (query || '').trim();
  if (!value) {
    resultsEl.innerHTML = '';
    return;
  }
  const items = await loadIndex();
  const matched = searchTopics(items, value);
  trackSearch(value);
  const safeQuery = escapeHtml(value);
  resultsEl.innerHTML = matched.length
    ? `<h2>「${safeQuery}」の候補</h2><ul>${matched
        .map(
          (page) =>
            `<li><a class="search-hit" href="${page.href}"><span class="result-ic" aria-hidden="true">${page.icon}</span><span><strong>${page.title}</strong><span>${page.category}</span></span><span aria-hidden="true">›</span></a></li>`
        )
        .join('')}</ul>`
    : `<h2>「${safeQuery}」の候補</h2><p class="mini">サイト内に一致する項目が見つかりませんでした。言葉を短くして検索してください。</p><p class="mini"><a href="/#category-links">カテゴリ一覧から探す →</a></p>`;
}

window.iwataSiteSearch = function iwataSiteSearch(event) {
  event.preventDefault();
  const input = document.getElementById('site-search-input');
  runSearch(input ? input.value : '');
  return false;
};

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('site-search-input');
  const initial = new URLSearchParams(window.location.search).get('q') || '';
  loadIndex();
  if (input && initial) {
    input.value = initial;
    runSearch(initial);
  }
  input?.addEventListener('input', () => runSearch(input.value));

  document.querySelectorAll('.search-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const term = chip.getAttribute('data-chip') || '';
      if (input) input.value = term;
      runSearch(term);
      document.getElementById('search-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
});
