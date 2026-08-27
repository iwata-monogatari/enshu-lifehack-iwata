#!/usr/bin/env python3
"""ブログ記事の表紙 blog/<slug>/cover.jpg (760x760) を生成する。

data/blog-posts.json の title と axis を読んで焼き込むので、台帳へ1件足してから実行する。
scripts/generate_ogp_images.py と同じく Windows 同梱の Meiryo を使う。

使い方:
  python scripts/make_blog_cover.py <slug>     指定した記事の表紙を作る
  python scripts/make_blog_cover.py --all      cover.jpg が無い記事すべてを作る
  python scripts/make_blog_cover.py --all --force  既存の cover.jpg も作り直す
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "blog-posts.json")
BLOG_DIR = os.path.join(ROOT, "blog")

SIZE = 760
FONT_BOLD = "C:/Windows/Fonts/meiryob.ttc"
FONT_REGULAR = "C:/Windows/Fonts/meiryo.ttc"

TOP = (0, 116, 174)      # site.css --green  #0074AE
BOTTOM = (0, 62, 100)    # --green-d より少し濃い
CARD = (255, 255, 255)
INK = (18, 58, 82)
MUTED = (92, 118, 136)

AXIS_LABEL = {
    "mon": "手続き・制度",
    "tue": "空き家・実家・相続",
    "wed": "歴史・文化財",
    "thu": "子育て・学び",
    "fri": "地区めぐり",
    "sat": "スポーツ・イベント",
    "sun": "移住・暮らし・データ",
}


def wrap(text, font, max_width, draw):
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=font) > max_width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def make_cover(slug, title, axis):
    img = Image.new("RGB", (SIZE, SIZE), TOP)
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        d.line(
            [(0, y), (SIZE, y)],
            fill=tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)),
        )
    # 遠州灘を思わせる波を下部に敷く
    for i, (base_y, tone) in enumerate(((600, 70), (650, 52), (700, 38))):
        points = [
            (x, base_y + int(14 * math.sin(x / 78.0 + i)))
            for x in range(0, SIZE + 1, 8)
        ]
        d.line(points, fill=(40 + tone, 120 + tone, 165 + tone), width=5)

    d.rounded_rectangle((52, 150, SIZE - 52, 560), radius=28, fill=CARD)

    f_axis = ImageFont.truetype(FONT_BOLD, 26)
    f_title = ImageFont.truetype(FONT_BOLD, 40)
    f_site = ImageFont.truetype(FONT_REGULAR, 26)

    label = AXIS_LABEL.get(axis, "")
    if label:
        w = d.textlength(label, font=f_axis)
        d.rounded_rectangle((88, 190, 88 + w + 40, 244), radius=27, fill=(233, 243, 249))
        d.text((108, 203), label, font=f_axis, fill=INK)

    lines = wrap(title, f_title, SIZE - 52 * 2 - 72, d)[:6]
    y = 282
    for line in lines:
        d.text((88, y), line, font=f_title, fill=INK)
        y += 56

    d.text((88, 500), "磐田ライフハック  iwata.enshu-lifehack.com", font=f_site, fill=MUTED)

    out_dir = os.path.join(BLOG_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "cover.jpg")
    img.save(out, "JPEG", quality=88, optimize=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    with open(LEDGER, encoding="utf-8-sig") as f:
        posts = json.load(f)["posts"]

    if args.slug:
        targets = [p for p in posts if p["slug"] == args.slug]
        if not targets:
            print("台帳に slug がありません: %s" % args.slug, file=sys.stderr)
            return 1
    elif args.all:
        targets = posts
    else:
        ap.print_help()
        return 1

    made = 0
    for p in targets:
        out = os.path.join(BLOG_DIR, p["slug"], "cover.jpg")
        if os.path.isfile(out) and not args.force and not args.slug:
            continue
        print("生成: %s" % make_cover(p["slug"], p["title"], p.get("axis", "")))
        made += 1
    print("表紙 %d 件を生成しました。" % made)
    return 0


if __name__ == "__main__":
    sys.exit(main())
