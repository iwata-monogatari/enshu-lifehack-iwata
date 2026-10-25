"""Editorial navigation; keep promotional choices explicit and reproducible."""
import html
import re
from pathlib import Path
from urllib.parse import urlencode

ESC = html.escape
CSS_HREF = '/assets/blog.css?v=20261021-navigation'
RECOMMENDED = (
    '20260828-bulky-garbage-estate-cleanout',
    '20260827-child-allowance-highschool',
    '20260827-five-districts',
)
# A single destination chosen for each relevant article, never by weekday alone.
CONSULTATIONS = {
    '20260828-bulky-garbage-estate-cleanout': 'belongings',
    '20260918-iwata-oversized-trash-guide': 'belongings',
    '20261006-iwata-heir-representative-form-preparation': 'inheritance',
    '20260908-inheritance-registration-vs-heir-declaration': 'inheritance',
    '20260908-vacant-house-30m-deduction': 'inheritance',
    '20260908-property-record-certificate-vs-nayosecho': 'inheritance',
    '20261020-iwata-inheritance-consultation-comparison': 'inheritance',
    '20261013-iwata-akiya-mimawari': 'distant-home',
    '20260929-iwata-demolition-subsidy-comparison': 'difficult-property',
    '20260922-iwata-akiya-consultation-family-memo': 'sell-rent-keep',
    '20260915-inherited-home-rebuild-subsidy': 'sell-rent-keep',
    '20260908-iwata-vacant-house-count-1880': 'sell-rent-keep',
    '20260829-akiya-bank-vs-okoshi-project': 'sell-rent-keep',
}
COPY = {
    'belongings': ('片付けた後の実家を、どうするか迷っている方へ', '荷物の整理と、家を売る・貸す・残す判断を、一緒に整理できます。売却が決まっていなくても相談できます。', '荷物が残った実家の相談・カルテの見本を見る'),
    'inheritance': ('相続した家の使い道も、整理したい方へ', '家の価格の目安と確認すべき点、次にすることを実家カルテで整理します。法律・税務の個別判断は、それぞれの専門家に確認します。', '相続した実家の相談・カルテの見本を見る'),
    'distant-home': ('遠方の実家を、これからどう管理するか', '帰省や管理の負担と家の状態を整理し、売る・貸す・残す選択肢を考えます。県外にお住まいのご家族も相談できます。', '遠方の実家の相談・カルテの見本を見る'),
    'difficult-property': ('古い家を、解体するか迷っている方へ', '家や土地の条件と価格の目安を整理してから、次の進め方を考えます。解体や売却を決める前の段階でも相談できます。', '古い家・土地の相談・カルテの見本を見る'),
    'sell-rent-keep': ('実家を売る・貸す・残す。まだ決まっていない方へ', '家の価格の目安、管理の負担、確認すべき課題を実家カルテで整理します。ご家族で判断するための材料としてご利用ください。', '実家の選択肢とカルテの見本を見る'),
}
CURATED_RELATED = {
    '20261025-iwata-fire-alarm-check': ['20260922-iwata-seismic-breaker-comparison', '20260906-iwata-disaster-drill-family-check'],
    # From clearing the house to managing it, then deciding its future.
    '20260828-bulky-garbage-estate-cleanout': ['20261013-iwata-akiya-mimawari', '20260829-akiya-bank-vs-okoshi-project'],
    '20260918-iwata-oversized-trash-guide': ['20260828-bulky-garbage-estate-cleanout', '20261013-iwata-akiya-mimawari'],
    '20261013-iwata-akiya-mimawari': ['20260922-iwata-akiya-consultation-family-memo', '20260829-akiya-bank-vs-okoshi-project'],
    '20261020-iwata-inheritance-consultation-comparison': ['20260908-inheritance-registration-vs-heir-declaration', '20260922-iwata-akiya-consultation-family-memo'],
}


def related_posts(current, posts):
    by_slug = {p['slug']: p for p in posts}
    if current['slug'] in CURATED_RELATED:
        return [by_slug[s] for s in CURATED_RELATED[current['slug']]]
    # Specific subject matches outrank broad editorial axes. Do not fill a
    # subject-specific article with unrelated recent posts when none match.
    groups = [r'ごみ|リサイクル|片付け', r'相続|空き家|実家|不動産|名寄帳',
              r'図書館|読書', r'介護|高齢|人生会議|スロープ',
              r'保育|こども|子育て|出産|母子', r'学校|就学|児童|学区',
              r'防災|避難|災害|感震|耐震', r'文化財|歴史|古墳|史料|神社']
    topics = {i for i, pattern in enumerate(groups) if re.search(pattern, current['title'])}
    paths = {r['href'] for r in current.get('related_life', []) if r['href'].strip('/').count('/') >= 2}
    existing = {r['href'] for r in current.get('related_life', [])}
    ranked = []
    for p in posts:
        if p['slug'] == current['slug'] or '/blog/' + p['slug'] + '/' in existing:
            continue
        shared_topics = sum(bool(re.search(groups[i], p['title'])) for i in topics)
        shared_paths = len(paths & {r['href'] for r in p.get('related_life', [])})
        score = shared_topics * 10 + shared_paths * 5
        if not topics and p['axis'] == current['axis']:
            score += 1
        if score:
            ranked.append((score, p['date'], p['slug'], p))
    return [item[3] for item in sorted(ranked, key=lambda x: x[:3], reverse=True)[:2]]


