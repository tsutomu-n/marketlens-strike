# Obsidian Note Rewrites 2026-05-29

このフォルダーは `../obsidian_note_copies/` の原ノート24本を、原本を読まなくても戦略準備に使えるように再構成した版です。

前日の `../obsidian_note_rewrites_2026-05-28/` は各ノートの要約としては使えますが、内容が薄く、原本を読まないと判断できない問題がありました。この `2026-05-29` 版では、原本由来の主張をそのまま信じず、追加調査と誤謬リスクの補正を入れています。

## 読む順番

1. [COMPLETE_REWRITE.md](COMPLETE_REWRITE.md)
   - 24本すべての厚めの再構成ノート。まずこれを読む。
2. [ERROR_CORRECTION_REGISTER.md](ERROR_CORRECTION_REGISTER.md)
   - 原ノートや前回リライトで誤解しやすい点、古い点、危険な点の一覧。
3. [RESEARCH_SOURCES.md](RESEARCH_SOURCES.md)
   - 追加調査で使う一次情報・公式情報の入口。
4. [EXPERIMENT_CARDS.md](EXPERIMENT_CARDS.md)
   - 再構成ノートから実際に試すなら、どの順で何を測るか。
5. [INDIVIDUAL_NOTE_DETAILS.md](INDIVIDUAL_NOTE_DETAILS.md)
   - 24本それぞれを、原本なしで読める独立カードにしたもの。
6. [STRATEGY_PARTS_HANDBOOK.md](STRATEGY_PARTS_HANDBOOK.md)
   - 戦略部品の役割、入力、出力、判断ロジック、誤用、検証指標を説明する。
7. [STRATEGY_COMPOSITION_EXAMPLES.md](STRATEGY_COMPOSITION_EXAMPLES.md)
   - 部品を組み合わせて戦略案へ落とす具体例。
8. [QUALITY_AUDIT.md](QUALITY_AUDIT.md)
   - 抜け、割愛、誤謬リスクを確認した監査メモ。
9. [STRATEGY_PARTS_DEEP_DIVE.md](STRATEGY_PARTS_DEEP_DIVE.md)
   - データ列、判定順、計算例、誤用、検証項目まで掘り下げた実用版。
10. [ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md](ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md)
   - 1本だけ読んで、部品理解から repo 内の実装先、signal CSV、backtest、paper run、first issue まで進めるための正本。
11. [appendix_materials/](appendix_materials/)
   - 図解、部品カード、サンプル成果物、チェックリスト、テンプレート、Solana/Jito安全表、ナラティブ誤謬カード。

## この版の方針

- 原ノートの物語を保存するのではなく、戦略に使える事実・仮説・失敗条件に変換する。
- 「AI」「Bot」「高速実行」「オンチェーン」「Jito」「注文簿」などの魅力的な言葉は、まず疑う。
- すべての戦略案を、`データ -> 特徴量 -> シグナル -> サイズ -> 執行 -> リスク停止 -> 検証` に分解する。
- 投資助言ではなく、研究・検証準備用の内部ドキュメントとして扱う。

## 付録の位置づけ

`ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md` が正本です。ただし、長文だけでは部品の境界や成果物の形が見えにくい場合は、`appendix_materials/` を先に見ます。

- 図で流れを掴む: `appendix_materials/01_PIPELINE_DIAGRAMS.md`
- 部品単位で理解する: `appendix_materials/02_COMPONENT_CARDS.md`
- repoの実装先を見る: `appendix_materials/03_REPO_IMPLEMENTATION_MAP.md`
- signal CSVやdecision logの形を見る: `appendix_materials/04_ARTIFACT_EXAMPLES.md`
- 具体例で追う: `appendix_materials/05_WORKED_EXAMPLE_TREND_PULLBACK.md`
