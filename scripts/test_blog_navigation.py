"""Regression checks for generated discovery and consultation paths."""
import json
import re
import tempfile
import unittest
from pathlib import Path

import blog_navigation as nav
from build_blog import AXIS_LABEL, ROOT


class NavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(ROOT)
        cls.posts = json.loads((cls.root / 'data/blog-posts.json').read_text(encoding='utf-8-sig'))['posts']
        cls.by_slug = {p['slug']: p for p in cls.posts}

    def test_article_outputs_and_idempotence(self):
        for post in self.posts:
            with self.subTest(slug=post['slug']):
                src = (self.root / 'blog' / post['slug'] / 'index.html').read_text(encoding='utf-8')
                self.assertEqual(src, nav.update_article(src, post))
                self.assertEqual(src.count('class="post-network"'), 1)
                self.assertIn('<!-- PART:footer:START -->', src)
                self.assertEqual(src.count('class="post-consultation"'), int(post['slug'] in nav.CONSULTATIONS))
                if post['slug'] in nav.CONSULTATIONS:
                    block = re.search(r'<!-- BLOG_CONSULTATION:START -->(.*?)<!-- BLOG_CONSULTATION:END -->', src, re.S)[1]
                    self.assertEqual(block.count('<a '), 1)
                    self.assertIn('#sample', block)
                    self.assertNotIn('<!-- family-home-referral:start -->', src)

    def test_related_links_exist_and_exclude_self(self):
        for post in self.posts:
            selected = nav.related_posts(post, self.posts)
            slugs = [p['slug'] for p in selected]
            self.assertEqual(len(slugs), len(set(slugs)))
            self.assertNotIn(post['slug'], slugs)
            for slug in slugs:
                self.assertTrue((self.root / 'blog' / slug / 'index.html').exists())

    def test_cleanup_leads_to_management_and_options(self):
        current = self.by_slug['20260828-bulky-garbage-estate-cleanout']
        self.assertEqual([p['slug'] for p in nav.related_posts(current, self.posts)],
                         ['20261013-iwata-akiya-mimawari', '20260829-akiya-bank-vs-okoshi-project'])

    def test_home_updates_when_new_article_arrives(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'index.html'
            home.write_text('<section class="home-blog">old</section>', encoding='utf-8')
            future = dict(self.posts[0], slug='20990101-future', date='2099-01-01', title='New article')
            nav.update_home(tmp, self.posts + [future], AXIS_LABEL)
            result = home.read_text(encoding='utf-8')
            self.assertLess(result.index('/blog/20990101-future/'), result.index('id="blog-recommended-title"'))
            self.assertIn('暮らしのおすすめ記事', result)
            self.assertFalse(nav.update_home(tmp, self.posts + [future], AXIS_LABEL))


if __name__ == '__main__':
    unittest.main()
