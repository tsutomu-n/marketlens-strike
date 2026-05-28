# 0902-Genetic Alogo for Trading

## このノートの扱い

遺伝的アルゴリズムを「戦略を自動発見する道具」ではなく、探索自由度と過学習リスクを学ぶ資料として扱う。

## 元ノートの要旨

遺伝的アルゴリズム、HMM、AI agent、APIキー、コスト、仮想環境など複数の研究メモが混在している。

## 今日時点での補正

GAは探索力が強いほど、金融時系列では過去データへの適合が起きやすい。戦略生成に使うなら、探索空間を狭くし、評価関数に複雑性ペナルティと未使用期間テストを入れる。

## 理想的ナラティブ / 誤謬リスク

- `BACKTEST_OVERFIT`: GAが過去の偶然パターンを最適化する。
- `PREDICTION_OVERCLAIM`: HMMやAI agentで市場状態を発見できるという前提。
- `SECURITY_SECRET`: APIキーやagent実行環境の扱いが混ざる。
- `OPERATIONAL_COMPLEXITY`: agentが自律的に改善する物語。

## 戦略部品への分解

- `Research Assistant`: 仮説候補生成に限定。
- `Optimizer`: ルールの微調整ではなく、部品選択の探索。
- `Evaluation Harness`: nested walk-forward、複雑性ペナルティ。
- `Security Guard`: APIキー、外部agent、実行権限の隔離。

## 実験に落とすなら

探索対象を3部品程度に限定し、fitnessは利益ではなく「単純性、DD、turnover、複数期間安定性」を含める。

## 採用条件

GAが発見したルールが、人間が理解でき、別期間でも単純ベースラインを上回ること。

## 捨て条件

探索回数を増やすほど過去成績だけが改善する場合。

## 現在性チェック

agent系ツールやAPI利用は、料金、権限、secret管理、外部送信データを確認する。

## 関連 docs

- `../RESEARCH_VALIDATION_PLAYBOOK.md`

## 原ノート

- `../obsidian_note_copies/03_model_research/0902-Genetic Alogo for Trading.md`

