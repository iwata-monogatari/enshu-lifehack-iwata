#!/usr/bin/env python3
"""data/blog-posts.json から /blog/ の一覧ページを生成し、記事の体裁を検証する。

森町ライフハック(enshu-lifehack-morimachi/scripts/build_blog.py)の方式を
磐田ライフハックへ移植したもの。記事の実体(blog/<slug>/index.html)は手書きで、
本スクリプトは
  1. 台帳と実ファイルの突き合わせ
  2. 品質ゲートの機械チェック
  3. 一覧ページ blog/index.html の生成
だけを担当する。生成物は blog/index.html のみ。記事本体は絶対に書き換えない。

品質ゲート(機械で見られる範囲):
  - 編集本文(post-editorial-body)が空白除外で5,000文字以上あるか
  - 編集本文の段落(<p>)が35以上あるか
  - 出典セクション(post-sources)に磐田市公式リンクが2本以上あるか
  - 記事固有の編集挿絵 fig1.svg / fig2.svg があり、磐田仕様のマーカーを持つか
  - 良い点・注文したい点・対案・大石の視点が本文にあるか
  - 著者表記(post-author)があるか
  - 表紙画像 cover.jpg があるか
  - ブログ用CSS(/assets/blog.css)を読み込んでいるか
  - 禁止語が含まれていないか
  - タイトル・slug の重複が無いか / 台帳に無い記事ディレクトリが残っていないか
本文の内容が本当に一次情報かどうかは機械では判定できないため、最終判断は執筆者が行う。

使い方:
  python scripts/build_blog.py           一覧を生成する
  python scripts/build_blog.py --check   検査だけ行い blog/index.html は書かない
"""
import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "blog-posts.json")
PARTS_DIR = os.path.join(ROOT, "parts")
BLOG_DIR = os.path.join(ROOT, "blog")
SITEMAP = os.path.join(ROOT, "sitemap.xml")
SITEMAP_START = "  <!-- BLOG:START 以下は scripts/build_blog.py が生成する。手で編集しない -->"
SITEMAP_END = "  <!-- BLOG:END -->"

SITE = "https://iwata.enshu-lifehack.com"
SITE_NAME = "磐田ライフハック"
HOME_LABEL = "磐田ライフハック"
OFFICIAL_PREFIX = "https://www.city.iwata.shizuoka.jp/"
CSS_HREF = "/assets/blog.css?v=20260828b"
FIG_MARKER = 'data-illustration="iwata-editorial"'

MIN_EDITORIAL_CHARS = 5000
MIN_PARAGRAPHS = 35
MIN_OFFICIAL_SOURCES = 2

# 磐田ライフハックは「暮らしと手続き」の非公式案内サイトであり、
# 同じ運営者の政治系サイトとは役割を分けている。政治色を持ち込まないため
# 森町版と同じ禁止語を引き継ぐ。増やすときはここへ追記する。
BANNED_WORDS = ("政策",)

# 曜日別テーマ軸。磐田市の13カテゴリ(life/)に対応させたもの。
AXIS_LABEL = {
    "mon": "手続き・制度",
    "tue": "空き家・実家・相続",
    "wed": "歴史・文化財",
    "thu": "子育て・学び",
    "fri": "地区めぐり",
    "sat": "スポーツ・イベント",
    "sun": "移住・暮らし・データ",
}

REQUIRED_SECTIONS = ("良い点", "注文したい点", "対案・結論", "大石の視点")
REQUIRED_KEYS = ("slug", "date", "axis", "title", "description")


def load_parts():
    """scripts/inject_parts.py と同じ読み方をする。

    newline="" を外すと改行が LF に変換され、inject_parts.py を後から走らせるたびに
    blog/index.html が書き換わってしまう(差分が無限に出る)。必ず揃えること。
    """
    parts = {}
    for name in ("head-css", "header", "disclaimer", "footer"):
        with open(os.path.join(PARTS_DIR, "%s.html" % name), encoding="utf-8", newline="") as f:
            parts[name] = f.read().strip()
    return parts


def part_markup(name, content):
    return "<!-- PART:%s:START -->%s<!-- PART:%s:END -->" % (name, content, name)


