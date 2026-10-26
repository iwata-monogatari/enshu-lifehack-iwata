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
**記事本文は手書き。一覧・Atomフィード・関連記事・サイトマップのブログ区画は台帳から生成します。**

```
data/blog-posts.json        記事台帳（手で1行足す）
blog/<slug>/index.html      記事の実体（手書き。slug は YYYYMMDD-テーマ英語）
blog/<slug>/cover.jpg       表紙 760x760（make_blog_cover.py が生成）
blog/<slug>/fig1.svg,fig2.svg  記事固有の挿絵（data-illustration="iwata-editorial" 必須）
blog/_template/             記事テンプレート（.assetsignore 済みで非公開）
blog/index.html             ★生成物★ build_blog.py が作る。手編集しない
blog/feed.xml              ★生成物★ 新着記事のAtomフィード
author/oishi-hiroyuki/     執筆者プロフィール（Article構造化データのauthor.url）
assets/blog.css             ブログ専用CSS（site.css は触らないので既存ページの ?v= 据え置き）
scripts/build_blog.py       品質ゲート＋一覧＋Atom＋関連記事＋sitemap のブログ区画を生成
scripts/make_blog_cover.py  表紙 cover.jpg を生成
```

### 公開手順

```bash
cp -r blog/_template blog/20260901-example      # 1. 雛形をコピー
#   2. {{...}} を全部置き換えて記事を書く（残置チェック: grep -r "{{" blog/<slug>/）
#   3. data/blog-posts.json の posts に1件追記（related_life も設定）
python scripts/make_blog_cover.py 20260901-example   # 4. 表紙を作る
#   5. fig1.svg / fig2.svg を用意
python scripts/inject_parts.py                       # 6. header/footer を流し込む
python scripts/build_blog.py --check                 # 7. 検査だけ（書き込みなし）
python scripts/build_blog.py                         # 8. 一覧＋Atom＋関連記事＋sitemap を生成
python scripts/ensure_canonical.py                    # 9. 全公開HTMLのcanonicalを正規化
git add -A && git commit && git push                 # 10. main へ push → Cloudflare が自動デプロイ
```

### 記事からの回遊・相談案内（2026-10-21）

`build_blog.py` はトップの「最新記事」3件も台帳から更新します。「暮らしのおすすめ記事」は `scripts/blog_navigation.py` の `RECOMMENDED` で選びます。
関連記事は `CURATED_RELATED` の編集指定を優先し、それ以外は本文タイトルのテーマ・共通の手続きガイド・テーマ軸から選びます。無関係な新着2件を一律に差し込まない設計です。
不動産の案内は `CONSULTATIONS` に明示した記事だけに1件表示し、該当する相談ページのカルテ見本へリンクします。記事別UTMと既存計測用の `data-track-click` を付与します。
ブログ記事の共通フッターは「運営者・関連サイトを見る」で展開できます。共通部品の外側に置くため、`inject_parts.py` での更新後も維持されます。
回帰チェック：`python scripts/test_blog_navigation.py`。

### 品質ゲート（`build_blog.py` が機械で見る範囲）

編集本文5,000文字以上／段落35以上／磐田市公式（`www.city.iwata.shizuoka.jp`）の出典2本以上／
`良い点`・`注文したい点`・`対案・結論`・`大石の視点` の各セクション／`post-author`／
`cover.jpg`／`fig1.svg`・`fig2.svg`／`/assets/blog.css` の読み込み／禁止語なし／
タイトル・slug の重複なし／台帳に無い `blog/<dir>/` が無いこと。
1件でも引っかかると `blog/index.html` は生成されない。

内容が本当に一次情報かどうかは機械では判定できない。最終確認は執筆者が行う。

