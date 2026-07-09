#!/usr/bin/env python3
"""K-04: categories.json の faq から schema.org/FAQPage JSON-LD を生成し<head>へ注入する。

各ページのURL(categories.json の item.url)からファイルパスを特定し、
</head> 直前に
  <!-- FAQ-JSONLD:START -->...<!-- FAQ-JSONLD:END -->
を挿入(初回のみ)、以後は間の中身をfaqに応じて再生成する(冪等)。
faqが空の項目は対象外(マーカーも挿入しない)。

使い方: python3 scripts/inject_faq_jsonld.py
"""
import glob
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")

START = "<!-- FAQ-JSONLD:START -->"
END = "<!-- FAQ-JSONLD:END -->"

MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def build_jsonld(faq):
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in faq
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


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
    skipped_no_head = []
    skipped_no_faq = []

    for cat in root["categories"]:
        for item in cat["items"]:
            faq = item.get("faq", [])
            filepath = url_to_path(item["url"])
            if not os.path.isfile(filepath):
                missing.append(item["url"])
                continue
            if not faq:
                skipped_no_faq.append(item["url"])
                continue

            with open(filepath, encoding="utf-8") as f:
                html = f.read()

            script_html = '<script type="application/ld+json">%s</script>' % build_jsonld(faq)
            marker_block = START + script_html + END

            if MARKER_RE.search(html):
                new_html = MARKER_RE.sub(lambda m: marker_block, html, count=1)
            else:
                idx = html.find("</head>")
                if idx == -1:
                    skipped_no_head.append(item["url"])
                    continue
                new_html = html[:idx] + marker_block + html[idx:]

            if new_html != html:
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(new_html)
                changed.append(os.path.relpath(filepath, ROOT))

    print("更新 %d ファイル" % len(changed))
    if missing:
        print("ファイル未検出 %d 件:" % len(missing), missing)
    if skipped_no_head:
        print("</head>未検出でスキップ %d 件:" % len(skipped_no_head), skipped_no_head)
    if skipped_no_faq:
        print("faq空でスキップ %d 件" % len(skipped_no_faq))
    return 1 if (missing or skipped_no_head) else 0


if __name__ == "__main__":
    sys.exit(main())