def consultation_block(post):
    topic = CONSULTATIONS.get(post['slug'])
    if not topic:
        return ''
    title, description, label = COPY[topic]
    query = urlencode({'utm_source': 'iwata-lifehack', 'utm_medium': 'referral',
                       'utm_campaign': 'article-consultation', 'utm_content': post['slug']})
    href = 'https://fudosan.atawi.link/lp/' + topic + '/?' + query + '#sample'
    return ('<!-- BLOG_CONSULTATION:START --><aside class="post-consultation" aria-labelledby="post-consultation-title">'
            '<p class="post-consultation-label">運営会社・富士ヶ丘サービスの不動産相談</p>'
            '<h2 id="post-consultation-title">%s</h2><p>%s</p>'
            '<a href="%s" data-track-click="article_consultation_%s">%s <span aria-hidden="true">→</span></a>'
            '<p class="post-consultation-note">相談・標準の実家カルテは無料。申込みだけで売却依頼にはなりません。市役所の窓口ではありません。</p>'
            '</aside><!-- BLOG_CONSULTATION:END -->') % (ESC(title), ESC(description), ESC(href), topic.replace('-', '_'), ESC(label))


def update_article(src, post):
    src = re.sub(r'/assets/blog\.css\?v=[^"\s]+', CSS_HREF, src)
    src = re.sub(r'\n?<!-- BLOG_CONSULTATION:START -->.*?<!-- BLOG_CONSULTATION:END -->', '', src, flags=re.S)
    if post['slug'] in CONSULTATIONS:
        # Replace the existing commercial card where present; do not duplicate it.
        src = re.sub(r'<!-- family-home-referral:start -->.*?<!-- family-home-referral:end -->\s*', '', src, flags=re.S)
        # Immediately after the editorial body, preserving the audit's action-grid boundary.
        src, count = re.subn(r'(<div class="action-grid">.*?</div>)',
                            lambda m: m[0] + '\n' + consultation_block(post), src, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Missing action-grid: ' + post['slug'])
    # Keep all existing network links available, but remove competing choices
    # from the default reading path. Wrapper sits outside shared-part markers.
    if 'class="post-network"' not in src:
        src = src.replace('<!-- PART:footer:START -->',
                          '<details class="post-network"><summary>運営者・関連サイトを見る（不動産・介護・地域情報）</summary>\n<!-- PART:footer:START -->', 1)
        src = src.replace('<!-- PART:footer:END -->', '<!-- PART:footer:END -->\n</details>', 1)
    return src


def update_home(root, posts, axis_labels):
    path = Path(root) / 'index.html'
    src = path.read_text(encoding='utf-8')
    by_slug = {p['slug']: p for p in posts}
    latest = sorted(posts, key=lambda p: (p['date'], p['slug']), reverse=True)[:3]
    def cards(items):
        result = []
        for p in items:
            result.append('<article class="home-blog-card"><a href="/blog/{slug}/"><img src="/blog/{slug}/{cover}" alt="" width="760" height="760" loading="lazy"><span class="home-blog-body"><span class="home-blog-meta"><time datetime="{date}">{display_date}</time><span>{axis}</span></span><span class="home-blog-title">{title}</span><span class="home-blog-desc">{description}</span></span></a></article>'.format(
                slug=ESC(p['slug']), cover=ESC(p.get('cover', 'cover.jpg')), date=p['date'], display_date=p['date'].replace('-', '.'),
                axis=ESC(axis_labels[p['axis']]), title=ESC(p['title']), description=ESC(p.get('home_description', p['description']))))
        return '\n'.join(result)
    block = ('<section class="home-blog" aria-labelledby="blog-title">\n'
             '<div class="home-blog-heading"><div><p class="eyebrow">IWATA BLOG</p><h2 id="blog-title">磐田ブログ</h2><p class="lead">磐田市の暮らし・手続き・住まい・地区について、市の公表情報を確認しながら書いています。</p></div><a class="home-blog-all" href="/blog/">記事をすべて見る <span aria-hidden="true">→</span></a></div>\n'
             '<h3 id="blog-latest-title">最新記事</h3><div class="home-blog-grid" aria-labelledby="blog-latest-title">%s</div>\n'
             '<h3 id="blog-recommended-title">暮らしのおすすめ記事</h3><div class="home-blog-grid" aria-labelledby="blog-recommended-title">%s</div>\n</section>') % (cards(latest), cards([by_slug[s] for s in RECOMMENDED]))
    new, count = re.subn(r'<section class="home-blog".*?</section>', lambda m: block, src, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Missing home blog section')
    if new != src:
        path.write_text(new, encoding='utf-8', newline='')
    return new != src
