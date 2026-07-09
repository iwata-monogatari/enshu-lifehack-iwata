# K-01 categories.json スキーマ拡張・全項目データ付与 完了報告

実施日: 2026-07-10
対象: data/categories.json 全13カテゴリ・136項目

## 処理結果

- 処理項目数: 136 / 136（全項目）
- machine-verified: 136項目（全項目、2026-07-10 追加調査で残り11件も解消）
- draft残: 0項目

## channels 分布

| channel | 該当件数 |
|---|---|
| online | 61 |
| konbini | 11 |
| counter | 113 |
| phone | 86 |

konbini対応は11件と少なく（住民票・マイナンバー関連の証明書交付が中心）、「コンビニでできる手続き一覧」等の派生企画を組むには収載強化が必要。

## null残存一覧（フィールド別件数）

| フィールド | null件数 | 主な理由 |
|---|---|---|
| konbini | 125 | 該当カテゴリ・手続きの多くがコンビニ交付・収納の対象外 |
| cost | 94 | 公式ページ本文に金額の明記がない（PDF資料のみ記載等） |
| online | 75 | 電子申請・LINE等のオンライン完結手段が本文に確認できない |
| counter | 18 | 読み物・相談系ページで窓口の具体的記載がない |
| tel | 16 | 代表電話番号が本文になく、担当地区ごとに窓口が分かれる等 |

## mismatch発生・解消件数

- 初回検証: 14件がmismatch（tel未一致10件、cost金額未一致1件、40字超過3件）
- 40字超過3件・電話番号混在1件（moving-out/school-nursery-procedures）を修正し再検証 → 残り11件
- 残り11件を個別調査し全件解消:
  - 8件（living-soon/transportation、start-living/garbage-sorting-calendar、education/school-district-transfer、education/study-facilities、health-medical/adult-vaccination、work-life/tax、end-of-life/bereavement-procedures、moving-out/school-nursery-procedures）は、電話番号自体は正しかったが `conclusion.source` がリンク集・ポータルページを指しており本文に番号が載っていなかった。番号が実際に記載されている担当課の組織案内ページ・詳細ページへ `source` を差し替え。
  - 1件（health-medical/health-checkups）は金額表記の全角カンマ有無の不一致（本文「1,700円」／記載「1700円」）。記載側をカンマ付きに統一。
  - 1件（health-medical/vaccinations）はtel自体が誤り（こども未来課の代表番号ではなく、予防接種スケジュールページに明記された「こども若者家庭センター 子育てサポートグループ」の番号が正しかった）。tel・sourceとも修正。
  - 1件（parents-care/adult-guardianship）は番号自体もsourceも正しかったが、磐田市公式ページが市外局番(0538)を省略し「37-2792」とのみ表記していたため単純一致検証で誤検知。`scripts/verify_sources.py` のtel照合に市外局番省略パターンの許容を追加。
- 最終結果: 136/136 machine-verified、mismatch 0件。

## 新規追加した公式URL本数

- 各項目の conclusion.source に磐田市公式サイト(city.iwata.shizuoka.jp)のURLを1本ずつ設定（136本、既存監査済み377本と重複するものを含む）。新規に特定したURLはリサーチ工程のAgent報告に記載の通り、既存ページが未リンクだった制度別詳細ページ（就学援助、地域包括支援センター、上下水道インターネット受付等）が中心。

## 注記

- 磐田ライフハック本番サイト(iwata.enshu-lifehack.com)への直接WebFetchは403で拒否されたため、各リサーチAgentはリポジトリ内のローカルHTMLから既存の公式リンクを抽出し、そこを起点に磐田市公式サイト本文を取得する方式で作業した。
- 本指示書の禁止事項（推測記入禁止・個別ページ手作業編集禁止・カテゴリ単位バッチ生成）はすべて遵守。表示変更（K-02以降）は本コミットに含まない。
