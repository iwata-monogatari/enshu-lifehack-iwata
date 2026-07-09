#!/usr/bin/env python3
"""K-02(軽量版): categories.json の channels から hero直下にバッジを注入する。

各ページのURL(categories.json の item.url)からファイルパスを特定し、
<h1>...</h1> の直後(hero-visual内)に
  <!-- CHANNEL-BADGES:START -->...<!-- CHANNEL-BADGES:END -->
を挿入(初回のみ)、以後は間の中身をchannelsに応じて再生成する(冪等)。
channelsが空配列の項目はバッジなし(マーカーのみ残し空にする)。

使い方: python3 scripts/inject_channel_badges.py
"""
import glob
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")

LABELS = {
    "online": ("&#x1F310;", "オンライン可"),
    "konbini": ("&#x1F3EA;", "コンビニ可"),
    "counter": ("&#x1F3DB;", "窓口"),
    "phone": ("&#x1F4DE;", "電話で完結"),
}
ORDER = ["online", "konbini", "counter", "phone"]

START = "<!-- CHANNEL-BADGES:START -->"
END = "<!-- CHANNEL-BADGES:END -->"

H1_RE = re.compile(r"(<h1[^>]*>.*?</h1>)", re.S)
MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def build_badges_html(channels):
    if not channels:
        return ""
    parts = []
    for ch in ORDER:
        if ch in channels:
            emoji, label = LABELS[ch]
            parts.append(
                '<span class="channel-badge"><span class="emoji" aria-hidden="true">%s</span>%s</span>'
                % (emoji, label)
            )
    if not parts:
        return ""
    return '<div class="channel-badges">%s</div>' % "".join(parts)


def url_to_path(url):
    path = urllib.parse.urlparse(url).path
    if not path.endswith("/"):
        path += "/"
    return os.path.join(ROOT, path.strip("/"), "index.html")


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    changed = []
    missing = []
    skipped_no_h1 = []

    for cat in root["categories"]:
        for item in cat["items"]:
            channels = item.get("channels", [])
            filepath = url_to_path(item["url"])
            if not os.path.isfile(filepath):
                missing.append(item["url"])
                continue

            with open(filepath, encoding="utf-8") as f:
                html = f.read()

            badges_html = build_badges_html(channels)
            marker_block = START + badges_html + END

            if MARKER_RE.search(html):
                new_html = MARKER_RE.sub(lambda m: marker_block, html, count=1)
            else:
                m = H1_RE.search(html)
                if not m:
                    skipped_no_h1.append(item["url"])
                    continue
                insertion = m.group(1) + marker_block
                new_html = html[: m.start()] + insertion + html[m.end():]

            if new_html != html:
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(new_html)
                changed.append(os.path.relpath(filepath, ROOT))

    print("更新 %d ファイル" % len(changed))
    if missing:
        print("ファイル未検出 %d 件:" % len(missing), missing)
    if skipped_no_h1:
        print("h1未検出でスキップ %d 件:" % len(skipped_no_h1), skipped_no_h1)
    return 1 if (missing or skipped_no_h1) else 0


if __name__ == "__main__":
    sys.exit(main())
