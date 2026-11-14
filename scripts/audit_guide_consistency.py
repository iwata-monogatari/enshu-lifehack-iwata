#!/usr/bin/env python3
"""Read-only checks for published HTML and the maintained guide data.

Requires BeautifulSoup4 for HTML parsing. Does not call production APIs.
"""
import json
import pathlib
import sys
import urllib.parse
from collections import Counter

from bs4 import BeautifulSoup
from derive_instant_header_fields import derive
from inject_instant_header import build_box
from inject_channel_badges import build_badges_html

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = 'https://iwata.enshu-lifehack.com'
EXCLUDE = {'.git', '.wrangler', 'node_modules', 'parts', 'docs', 'tmp', 'output', 'scratchpad', '_template'}


def normalized(value):
    return ' '.join(value.split())


def visible_faq(soup):
    result = []
    for detail in soup.select('.qa details'):
        copy = BeautifulSoup(str(detail), 'html.parser')
        question = copy.find('summary')
        if question:
            label = question.get_text(' ', strip=True)
            question.extract()
            result.append({'q': label, 'a': copy.get_text(' ', strip=True)})
    return result


def audit():
    errors = []
    blog_answers = 0
    files = [p for p in ROOT.rglob('*.html') if not (set(p.relative_to(ROOT).parts) & EXCLUDE)]
    documents = {p: BeautifulSoup(p.read_bytes(), 'html.parser') for p in files}
    refs = 0
    for path, soup in documents.items():
        rel = path.relative_to(ROOT).as_posix()
        if rel == '404.html':
            continue
        canonicals = soup.select('link[rel="canonical"]')
        expected = SITE + '/' + (rel[:-10] if rel.endswith('index.html') else rel)
        if len(canonicals) != 1 or canonicals[0].get('href') != expected:
            errors.append([rel, 'canonical', expected])
        if len(soup.select('h1')) != 1:
            errors.append([rel, 'h1-count', len(soup.select('h1'))])
        if soup.select('[data-feedback], .feedback-box'):
            errors.append([rel, 'inert-feedback-ui'])
        ids = Counter(node['id'] for node in soup.select('[id]'))
        if any(count > 1 for count in ids.values()):
            errors.append([rel, 'duplicate-ids', [key for key, count in ids.items() if count > 1]])
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())
                if rel.startswith('blog/'):
                    for entry in data.get('@graph', [data]):
                        if entry.get('@type') != 'FAQPage':
                            continue
                        for question in entry['mainEntity']:
                            blog_answers += 1
                            heading = next((h for h in soup.select('h3,summary') if h.get_text(' ', strip=True) == question['name']), None)
                            answer = None if not heading else heading.parent.find('p') if heading.name == 'summary' else heading.find_next_sibling('p')
                            combined = next((p.get_text(' ', strip=True)[len(question['name']):].strip() for p in soup.select('main p') if p.get_text(' ', strip=True).startswith(question['name'])), None)
                            if (not answer or answer.get_text(' ', strip=True) != question['acceptedAnswer']['text']) and combined != question['acceptedAnswer']['text']:
                                errors.append([rel, 'blog-faq-vs-schema', question['name']])
            except ValueError as error:
                errors.append([rel, 'invalid-jsonld', str(error)])
        for node in soup.select('[href], img[src], script[src]'):
            raw = node.get('href') or node.get('src')
            if not raw:
                continue
            url = urllib.parse.urlparse(urllib.parse.urljoin(SITE + '/' + rel, raw))
            if url.scheme not in ('https', 'http') or url.netloc != 'iwata.enshu-lifehack.com':
                continue
            target = ROOT / urllib.parse.unquote(url.path).lstrip('/')
            if url.path.endswith('/'):
                target /= 'index.html'
            if not target.exists():
                errors.append([rel, 'missing-local-target', raw])
                continue
            refs += 1
            if url.fragment and target.suffix == '.html':
                other = documents.get(target)
                if other is None:
                    other = BeautifulSoup(target.read_bytes(), 'html.parser')
                fragment = urllib.parse.unquote(url.fragment)
                if not other.find(id=fragment) and not other.find('a', attrs={'name': fragment}):
                    errors.append([rel, 'missing-local-anchor', raw])
    categories = json.loads((ROOT / 'data/categories.json').read_text(encoding='utf-8'))
    total = 0
    for category in categories['categories']:
        for item in category['items']:
            total += 1
            path = ROOT / urllib.parse.urlparse(item['url']).path.strip('/') / 'index.html'
            soup = documents[path]
            expected_badges = BeautifulSoup(build_badges_html(item.get('channels', [])), 'html.parser')
            badges = lambda document: [normalized(node.get_text(' ', strip=True)) for node in document.select('.channel-badge')]
            if badges(soup) != badges(expected_badges):
                errors.append([item['id'], 'channel-badges-vs-source'])
            faq = visible_faq(soup)
            if faq != item.get('faq', []):
                errors.append([item['id'], 'visible-faq-vs-source'])
            structured = []
            for script in soup.select('script[type="application/ld+json"]'):
                data = json.loads(script.string or script.get_text())
                for entry in data.get('@graph', [data]):
                    if entry.get('@type') == 'FAQPage':
                        structured.extend({'q': x['name'], 'a': x['acceptedAnswer']['text']} for x in entry['mainEntity'])
            if structured != faq:
                errors.append([item['id'], 'visible-faq-vs-schema'])
            expected = dict(item, **derive(item))
            box = build_box(expected)
            actual = soup.select_one('.instant-header')
            if box and (not actual or normalized(actual.get_text(' ', strip=True)) != normalized(BeautifulSoup(box, 'html.parser').get_text(' ', strip=True))):
                errors.append([item['id'], 'instant-header-vs-source'])
    contacts = {
        'housing/build-house': '0538-37-4935',
        'housing/buy-house': '0538-37-4851',
        'housing/municipal-housing': '0538-37-4851',
        'housing/earthquake-demolition': '0538-37-4899',
        'housing/clean-parents-house': '0538-37-4812',
        'family-grow/child-vaccination': '0538-37-2012',
        'family-grow/nursery-childcare': '0538-37-4858',
        'troubles-consult/cannot-pay-tax': '0538-37-4906',
    }
    for name, telephone in contacts.items():
        soup = documents[ROOT / 'life' / name / 'index.html']
        calls = [a.get('href') for a in soup.select('.cta-row a[href^="tel:"]')]
        if 'tel:' + telephone not in calls:
            errors.append([name, 'reviewed-telephone-button', calls])
        if name == 'housing/clean-parents-house' and not any('ごみ資源循環課' in a.get_text() for a in soup.select('.cta-row a[href^="tel:"]')):
            errors.append([name, 'reviewed-department-name'])
    for name, marker in {
        'start-living/public-transit': 'trial-reservation-update',
        'troubles-consult/farmland': 'farmland-bank-scope',
    }.items():
        if not documents[ROOT / 'life' / name / 'index.html'].find(id=marker):
            errors.append([name, 'missing-reviewed-answer', marker])
    css = (ROOT / 'assets/site.css').read_text(encoding='utf-8')
    if 'body:not(.hub) .hero-visual{' not in css or 'display:flex;flex-direction:column;align-items:stretch' not in css:
        errors.append(['assets/site.css', 'guide-hero-stacking'])
    return {'html': len(files), 'guides': total, 'blog_faq_answers': blog_answers, 'local_references': refs, 'errors': errors}


if __name__ == '__main__':
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(bool(report['errors']))
