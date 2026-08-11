#!/usr/bin/env python3
"""売却系ページの不動産導線を実家カルテへ一本化し、UTMとタイトルを整える。

2026-08-11の導線監査で判明した3点を機械的に直す。

1. 本文の「売却相談」「相談先を見る」等が www.fujigaoka-service.co.jp（会社トップ）
   へ飛んでいた。カルテCTAより手前にあり、UTMも無く計測できず、着地先の
   ファーストビューが仕入れ寄りで読者の温度と合わない。本文リンクはカルテへ
   差し替え、会社トップはフッターの会社紹介として残す。
   ※管理フッター（managed-footer）と PART:footer 内は対象外。

2. カルテURLのUTMが2系統に割れていた。
   iwata_lifehack/iwata_karte（utm_contentあり）と
   enshu_lifehack_iwata/karte_context（utm_contentなし）。
   後者は流入元ページを判別できないため、前者へ統一する。

3. <title>先頭セグメントに市名が無く、「磐田市 家を売る」等のローカル検索で
   不利だった。売却系14ページのみ市名を入れる（og/twitterは
   inject_ogp_meta.py が<title>から再生成するので本スクリプトでは触らない）。

冪等。実行後に scripts/inject_ogp_meta.py と scripts/build-search-index.mjs を回すこと。

使い方: python3 scripts/normalize_karte_links_iwata.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KARTE_BASE = (
    "https://fudosan.atawi.link/karte/?area=磐田市"
    "&amp;utm_source=iwata_lifehack&amp;utm_medium=referral"
    "&amp;utm_campaign=iwata_karte&amp;utm_content=%s"
)

CORP_URL = "https://www.fujigaoka-service.co.jp/"

# 本文リンクをカルテへ差し替える対象（rel: utm_content slug）
INLINE_TARGETS = {
    "life/end-of-life/house-became-vacant": "house_became_vacant",
    "life/end-of-life/inherited-house": "inherited_house",
    "life/end-of-life/inherited-vacant-house": "inherited_vacant_house",
    "life/end-of-life/inheritance": "inheritance",
    "life/end-of-life/property-tax-inheritance": "property_tax_inheritance",
    "life/housing/sell-house": "sell_house",
    "life/housing/vacant-house": "vacant_house",
    "life/housing/clean-parents-house": "clean_parents_house",
    "life/parents-care/find-nursing-home": "find_nursing_home",
    "life/troubles-consult/vacant-house-consultation": "vacant_house_consultation",
    "life/housing/property-tax": "property_tax",
    "life/housing/earthquake-demolition": "earthquake_demolition",
    "life/troubles-consult/farmland": "farmland",
    "life/moving-out/moving-away": "moving_away",
}

# 旧UTM(karte_context)を持つページ（rel: utm_content slug）
CONTEXT_TARGETS = {
    "life/housing/index.html": "housing_hub_ctx",
    "life/parents-care/index.html": "parents_care_hub_ctx",
    "life/housing/vacant-house/index.html": "vacant_house_ctx",
    "life/housing/clean-parents-house/index.html": "clean_parents_house_ctx",
    "life/troubles-consult/vacant-house-consultation/index.html": "vacant_house_consultation_ctx",
}

OLD_CONTEXT_RE = re.compile(
    r"https://fudosan\.atawi\.link/karte/\?utm_source=enshu_lifehack_iwata"
    r"(?:&amp;|&)utm_medium=referral(?:&amp;|&)utm_campaign=karte_context"
)

# <title>先頭セグメントの置換（旧 -> 新）。moving-awayは既に市名を含むため対象外。
TITLE_HEADS = {
    "life/end-of-life/house-became-vacant": ("空き家になった（相続後）", "磐田市で空き家になった実家（相続後）"),
    "life/end-of-life/inherited-house": ("親の家をどうするか", "磐田市で親の家をどうするか"),
    "life/end-of-life/inherited-vacant-house": ("空き家・実家じまい・相続した家", "磐田市の空き家・実家じまい・相続した家"),
    "life/end-of-life/inheritance": ("相続", "磐田市の相続手続き"),
    "life/end-of-life/property-tax-inheritance": ("固定資産税（相続）", "磐田市の固定資産税（相続後の手続き）"),
    "life/housing/sell-house": ("家を売る", "磐田市で家を売る"),
    "life/housing/vacant-house": ("空き家", "磐田市の空き家"),
    "life/housing/clean-parents-house": ("親の家を片付ける", "磐田市で親の家を片付ける"),
    "life/parents-care/find-nursing-home": (
        "介護施設を探したい（特養・老健・サ高住・グループホーム）",
        "磐田市で介護施設を探したい（特養・老健・サ高住・グループホーム）",
    ),
    "life/troubles-consult/vacant-house-consultation": (
        "空き家の相談（親の家・実家をどうするか）",
        "磐田市の空き家の相談（親の家・実家をどうするか）",
    ),
    "life/housing/property-tax": ("固定資産税・都市計画税", "磐田市の固定資産税・都市計画税"),
    "life/housing/earthquake-demolition": ("耐震・解体を考える", "磐田市で耐震・解体を考える"),
    "life/troubles-consult/farmland": (
        "農地・田畑の困りごと相談（売る・貸す・転用・相続・管理）",
        "磐田市の農地・田畑の困りごと相談（売る・貸す・転用・相続・管理）",
    ),
}

# 市名を2度繰り返さないための第2セグメント調整
TITLE_TAILS = {
    "life/troubles-consult/vacant-house-consultation": (
        "磐田市の空き家バンク・解体補助・固定資産税",
        "空き家バンク・解体補助・固定資産税",
    ),
    "life/troubles-consult/farmland": (
        "磐田市の農業委員会・農地法手続き入口",
        "農業委員会・農地法手続き入口",
    ),
}

CORP_ANCHOR_RE = re.compile(r'<a\b[^>]*href="' + re.escape(CORP_URL) + r'"[^>]*>')


def split_content(html):
    """本文（</main>まで）とそれ以降（フッター類）に分ける。"""
    i = html.find("</main>")
    if i == -1:
        return html, ""
    return html[:i], html[i:]


def swap_corp_anchor(tag, slug):
    tag = tag.replace('href="' + CORP_URL + '"', 'href="' + (KARTE_BASE % (slug + "_inline")) + '#apply"')
    if "data-track-click" not in tag:
        tag = tag[:-1] + ' data-track-click="cta_karte_inline">'
    if "target=" not in tag:
        tag = tag[:-1] + ' target="_blank" rel="noopener">'
    return tag


def process(path, rel_dir, rel_file):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    original = html

    # 1) 本文の会社トップリンク -> カルテ
    slug = INLINE_TARGETS.get(rel_dir)
    if slug:
        head, tail = split_content(html)
        head = CORP_ANCHOR_RE.sub(lambda m: swap_corp_anchor(m.group(0), slug), head)
        html = head + tail

    # 2) 旧UTM -> 統一UTM
    ctx = CONTEXT_TARGETS.get(rel_file)
    if ctx:
        html = OLD_CONTEXT_RE.sub(KARTE_BASE % ctx, html)

    # 3) <title>に市名
    heads = TITLE_HEADS.get(rel_dir)
    if heads:
        old, new = heads
        html = html.replace("<title>%s |" % old, "<title>%s |" % new, 1)
    tails = TITLE_TAILS.get(rel_dir)
    if tails:
        old, new = tails
        html = html.replace("| %s |" % old, "| %s |" % new, 1)

    if html != original:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        return True
    return False


def main():
    rels = set(INLINE_TARGETS) | {os.path.dirname(k) for k in CONTEXT_TARGETS}
    changed = []
    for rel_dir in sorted(rels):
        rel_file = rel_dir + "/index.html"
        path = os.path.join(ROOT, rel_file.replace("/", os.sep))
        if not os.path.exists(path):
            print("ファイル無し:", rel_file, file=sys.stderr)
            continue
        if process(path, rel_dir, rel_file):
            changed.append(rel_file)

    print("更新 %d ファイル" % len(changed))
    for rel in changed:
        print("  " + rel)

    # 検証: 対象ページの本文に会社トップリンクと旧UTMが残っていないこと
    leftovers = []
    for rel_dir in sorted(rels):
        path = os.path.join(ROOT, rel_dir.replace("/", os.sep), "index.html")
        with open(path, encoding="utf-8") as f:
            html = f.read()
        head, _ = split_content(html)
        if rel_dir in INLINE_TARGETS and CORP_URL in head:
            leftovers.append(rel_dir + "(会社トップ残存)")
        if OLD_CONTEXT_RE.search(html):
            leftovers.append(rel_dir + "(旧UTM残存)")
    print("残存チェック:", leftovers if leftovers else "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
