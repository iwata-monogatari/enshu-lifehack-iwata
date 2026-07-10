#!/usr/bin/env python3
"""カテゴリindexページの文字量を減らす2つの修正を一括適用する。

1. procedure-grid内のlink-card見出し(各中項目ページの長いh1文)を、
   categories.jsonの短いlabelに差し替える(一瞥で判断しやすくする)。
2. hero直下の「検索で使われやすい言葉」行(内部SEOメモが誤って表示されていた)を削除する。

使い方: python3 scripts/simplify_category_pages.py
"""
import glob
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")

LINK_CARD_RE = re.compile(
    r'(<a class="link-card" href="([^"]+)"><span class="topic-icon"[^>]*>[^<]*</span>'
    r'<span class="card-text"><span class="card-title">)([^<]+)(</span>)'
)
SEARCH_WORDS_RE = re.compile(r'<p class="[^"]*">検索で使われやすい言葉：[^<]*</p>')


def load_href_to_label():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)
    mapping = {}
    for cat in root["categories"]:
        for item in cat["items"]:
            path = urllib.parse.urlparse(item["url"]).path
            mapping[path] = item["label"]
    return mapping


def main():
    href_to_label = load_href_to_label()

    changed = []
    unmatched = []
    for path in sorted(glob.glob(os.path.join(ROOT, "life", "*", "index.html"))):
        with open(path, encoding="utf-8") as f:
            html = f.read()

        def replace_title(m):
            prefix, href, _old_title, suffix = m.group(1), m.group(2), m.group(3), m.group(4)
            label = href_to_label.get(href)
            if label is None:
                unmatched.append(href)
                return m.group(0)
            return prefix + label + suffix

        new_html = LINK_CARD_RE.sub(replace_title, html)
        new_html = SEARCH_WORDS_RE.sub("", new_html)

        if new_html != html:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_html)
            changed.append(os.path.relpath(path, ROOT))

    print("更新 %d ファイル" % len(changed))
    if unmatched:
        print("categories.jsonに該当labelが見つからなかったhref:", sorted(set(unmatched)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
