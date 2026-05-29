# Quality Audit

2026-05-29版に対する抜け漏れ・割愛・誤謬リスクの再点検です。

## 前回版の問題

- 各ノート約50行で、原本の代替にならなかった。
- 24本を個別に読んだ時の判断材料が不足していた。
- 外部仕様の古さを「要確認」と書くだけで、どの主張をどう疑うかが弱かった。
- 実験に進む際の具体的な測定項目が不足していた。

## 今回の修正

- `COMPLETE_REWRITE.md` で24本を通読可能な統合ノートにした。
- `INDIVIDUAL_NOTE_DETAILS.md` で24本それぞれを独立カード化した。
- `ERROR_CORRECTION_REGISTER.md` で、原ノートの誤り・古い主張・誤解しやすい表現を補正した。
- `EXPERIMENT_CARDS.md` で、戦略化のための10個の検証カードに落とした。
- `STRATEGY_PARTS_HANDBOOK.md` で、戦略部品の役割、入力、出力、判断ロジック、誤用、検証指標、捨て条件を説明した。
- `STRATEGY_PARTS_DEEP_DIVE.md` で、データスキーマ、判定順、計算例、部品依存関係まで掘り下げた。
- `ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md` で、部品理解から repo 内の実装先、signal CSV、backtest、paper run、first issue までを1本で追える正本にした。
- `appendix_materials/` で、図解、部品カード、repo実装対応、artifact例、worked example、検証表、Solana/Jito安全表、テンプレート、ナラティブ誤謬カードを追加した。
- `INDIVIDUAL_NOTE_DETAILS.md` の部品名だけの列挙を、24本分の抽出部品テーブルへ置き換えた。
- `STRATEGY_COMPOSITION_EXAMPLES.md` で、部品を実際の戦略案へ組み合わせる例を追加した。

## まだ残るリスク

- 各ライブラリ/API/protocolの仕様は今後も変わる。実装直前に公式情報へ戻る。
- 原ノートの一部はYouTube/Medium/古いREADME由来で、転記誤りやマーケティング表現が混ざる。
- 2026-05-29版は戦略準備docsであり、実装済み検証結果ではない。
- 「良さそうな戦略」はまだ仮説であり、バックテストやpaper observationを通して捨てる前提で扱う。
- 付録内の外部仕様メモも固定仕様ではない。Jito、Solana、PyBotters、LightGBM、Polars、VectorBTは実装直前に公式情報へ戻る。

## 合格条件

- 原本を開かなくても、各ノートの要旨、危険な前提、補正後の使い方、実験案が分かる。
- 「勝てる」「稼げる」「高精度」「低遅延で有利」を結論として扱っていない。
- APIキー、private key、wallet、credentialの実値を含まない。
- すべての候補が、採用条件だけでなく捨て条件を持つ。
- 部品名だけで終わらず、入力、出力、判断内容、誤用リスク、検証方法が分かる。
- 部品をどう組み合わせると戦略案になるか、少なくとも5例で追える。
- 主要部品について、必要なデータ列と最小の判定順が分かる。
- 1本だけ読んでも、最初に触るファイル、触らない方がよいlive execution層、テスト観点、paper runの確認対象が分かる。
- 長文を読まなくても、図表、カード、artifact例、テンプレートから戦略検討を開始できる。
- 原ノート24本が、どの付録や補助資料に変換されたか追跡できる。
