function htmlEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isExternal(url) {
  try {
    return new URL(url, window.location.origin).origin !== window.location.origin;
  } catch (error) {
    return false;
  }
}

function normalizeColor(rawColor) {
  return String(rawColor || "green").replace(/[^a-z0-9_-]/gi, "") || "green";
}

function resolveCta(page, ctaRules) {
  const byType = ctaRules[page.cta_type] || {};
  const hasCompany = page.related_company && page.related_company !== "none";
  const byCompany = hasCompany ? ctaRules[page.related_company] || {} : {};
  const fallback = ctaRules.official || {};
  const merged = { ...fallback, ...byType, ...byCompany };

  const href = merged.url || page.url || page.official_url || "/";
  const target = isExternal(href) ? ' target="_blank" rel="noopener noreferrer"' : "";
  const title = merged.label || "先に内容確認";

  return {
    href,
    target,
    buttonText: merged.button_text || "詳しく見る",
    tagLabel: title,
    description: merged.description || "",
    strength: merged.strength || "weak"
  };
}

function renderCard(page, ctaRules) {
  const icon = htmlEscape(page.ui_icon || "💬");
  const color = normalizeColor(page.ui_color);
  const title = htmlEscape(page.young_label || page.title || "相談カテゴリ");
  const summary = htmlEscape(page.summary_short || page.title || "");
  const group = htmlEscape(page.ui_group || "");
  const cta = resolveCta(page, ctaRules);

  return `
    <a class="lh-card is-${color}" href="${htmlEscape(cta.href)}"${cta.target}>
      <span class="lh-icon" aria-hidden="true">${icon}</span>
      <strong>${title}</strong>
      <small>${summary}</small>
      <div class="lh-meta">
        <span class="lh-tag">${group || cta.tagLabel}</span>
        <span>${htmlEscape(cta.buttonText)} ▸</span>
      </div>
    </a>
  `;
}

async function loadLifehackCards() {
  const target = document.querySelector("[data-lifehack-cards]");
  if (!target) return;

  const failMessage =
    '<p class="renewal-fallback">カードの取得に失敗しました。時間をおいて再度お試しください。</p>';

  try {
    const [pagesResult, ctaResult] = await Promise.all([
      fetch("/data/pages.json"),
      fetch("/data/cta-rules.json")
    ]);

    if (!pagesResult.ok) {
      throw new Error("pages.json fetch failed");
    }

    const pages = await pagesResult.json();
    const ctaRules = ctaResult.ok ? await ctaResult.json() : {};

    const visibleCards = Array.isArray(pages)
      ? pages
          .filter((page) => page && page.status === "published")
          .slice(0, 8)
      : [];

    if (!visibleCards.length) {
      target.innerHTML = '<p class="renewal-fallback">表示対象のカードがありません。</p>';
      return;
    }

    const cards = visibleCards
      .map((page) => renderCard(page, ctaRules))
      .join("");
    target.innerHTML = cards;
  } catch (error) {
    console.warn("Lifehack cards render failed", error);
    target.innerHTML = failMessage;
  }
}

document.addEventListener("DOMContentLoaded", loadLifehackCards);
