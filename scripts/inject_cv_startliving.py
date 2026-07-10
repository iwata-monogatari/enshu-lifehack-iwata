#!/usr/bin/env python3
"""start-livingカテゴリ全ページ(住民票・転入等)に介護/不動産のCV導線を注入する。

30日PV92(トップ)・PV18(住民票を今すぐ取得)に対し相談導線からの相談が0件だったため、
運営判断で追加する(既存の横展開仕様書の「証明書ページには前面導線を出さない」方針を
このカテゴリに限り上書きする)。トップページ(index.html)の.company-strip文言・構造を
再利用し、表記を統一する。

<!-- CV-BANNER:START/END --> マーカーで</main>直前(フッター直上)へ冪等注入する。

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
    "<h2>住まい・空き家のご相談窓口</h2>"
    "<p>相続した実家や空き家、親の住まいのことで迷ったら、公式の制度確認とあわせて専門の相談窓口も活用できます。</p>"
    '<div class="company-grid">'
    '<div class="company-card"><h3>富士ヶ丘サービス（不動産）</h3><p>空き家や相続した実家の売却・整理を、地域密着で相談できます。</p>'
    '<a class="btn btn-main" href="https://www.fujigaoka-service.co.jp/" target="_blank" rel="noopener">不動産ページを見る</a></div>'
    '<div class="company-card"><h3>富士ヶ丘サービス（介護）</h3><p>高齢者向け住宅や親の住まいのことを、介護の視点から相談できます。</p>'
    '<a class="btn btn-main" href="https://www.fujigaoka-service.info/" target="_blank" rel="noopener">介護ページを見る</a></div>'
    '<div class="company-card"><h3>公式情報</h3><p>制度の詳細や申請の可否は、必ず磐田市公式ページまたは担当窓口でご確認ください。</p>'
    '<a class="btn btn-main" href="https://www.city.iwata.shizuoka.jp/" target="_blank" rel="noopener">磐田市公式サイトを見る</a></div>'
    "</div></section>"
)


def main():
    changed = []
    skipped = []
    for path in sorted(glob.glob(TARGET_GLOB)):
        with open(path, encoding="utf-8") as f:
            html = f.read()

        marker_block = START + BANNER + END

        # 既存マーカーがあれば一旦除去し、</main>直前へ再配置する(内容更新+位置移動の両対応)
        base_html = MARKER_RE.sub("", html, count=1) if MARKER_RE.search(html) else html

        if "company-strip" in base_html:
            # 既存の(マーカー無し)company-stripが手作りで既にあるページは二重掲載を避けスキップ
            skipped.append(os.path.relpath(path, ROOT) + "(既存company-strip有)")
            continue

        m = re.search(r"</main>", base_html)
        if not m:
            skipped.append(os.path.relpath(path, ROOT))
            continue
        insert_at = base_html.rfind("</div>", 0, m.start())
        if insert_at == -1:
            skipped.append(os.path.relpath(path, ROOT))
            continue
        new_html = base_html[:insert_at] + marker_block + base_html[insert_at:]

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
