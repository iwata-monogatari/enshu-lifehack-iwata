(() => {
  const controls = document.querySelector('.blog-filter');
  const select = document.getElementById('blog-theme');
  const status = document.getElementById('blog-filter-status');
  const items = [...document.querySelectorAll('#blog-post-list > .post-item')];
  if (!controls || !select || !status || !items.length) return;

  function applyFromUrl() {
    const url = new URL(window.location.href);
    let theme = url.searchParams.get('theme') || '';
    if (![...select.options].some(option => option.value === theme)) theme = '';
    // A shared article anchor must remain visible, even with a different theme.
    const target = document.getElementById(url.hash.slice(1));
    if (target?.matches('.post-item') && theme && target.dataset.axis !== theme) theme = target.dataset.axis;
    select.value = theme;
    let count = 0;
    items.forEach(item => {
      item.hidden = !!theme && item.dataset.axis !== theme;
      if (!item.hidden) count++;
    });
    const label = theme ? select.selectedOptions[0].textContent.replace(/（\d+件）$/, '') + '：' : '';
    status.textContent = `${label}${count}件の記事を表示`;
  }

  select.addEventListener('change', () => {
    const url = new URL(window.location.href);
    if (select.value) url.searchParams.set('theme', select.value);
    else url.searchParams.delete('theme');
    url.hash = '';
    window.history.pushState(null, '', url);
    applyFromUrl();
  });
  window.addEventListener('popstate', applyFromUrl);
  window.addEventListener('hashchange', applyFromUrl);
  applyFromUrl();
  controls.hidden = false;
  const fallback = document.querySelector('.blog-topics');
  if (fallback) fallback.hidden = true;
})();
