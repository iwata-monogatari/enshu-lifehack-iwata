#!/usr/bin/env python3
"""data/blog-posts.json から /blog/ の一覧ページを生成し、記事の体裁を検証する。

森町ライフハック(enshu-lifehack-morimachi/scripts/build_blog.py)の方式を
磐田ライフハックへ移植したもの。記事の実体(blog/<slug>/index.html)は手書きで、
本スクリプトは
  1. 台帳と実ファイルの突き合わせ
  2. 品質ゲートの機械チェック
  3. 一覧ページ blog/index.html と Atom フィードの生成
  4. 記事末尾の関連記事ブロックとフィード検出タグの同期
を担当する。記事本文(post-editorial-body)は書き換えない。

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
FEED = os.path.join(BLOG_DIR, "feed.xml")
SITEMAP_START = "  <!-- BLOG:START 以下は scripts/build_blog.py が生成する。手で編集しない -->"
SITEMAP_END = "  <!-- BLOG:END -->"

SITE = "https://iwata.enshu-lifehack.com"
SITE_NAME = "磐田ライフハック"
HOME_LABEL = "磐田ライフハック"
AUTHOR_URL = SITE + "/author/oishi-hiroyuki/"
OFFICIAL_PREFIX = "https://www.city.iwata.shizuoka.jp/"
CSS_HREF = "/assets/blog.css?v=20260828c"
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
        if p.get("modified") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["modified"]):
            problems.append((slug, "modified は YYYY-MM-DD の形にする"))
        if p["axis"] not in AXIS_LABEL:
            problems.append((slug, "axis が未定義: %s(使えるのは %s)" % (p["axis"], "/".join(AXIS_LABEL))))
        for related in p.get("related_life", []):
            href = related.get("href", "")
            label = related.get("label", "")
            if not href.startswith("/") or not label:
                problems.append((slug, "related_life は / から始まる href と label が必要"))
                continue
            target = os.path.join(ROOT, href.strip("/").replace("/", os.sep), "index.html")
            if not os.path.isfile(target):
                problems.append((slug, "related_life のリンク先が無い: %s" % href))

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
    sorted_posts = sorted(posts, key=lambda x: (x["date"], x["slug"]), reverse=True)
    items = []
    for p in sorted_posts:
        axis = AXIS_LABEL.get(p.get("axis"), "")
        badge = '<span class="post-axis">%s</span>' % html.escape(axis) if axis else ""
        items.append(
            '<li class="post-item" id="post-%s">'
            '<a class="post-item-link" href="/blog/%s/">'
            '<img class="post-item-thumb" src="/blog/%s/cover.jpg" alt="" width="760" height="760" loading="lazy" decoding="async">'
            '<span class="post-item-body">'
            '<span class="post-item-date"><time datetime="%s">%s</time></span>'
            "%s"
            '<span class="post-item-title">%s</span>'
            '<span class="post-item-desc">%s</span>'
            "</span></a></li>"
            % (
                p["slug"], p["slug"], p["slug"], p["date"], p["date"].replace("-", "."),
                badge, html.escape(p["title"]), html.escape(p["description"]),
            )
        )

    lead = "静岡県磐田市の暮らし・手続き・住まい・地区について、市の公表情報を確認しながら書いています。"
    index_title = "磐田ブログ｜暮らし・住まい・手続きを一次情報で読む"
    newest = sorted_posts[0] if sorted_posts else None
    index_image = "%s/blog/%s/cover.jpg" % (SITE, newest["slug"]) if newest else "%s/favicon.svg" % SITE
    topic_links = []
    seen_axes = set()
    for p in sorted_posts:
        axis = p.get("axis")
        if axis in seen_axes:
            continue
        seen_axes.add(axis)
        topic_links.append('<a href="#post-%s">%s</a>' % (html.escape(p["slug"]), html.escape(AXIS_LABEL.get(axis, axis))))
    topic_nav = '<nav class="blog-topics" aria-label="ブログのテーマ"><span>テーマから読む</span>%s</nav>' % "".join(topic_links) if topic_links else ""
    body = '%s<ul class="post-list">%s</ul><p class="blog-feed-link"><a href="/blog/feed.xml">新着記事をAtomフィードで受け取る</a></p>' % (topic_nav, "".join(items)) if items else '<p class="lead">記事はまだありません。</p>'

    graph = [
        {
            "@type": "Blog", "@id": "%s/blog/#blog" % SITE, "url": "%s/blog/" % SITE,
            "name": "磐田ブログ", "description": lead, "inLanguage": "ja",
            "publisher": {"@type": "Organization", "name": "富士ヶ丘サービス株式会社"},
            "blogPost": [
                {
                    "@type": "BlogPosting", "@id": "%s/blog/%s/#article" % (SITE, p["slug"]),
                    "url": "%s/blog/%s/" % (SITE, p["slug"]), "headline": p["title"],
                    "description": p["description"], "datePublished": p["date"],
                    "dateModified": p.get("modified", p["date"]),
                    "image": "%s/blog/%s/cover.jpg" % (SITE, p["slug"]),
                    "author": {"@type": "Person", "name": "大石浩之", "url": AUTHOR_URL},
                }
                for p in sorted_posts
            ],
        },
        {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": "%s/blog/%s/" % (SITE, p["slug"])}
                for i, p in enumerate(sorted_posts)
            ],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": HOME_LABEL, "item": "%s/" % SITE},
                {"@type": "ListItem", "position": 2, "name": "ブログ", "item": "%s/blog/" % SITE},
            ],
        },
    ]
    json_ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html><html lang="ja"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(index_title)}</title>
<meta name="description" content="{html.escape(lead)}">
<meta name="robots" content="max-image-preview:large">
<link rel="canonical" href="{SITE}/blog/">
<link rel="alternate" type="application/atom+xml" title="磐田ブログ" href="/blog/feed.xml">
<meta property="og:type" content="website"><meta property="og:locale" content="ja_JP"><meta property="og:site_name" content="{html.escape(SITE_NAME)}"><meta property="og:title" content="{html.escape(index_title)}"><meta property="og:description" content="{html.escape(lead)}"><meta property="og:url" content="{SITE}/blog/"><meta property="og:image" content="{index_image}"><meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json_ld}</script>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
{part_markup("head-css", parts["head-css"])}
<link rel="stylesheet" href="{CSS_HREF}">
</head><body>
{part_markup("header", parts["header"])}
{part_markup("disclaimer", parts["disclaimer"])}
<main id="main"><div class="wrap">
<p class="breadcrumb"><a href="/">{html.escape(HOME_LABEL)}</a> ／ ブログ</p>
<section class="hero"><div class="hero-visual"><h1><span aria-hidden="true">📝</span> ブログ</h1></div><div class="hero-body"><p class="lead">{html.escape(lead)}</p></div></section>
{body}
</div></main>
{part_markup("footer", parts["footer"])}
</body></html>
'''


def build_feed(posts):
    sorted_posts = sorted(posts, key=lambda x: (x["date"], x["slug"]), reverse=True)
    updated = (sorted_posts[0].get("modified", sorted_posts[0]["date"]) if sorted_posts else "2026-08-28") + "T00:00:00+09:00"
    entries = []
    for p in sorted_posts:
        url = "%s/blog/%s/" % (SITE, p["slug"])
        entries.append(
            '<entry><title>%s</title><id>%s</id><link href="%s"/><published>%sT00:00:00+09:00</published><updated>%sT00:00:00+09:00</updated><author><name>大石浩之</name></author><summary>%s</summary></entry>'
            % (html.escape(p["title"]), url, url, p["date"], p.get("modified", p["date"]), html.escape(p["description"]))
        )
    return '<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>磐田ブログ</title><id>%s/blog/</id><link href="%s/blog/"/><link rel="self" type="application/atom+xml" href="%s/blog/feed.xml"/><updated>%s</updated>%s</feed>\n' % (SITE, SITE, SITE, updated, "".join(entries))


def build_related_block(current, posts):
    cards = []
    for related in current.get("related_life", []):
        cards.append('<a class="post-related-card" href="%s"><span>手続きガイド</span><strong>%s</strong></a>' % (html.escape(related["href"]), html.escape(related["label"])))
    others = [p for p in sorted(posts, key=lambda x: (x["date"], x["slug"]), reverse=True) if p["slug"] != current["slug"]][:2]
    for p in others:
        cards.append('<a class="post-related-card" href="/blog/%s/"><span>磐田ブログ</span><strong>%s</strong></a>' % (html.escape(p["slug"]), html.escape(p["title"])))
    return '<!-- BLOG_RELATED:START --><section class="post-related" aria-labelledby="post-related-title"><h2 class="sec" id="post-related-title">関連記事・次に読む</h2><div class="post-related-grid">%s</div></section><!-- BLOG_RELATED:END -->' % "".join(cards)


def update_article_discovery(posts):
    updated = 0
    for p in posts:
        path = os.path.join(BLOG_DIR, p["slug"], "index.html")
        with open(path, encoding="utf-8", newline="") as f:
            src = f.read()
        new = src
        block = build_related_block(p, posts)
        pattern = re.compile(r"<!-- BLOG_RELATED:START -->.*?<!-- BLOG_RELATED:END -->", re.S)
        if pattern.search(new):
            new = pattern.sub(lambda m: block, new)
        else:
            new = new.replace('<div class="post-author-box">', block + '\n<div class="post-author-box">', 1)
        if 'type="application/atom+xml"' not in new:
            new = new.replace("</head>", '<link rel="alternate" type="application/atom+xml" title="磐田ブログ" href="/blog/feed.xml">\n</head>', 1)
        if 'name="robots"' not in new:
            new = new.replace("</head>", '<meta name="robots" content="max-image-preview:large">\n</head>', 1)
        new = new.replace(
            '"name":"大石浩之","url":"%s/terms/"' % SITE,
            '"name":"大石浩之","url":"%s"' % AUTHOR_URL,
            1,
        )
        modified = p.get("modified", p["date"])
        date_line = re.compile(
            r'(<p class="post-date"><time datetime="%s">.*?</time>)(?:<span class="post-updated">.*?</span>)?'
            % re.escape(p["date"])
        )
        if modified != p["date"]:
            label = '<span class="post-updated">更新：%s</span>' % modified.replace("-", ".")
            new = date_line.sub(lambda m: m.group(1) + label, new, count=1)
        else:
            new = date_line.sub(lambda m: m.group(1), new, count=1)
        new = re.sub(r'("dateModified":")\d{4}-\d{2}-\d{2}(")', r'\g<1>%s\2' % p.get("modified", p["date"]), new, count=1)
        if new != src:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            updated += 1
    return updated


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
    if 'xmlns:image=' not in src:
        src = src.replace(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
            1,
        )

    newest_modified = max((p.get("modified", p["date"]) for p in posts), default="2026-08-28")
    lines = [SITEMAP_START, "  <url><loc>%s/blog/</loc><lastmod>%s</lastmod></url>" % (SITE, newest_modified)]
    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        lines.append(
            "  <url><loc>%s/blog/%s/</loc><lastmod>%s</lastmod><image:image><image:loc>%s/blog/%s/cover.jpg</image:loc><image:title>%s</image:title></image:image></url>"
            % (SITE, p["slug"], p.get("modified", p["date"]), SITE, p["slug"], html.escape(p["title"]))
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
    article_note = "未更新:--check"
    feed_note = "未更新:--check"
    if not args.check:
        with open(out, "w", encoding="utf-8", newline="") as f:
            f.write(html_out)
        with open(FEED, "w", encoding="utf-8", newline="") as f:
            f.write(build_feed(posts))
        feed_note = "更新"
        article_note = "%d件更新" % update_article_discovery(posts)
        sitemap_note = "更新" if update_sitemap(posts) else "変更なし"
    print(
        "記事 %d 件 / 品質ゲート未達 0 / 一覧: blog/index.html%s / Atom: %s / 関連導線: %s / sitemap.xml: %s"
        % (len(posts), "（未書き込み:--check）" if args.check else "", feed_note, article_note, sitemap_note)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
