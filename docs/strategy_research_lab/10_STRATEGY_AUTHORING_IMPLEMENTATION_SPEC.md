# Strategy Authoring Implementation Spec

`strategy_authoring_spec.v1` は、ユーザーが宣言型 YAML で Strategy Lab signal を作るための interface です。

## Public CLI

```bash
uv run sis strategy-author-init --template trend_pullback --out PATH
uv run sis strategy-author-validate --spec PATH
uv run sis strategy-author-explain --spec PATH --out PATH
uv run sis strategy-author-run --spec PATH --through signals
uv run sis strategy-author-run --spec PATH --through backtest
uv run sis strategy-author-run --spec PATH --through paper-preview
```

`--through` は段階実行です。後段を指定すると前段も実行します。

## Source Of Truth

新 authoring flow の signal 正本は `data/research/strategy_signals.parquet` です。`data/research/signals.csv` は互換用 legacy export です。

backtest は `strategy_signals.parquet` から `ResearchSignal` へ変換し、既存 backtest bridge に渡します。`build-backtest` の legacy CSV default には依存しません。

## YAML Sections

- `experiment`: strategy id、family、version、symbol bindings、run profile
- `data`: feature panel、quote parquet、cost model
- `rules`: side、timeframe、entry conditions、score、confidence、reason code
- `backtest`: split method、era unit、fixed horizon、purge、embargo、min trade count
- `promotion`: paper-preview の既定 decision

## Validation

validation は次を stop condition にします。

- YAML root が object ではない
- schema version が `strategy_authoring_spec.v1` ではない
- feature panel が存在しない
- rule / score が参照する column が feature panel に存在しない
- `symbol_bindings.real_market_symbol` の row が feature panel に存在しない
- `backtest.label_horizon_minutes` が 0 以下
- `rules.confidence` が 0.0 から 1.0 の範囲外

## Signal Compilation

compiler は feature panel を `canonical_symbol`, `ts` で sort し、symbol binding の `real_market_symbol` に一致する row だけを評価します。

entry 判定は `all AND any` です。`any` が空なら `all` だけで通過します。

通過 row は `strategy_signal.v1` row へ変換されます。

- `execution_symbol` は symbol binding から決める
- `real_market_symbol` は feature panel の `canonical_symbol`
- `reason_codes` は `rules.reason_code`
- `parameter_hash` は YAML payload の stable hash
- `confidence` は `rules.confidence`

## Backtest

`strategy-author-run --through backtest` は fixed horizon で評価します。

- entry quote は `ts_client >= ts_signal` の最初の quote
- exit quote は entry quote から `label_horizon_minutes` 後以降の最初の quote
- cost は `data.cost_model_path` が存在すれば使い、無ければ quote spread fallback を使う
- metrics は既存 `BacktestMetrics` を JSON と Markdown に出す
- `pass_thresholds` は aggregate metrics と比較し、`summary.pass_thresholds`, `summary.pass_all_thresholds`, `summary.backtest_passed` に出す
- `summary.backtest_passed` は `min_trade_count` と `pass_thresholds` の両方を満たした場合だけ true

v1 の `purged_walk_forward` は report metadata です。自動最適化、ML training、parameter fitting はしません。

## Paper Preview

`strategy-author-run --through paper-preview` は paper-only artifact を出します。

- `trial_ledger.jsonl`
- `paper_candidate_pack.json`
- `promotion_decision.json`
- `paper_intent_preview.json`

既定 decision は `hold` です。operator review を挟むため、既定では `paper_intent_preview.json` は空配列です。

## Non Goals

- live order submission
- wallet access
- exchange write
- arbitrary Python plugin
- arbitrary expression eval
- automatic optimizer
- profitability guarantee
