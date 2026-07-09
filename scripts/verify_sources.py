#!/usr/bin/env python3
"""K-01: data/categories.json の conclusion/faq を機械検証する。

検証内容:
1. スキーマ検証: 全項目に channels/conclusion/faq/conclusion_status が存在し、
   conclusion.source が必須・HTTP到達可能であること。channels の値が定義済み4値のみ。
   conclusion 各文が40字以内。faq.a が120字以内。
2. 内容照合: conclusion.tel の電話番号、cost 内の金額文字列が
   source の公式ページ本文に存在すること。
3. 上記をすべて満たす項目は conclusion_status を "machine-verified" に更新する。
   満たさない項目は "draft" のまま mismatch-report.md に出力する。

使い方: python3 scripts/verify_sources.py
"""
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")
REPORT_PATH = os.path.join(ROOT, "_audit", "k01-mismatch-report.md")
TIMEOUT = 10
INTERVAL = 0.5
UA = "enshu-lifehack-verify/1.0"
VALID_CHANNELS = {"online", "konbini", "counter", "phone"}

_body_cache = {}


def fetch_body(url):
    if url in _body_cache:
        return _body_cache[url]
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            body = res.read().decode("utf-8", errors="ignore")
    except Exception as e:
        body = None
    _body_cache[url] = body
    time.sleep(INTERVAL)
    return body


def extract_yen_amounts(text):
    return set(re.findall(r"[0-9][0-9,]*円", text or ""))


def extract_phone(text):
    m = re.search(r"0\d{1,4}-\d{1,4}-\d{3,4}", text or "")
    return m.group(0) if m else None


def check_item(cat_id, item, issues):
    item_key = "%s/%s" % (cat_id, item["id"])
    for field in ("channels", "conclusion", "faq", "conclusion_status"):
        if field not in item:
            issues.append((item_key, "missing field: %s" % field))
            return False

    for ch in item["channels"]:
        if ch not in VALID_CHANNELS:
            issues.append((item_key, "invalid channel: %s" % ch))
            return False

    concl = item["conclusion"]
    for f in ("online", "konbini", "counter", "cost", "tel", "source"):
        if f not in concl:
            issues.append((item_key, "conclusion missing field: %s" % f))
            return False

    for f in ("online", "konbini", "counter"):
        v = concl[f]
        if v is not None and len(v) > 40:
            issues.append((item_key, "conclusion.%s exceeds 40 chars" % f))
            return False

    for faq in item["faq"]:
        if len(faq.get("a", "")) > 120:
            issues.append((item_key, "faq answer exceeds 120 chars"))
            return False

    source = concl["source"]
    if not source:
        issues.append((item_key, "conclusion.source is empty"))
        return False

    body = fetch_body(source)
    if body is None:
        issues.append((item_key, "source unreachable: %s" % source))
        return False

    tel = concl.get("tel")
    if tel:
        digits = tel.replace("-", "")
        local_part = "-".join(tel.split("-")[1:])  # 市外局番(0538)を省略した表記も許容
        if tel not in body and digits not in re.sub(r"[^\d]", "", body) and (
            not local_part or local_part not in body
        ):
            issues.append((item_key, "tel not found in source body: %s" % tel))
            return False

    cost = concl.get("cost")
    if cost and cost != "無料":
        amounts_in_cost = extract_yen_amounts(cost)
        amounts_in_body = extract_yen_amounts(body)
        if amounts_in_cost and not (amounts_in_cost & amounts_in_body):
            issues.append((item_key, "cost amount not found in source body: %s" % cost))
            return False

    return True


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    issues = []
    verified = 0
    total = 0

    for cat in root["categories"]:
        for item in cat["items"]:
            if "conclusion" not in item:
                continue
            total += 1
            ok = check_item(cat["id"], item, issues)
            item["conclusion_status"] = "machine-verified" if ok else "draft"
            if ok:
                verified += 1

    with open(CATEGORIES_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)
        f.write("\n")

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    lines = ["# K-01 mismatch report", "", "| 項目 | 問題 |", "|---|---|"]
    for key, msg in issues:
        lines.append("| %s | %s |" % (key, msg))
    if not issues:
        lines.append("| (なし) | 全項目 machine-verified |")
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("検証対象 %d / machine-verified %d / draft残 %d" % (total, verified, total - verified))
    print("レポート出力:", os.path.relpath(REPORT_PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