def visible_chars(fragment):
    fragment = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    fragment = re.sub(r"<(script|style)\b.*?</\1>", "", fragment, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", fragment))
    return len(re.sub(r"\s+", "", text))


def audit(posts):
    """記事ごとの品質ゲート。問題があれば (slug, 理由) のリストを返す。"""
    problems = []
    seen_titles = {}
    seen_slugs = set()
    for p in posts:
        slug = p.get("slug", "(slug無し)")
        missing = [k for k in REQUIRED_KEYS if not p.get(k)]
        if missing:
            problems.append((slug, "台帳の必須キーが空: %s" % "、".join(missing)))
            continue
        if slug in seen_slugs:
            problems.append((slug, "台帳に slug が重複している"))
            continue
        seen_slugs.add(slug)
        if not re.fullmatch(r"\d{8}-[a-z0-9-]+", slug):
            problems.append((slug, "slug は YYYYMMDD-英小文字ハイフン の形にする"))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]):
            problems.append((slug, "date は YYYY-MM-DD の形にする"))
        if p["axis"] not in AXIS_LABEL:
            problems.append((slug, "axis が未定義: %s(使えるのは %s)" % (p["axis"], "/".join(AXIS_LABEL))))

        d = os.path.join(BLOG_DIR, slug)
        idx = os.path.join(d, "index.html")
        if not os.path.isfile(idx):
            problems.append((slug, "記事本体が無い: blog/%s/index.html" % slug))
            continue
        with open(idx, encoding="utf-8") as f:
            src = f.read()

        body = re.search(
            r'<div class="post-editorial-body">(.*?)</div>\s*<div class="action-grid">', src, re.S
        )
        if not body:
            problems.append((slug, "編集本文(post-editorial-body)が無い、または直後に action-grid が無い"))
        else:
            count = visible_chars(body.group(1))
            if count < MIN_EDITORIAL_CHARS:
                problems.append((slug, "編集本文が %d 文字。最低 %d 文字に未達" % (count, MIN_EDITORIAL_CHARS)))
            paragraph_count = len(re.findall(r"<p(?:\s|>)", body.group(1)))
            if paragraph_count < MIN_PARAGRAPHS:
                problems.append((slug, "編集本文の段落が %d。%d段落未満" % (paragraph_count, MIN_PARAGRAPHS)))

        m = re.search(r'<ul class="post-sources">(.*?)</ul>', src, re.S)
        official_links = re.findall(
            r'href="%s[^"]*"' % re.escape(OFFICIAL_PREFIX), m.group(1) if m else ""
        )
        if len(set(official_links)) < MIN_OFFICIAL_SOURCES:
            problems.append((slug, "磐田市公式の出典が%d本未満" % MIN_OFFICIAL_SOURCES))

        if "post-author" not in src:
            problems.append((slug, "著者表記(post-author)が無い"))
        if "/assets/blog.css" not in src:
            problems.append((slug, "ブログ用CSS(/assets/blog.css)を読み込んでいない"))
        if not os.path.isfile(os.path.join(d, "cover.jpg")):
            problems.append((slug, "表紙 cover.jpg が無い"))
        for number in (1, 2):
            fig_path = os.path.join(d, "fig%d.svg" % number)
            if not os.path.isfile(fig_path):
                problems.append((slug, "挿絵 fig%d.svg が無い" % number))
                continue
            with open(fig_path, encoding="utf-8") as f:
                fig_src = f.read()
            if FIG_MARKER not in fig_src:
                problems.append((slug, "fig%d.svg が磐田編集挿絵仕様(%s)ではない" % (number, FIG_MARKER)))
        for required in REQUIRED_SECTIONS:
            if required not in src:
                problems.append((slug, "必須セクション『%s』が無い" % required))
        for word in BANNED_WORDS:
            if word in src:
                problems.append((slug, "禁止語『%s』が本文・属性に含まれる" % word))
        if p["title"] in seen_titles:
            problems.append((slug, "タイトルが %s と重複" % seen_titles[p["title"]]))
        seen_titles[p["title"]] = slug

    # 台帳に無い記事ディレクトリ(消し忘れ・登録忘れ)を検出する。_ 始まりは雛形なので除外。
    if os.path.isdir(BLOG_DIR):
        for name in sorted(os.listdir(BLOG_DIR)):
            if name.startswith("_") or not os.path.isdir(os.path.join(BLOG_DIR, name)):
                continue
            if name not in seen_slugs:
                problems.append((name, "blog/%s/ が台帳(data/blog-posts.json)に登録されていない" % name))
    return problems


