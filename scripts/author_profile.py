"""記事ページの著者欄と JSON-LD の author を、人物情報の正本（oishi-hiroyuki.org）へそろえる。

build_blog.py から毎回呼ばれる（冪等）。単体でも実行できる:
    python scripts/author_profile.py          # blog/*/index.html を書き換え
    python scripts/author_profile.py --check  # 書き換えずに差分件数だけ表示

- 既存の著者欄（class に post-author / post-author-box / author-box を含むブロック要素）を外し、
  統一の著者欄を </article> の直前に1つだけ置く。出典・確認日（post-sources / verified）は触らない。
- 記事内メタ行の <span class="post-author"> は表示名とリンク先だけ正本へ差し替える。
- JSON-LD は author を正本 Person 参照へ、運営主体を別 @id の Organization へ置き換える。
人物・運営主体の内容を変えるときは、このファイルの定数だけを直す（森町版にも同じファイルがある）。
"""
import glob
import html
import json
import os
import re
import sys

PERSON_ID = "https://oishi-hiroyuki.org/#person"
PROFILE_URL = "https://oishi-hiroyuki.org/profile"
PERSON = {"@type": "Person", "@id": PERSON_ID, "name": "大石浩之", "url": PROFILE_URL}
ORG_ID = "https://www.fujigaoka-service.co.jp/#organization"
ORG = {"@type": "Organization", "@id": ORG_ID, "name": "富士ヶ丘サービス株式会社", "url": "https://www.fujigaoka-service.co.jp/"}

MARK = 'data-author-profile="oishi-hiroyuki-org"'
AUTHOR_BOX = (
    '<aside class="post-author post-author-profile" ' + MARK + ' aria-label="この記事を書いた人" '
    'style="margin:32px 0 0;padding:14px 0 0;border-top:1px solid rgba(0,0,0,.14);font-size:14px;line-height:1.75;color:#4a5550">'
    '<p style="margin:0;font-size:15px;color:#222"><strong>大石浩之</strong>'
    '<span style="display:inline-block;margin-left:.5em;font-size:13px;color:#5b6660">編集・運営／富士ヶ丘サービス株式会社 代表</span></p>'
    '<p style="margin:.35em 0 0">磐田を拠点に、不動産・介護の現場で地域の暮らしに関わっています。'
    '遠州ライフハックでは、行政手続き、住まい、高齢者支援など、暮らしの中で調べにくい情報を、公的情報を確認しながら整理しています。</p>'
    '<p style="margin:.35em 0 0"><a href="' + PROFILE_URL + '">プロフィールを見る</a></p>'
    '</aside>'
)
SPAN_BYLINE = '<span class="post-author"><a href="' + PROFILE_URL + '">大石浩之</a></span>'

