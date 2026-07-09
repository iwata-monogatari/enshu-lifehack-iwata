#!/usr/bin/env python3
"""K-03: _staging/k03/*.json の口語シノニムを data/topics_master.json にマージする。

各hrefの既存synonymsを保持したまま、add_synonymsを重複排除して追記する。
手作業マージ禁止のため必ずこのスクリプトを使う。

使い方: python3 scripts/merge_k03.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_PATH = os.path.join(ROOT, "data", "topics_master.json")
STAGING_DIR = os.path.join(ROOT, "_staging", "k03")


def load_additions():
    additions = {}
    for fp in sorted(glob.glob(os.path.join(STAGING_DIR, "*.json"))):
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        for item in data["items"]:
            additions[item["href"]] = item["add_synonyms"]
    return additions


def main():
    with open(TOPICS_PATH, encoding="utf-8") as f:
        topics = json.load(f)

    additions = load_additions()

    merged = 0
    added_total = 0
    missing = []
    for t in topics:
        add = additions.pop(t["href"], None)
        if add is None:
            continue
        existing = set(t["synonyms"])
        new_syns = [s for s in add if s not in existing]
        t["synonyms"].extend(new_syns)
        added_total += len(new_syns)
        merged += 1

    if additions:
        missing = list(additions.keys())
        print("警告: topics_masterに該当hrefがなくマージできなかった項目:", missing)

    with open(TOPICS_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("マージ完了: %d ページ / 追加synonyms %d 件" % (merged, added_total))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
