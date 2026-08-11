#!/usr/bin/env python3
"""売却予備軍ページに磐田独自の実家カルテCTAを注入する（上部・下部・追従バーの3点）。

2026-08-11の導線監査で、カルテ申込ボタンがモバイル実測でスクロール深度87〜88%
の位置にしか無く、追従CTAも無いことが判明した。売却意向が最も高い読者が公式
リンク集と関連リンク集を抜けないと申込に到達しない状態だったため、

  1. ヒーロー直下（h1直下）に軽量CTA  <!-- KARTE-TOP -->
  2. フッター直上に従来の強CTA        <!-- KARTE-CTA -->
  3. モバイル限定の追従バー            （KARTE-CTAブロック内）

の3点配置に変更した。どの位置が効いたかを分離計測するため utm_content は
「{slug}_top / {slug} / {slug}_bar」と placement 別に振り分ける。

対象は企画書v3.0 §3-4の10ページに、売却直前の検索で当たる4ページ
(固定資産税・解体耐震・農地・転出)を追加した計14ページ。緊急・医療・生活困窮
ページには配置しない。

配色は公的情報のブルー系と区別するためアンバー系(site.cssに定義)。

使い方: python3 scripts/inject_karte_iwata.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (相対パス, utm_content用slug)
TARGETS = [
    ("life/end-of-life/house-became-vacant", "house_became_vacant"),
    ("life/end-of-life/inherited-house", "inherited_house"),
    ("life/end-of-life/inherited-vacant-house", "inherited_vacant_house"),
    ("life/end-of-life/inheritance", "inheritance"),
    ("life/end-of-life/property-tax-inheritance", "property_tax_inheritance"),
    ("life/housing/sell-house", "sell_house"),
    ("life/housing/vacant-house", "vacant_house"),
    ("life/housing/clean-parents-house", "clean_parents_house"),
    ("life/parents-care/find-nursing-home", "find_nursing_home"),
    ("life/troubles-consult/vacant-house-consultation", "vacant_house_consultation"),
    # 2026-08-11 追加: 売却を決める直前に検索される4ページ
    ("life/housing/property-tax", "property_tax"),
    ("life/housing/earthquake-demolition", "earthquake_demolition"),
    ("life/troubles-consult/farmland", "farmland"),
    ("life/moving-out/moving-away", "moving_away"),
]

TOP_START, TOP_END = "<!-- KARTE-TOP:START -->", "<!-- KARTE-TOP:END -->"
CTA_START, CTA_END = "<!-- KARTE-CTA:START -->", "<!-- KARTE-CTA:END -->"
TOP_RE = re.compile(re.escape(TOP_START) + r".*?" + re.escape(TOP_END), re.S)
CTA_RE = re.compile(re.escape(CTA_START) + r".*?" + re.escape(CTA_END), re.S)

KARTE_URL = (
    "https://fudosan.atawi.link/karte/?area=磐田市"
    "&amp;utm_source=iwata_lifehack&amp;utm_medium=referral"
    "&amp;utm_campaign=iwata_karte&amp;utm_content={slug}#apply"
)

# 電話はカルテ受付窓口の表記に統一する（富士ヶ丘サービス不動産／9:00〜17:00・予約営業）
TEL_NUM = "0538-31-3308"
TEL_HREF = "tel:0538313308"
TEL_HOURS = "9:00〜17:00・予約営業"

# 「売却依頼にはなりません」で終わらせず、依頼という次段階が存在することを示す一文。
# 否定だけだと読者の中に依頼への道筋が残らない。
ASSURANCE = (
    "申込みだけで売却依頼にはなりません。"
    "売ると決めたときは、そのまま当社（宅地建物取引士・静岡県知事(2)第14083号）がお手伝いできます。"
)

TOP_BANNER = (
    '<section class="karte-lead">'
    '<p class="karte-lead-text"><b>実家・空き家をどうするか、まだ決めていなくて大丈夫です。</b>'
    "住所をもとに、道路・境界・登記・農地など次に確認する順番を、"
    "宅地建物取引士（大石浩之）が無料で整理します。入力約1分。</p>"
    '<div class="karte-lead-actions">'
    '<a class="karte-lead-btn" href="' + KARTE_URL + '" target="_blank" rel="noopener" '
    'data-track-click="cta_karte_top">無料で実家カルテを申し込む</a>'
    '<a class="karte-lead-tel" href="' + TEL_HREF + '" data-track-click="tel_tap">'
    '<span aria-hidden="true">📞</span>電話 ' + TEL_NUM + "</a>"
    "</div>"
    "</section>"
)

BANNER = (
    '<section class="karte-cta">'
    "<h2>磐田の実家・空き家、どうするかまだ決めていなくても大丈夫です</h2>"
    "<p>住所をもとに、道路・境界・登記・農地など、次に確認する順番を宅地建物取引士（大石浩之）が整理します。"
    "作成料0円・入力約1分。" + ASSURANCE + "</p>"
    '<div class="karte-cta-actions">'
    '<a class="karte-cta-btn" href="' + KARTE_URL + '" target="_blank" rel="noopener" data-track-click="cta_karte">無料で実家カルテを申し込む</a>'
    '<a class="karte-cta-sub" href="https://fudosan.atawi.link/karte/sample/" target="_blank" rel="noopener">カルテの見本を見る</a>'
    "</div>"
    '<p class="karte-cta-tel">お電話でも受け付けます　'
    '<a href="' + TEL_HREF + '" data-track-click="tel_tap">' + TEL_NUM + "</a>（" + TEL_HOURS + "）</p>"
    '<p class="mini">※このご案内は、本サイト運営会社（富士ヶ丘サービス株式会社）の民間サービスです。'
    "ご利用は任意で、磐田市の制度利用には影響しません。磐田市役所とは関係ありません。</p>"
    "</section>"
)

# モバイル追従バー。spacerはfixed分の高さを確保し、フッター末尾が隠れるのを防ぐ。
BAR = (
    '<div class="karte-bar-space" aria-hidden="true"></div>'
    '<div class="karte-bar">'
    '<a class="karte-bar-btn" href="' + KARTE_URL + '" target="_blank" rel="noopener" '
    'data-track-click="cta_karte_bar">無料で実家カルテを申し込む</a>'
    '<a class="karte-bar-tel" href="' + TEL_HREF + '" data-track-click="tel_tap" aria-label="電話 ' + TEL_NUM + '">'
    '<span aria-hidden="true">📞</span><span class="karte-bar-tel-label">電話</span></a>'
    "</div>"
)


def build(fragment, slug, placement):
    content = slug if placement == "" else slug + "_" + placement
    return fragment.replace("{slug}", content)


def inject_top(html, slug):
    """ヒーロー直下（h1と同じ画面内）へ軽量CTAを置く。"""
    base = TOP_RE.sub("", html, count=1) if TOP_RE.search(html) else html
    hero = base.find('<div class="hero-body">')
    if hero == -1:
        return None
    close = base.find("</section>", hero)
    if close == -1:
        return None
    at = close + len("</section>")
    block = TOP_START + build(TOP_BANNER, slug, "top") + TOP_END
    return base[:at] + block + base[at:]


def inject_bottom(html, slug):
    """フッター直上へ強CTA＋追従バーを置く。"""
    base = CTA_RE.sub("", html, count=1) if CTA_RE.search(html) else html
    m = re.search(r"</main>", base)
    if not m:
        return None
    at = base.rfind("</div>", 0, m.start())
    if at == -1:
        return None
    block = CTA_START + build(BANNER, slug, "") + build(BAR, slug, "bar") + CTA_END
    return base[:at] + block + base[at:]


def main():
    changed, skipped = [], []
    for rel, slug in TARGETS:
        path = os.path.join(ROOT, rel, "index.html")
        if not os.path.exists(path):
            skipped.append(rel + "(ファイル無し)")
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()

        new_html = inject_top(html, slug)
        if new_html is None:
            skipped.append(rel + "(hero挿入位置無し)")
            new_html = html
        after = inject_bottom(new_html, slug)
        if after is None:
            skipped.append(rel + "(</main>挿入位置無し)")
        else:
            new_html = after

        if new_html != html:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_html)
            changed.append(rel)

    print("更新 %d ファイル / 対象 %d ページ" % (len(changed), len(TARGETS)))
    for rel in changed:
        print("  " + rel)
    if skipped:
        print("スキップ:", skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
