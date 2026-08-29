#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
submit_indexnow.py — sitemap.xml の全URLを IndexNow に送信する

Bing / Yandex 系のクローラへ「このURLがある」と直接通知するための discovery 経路。
Google のサイトマップ再送信とは別系統なので、両方を回しても重複しない。

前提: https://iwata.enshu-lifehack.com/<KEY>.txt が 200 で、本文がキー文字列と一致すること
      （キーファイルはリポジトリ直下に置いてある）。

送信方式が2つあるのは、当サイトが一括POSTを受け付けてもらえないため。2026-08-29 時点で
キーファイルが 200 / text/plain / 本文一致で配信できていても、JSON body の一括POSTだけは
api.indexnow.org・www.bing.com のどちらも UserForbiddedToAccessSite で 403 を返す。
一方でクエリ文字列に1URLずつ載せる GET 形式は同じキーで 202 が返る。仕様上どちらも正規の
送信方法なので、一括POSTを先に試し、駄目なら1件ずつのGETに落とす。
（一括POSTが通るようになったら自動的にそちらが使われる。）

使い方: python scripts/submit_indexnow.py [--dry-run] [--batch 100] [--delay 0.3]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://iwata.enshu-lifehack.com"
INDEXNOW_KEY = "9aacdc8ce3b94cb9ba20a4b29fe99f59"

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]
HOST = urlparse(SITE_URL).netloc
KEY_LOCATION = f"{SITE_URL}/{INDEXNOW_KEY}.txt"
UA = "iwata-lifehack-indexnow/1.0"


def read_sitemap_urls():
    xml = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    urls = re.findall(r"<loc>(.*?)</loc>", xml)
    # 同一ホストのURLのみ送れる（IndexNow の仕様）
    return [u for u in urls if urlparse(u).netloc == HOST]


def _send(req):
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, res.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except urllib.error.URLError as e:
        return 0, str(e.reason)[:200]


def post_bulk(endpoint, url_list):
    payload = json.dumps({
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": url_list,
    }, ensure_ascii=False).encode("utf-8")
    return _send(urllib.request.Request(endpoint, data=payload, method="POST", headers={
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": UA,
    }))


def get_one(endpoint, url):
    q = urllib.parse.urlencode({"url": url, "key": INDEXNOW_KEY})
    return _send(urllib.request.Request(f"{endpoint}?{q}", headers={"User-Agent": UA}))


def ok(status):
    return status in (200, 202)


def try_bulk(urls, batch):
    """一括POSTを試す。全バッチが通れば True。"""
    batches = [urls[i:i + batch] for i in range(0, len(urls), batch)]
    for endpoint in ENDPOINTS:
        results = [post_bulk(endpoint, b) for b in batches]
        for i, (status, body) in enumerate(results, 1):
            print(f"  bulk {i}/{len(batches)} ({len(batches[i - 1])} urls) -> "
                  f"{endpoint} {status} {'OK' if ok(status) else 'NG'} {body}".rstrip())
        if all(ok(s) for s, _ in results):
            print(f"indexnow: OK / bulk ({len(urls)} urls / {len(batches)} batches / {endpoint})")
            return True
    return False


def try_per_url(urls, delay):
    """1URLずつ GET で送る。成功数を返す。"""
    endpoint = ENDPOINTS[0]
    sent, failed = 0, []
    for i, u in enumerate(urls, 1):
        status, body = get_one(endpoint, u)
        if ok(status):
            sent += 1
        else:
            failed.append((u, status, body))
            print(f"  NG {status} {u} {body}".rstrip())
        if i % 25 == 0 or i == len(urls):
            print(f"  {i}/{len(urls)} 送信済み（成功 {sent}）")
        if delay:
            time.sleep(delay)
    return sent, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=100, help="一括POST時の1リクエストあたりのURL数")
    ap.add_argument("--delay", type=float, default=0.3, help="1件ずつ送る際の待ち秒数")
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

    print("一括POSTを試す:")
    if try_bulk(urls, a.batch):
        return

    print("一括POSTが通らないので1URLずつのGETに切り替える:")
    sent, failed = try_per_url(urls, a.delay)
    if failed:
        print(f"FAIL: {len(failed)}/{len(urls)} 件が 200/202 以外"
              f"（403 ならキーファイルの配信を確認する）")
        sys.exit(1)
    print(f"indexnow: OK / per-url ({sent} urls)")


if __name__ == "__main__":
    main()
