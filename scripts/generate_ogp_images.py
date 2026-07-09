#!/usr/bin/env python3
"""K-07: categories.json をもとに og:image (1200x630) を一括生成する。

各項目のページ<title>先頭セグメントをタイトル文字として画像に焼き込む。
カテゴリごとに背景色を割り当て、右下にサイト名を配置する。
出力先: assets/ogp/<category_id>/<item_id>.png

使い方: python3 scripts/generate_ogp_images.py
"""
import glob
import json
import os
import re
import sys
import urllib.parse

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")
OUT_DIR = os.path.join(ROOT, "assets", "ogp")
W, H = 1200, 630

FONT_BOLD = "C:/Windows/Fonts/meiryob.ttc"
FONT_REGULAR = "C:/Windows/Fonts/meiryo.ttc"
FONT_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"

# カテゴリごとの背景グラデーション(左上→右下)
CATEGORY_COLORS = {
    "living-soon": ("#0074AE", "#15503C"),
    "start-living": ("#0E8F6B", "#0B5C46"),
    "housing": ("#8A5A2B", "#5C3A18"),
    "family-grow": ("#E0708A", "#A8385A"),
    "play-out": ("#2FA84F", "#1D6B32"),
    "education": ("#3E6FD9", "#26468C"),
    "health-medical": ("#2AA8A0", "#1B6E68"),
    "work-life": ("#5A6B8C", "#38425C"),
    "parents-care": ("#B08840", "#7A5C24"),
    "emergency": ("#D9564A", "#8C2E26"),
    "troubles-consult": ("#7A5CC4", "#4E3782"),
    "end-of-life": ("#5C6670", "#3A4149"),
    "moving-out": ("#3E9BD9", "#256B99"),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def make_gradient(w, h, c1, c2):
    c1, c2 = hex_to_rgb(c1), hex_to_rgb(c2)
    base = Image.new("RGB", (w, h), c1)
    top = Image.new("RGB", (w, h), c2)
    mask = Image.new("L", (w, h))
    mask_data = []
    for y in range(h):
        for x in range(w):
            mask_data.append(int(255 * ((x / w) + (y / h)) / 2))
    mask.putdata(mask_data)
    return Image.composite(top, base, mask)


def wrap_text(draw, text, font, max_width):
    lines = []
    current = ""
    for ch in text:
        trial = current + ch
        if draw.textlength(trial, font=font) > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def extract_title(filepath):
    with open(filepath, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"<title>(.*?)\s*\|", html)
    if m:
        return m.group(1).strip()
    m = re.search(r"<title>(.*?)</title>", html)
    return m.group(1).strip() if m else ""


def url_to_path(url):
    path = urllib.parse.urlparse(url).path
    if not path.endswith("/"):
        path += "/"
    return os.path.join(ROOT, path.strip("/"), "index.html")


def render(cat_id, emoji, title, out_path):
    c1, c2 = CATEGORY_COLORS.get(cat_id, ("#0074AE", "#15503C"))
    img = make_gradient(W, H, c1, c2)
    draw = ImageDraw.Draw(img)

    emoji_font = ImageFont.truetype(FONT_EMOJI, 90)
    draw.text((70, 55), emoji, font=emoji_font, embedded_color=True)

    title_font = ImageFont.truetype(FONT_BOLD, 64)
    lines = wrap_text(draw, title, title_font, W - 140)[:3]
    y = 210
    for line in lines:
        draw.text((70, y), line, font=title_font, fill="#ffffff")
        y += 78

    brand_font = ImageFont.truetype(FONT_BOLD, 34)
    draw.text((70, H - 90), "磐田ライフハック", font=brand_font, fill="#ffffff")
    sub_font = ImageFont.truetype(FONT_REGULAR, 24)
    draw.text((70, H - 50), "iwata.enshu-lifehack.com", font=sub_font, fill="#e8f0ee")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG")


def main():
    with open(CATEGORIES_PATH, encoding="utf-8") as f:
        root = json.load(f)

    generated = 0
    missing = []
    for cat in root["categories"]:
        for item in cat["items"]:
            filepath = url_to_path(item["url"])
            if not os.path.isfile(filepath):
                missing.append(item["url"])
                continue
            title = extract_title(filepath) or item["label"]
            out_path = os.path.join(OUT_DIR, cat["id"], "%s.png" % item["id"])
            render(cat["id"], cat["emoji"], title, out_path)
            generated += 1

    print("生成 %d 件" % generated)
    if missing:
        print("ファイル未検出:", missing)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
