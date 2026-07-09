#!/usr/bin/env python3
"""K-07: LINEシェア＋URLコピーのシェアボックスをfeedback-boxの直後へ注入する。

プリセット文は「磐田市の<ページ名>、ここ見ると早いよ」(友人・パートナー向けの温度感)。
<!-- SHARE-BOX:START/END --> マーカーで冪等に管理する。

使い方: python3 scripts/inject_share_box.py
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

START = "<!-- SHARE-BOX:START -->"
END = "<!-- SHARE-BOX:END -->"
MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
FEEDBACK_END = '</section>'


def url_to_path(url):
    path = urllib.parse.urlparse(url).path
    if not path.endswith("/"):
        path += "/"
    return os.path.join(ROOT, path.strip("/"), "index.html")


def build_share_box(label, page_url):
    line_text = "磐田市の%sについて、ここ見ると早いよ" % label
    line_href = "https://social-plugins.line.me/lineit/share?url=%s&text=%s" % (
        urllib.parse.quote(page_url, safe=""),
        urllib.parse.quote(line_text, safe=""),
    )
    esc_url = html.escape(page_url, quote=True)
    return (
        '<section class="share-box" aria-label="このページをシェア">'
        '<h2 class="sec" style="margin-top:0">友人・家族に送る</h2>'
        '<div class="share-actions">'
        '<a class="share-btn share-line" href="%s" target="_blank" rel="noopener">LINEで送る</a>'
        '<button type="button" class="share-btn share-copy" data-share-url="%s">リンクをコピー</button>'
        "</div>"
        '<p class="share-copied" hidden>コピーしました</p>'
        "</section>"
        "<script>(function(){"
        "var box=document.currentScript.previousElementSibling;"
        "var btn=box&&box.querySelector('.share-copy');"
        "if(!btn){return;}"
        "btn.addEventListener('click',function(){"
        "var url=btn.getAttribute('data-share-url');"
        "var done=function(){var msg=box.querySelector('.share-copied');if(msg){msg.hidden=false;setTimeout(function(){msg.hidden=true;},2500);}};"
        "var fallback=function(){var ta=document.createElement('textarea');ta.value=url;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);done();};"
        "if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(url).then(done).catch(fallback);}"
        "else{fallback();}"
        "});"
        "})();</script>"
    ) % (line_href, esc_url)


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

            block = START + build_share_box(item["label"], item["url"]) + END

            if MARKER_RE.search(html_src):
                new_html = MARKER_RE.sub(lambda m: block, html_src, count=1)
            else:
                m = re.search(r'<section class="feedback-box"[^>]*>.*?</section>', html_src, re.S)
                if not m:
                    skipped.append(item["url"])
                    continue
                insert_at = m.end()
                new_html = html_src[:insert_at] + block + html_src[insert_at:]

            if new_html != html_src:
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(new_html)
                changed.append(os.path.relpath(filepath, ROOT))

    print("更新 %d ファイル" % len(changed))
    if missing:
        print("ファイル未検出 %d 件:" % len(missing), missing)
    if skipped:
        print("feedback-box未検出でスキップ %d 件:" % len(skipped), skipped)
    return 1 if (missing or skipped) else 0


if __name__ == "__main__":
    sys.exit(main())
