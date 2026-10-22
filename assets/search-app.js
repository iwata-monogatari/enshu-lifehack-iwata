import { searchSite } from '/assets/site-search.mjs';

let indexPromise = null;
function loadIndex() {
  if (!indexPromise) {
    indexPromise = Promise.all(['/search-index.json', '/blog/search-index.json'].map(async (url) => {
      const res = await fetch(url);
      if (!res.ok) throw new Error('Search index unavailable');
      return res.json();
    })).then((groups) => groups.flat()).catch((error) => {
      indexPromise = null;
      throw error;
    });
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

function logSearchQuery(query, hits) {
  try {
    const payload = JSON.stringify({
      query: (query || '').slice(0, 100),
      hits,
      path: window.location.pathname,
    });
    const url = '/api/search-log';
    if (navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
    } else {
      fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true }).catch(() => {});
    }
  } catch (e) {
    /* noop */
  }
}

const TOP_TASKS = [
  { emoji: '🗑', label: 'ごみ分別・収集日', href: '/life/start-living/garbage-sorting-calendar/' },
  { emoji: '📄', label: '住民票をとる', href: '/life/start-living/resident-registration/' },
  { emoji: '🚚', label: '引っ越してきた', href: '/life/start-living/moved-in/' },
  { emoji: '👶', label: '保育園を探す', href: '/life/family-grow/nursery-school/' },
  { emoji: '💍', label: '婚姻届を出す', href: '/life/family-grow/marriage/' },
  { emoji: '🛋', label: '粗大ごみを出す', href: '/life/start-living/bulky-garbage-dropoff/' },
  { emoji: '💳', label: 'マイナンバーカード', href: '/life/start-living/mynumber/' },
  { emoji: '🏥', label: '休日・夜間の病院', href: '/life/health-medical/holiday-night-emergency-care/' },
];

function renderHitList(label, matched) {
  if (!matched.length) return '';
  return `<h3>${label}</h3><ul>${matched
    .map(
      (page) =>
        `<li><a class="search-hit" href="${escapeHtml(page.href)}"><span class="result-ic" aria-hidden="true">${escapeHtml(page.icon)}</span><span><strong>${escapeHtml(page.title)}</strong><span>${escapeHtml(page.category)}</span></span><span aria-hidden="true">›</span></a></li>`
    )
    .join('')}</ul>`;
}

function renderNoHits(safeQuery) {
  const tasksHtml = TOP_TASKS.map(
    (t) => `<a class="top-task" href="${t.href}"><span class="emoji" aria-hidden="true">${t.emoji}</span>${t.label}</a>`
  ).join('');
  return (
    `<h2>「${safeQuery}」の候補</h2>` +
    `<p class="mini">サイト内に一致する項目が見つかりませんでした。よく使われる手続きから探すか、言葉を変えて検索してください。</p>` +
    `<div class="top-tasks">${tasksHtml}</div>` +
    `<p class="mini" style="margin-top:10px"><a href="https://www.city.iwata.shizuoka.jp/" target="_blank" rel="noopener">磐田市公式サイトで探す →</a></p>`
  );
}

let searchRequest = 0;

async function runSearch(query) {
  const resultsEl = document.getElementById('search-results');
  if (!resultsEl) return;
  const request = ++searchRequest;
  const value = (query || '').trim();
  if (!value) {
    resultsEl.innerHTML = '';
    return;
  }
  let items;
  try {
    items = await loadIndex();
  } catch (error) {
    if (request === searchRequest) resultsEl.innerHTML = '<p role="status">検索データを読み込めませんでした。通信状況を確認して、もう一度「探す」を押してください。</p>';
    return;
  }
  if (request !== searchRequest) return;
  const matched = searchSite(items, value);
  const count = matched.guides.length + matched.articles.length;

  trackSearch(value);
  logSearchQuery(value, count);
  const safeQuery = escapeHtml(value);
  resultsEl.innerHTML = count ? `<h2>「${safeQuery}」の候補</h2>` + renderHitList('手続き・相談ガイド', matched.guides) + renderHitList('ブログ記事', matched.articles) : renderNoHits(safeQuery);
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
  loadIndex().catch(() => {});
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
