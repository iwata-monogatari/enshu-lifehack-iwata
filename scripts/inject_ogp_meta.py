#!/usr/bin/env python3
"""K-07: OGP(og:title/description/image)とTwitter Cardメタタグを<head>へ注入する。

既存の<title>先頭セグメントと<meta name="description">の内容を流用し、
og:imageは assets/ogp/<category>/<id>.png (要 generate_ogp_images.py 実行済み) を指す。
<!-- OGP-META:START/END --> マーカーで冪等に管理する。

使い方: python3 scripts/inject_ogp_meta.py
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
SITE_ORIGIN = "https://iwata.enshu-lifehack.com"

START = "<!-- OGP-META:START -->"
END = "<!-- OGP-META:END -->"
MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def url_to_path(url):
    path = urllib.parse.urlparse(url).path
    if not path.endswith("/"):
        path += "/"
    return os.path.join(ROOT, path.strip("/"), "index.html")


def build_meta(title, desc, image_url, page_url):
    esc_title = html.escape(title, quote=True)
    esc_desc = html.escape(desc, quote=True)
    tags = [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="磐田ライフハック">',
        '<meta property="og:title" content="%s">' % esc_title,
        '<meta property="og:description" content="%s">' % esc_desc,
        '<meta property="og:url" content="%s">' % page_url,
        '<meta property="og:image" content="%s">' % image_url,
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % esc_title,
        '<meta name="twitter:description" content="%s">' % esc_desc,
        '<meta name="twitter:image" content="%s">' % image_url,
    ]
    return "".join(tags)


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    changed = []
    missing = []
    skipped = []

    for cat in root["categories"]:
        for item in cat["items"]:
            filepath = url_to_path(item["url"])
            if not os.path.isfile(filepath):
                missing.append(item["url"])
                continue

            with open(filepath, encoding="utf-8") as f:
                html_src = f.read()

            title_m = re.search(r"<title>(.*?)\s*\|", html_src)
            title = title_m.group(1).strip() if title_m else item["label"]
            desc_m = re.search(r'<meta name="description" content="(.*?)">', html_src)
            if not desc_m:
                skipped.append(item["url"])
                continue
            desc = html.unescape(desc_m.group(1))

            image_url = "%s/assets/ogp/%s/%s.png" % (SITE_ORIGIN, cat["id"], item["id"])
            meta_block = START + build_meta(title, desc, image_url, item["url"]) + END

            if MARKER_RE.search(html_src):
                new_html = MARKER_RE.sub(lambda m: meta_block, html_src, count=1)
            else:
                idx = html_src.find("<link rel=\"icon\"")
                if idx == -1:
                    skipped.append(item["url"])
                    continue
                new_html = html_src[:idx] + meta_block + html_src[idx:]

            if new_html != html_src:
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(new_html)
                changed.append(os.path.relpath(filepath, ROOT))

    print("更新 %d ファイル" % len(changed))
    if missing:
        print("ファイル未検出 %d 件:" % len(missing), missing)
    if skipped:
        print("description未検出等でスキップ %d 件:" % len(skipped), skipped)
    return 1 if (missing or skipped) else 0


if __name__ == "__main__":
    sys.exit(main())
