#!/usr/bin/env python3
"""売却予備軍10ページに磐田独自の実家カルテ強CTAを注入する。

対象は企画書v3.0 §3-4の10ページ(end-of-life 5・housing 3・parents-care 1・
troubles-consult 1)。転入者向け15ページの旧CVバナーが相談0件だった運営記録を
踏まえ、売る側の文脈のページに強い導線を置く。緊急・医療・生活困窮ページには
配置しない。

<!-- KARTE-CTA:START/END --> マーカーで</main>直前(フッター直上)へ冪等注入する。
配色は公的情報のブルー系と区別するためアンバー系(.karte-cta、site.cssに定義)。

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
]

START = "<!-- KARTE-CTA:START -->"
END = "<!-- KARTE-CTA:END -->"
MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)

KARTE_URL = (
    "https://fudosan.atawi.link/karte/?area=磐田市"
    "&amp;utm_source=iwata_lifehack&amp;utm_medium=referral"
    "&amp;utm_campaign=iwata_karte&amp;utm_content={slug}#apply"
)

BANNER = (
    '<section class="karte-cta">'
    "<h2>磐田の実家・空き家、どうするかまだ決めていなくても大丈夫です</h2>"
    "<p>住所をもとに、道路・境界・登記・農地など、次に確認する順番を宅地建物取引士（大石浩之）が整理します。"
    "作成料0円・入力約1分。申込みだけで売却依頼にはなりません。</p>"
    '<div class="karte-cta-actions">'
    '<a class="karte-cta-btn" href="' + KARTE_URL + '" target="_blank" rel="noopener" data-track-click="cta_karte">無料で実家カルテを申し込む</a>'
    '<a class="karte-cta-sub" href="https://fudosan.atawi.link/karte/sample/" target="_blank" rel="noopener">カルテの見本を見る</a>'
    "</div>"
    '<p class="mini">※このご案内は、本サイト運営会社（富士ヶ丘サービス株式会社）の民間サービスです。'
    "ご利用は任意で、磐田市の制度利用には影響しません。磐田市役所とは関係ありません。</p>"
    "</section>"
)


def main():
    changed = []
    skipped = []
    for rel, slug in TARGETS:
        path = os.path.join(ROOT, rel, "index.html")
        if not os.path.exists(path):
            skipped.append(rel + "(ファイル無し)")
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()

        marker_block = START + BANNER.replace("{slug}", slug) + END

        # 既存マーカーがあれば一旦除去し、</main>直前へ再配置する(内容更新+位置移動の両対応)
        base_html = MARKER_RE.sub("", html, count=1) if MARKER_RE.search(html) else html

        m = re.search(r"</main>", base_html)
        if not m:
            skipped.append(rel + "(</main>無し)")
            continue
        insert_at = base_html.rfind("</div>", 0, m.start())
        if insert_at == -1:
            skipped.append(rel + "(挿入位置無し)")
            continue
        new_html = base_html[:insert_at] + marker_block + base_html[insert_at:]

        if new_html != html:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_html)
            changed.append(rel)

    print("更新 %d ファイル" % len(changed))
    if skipped:
        print("スキップ:", skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
