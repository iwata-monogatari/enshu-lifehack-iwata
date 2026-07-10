#!/usr/bin/env python3
"""Phase 3: categories.json の channels/conclusion(K-01・machine-verified済み)から
即答ヘッダー用フィールド(online_status/online_note/time_estimate/counter_info)を導出する。

新規の外部リサーチは行わない。既にverify_sources.pyで検証済みのconclusionフィールドを
変換するだけなので、推測記入の禁止ルールに抵触しない。time_estimateは元データに
所要時間の明記がある場合のみ抽出し、なければ"n/a"のままにする(推測しない)。

使い方: python3 scripts/derive_instant_header_fields.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")

TIME_RE = re.compile(r"(所要|約)[^\s、。]*?(\d+分)")


def derive(item):
    channels = item.get("channels", [])
    concl = item.get("conclusion", {})

    if "online" in channels:
        status = "yes"
        note = concl.get("online")
    elif "konbini" in channels:
        status = "partial"
        note = concl.get("konbini")
    elif channels:
        status = "no"
        note = None
    else:
        status = "n/a"
        note = None

    counter_parts = []
    if concl.get("counter"):
        counter_parts.append(concl["counter"])
    if concl.get("tel"):
        counter_parts.append("電話：%s" % concl["tel"])
    counter_info = "。".join(counter_parts) if counter_parts else None

    time_estimate = "n/a"
    for field in ("counter", "online", "konbini"):
        text = concl.get(field) or ""
        m = TIME_RE.search(text)
        if m:
            time_estimate = m.group(2)
            break

    return {
        "online_status": status,
        "online_note": note,
        "time_estimate": time_estimate,
        "counter_info": counter_info,
    }


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    updated = 0
    for cat in root["categories"]:
        for item in cat["items"]:
            if "conclusion" not in item:
                continue
            item.update(derive(item))
            updated += 1

    with open(CATEGORIES_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("更新 %d 項目" % updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
