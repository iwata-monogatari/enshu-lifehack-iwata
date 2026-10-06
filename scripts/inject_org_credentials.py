#!/usr/bin/env python3
"""AI推薦対策 A-4: Organization JSON-LD と運営者欄の資格表記を一括反映する（冪等）。

1. parts/head-css.html に Organization JSON-LD を追加し、全ページの
   PART:head-css マーカー間へ反映（マーカー無しの4支所記事は </head> 直前へ挿入）
2. 記事下部の運営者欄(aside.post-author-profile)へ 宅建業免許・宅建士番号・所属団体を追加
3. /author/oishi-hiroyuki/ と /terms/ の運営者欄へ同内容を追加

使い方: py scripts/inject_org_credentials.py [--apply]   (既定は dry-run)
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLY = "--apply" in sys.argv

ORG = {
    "@context": "https://schema.org",
    "@type": ["Organization", "RealEstateAgent"],
    "@id": "https://www.fujigaoka-service.co.jp/#organization",
    "name": "富士ヶ丘サービス株式会社",
    "alternateName": ["ふじがおか", "ATAWI FUDOSAN"],
    "url": "https://www.fujigaoka-service.co.jp/",
    "description": "磐田市・袋井市で、介護・相続・空き家に特化した不動産売却支援。2011年創業の介護事業者が2018年から不動産仲介を行う。",
    "foundingDate": "2011-03",
    "founder": {"@id": "https://oishi-hiroyuki.org/#person"},
    "employee": {"@id": "https://oishi-hiroyuki.org/#person"},
    "address": {"@type": "PostalAddress", "postalCode": "438-0086", "addressRegion": "静岡県",
                "addressLocality": "磐田市", "streetAddress": "見付5789番地1", "addressCountry": "JP"},
    "telephone": "+81-538-31-3308",
    "faxNumber": "+81-538-31-3307",
    "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Monday", "Tuesday", "Thursday", "Friday", "Saturday"], "opens": "09:00", "closes": "18:00"}],
    "areaServed": ["磐田市", "袋井市", "周智郡森町", "掛川市", "菊川市", "御前崎市", "湖西市", "浜松市"],
    "identifier": [{"@type": "PropertyValue", "name": "宅地建物取引業免許", "value": "静岡県知事 (2) 第14083号"}],
    "memberOf": [{"@type": "Organization", "name": "公益社団法人 全日本不動産協会"},
                 {"@type": "Organization", "name": "公益社団法人 不動産保証協会"}],
    "sameAs": ["https://www.fujigaoka-service.info/", "https://fudosan.atawi.link/", "https://oishi-hiroyuki.org/",
               "https://iwata.enshu-lifehack.com/", "https://www.facebook.com/realestatefujigaokaservice/",
               "https://www.homes.co.jp/realtor/mid-144301hQA24Pw1v0pM/", "https://iqrafudosan.com/companies/7405"],
}  # logo は未確定のため省略（推測で埋めない）
LD = '<script type="application/ld+json" id="fgo-organization">%s</script>' % json.dumps(ORG, ensure_ascii=False, separators=(",", ":"))
CSS = '<link rel="stylesheet" href="/assets/site.css?v=20260828a">'
NEW_HEAD = CSS + LD

CRED = ("運営：富士ヶ丘サービス株式会社（宅地建物取引業免許 静岡県知事 (2) 第14083号／"
        "宅地建物取引士 静岡県知事 第027186号〔大石浩之〕／"
        "所属団体 公益社団法人 全日本不動産協会・公益社団法人 不動産保証協会・公正取引協議会加盟事業者／"
        "TEL 0538-31-3308）")
BOX_P = '<!-- operator-credentials --><p style="margin:.35em 0 0;font-size:13px;color:#5b6660">%s</p>' % CRED
PROFILE_P = '<p style="margin:.35em 0 0"><a href="https://oishi-hiroyuki.org/profile">'
AUTHOR_CARD = ('<!-- operator-credentials --><section class="card"><h2 class="sec">運営者の資格・所属</h2>'
               '<p>富士ヶ丘サービス株式会社（静岡県磐田市見付5789番地1／TEL 0538-31-3308）</p>'
               '<p>宅地建物取引業免許：静岡県知事 (2) 第14083号<br>宅地建物取引士：静岡県知事 第027186号（大石浩之）<br>'
               '所属団体：公益社団法人 全日本不動産協会／公益社団法人 不動産保証協会／公正取引協議会加盟事業者</p></section>\n')
TERMS_OLD = "電話　0538-31-3308</p></div>"

def rd(p):
    with open(p, encoding="utf-8", newline="") as f: return f.read()
def wr(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(s)

changed = {"head": [], "box": [], "author": [], "terms": [], "skip": []}
def save(kind, rel, old, new):
    if new != old:
        changed[kind].append(rel)
        if APPLY: wr(os.path.join(ROOT, rel), new)

# parts
rel = "parts/head-css.html"; old = rd(os.path.join(ROOT, rel))
save("head", rel, old, NEW_HEAD if old.strip() != NEW_HEAD else old)

pat = re.compile(r"(<!-- PART:head-css:START -->).*?(<!-- PART:head-css:END -->)", re.S)
for p in sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)):
    rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
    if rel.split("/")[0] in ("parts", "tmp", "output", "scratchpad", "node_modules", ".git", "docs", "_audit"): continue
    s = rd(p); n = s
    if pat.search(s):
        n = pat.sub(lambda m: m.group(1) + NEW_HEAD + m.group(2), s, count=1)
    elif 'id="fgo-organization"' not in s and "</head>" in s and rel != "404.html":
        n = s.replace("</head>", LD + "</head>", 1)
    save("head", rel, s, n); s = n
    if 'class="post-author post-author-profile"' in s and "<!-- operator-credentials -->" not in s:
        if s.count(PROFILE_P) != 1: changed["skip"].append(rel + " (box anchor)"); continue
        n = s.replace(PROFILE_P, BOX_P + PROFILE_P, 1); save("box", rel, s, n)
    if rel == "author/oishi-hiroyuki/index.html" and "<!-- operator-credentials -->" not in s:
        nl = "\r\n" if "\r\n" in s else "\n"
        k = '<section class="card">' + nl + '<h2 class="sec">記事と運営情報</h2>'
        if k in s: save("author", rel, s, s.replace(k, AUTHOR_CARD.replace("\n", nl) + k, 1))
        else: changed["skip"].append(rel + " (anchor)")
    if rel == "terms/index.html" and "運営者の資格" not in s and s.count(TERMS_OLD) == 1:
        add = ("電話　0538-31-3308<br>宅地建物取引業免許：静岡県知事 (2) 第14083号<br>"
               "宅地建物取引士：静岡県知事 第027186号（大石浩之）<br>"
               "所属団体：公益社団法人 全日本不動産協会／公益社団法人 不動産保証協会／公正取引協議会加盟事業者</p></div>")
        save("terms", rel, s, s.replace(TERMS_OLD, add, 1))

for k, v in changed.items(): print(k, len(v))
for r in changed["skip"]: print("SKIP", r)
print("APPLIED" if APPLY else "DRY-RUN")
