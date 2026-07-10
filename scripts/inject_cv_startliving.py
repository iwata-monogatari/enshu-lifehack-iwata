#!/usr/bin/env python3
"""start-livingカテゴリ全ページ(住民票・転入等)に介護/不動産のCV導線を注入する。

30日PV92(トップ)・PV18(住民票を今すぐ取得)に対し相談導線からの相談が0件だったため、
運営判断で追加する(既存の横展開仕様書の「証明書ページには前面導線を出さない」方針を
このカテゴリに限り上書きする)。既存のhousingページと同じ.company-strip構造を再利用する。

<!-- CV-BANNER:START/END --> マーカーでfeedback-box直前へ冪等注入する。

使い方: python3 scripts/inject_cv_startliving.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_GLOB = os.path.join(ROOT, "life", "start-living", "*", "index.html")

START = "<!-- CV-BANNER:START -->"
END = "<!-- CV-BANNER:END -->"
MARKER_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)

BANNER = (
    '<section class="company-strip">'
    '<h2 class="sec" style="margin-top:0">住まい・介護のご相談も承っています</h2>'
    '<p class="mini">手続きのついでに、実家の空き家や親の介護のことで迷っていることがあれば、あわせて相談できます。</p>'
    '<div class="company-grid">'
    '<div class="card"><h3>富士ヶ丘サービス（不動産）</h3><p class="mini">空き家・実家の売却や整理を地域密着で相談できます。</p>'
    '<a class="official-link" href="https://www.fujigaoka-service.co.jp/" target="_blank" rel="noopener">不動産の相談先を見る <span>会社</span></a></div>'
    '<div class="card"><h3>富士ヶ丘サービス（介護）</h3><p class="mini">高齢者向け住宅や親の住まいを介護の視点から相談できます。</p>'
    '<a class="official-link" href="https://www.fujigaoka-service.info/" target="_blank" rel="noopener">介護の相談先を見る <span>会社</span></a></div>'
    "</div></section>"
)


def main():
    changed = []
    skipped = []
    for path in sorted(glob.glob(TARGET_GLOB)):
        with open(path, encoding="utf-8") as f:
            html = f.read()

        marker_block = START + BANNER + END

        if MARKER_RE.search(html):
            new_html = MARKER_RE.sub(lambda m: marker_block, html, count=1)
        elif "company-strip" in html:
            # 既存の(マーカー無し)company-stripが手作りで既にあるページは二重掲載を避けスキップ
            skipped.append(os.path.relpath(path, ROOT) + "(既存company-strip有)")
            continue
        else:
            m = re.search(r'<section class="feedback-box"', html)
            if not m:
                skipped.append(os.path.relpath(path, ROOT))
                continue
            new_html = html[: m.start()] + marker_block + html[m.start():]

        if new_html != html:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_html)
            changed.append(os.path.relpath(path, ROOT))

    print("更新 %d ファイル" % len(changed))
    if skipped:
        print("feedback-box未検出でスキップ:", skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
