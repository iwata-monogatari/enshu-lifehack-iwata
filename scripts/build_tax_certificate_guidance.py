#!/usr/bin/env python3
"""Render only the tax-certificate page from reviewed guidance and canonical FAQ.

Run this after editing data/tax-certificate-guidance.json or the target FAQ in
data/categories.json, then regenerate search-index.json. Never reads old D1 data.
"""
from pathlib import Path
import argparse, html, json, re
from inject_faq_jsonld import build_jsonld

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'life/work-life/tax-certificates/index.html'
START, END = '<!-- TAX-GUIDANCE:START -->', '<!-- TAX-GUIDANCE:END -->'
URL = 'https://iwata.enshu-lifehack.com/life/work-life/tax-certificates/'
ONLINE = 'https://www.city.iwata.shizuoka.jp/kurashi_tetsuzuki/zeikin/shizei_shoumei/1012724.html'
COUNTER = 'https://www.city.iwata.shizuoka.jp/kurashi_tetsuzuki/zeikin/shizei_shoumei/1001381.html'

def esc(value):
    return html.escape(value, quote=True)

def render(data):
    style = ('<style>#tax-certificate-guidance{margin:24px 0;padding:18px;border:1px solid #cfe4f1;border-radius:12px;background:#f6fafc}'
             '#tax-certificate-guidance p,#tax-certificate-guidance li{line-height:1.85}'
             '#tax-certificate-guidance .tax-table-scroll{overflow-x:auto;max-width:100%;margin:12px 0}'
             '#tax-certificate-guidance .tax-table-scroll:focus-visible{outline:3px solid #006b8f;outline-offset:3px}'
             '#tax-certificate-guidance table{width:100%;min-width:660px;border-collapse:collapse;background:#fff}'
             '#tax-certificate-guidance th,#tax-certificate-guidance td{border:1px solid #cbd5dc;padding:12px;text-align:left;vertical-align:top;line-height:1.8}'
             '#tax-certificate-guidance thead{background:#e8f2f5}#tax-certificate-guidance th[scope=row]{width:16%}'
             '#tax-certificate-guidance .tax-sources a{margin:0;min-height:44px;display:inline-flex;align-items:center}'
             '#tax-certificate-guidance .tax-sources li{margin:6px 0}</style>')
    steps = ''.join('<li>%s</li>' % esc(s) for s in data['steps'])
    rows = ''.join('<tr><th scope="row">%s</th><td>%s</td><td>%s</td></tr>' %
                   (esc(m['name']), esc(m['conditions']), esc(m['next'])) for m in data['methods'])
    sources = ''.join('<li><a href="%s" target="_blank" rel="noopener">%s（市公式）</a></li>' %
                      (esc(s['url']), esc(s['label'])) for s in data['sources'])
    return (START + style + '<section id="tax-certificate-guidance" aria-labelledby="tax-certificate-heading">'
            '<h2 class="sec" id="tax-certificate-heading">%s</h2><p>年度・取得方法の確認日：<time datetime="%s">%s</time></p>' %
            (esc(data['heading']), data['checked'], data['checked'].replace('-', '/')) +
            '<h3>%s</h3><ol>%s</ol><h3>取得方法の選択表</h3><p>表は横にスクロールできます。</p>' % (esc(data['example_heading']), steps) +
            '<div class="tax-table-scroll" tabindex="0" role="region" aria-label="税証明の取得方法の比較表">'
            '<table><caption>所得・課税証明の取得方法と条件</caption><thead><tr><th scope="col">方法</th><th scope="col">年度・住所</th>'
            '<th scope="col">本人・代理と次の確認</th></tr></thead><tbody>%s</tbody></table></div>' % rows +
            '<p>%s</p><h3>公式の条件を確認する</h3><ul class="tax-sources">%s</ul></section>' % (esc(data['note']), sources) + END)

def transform(src, data, item):
    block = render(data)
    pattern = re.escape(START) + '.*?' + re.escape(END)
    if START in src:
        assert src.count(START) == src.count(END) == 1
        src = re.sub(pattern, lambda _: block, src, flags=re.S)
    else:
        old = '<div class="note">マイナンバーカードをお持ちの場合、最新年度の所得・課税（非課税）証明書はコンビニで取得可能です。</div>'
        assert src.count(old) == 1, 'Tax guidance insertion point missing'
        src = src.replace(old, block, 1)
    src, n = re.subn(r'<p class="lead">.*?</p>', '<p class="lead">%s</p>' % esc(data['lead']), src, count=1, flags=re.S)
    assert n == 1
    for attr in ['name="description"', 'property="og:description"', 'name="twitter:description"']:
        src, n = re.subn(r'(<meta '+re.escape(attr)+r' content=")[^"]*(">)', lambda m:m[1]+esc(data['lead'])+m[2], src, count=1)
        assert n == 1, attr
    faq = '<h2 class="sec">不安を先につぶすQ&A</h2><div class="qa">' + ''.join(
        '<details%s><summary>%s</summary><p>%s</p></details>' % (' open' if i == 0 else '', esc(f['q']), esc(f['a']))
        for i, f in enumerate(item['faq'])) + '</div>'
    src, n = re.subn(r'<h2 class="sec">不安を先につぶすQ&A</h2><div class="qa">.*?</div>(?=<h2 class="sec">タイプ別)', lambda _:faq, src, count=1, flags=re.S)
    assert n == 1, 'FAQ display insertion point missing'
    ld = '<!-- FAQ-JSONLD:START --><script type="application/ld+json">'+build_jsonld(item['faq'])+'</script><!-- FAQ-JSONLD:END -->'
    src, n = re.subn(r'<!-- FAQ-JSONLD:START -->.*?<!-- FAQ-JSONLD:END -->', lambda _:ld, src, count=1, flags=re.S)
    assert n == 1
    src = re.sub(r'(オンラインでできること：).*?(</div>)', lambda m:m[1]+esc(item['online_note'])+m[2], src, count=1)
    # Existing online/counter labels pointed to the opposite official pages.
    def links(m):
        label = re.sub(r'<span\b[^>]*class="badge"[^>]*>.*?</span>', '', m[4], flags=re.S)
        label = re.sub('<[^>]+>', '', label).removesuffix('磐田市公式').strip()
        target = ONLINE if label in ('オンライン申請','証明オンライン申請') else COUNTER if label in ('窓口での申請','窓口申請について','証明窓口申請') else m[2]
        return m[1]+target+m[3]+m[4]+'</a>'
    src = re.sub(r'(<a\b[^>]*href=")([^"]+)("[^>]*>)(.*?)</a>', links, src, flags=re.S)
    src = re.sub(r'<p class="verified">.*?</p>', '<p class="verified">所得・課税証明の年度・取得方法を確認：%s。必要年度、住所条件、申告の要否、必要書類は磐田市公式ページで確認してください。</p>' % data['checked'].replace('-', '/'), src, count=1)
    return src

def main():
    ap = argparse.ArgumentParser();ap.add_argument('--check', action='store_true');args=ap.parse_args()
    data=json.loads((ROOT/'data/tax-certificate-guidance.json').read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'data/categories.json').read_text(encoding='utf-8-sig'))
    item=next(x for c in cats['categories'] for x in c['items'] if x['url']==URL)
    raw=PAGE.read_bytes().decode('utf-8');new=transform(raw,data,item)
    if args.check:
        if new!=raw: print('Tax guidance needs regeneration');return 1
    elif new!=raw:PAGE.write_bytes(new.encode('utf-8'))
    print('Tax guidance and canonical FAQ are consistent');return 0

if __name__=='__main__':raise SystemExit(main())
