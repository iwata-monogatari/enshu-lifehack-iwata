#!/usr/bin/env python3
"""K-09: tel:リンクにdata-track-click属性を付与し、計測対象にする。

既存のトラッカー(assets経由でfooterに全ページ注入済み)は
[data-track-click]要素のクリックを自動収集するため、属性を足すだけでよい。
既に付与済みの場合はスキップ(冪等)。

使い方: python3 scripts/inject_tel_tracking.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = ("parts", "tmp", "output", "scratchpad", "node_modules", ".git", ".wrangler", "docs", "reports", "assets")

TEL_RE = re.compile(r'(<a\s+[^>]*href="tel:[^"]+"[^>]*>)')


def add_track_attr(tag):
    if "data-track-click" in tag:
        return tag
    return tag[:-1] + ' data-track-click="tel_tap">'


def main():
    changed = []
    for path in sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if rel.split("/")[0] in EXCLUDE_DIRS:
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()
        new_html = TEL_RE.sub(lambda m: add_track_attr(m.group(1)), html)
        if new_html != html:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_html)
            changed.append(rel)

    print("更新 %d ファイル" % len(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
