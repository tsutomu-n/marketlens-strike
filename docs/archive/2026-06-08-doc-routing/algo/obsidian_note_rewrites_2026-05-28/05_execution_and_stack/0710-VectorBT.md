# 0710-VectorBT

## このノートの扱い

VectorBTを高速な研究ツールとして扱う。バックテスト結果をそのまま実運用可能性と見なさない。

## 元ノートの要旨

VectorBTの導入、データ取得、移動平均、RSI、ボリンジャーバンド、パラメータ最適化、複数銘柄、可視化、リスク管理などのcookbook。

## 今日時点での補正

VectorBTは大量の組み合わせ検証に便利だが、便利さが過剰最適化を誘発する。最初に検証分割、コスト、slippage、重複シグナル、look-aheadを固定する。

## 理想的ナラティブ / 誤謬リスク

- `BACKTEST_OVERFIT`: パラメータ探索が簡単すぎる。
- `PREDICTION_OVERCLAIM`: デモ戦略の成績を一般化しやすい。
- `EXECUTION_GAP`: vectorized backtestと約定現実の差。

## 戦略部品への分解

- `Evaluation Harness`: 高速な一次スクリーニング。
- `Feature Factory`: indicator計算とパラメータ比較。
- `Portfolio Allocator`: 複数銘柄/複数戦略の比較。
- `Risk Guard`: コスト感応度とturnover制約。

## 実験に落とすなら

1戦略1銘柄のベースラインから始め、パラメータ探索範囲を事前固定する。最適値ではなく、近傍が安定しているかを見る。

## 採用条件

VectorBT上で良いだけでなく、同じロジックをイベント駆動/約定モデルに移しても崩れないこと。

## 捨て条件

探索範囲を広げた時だけ良いパラメータが見つかる場合。

## 現在性チェック

VectorBT公式docs、互換Python/Pandas/NumPy、メンテ状況を確認する。

## 関連 docs

- `../RESEARCH_VALIDATION_PLAYBOOK.md`

## 原ノート

- `../obsidian_note_copies/05_execution_and_stack/0710-VectorBT.md`

