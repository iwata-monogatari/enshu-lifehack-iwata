#!/usr/bin/env python3
"""K-01: _staging/k01/*.json を data/categories.json にマージする。

各カテゴリの各項目(id一致)に channels / conclusion / faq / conclusion_status を追加する。
既存フィールド(id/label/url等)は変更しない。手作業マージ禁止のため必ずこのスクリプトを使う。

使い方: python3 scripts/merge_k01.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")
STAGING_DIR = os.path.join(ROOT, "_staging", "k01")

REQUIRED_ITEM_FIELDS = ("channels", "conclusion", "faq", "conclusion_status")


def load_staging():
    staged = {}
    for fp in sorted(glob.glob(os.path.join(STAGING_DIR, "*.json"))):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        cat_id = data["category"]
        by_id = {}
        for item in data["items"]:
            by_id[item["id"]] = item
        staged[cat_id] = by_id
    return staged


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    staged = load_staging()

    merged = 0
    missing = []
    for cat in root["categories"]:
        cat_id = cat["id"]
        if cat_id not in staged:
            missing.append(cat_id)
            continue
        by_id = staged[cat_id]
        for item in cat["items"]:
            src = by_id.get(item["id"])
            if src is None:
                missing.append("%s/%s" % (cat_id, item["id"]))
                continue
            for field in REQUIRED_ITEM_FIELDS:
                item[field] = src[field]
            merged += 1

    if missing:
        print("警告: マージできなかった項目/カテゴリ:", missing)

    with open(CATEGORIES_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("マージ完了: %d 項目" % merged)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
