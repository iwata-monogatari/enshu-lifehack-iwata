"""Add reciprocal reading links from existing, explicit editorial references.

Standard library only. Never infer relationships from search metrics or attach
unrelated pages. Generated blocks are ignored when deriving the relationship map.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from html import escape, unescape
import re

START = '<!-- DISCOVERY:START -->'
END = '<!-- DISCOVERY:END -->'
BLOCK = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
STYLE = '''<style>.discovery-links{max-width:1040px;margin:24px auto;padding:20px;border:1px solid #d5ddd7;border-radius:8px;background:#f7faf7;color:#202a24}.discovery-links h2{font-size:1.25rem;margin:0 0 10px}.discovery-links p{margin:0 0 10px}.discovery-links ul{margin:0;padding-left:22px}.discovery-links li{margin:6px 0}.discovery-links a{display:inline-block;padding:8px 2px;color:#245441;text-decoration:underline;line-height:1.6;overflow-wrap:anywhere}</style>'''

class EditorialLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_main = False
        self.in_title = False
        self.title = ''
        self.links = set()
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'main': self.in_main = True
        if tag == 'title': self.in_title = True
        if tag == 'a' and self.in_main and values.get('href'):
            self.links.add(values['href'])
    def handle_endtag(self, tag):
        if tag == 'main': self.in_main = False
        if tag == 'title': self.in_title = False
    def handle_data(self, text):
        if self.in_title: self.title += text

def apply(root, host, source_prefixes, target_prefixes, label='このテーマを扱う関連記事'):
    root = Path(root)
    pages = {}
    for file in sorted(root.rglob('index.html')):
        rel = file.parent.relative_to(root)
        if any(part.startswith('.') or part.startswith('_') or part in ('node_modules','work') for part in rel.parts): continue
        route = '/' if str(rel) == '.' else '/' + rel.as_posix() + '/'
        raw = file.read_text(encoding='utf-8')
        cleaned = BLOCK.sub('', raw)
        parser = EditorialLinks()
        parser.feed(cleaned)
        links = set()
        for href in parser.links:
            url = urlsplit(unescape(href))
            if url.netloc and url.netloc != host: continue
            if url.scheme and url.scheme not in ('http','https'): continue
            if url.path.startswith('/'):
                path = url.path.replace('/index.html','/')
                if not Path(path).suffix and not path.endswith('/'): path += '/'
                links.add(path)
        pages[route] = (file,raw,cleaned,parser.title.strip(),links)
    inbound = {}
    for route, (_,raw,cleaned,title,links) in pages.items():
        if not any(route.startswith(p) and route != p for p in source_prefixes): continue
        if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', raw, re.I): continue
        for target in sorted(links):
            if target == route or target not in pages: continue
            if not any(target.startswith(p) and target != p for p in target_prefixes): continue
            # These are presentation routes, not a topic to be promoted.
            if '/photos/' in target or '/feed' in target: continue
            if route in pages[target][4]: continue
            inbound.setdefault(target,[]).append((route,title))
    changed = {}
    total = 0
    for route, (file,raw,cleaned,title,links) in pages.items():
        referring = sorted(set(inbound.get(route,[])), reverse=True)[:4]
        block = ''
        if referring:
            entries = ''.join('<li><a href="%s">%s</a></li>' % (escape(url,quote=True),escape(t.split('｜ATAWI')[0].split(' | 磐田ライフハック')[0])) for url,t in referring)
            block = START + STYLE + '<section class="discovery-links" aria-labelledby="discovery-title"><h2 id="discovery-title">' + escape(label) + '</h2><p>このページの内容を取り上げた記事から、背景や確認する手順を読めます。</p><ul>' + entries + '</ul></section>' + END
            total += len(referring)
        # Place inside the reading column if it has an article, otherwise in main.
        new = cleaned
        if block:
            main_end = cleaned.find('</main>')
            article_end = cleaned.rfind('</article>',0,main_end)
            at = article_end if article_end >= 0 and '<article' in cleaned[cleaned.find('<main'):article_end] else main_end
            if at < 0: raise ValueError('main missing: ' + route)
            new = cleaned[:at] + block + cleaned[at:]
        if new != raw:
            file.write_text(new,encoding='utf-8')
            changed[route] = new
    return changed, total

def update_sitemap(root, routes, date):
    """Update only routes whose rendered content changed; preserve XML prefixes."""
    sitemap = Path(root) / 'sitemap.xml'
    raw = sitemap.read_text(encoding='utf-8')
    def update(m):
        loc = re.search(r'<loc>(.*?)</loc>',m[0])
        if not loc or urlsplit(unescape(loc[1])).path not in routes: return m[0]
        if '<lastmod>' in m[0]:
            return re.sub(r'<lastmod>.*?</lastmod>', '<lastmod>'+date+'</lastmod>', m[0])
        return m[0].replace('</url>','<lastmod>'+date+'</lastmod></url>')
    new = re.sub(r'<url>.*?</url>',update,raw,flags=re.S)
    if new != raw: sitemap.write_text(new,encoding='utf-8')
