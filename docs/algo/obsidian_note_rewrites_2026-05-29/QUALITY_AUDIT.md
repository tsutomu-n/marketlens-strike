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
- `EXPERIMENT_CARDS.md` で、戦略化のための検証カードに落とした。後続修正で、Crypto/DeFiよりもtrend、pullback、breakout、mean reversionなどの売買発生シグナルを前段に再編した。
- `STRATEGY_PARTS_HANDBOOK.md` で、戦略部品の役割、入力、出力、判断ロジック、誤用、検証指標、捨て条件を説明した。
- `STRATEGY_PARTS_DEEP_DIVE.md` で、データスキーマ、判定順、計算例、部品依存関係まで掘り下げた。
- `ONE_DOC_STRATEGY_TO_IMPLEMENTATION.md` で、部品理解から repo 内の実装先、signal CSV、backtest、paper run、first issue までを1本で追える正本にした。
- `appendix_materials/` で、図解、部品カード、repo実装対応、artifact例、worked example、検証表、テンプレート、ナラティブ誤謬カードを追加した。
- Crypto/DeFi固有資料が前に出すぎるリスクを補正し、`SIGNAL_DESIGN_PLAYBOOK`、`SIGNAL_PATTERN_LIBRARY`、`SIGNAL_REVIEW_SCORECARD` を追加して、純粋な戦略・売買発生シグナルを主軸にした。
- `INDIVIDUAL_NOTE_DETAILS.md` の部品名だけの列挙を、24本分の抽出部品テーブルへ置き換えた。
- `STRATEGY_COMPOSITION_EXAMPLES.md` で、部品を実際の戦略案へ組み合わせる例を追加した。後続修正で、Token Safety / Jitoを後段の特殊ケースへ下げ、シグナルarchetype中心へ再編した。
- 上位 `../strategy_factory/` を追加し、読み物ではなく、candidate sheet、reject taxonomy、backlog table、state gateで戦略候補を量産管理できるようにした。
- `strategy_factory/` の抜けを再点検し、gate checklist、duplicate control、factory audit、promotion blocker/evidence欄を追加した。

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
- Crypto/DeFi固有の話より先に、シグナルの定義、型、出力契約、invalidation、baseline、採点基準を確認できる。
- 戦略候補を自由文で増やすのではなく、状態、重複キー、固定reject理由、次gateで管理できる。
- 次gateへ進める時に、証跡、blocker、duplicate、taxonomy codeを確認できる。