BLOCK_TAGS = ("div", "p", "section", "aside")
_OPEN = re.compile(r'<(div|p|section|aside|span)\b[^>]*\bclass="([^"]*)"[^>]*>', re.I)
_JSONLD = re.compile(r'(<script[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.S | re.I)
_AUTHOR_CLASSES = {"post-author", "post-author-box", "author-box"}


def _element_end(src, tag, start):
    """start にある開始タグに対応する終了タグの直後の位置を返す（同名タグの入れ子を数える）。"""
    pat = re.compile(r'<(/?)%s\b[^>]*>' % tag, re.I)
    depth = 0
    for m in pat.finditer(src, start):
        if m.group(0).endswith("/>"):
            continue
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
    return -1


def _fix_html(src):
    out, pos = [], 0
    while True:
        m = _OPEN.search(src, pos)
        if not m:
            out.append(src[pos:])
            break
        classes = set(m.group(2).split())
        if not classes & _AUTHOR_CLASSES:
            out.append(src[pos:m.end()])
            pos = m.end()
            continue
        tag = m.group(1).lower()
        end = _element_end(src, tag, m.start())
        if end < 0:
            out.append(src[pos:m.end()])
            pos = m.end()
            continue
        out.append(src[pos:m.start()])
        if tag == "span":
            out.append(SPAN_BYLINE)
        # ブロック要素の著者欄は外す（後で統一版を1つ置く）
        pos = end
    new = "".join(out)
    i = new.rfind("</article>")
    if i < 0:
        i = new.rfind("</main>")
    if i < 0:
        return src
    return new[:i] + AUTHOR_BOX + new[i:]


def _is_org_self(d):
    return d.get("@type") == "Organization" and "富士ヶ丘サービス" in str(d.get("name", ""))


def _walk(node, key=None):
    if isinstance(node, list):
        if key == "author":
            return dict(PERSON)
        return [_walk(x) for x in node]
    if not isinstance(node, dict):
        return node
    if key == "author":
        return dict(PERSON)
    t = node.get("@type")
    nid = str(node.get("@id", ""))
    is_oishi = "大石" in str(node.get("name", "")) or nid == PERSON_ID or nid.endswith("/author/oishi-hiroyuki/#person") or nid.endswith("/about/author/#person")
    if is_oishi and t in (None, "Person"):
        return {**PERSON, **{k: node[k] for k in ("sameAs", "jobTitle", "image") if k in node}}
    if _is_org_self(node) or nid == ORG_ID:
        return dict(ORG)
    return {k: _walk(v, k) for k, v in node.items()}


def _fix_jsonld(src, errors, label):
    def repl(m):
        body = m.group(2)
        try:
            data = json.loads(body)
        except ValueError as e:
            errors.append("%s: JSON-LD 解析失敗 (%s)" % (label, e))
            return m.group(0)
        if "Person" not in body and "author" not in body and "富士ヶ丘" not in body:
            return m.group(0)
        ctx = data.get("@context") if isinstance(data, dict) else None
        data = _walk(data)
        if ctx and isinstance(data, dict) and "@context" not in data:
            data = {"@context": ctx, **data}
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return m.group(1) + text + m.group(3)
    return _JSONLD.sub(repl, src)


def _meta(src, pattern):
    m = re.search(pattern, src, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def _ensure_article_jsonld(src):
    """記事に author を持つ JSON-LD が無ければ、最小の BlogPosting を head に足す。"""
    if '"author"' in src:
        return src
    url = _meta(src, r'<link rel="canonical" href="([^"]+)"')
    m = re.search(r"/blog/(\d{4})(\d{2})(\d{2})-", url)
    if not url or not m:
        return src
    headline = _meta(src, r'<meta property="og:title" content="([^"]*)"') or _meta(src, r"<title>(.*?)</title>")
    node = {"@context": "https://schema.org", "@type": "BlogPosting", "@id": url + "#article",
            "headline": headline, "url": url, "mainEntityOfPage": url,
            "datePublished": "%s-%s-%s" % m.groups()}
    desc = _meta(src, r'<meta name="description" content="([^"]*)"')
    if desc:
        node["description"] = desc
    image = _meta(src, r'<meta property="og:image" content="([^"]+)"')
    if image:
        node["image"] = image
    node["author"] = dict(PERSON)
    node["publisher"] = dict(ORG)
    text = json.dumps(node, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    i = src.find("</head>")
    if i < 0:
        return src
    return src[:i] + '<script type="application/ld+json">' + text + "</script>\n" + src[i:]


def apply_to_html(src, label="", errors=None):
    errors = [] if errors is None else errors
    return _ensure_article_jsonld(_fix_jsonld(_fix_html(src), errors, label))


def apply_all(root, check=False, extra_paths=()):
    paths = sorted(glob.glob(os.path.join(root, "blog", "*", "index.html")))
    changed, errors = 0, []
    for path in paths:
        with open(path, encoding="utf-8", newline="") as f:
            src = f.read()
        new = apply_to_html(src, os.path.relpath(path, root), errors)
        if new != src:
            changed += 1
            if not check:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
    for path in extra_paths:  # 著者ページなど、JSON-LD だけそろえるページ
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", newline="") as f:
            src = f.read()
        new = _fix_jsonld(src, errors, os.path.relpath(path, root))
        if new != src:
            changed += 1
            if not check:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(new)
    return changed, errors


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    n, errs = apply_all(root, check="--check" in sys.argv)
    for e in errs:
        print(e)
    print("著者欄・JSON-LD 更新: %d ファイル%s" % (n, "（--check）" if "--check" in sys.argv else ""))
