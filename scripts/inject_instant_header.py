#!/usr/bin/env python3
"""Phase 3: 即答ヘッダー(所要時間/オンライン可否/窓口情報)をh1直後へ注入する。

categories.jsonのonline_status/online_note/time_estimate/counter_info
(いずれもderive_instant_header_fields.pyでK-01検証済みconclusionから導出済み)を使う。
<!-- INSTANT-HEADER:START/END --> マーカーで冪等管理し、K-02のCHANNEL-BADGESの直後に置く。
表示する情報が1つも無い項目は注入しない(推測での埋め合わせをしない)。

使い方: python3 scripts/inject_instant_header.py
"""
import glob
import html
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")

START = "<!-- INSTANT-HEADER:START -->"
END = "<!-- INSTANT-HEADER:END -->"
MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
BADGES_END = "<!-- CHANNEL-BADGES:END -->"

STATUS_LABEL = {
    "yes": ("オンライン申請：できます", "ih-yes"),
    "partial": ("オンライン申請：一部可能（コンビニ等）", "ih-partial"),
    "no": ("オンライン申請：窓口のみ", "ih-no"),
}


def url_to_path(url):
    path = urllib.parse.urlparse(url).path
    if not path.endswith("/"):
        path += "/"
    return os.path.join(ROOT, path.strip("/"), "index.html")


def build_box(item):
    rows = []
    if item.get("time_estimate") and item["time_estimate"] != "n/a":
        rows.append(
            '<div class="ih-row"><span class="ih-icon" aria-hidden="true">⏱</span>所要時間の目安：%s</div>'
            % html.escape(item["time_estimate"])
        )

    status = item.get("online_status")
    if status in STATUS_LABEL:
        label, cls = STATUS_LABEL[status]
        note = item.get("online_note")
        text = label + (("　" + html.escape(note)) if note else "")
        rows.append(
            '<div class="ih-row %s"><span class="ih-icon" aria-hidden="true">📱</span>%s</div>' % (cls, text)
        )

    if item.get("counter_info"):
        rows.append(
            '<div class="ih-row"><span class="ih-icon" aria-hidden="true">📍</span>窓口：%s</div>'
            % html.escape(item["counter_info"])
        )

    if not rows:
        return None
    return '<div class="instant-header">%s</div>' % "".join(rows)


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    changed = []
    missing = []
    skipped_no_anchor = []
    skipped_empty = []

    for cat in root["categories"]:
        for item in cat["items"]:
            filepath = url_to_path(item["url"])
            if not os.path.isfile(filepath):
                missing.append(item["url"])
                continue

            box_html = build_box(item)
            if box_html is None:
                skipped_empty.append(item["url"])
                continue

            with open(filepath, encoding="utf-8") as f:
                html_src = f.read()

            marker_block = START + box_html + END

            if MARKER_RE.search(html_src):
                new_html = MARKER_RE.sub(lambda m: marker_block, html_src, count=1)
            else:
                idx = html_src.find(BADGES_END)
                if idx == -1:
                    skipped_no_anchor.append(item["url"])
                    continue
                insert_at = idx + len(BADGES_END)
                new_html = html_src[:insert_at] + marker_block + html_src[insert_at:]

            if new_html != html_src:
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(new_html)
                changed.append(os.path.relpath(filepath, ROOT))

    print("更新 %d ファイル" % len(changed))
    print("情報なしでスキップ %d 件" % len(skipped_empty))
    if missing:
        print("ファイル未検出:", missing)
    if skipped_no_anchor:
        print("CHANNEL-BADGES未検出でスキップ:", skipped_no_anchor)
    return 1 if (missing or skipped_no_anchor) else 0


if __name__ == "__main__":
    sys.exit(main())
