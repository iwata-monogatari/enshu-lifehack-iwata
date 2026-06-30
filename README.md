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

## 静的化に伴う仕様

- **検索バー**：本番の動的検索（`/navigate`）は使えないため、Google サイト内検索に置換。
- **「相談先を探す」リンク**：相談ハブ `/life/troubles-consult/` に置換。
- **フィードバックボタン**：送信先API（`/api/feedback`）が無いため記録はされないが、
  クリックで「ありがとうございます」表示までは動作する（UX上は無害）。
- **困りごとガイド / category / article ページ**：本番でも公開ナビ・sitemap から未リンクのため未収録。

## 免責

本サイトは磐田市公式サイトではありません。最新・正確な情報は磐田市公式サイトをご確認ください。
運営：富士ヶ丘サービス ／ 代表：大石浩之
