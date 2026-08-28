# enshu-lifehack-iwata

磐田ライフハック（遠州ライフハック 磐田版）の **静的サイト** リポジトリ。
公開先：`https://iwata.enshu-lifehack.com/`（Cloudflare Pages）

## 構成

静的HTMLのみ。Cloudflare Pages の **Build output directory = `/`**（ビルド不要）で配信する。

```
index.html              トップ（くらしの場面・目的から選ぶ）
life/<大項目>/           くらしの大項目ページ
life/<大項目>/<中項目>/   個別ページ
sitemap.xml             サイトマップ
robots.txt
_redirects              旧 /iwata/ 配下 → 直下への 301
404.html                カスタム404
favicon.svg
```

## 生成方法（再生成手順）

このサイトは Cloudflare Workers + D1 で動く本番（`iwata-hack`）の公開ページを
クロールして静的化したスナップショットである。元データを更新したら再生成する。

1. 本番 `iwata-hack` を最新化（クロール／デプロイ）
2. `iwata-hack` リポジトリ内の `scripts/snapshot.mjs`（または scratchpad の同等スクリプト）を
   Node で実行し、このディレクトリへ出力
3. 差分を commit / push → Cloudflare Pages が自動デプロイ

## ブログ `/blog/`

森町ライフハック（`enshu-lifehack-morimachi`）と同じ「台帳＋手書き記事＋品質ゲート」方式。
**記事本体は手書き。生成物は `blog/index.html` と `sitemap.xml` のブログ区画だけ。**

```
data/blog-posts.json        記事台帳（手で1行足す）
blog/<slug>/index.html      記事の実体（手書き。slug は YYYYMMDD-テーマ英語）
blog/<slug>/cover.jpg       表紙 760x760（make_blog_cover.py が生成）
blog/<slug>/fig1.svg,fig2.svg  記事固有の挿絵（data-illustration="iwata-editorial" 必須）
blog/_template/             記事テンプレート（.assetsignore 済みで非公開）
blog/index.html             ★生成物★ build_blog.py が作る。手編集しない
assets/blog.css             ブログ専用CSS（site.css は触らないので既存ページの ?v= 据え置き）
scripts/build_blog.py       品質ゲート＋一覧＋sitemap のブログ区画を生成
scripts/make_blog_cover.py  表紙 cover.jpg を生成
```

### 公開手順

```bash
cp -r blog/_template blog/20260901-example      # 1. 雛形をコピー
#   2. {{...}} を全部置き換えて記事を書く（残置チェック: grep -r "{{" blog/<slug>/）
#   3. data/blog-posts.json の posts に1件追記
python scripts/make_blog_cover.py 20260901-example   # 4. 表紙を作る
#   5. fig1.svg / fig2.svg を用意
python scripts/inject_parts.py                       # 6. header/footer を流し込む
python scripts/build_blog.py --check                 # 7. 検査だけ（書き込みなし）
python scripts/build_blog.py                         # 8. 一覧＋sitemap を生成
python scripts/ensure_canonical.py                    # 9. 全公開HTMLのcanonicalを正規化
git add -A && git commit && git push                 # 10. main へ push → Cloudflare が自動デプロイ
```

### 品質ゲート（`build_blog.py` が機械で見る範囲）

編集本文5,000文字以上／段落35以上／磐田市公式（`www.city.iwata.shizuoka.jp`）の出典2本以上／
`良い点`・`注文したい点`・`対案・結論`・`大石の視点` の各セクション／`post-author`／
`cover.jpg`／`fig1.svg`・`fig2.svg`／`/assets/blog.css` の読み込み／禁止語なし／
タイトル・slug の重複なし／台帳に無い `blog/<dir>/` が無いこと。
1件でも引っかかると `blog/index.html` は生成されない。

内容が本当に一次情報かどうかは機械では判定できない。最終確認は執筆者が行う。

### 禁止語

`build_blog.py` の `BANNED_WORDS` に「政策」を入れてある（森町版から引き継ぎ）。
このサイトは暮らしと手続きの非公式案内であり、同じ運営者の政治系サイトとは役割を分けるため。

### 曜日別テーマ軸（台帳の `axis`）

mon=手続き・制度／tue=空き家・実家・相続／wed=歴史・文化財／thu=子育て・学び／
fri=地区めぐり／sat=スポーツ・イベント／sun=移住・暮らし・データ

## 静的化に伴う仕様

- **検索バー**：本番の動的検索（`/navigate`）は使えないため、Google サイト内検索に置換。
- **「相談先を探す」リンク**：相談ハブ `/life/troubles-consult/` に置換。
- **フィードバックボタン**：送信先API（`/api/feedback`）が無いため記録はされないが、
  クリックで「ありがとうございます」表示までは動作する（UX上は無害）。
- **困りごとガイド / category / article ページ**：本番でも公開ナビ・sitemap から未リンクのため未収録。

## 免責

本サイトは磐田市公式サイトではありません。最新・正確な情報は磐田市公式サイトをご確認ください。
運営：富士ヶ丘サービス ／ 代表：大石浩之
