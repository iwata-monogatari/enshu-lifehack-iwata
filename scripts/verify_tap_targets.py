#!/usr/bin/env python3
"""Phase 4: 全ページのアンカー/ボタン要素のタップ領域(44x44px以上)をheadless Chromeで機械検証する。

Playwrightでローカルの静的ファイルを直接file://で開き、モバイル幅(375px)で
可視のa/button要素のboundingClientRectを計測する。非表示要素・0x0要素は除外。
44px未満が見つかったページ・要素を一覧化し、レポートを出力する。

使い方: python3 scripts/verify_tap_targets.py [--sample N]
"""
import argparse
import glob
import http.server
import json
import os
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = ("parts", "tmp", "output", "scratchpad", "node_modules", ".git", ".wrangler", "docs", "reports", "src")
MIN_SIZE = 44

CHECK_JS = """
() => {
  const els = Array.from(document.querySelectorAll('a[href], button'));
  const results = [];
  for (const el of els) {
    if (el.classList.contains('skip-link')) continue;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    if (rect.right < 0 || rect.bottom < 0) continue;
    if (rect.height < %d || rect.width < %d) {
      results.push({
        tag: el.tagName.toLowerCase(),
        text: (el.textContent || '').trim().slice(0, 40),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });
    }
  }
  return results;
}
""" % (MIN_SIZE, MIN_SIZE)


def collect_pages(sample):
    paths = []
    for path in sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if rel.split("/")[0] in EXCLUDE_DIRS:
            continue
        paths.append(path)
    if sample:
        paths = paths[:sample]
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="先頭N件のみ検証(0で全件)")
    args = parser.parse_args()

    pages = collect_pages(args.sample)
    print("検証対象 %d ページ" % len(pages))

    # 絶対パス(/assets/...)を正しく解決するため、ROOTを配信するHTTPサーバーを起動する
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=ROOT, **kw)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    issues = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 375, "height": 812})
            for i, path in enumerate(pages, 1):
                rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
                url = "http://127.0.0.1:%d/%s" % (port, rel)
                try:
                    page.goto(url, wait_until="load", timeout=15000)
                    found = page.evaluate(CHECK_JS)
                except Exception as e:
                    found = [{"tag": "ERROR", "text": str(e)[:80], "width": 0, "height": 0}]
                if found:
                    issues[rel] = found
                if i % 25 == 0:
                    print("  ... %d/%d" % (i, len(pages)))
            browser.close()
    finally:
        httpd.shutdown()

    os.makedirs(os.path.join(ROOT, "_audit"), exist_ok=True)
    report_path = os.path.join(ROOT, "_audit", "tap-target-report.md")
    lines = ["# タップ領域検証レポート (44x44px未満)", ""]
    total_issues = sum(len(v) for v in issues.values())
    lines.append("検証ページ数: %d / 問題あり: %d ページ / 要素数: %d" % (len(pages), len(issues), total_issues))
    lines.append("")
    for rel, found in sorted(issues.items()):
        lines.append("## %s" % rel)
        for f in found:
            lines.append("- <%s> %dx%d px: %s" % (f["tag"], f["width"], f["height"], f["text"]))
        lines.append("")
    if not issues:
        lines.append("問題なし。全ページで44x44px以上を確保。")

    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("問題ページ数: %d / 要素数: %d" % (len(issues), total_issues))
    print("レポート出力:", os.path.relpath(report_path, ROOT))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