既存記事の事実訂正では、誤記を残したり長さを満たすために未確認情報を補ったりしない。
台帳に `correction_notice`（読者に表示する訂正理由）と `modified` を記録した記事は、
本文800文字・8段落を下限とする。訂正告知の本文との一致、および出典・図版など他のゲートは引き続き必須。
2026年10月12日の照合記録は `reports/official-content-review-20261012.json` を参照。
表紙を図解で作る場合は `cover: "cover.svg"` を指定できる（省略時は従来どおり `cover.jpg`）。

### 禁止語

`build_blog.py` の `BANNED_WORDS` に「政策」を入れてある（森町版から引き継ぎ）。
このサイトは暮らしと手続きの非公式案内であり、同じ運営者の政治系サイトとは役割を分けるため。

### 曜日別テーマ軸（台帳の `axis`）

mon=手続き・制度／tue=空き家・実家・相続／wed=歴史・文化財／thu=子育て・学び／
fri=地区めぐり／sat=スポーツ・イベント／sun=移住・暮らし・データ

## 静的化に伴う仕様

- **検索バー**：本番の動的検索（`/navigate`）は使えないため、Google サイト内検索に置換。
- **「相談先を探す」リンク**：相談ハブ `/life/troubles-consult/` に置換。
- **旧フィードバックAPI**：`/api/feedback` は静的化で廃止済み（404）。
  2026-10-12、子どもの予防接種ページに残っていた送信ボタンと呼び出しを撤去。
  保存されない反応を受付済みと表示しない。旧APIは検索対象ページではなく、サイトマップにも載せない。
- **困りごとガイド / category / article ページ**：本番でも公開ナビ・sitemap から未リンクのため未収録。

## 免責

本サイトは磐田市公式サイトではありません。最新・正確な情報は磐田市公式サイトをご確認ください。
運営：富士ヶ丘サービス ／ 代表：大石浩之

### ブログ検索・テーマ絞り込み（2026-10-22）

`python scripts/build_blog.py` は記事台帳から `blog/search-index.json` も生成します。
トップの検索は従来の `search-index.json` と合わせて読み込み、手続き・相談ガイドとブログ記事を別々に順位付けします。
記事公開時に既存のブログ生成コマンドを実行すれば検索対象も同期されます。記事本文の全文は検索データに含めません。
回帰検査：`node scripts/test-search.mjs` と `node scripts/test-site-search.mjs`。

ブログ一覧のテーマ選択は `assets/blog-filter.js` と `assets/blog-filter.css` が担当します。
`?theme=tue` のようなURLで選択を共有でき、ブラウザーの戻る操作にも対応します。
JavaScriptが無効な場合は全記事と従来のテーマ別ジャンプリンクを表示します。
一覧の項目・テーマ・件数は `scripts/build_blog.py` が台帳から生成するため、生成後HTMLを手編集しません。

### ブログ検索の続き（2026-10-23）

トップ検索のブログ候補が4件を超える場合、`/blog/?q=検索語` に全候補を探すリンクを表示します。
一覧は `assets/blog-search.mjs` で既存の検索スコアリングを共用し、タイトル・テーマ・要約を対象にキーワードとテーマを併用できます。
キーワード検索時も記事の新しい順を保ち、件数・該当なし・解除・URL再読込・戻る操作に対応します。
キーワード欄はJavaScript有効時に表示し、無効時の全記事HTMLとテーマ別ジャンプリンクを保ちます。
追加回帰検査：`node scripts/test-blog-search.mjs`。

### 税の証明書の限定生成

年度・住所・取得方法の説明は `data/tax-certificate-guidance.json`、FAQと冒頭の取得方法は `data/categories.json` の対象項目で管理します。
`python scripts/build_tax_certificate_guidance.py` で対象HTMLの限定ブロック・冒頭のページ内リンク・FAQ本文/JSON-LD・リードと概要を同期し、`--check` で一致を検査できます。
内容更新後は `node scripts/build-search-index.mjs` を実行し、変更時のsitemap・改善履歴も確認します。旧snapshot・D1を再取得する全サイト生成は不要です。
