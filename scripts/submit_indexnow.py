#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
submit_indexnow.py — sitemap.xml の全URLを IndexNow に一括送信する

Bing / Yandex 系のクローラへ「このURLがある」と直接通知するための discovery 経路。
Google のサイトマップ再送信とは別系統なので、両方を回しても重複しない。

前提: https://iwata.enshu-lifehack.com/<KEY>.txt が 200 で、本文がキー文字列と一致すること
      （キーファイルはリポジトリ直下に置いてある）。

使い方: python scripts/submit_indexnow.py [--dry-run] [--batch 100]
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://iwata.enshu-lifehack.com"
INDEXNOW_KEY = "9aacdc8ce3b94cb9ba20a4b29fe99f59"

ENDPOINT = "https://api.indexnow.org/indexnow"
HOST = urlparse(SITE_URL).netloc
KEY_LOCATION = f"{SITE_URL}/{INDEXNOW_KEY}.txt"


def read_sitemap_urls():
    xml = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    # 同一ホストのURLのみ送れる（IndexNow の仕様）
    return [u for u in urls if urlparse(u).netloc == HOST]


def post(url_list):
    payload = json.dumps({
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": url_list,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=payload, method="POST", headers={
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "iwata-lifehack-indexnow/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, res.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=100, help="1リクエストあたりのURL数（仕様上の上限は10,000）")
    ap.add_argument("--dry-run", action="store_true", help="送信せずに件数だけ出す")
    a = ap.parse_args()

    urls = read_sitemap_urls()
    if not urls:
        print("FAIL: sitemap.xml から URL を読めなかった")
        sys.exit(1)
    print(f"host: {HOST}")
    print(f"keyLocation: {KEY_LOCATION}")
    print(f"urls: {len(urls)}")
    if a.dry_run:
        print("dry-run: 送信しない")
        return

    batches = [urls[i:i + a.batch] for i in range(0, len(urls), a.batch)]
    ng = 0
    for i, b in enumerate(batches, 1):
        status, body = post(b)
        ok = status in (200, 202)
        if not ok:
            ng += 1
        print(f"batch {i}/{len(batches)} ({len(b)} urls) -> {status} {'OK' if ok else 'NG'} {body}".rstrip())
    if ng:
        print(f"FAIL: {ng}/{len(batches)} バッチが 200/202 以外（403 ならキーファイルの配信を確認する）")
        sys.exit(1)
    print(f"indexnow: OK ({len(urls)} urls / {len(batches)} batches)")


if __name__ == "__main__":
    main()