def build_index(posts, parts):
    items = []
    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        axis = AXIS_LABEL.get(p.get("axis"), "")
        badge = '<span class="post-axis">%s</span>' % html.escape(axis) if axis else ""
        items.append(
            '<li class="post-item">'
            '<a class="post-item-link" href="/blog/%s/">'
            '<img class="post-item-thumb" src="/blog/%s/cover.jpg" alt="" width="760" height="760" loading="lazy" decoding="async">'
            '<span class="post-item-body">'
            '<span class="post-item-date"><time datetime="%s">%s</time></span>'
            "%s"
            '<span class="post-item-title">%s</span>'
            '<span class="post-item-desc">%s</span>'
            "</span></a></li>"
            % (
                p["slug"],
                p["slug"],
                p["date"],
                p["date"].replace("-", "."),
                badge,
                html.escape(p["title"]),
                html.escape(p["description"]),
            )
        )

    lead = "静岡県磐田市の暮らし・手続き・住まい・地区について、市の公表情報を確認しながら書いています。"
    index_title = "磐田ブログ｜暮らし・住まい・手続きを一次情報で読む"
    newest = sorted(posts, key=lambda x: x["date"], reverse=True)[0] if posts else None
    index_image = (
        "%s/blog/%s/cover.jpg" % (SITE, newest["slug"]) if newest else "%s/favicon.svg" % SITE
    )
    body = (
        '<ul class="post-list">%s</ul>' % "".join(items)
        if items
        else '<p class="lead">記事はまだありません。</p>'
    )

    return (
        '<!doctype html><html lang="ja"><head>\n'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>%s</title>\n"
        '<meta name="description" content="%s">\n'
        '<link rel="canonical" href="%s/blog/">\n'
        '<meta property="og:type" content="website"><meta property="og:locale" content="ja_JP">'
        '<meta property="og:site_name" content="%s">'
        '<meta property="og:title" content="%s"><meta property="og:description" content="%s">'
        '<meta property="og:url" content="%s/blog/"><meta property="og:image" content="%s">'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":'
        '[{"@type":"ListItem","position":1,"name":"%s","item":"%s/"},'
        '{"@type":"ListItem","position":2,"name":"ブログ","item":"%s/blog/"}]}</script>\n'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
        "%s\n"
        '<link rel="stylesheet" href="%s">\n'
        "</head><body>\n%s\n%s\n"
        '<main id="main"><div class="wrap">\n'
        '<p class="breadcrumb"><a href="/">%s</a> ／ ブログ</p>\n'
        '<section class="hero"><div class="hero-visual">'
        '<h1><span aria-hidden="true">📝</span> ブログ</h1></div>'
        '<div class="hero-body"><p class="lead">%s</p></div></section>\n'
        "%s\n</div></main>\n%s\n</body></html>\n"
    ) % (
        index_title,
        lead,
        SITE,
        SITE_NAME,
        index_title,
        lead,
        SITE,
        index_image,
        HOME_LABEL,
        SITE,
        SITE,
        part_markup("head-css", parts["head-css"]),
        CSS_HREF,
        part_markup("header", parts["header"]),
        part_markup("disclaimer", parts["disclaimer"]),
        HOME_LABEL,
        lead,
        body,
        part_markup("footer", parts["footer"]),
    )


def update_sitemap(posts):
    """sitemap.xml のブログ区画(BLOG:START〜BLOG:END)を作り直す。

    区画が無ければ </urlset> の直前に作る。既存の url 要素は一切触らない。
    BOM と CRLF は元ファイルのまま維持する。戻り値は書き換えたかどうか。
    """
    if not os.path.isfile(SITEMAP):
        return False
    with open(SITEMAP, encoding="utf-8-sig", newline="") as f:
        src = f.read()
    eol = "\r\n" if "\r\n" in src else "\n"

    lines = [SITEMAP_START, "  <url><loc>%s/blog/</loc></url>" % SITE]
    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        lines.append(
            "  <url><loc>%s/blog/%s/</loc><lastmod>%s</lastmod></url>" % (SITE, p["slug"], p["date"])
        )
    lines.append(SITEMAP_END)
    block = eol.join(lines)

    pattern = re.compile(
        "%s.*?%s" % (re.escape(SITEMAP_START), re.escape(SITEMAP_END)), re.S
    )
    if pattern.search(src):
        new = pattern.sub(lambda m: block, src)
    else:
        new = src.replace("</urlset>", block + eol + "</urlset>", 1)
    if new == src:
        return False
    with open(SITEMAP, "w", encoding="utf-8-sig", newline="") as f:
        f.write(new)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="検査のみ。blog/index.html を書き換えない")
    args = ap.parse_args()

    with open(LEDGER, encoding="utf-8-sig") as f:
        posts = json.load(f)["posts"]

    problems = audit(posts)
    if problems:
        print("品質ゲート未達 %d 件:" % len(problems))
        for slug, why in problems:
            print("  %s: %s" % (slug, why))
        print("→ 一覧は生成しません。記事を直してから再実行してください。")
        return 1

    parts = load_parts()
    html_out = build_index(posts, parts)
    out = os.path.join(BLOG_DIR, "index.html")
    os.makedirs(BLOG_DIR, exist_ok=True)
    sitemap_note = "未更新:--check"
    if not args.check:
        with open(out, "w", encoding="utf-8", newline="") as f:
            f.write(html_out)
        sitemap_note = "更新" if update_sitemap(posts) else "変更なし"
    print(
        "記事 %d 件 / 品質ゲート未達 0 / 一覧: blog/index.html%s / sitemap.xml: %s"
        % (len(posts), "（未書き込み:--check）" if args.check else "", sitemap_note)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
