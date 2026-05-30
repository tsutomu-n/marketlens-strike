# Strategy Author Guide

この guide は、ユーザーが Strategy Lab で売買ロジックを作るための最短導線です。対象は paper-only research です。ライブ発注、ウォレット操作、取引所書き込みは行いません。

## 1. テンプレートを作る

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

生成される YAML は `strategy_authoring_spec.v1` です。v1 の正式入力は YAML だけです。

## 2. YAML を検証する

```bash
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

検証では次を確認します。

- 必須 section があるか
- `feature_panel_path` が存在するか
- rule と score が参照する feature column が存在するか
- `symbol_bindings.real_market_symbol` の row が feature panel に存在するか
- paper-only 境界から外れる claim を作っていないか

## 3. 人間向け説明レポートを出す

```bash
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

既定出力は `data/reports/strategy_authoring_explain.md` です。売買条件、必要 column、symbol binding、backtest 条件、validation error を一覧できます。

## 4. シグナルを作る

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through signals
```

出力は既存 Strategy Lab artifact と同じです。

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signals.jsonl`
- `data/research/strategy_signal_manifest.json`
- `data/research/signals.csv`
- `data/research/strategy_authoring_run.json`

`signals.csv` は legacy export です。新しい authoring flow の正本は `strategy_signals.parquet` です。

## 5. バックテストまで実行する

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

既存 backtest bridge を使い、Strategy Lab signals を直接 `ResearchSignal` に変換して評価します。legacy `signals.csv` を正本にしません。

追加出力は次です。

- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_backtest_report.md`

v1 は fixed horizon exit です。`backtest.label_horizon_minutes` で horizon を指定します。

`backtest.pass_thresholds` は `strategy_backtest_metrics.json` の `summary.pass_thresholds` と `summary.backtest_passed` に反映されます。`max_drawdown` は `-0.2` 以上なら pass、`cost_drag_bps`, `stale_rejected_count`, `halt_rejected_count` は threshold 以下なら pass、それ以外は threshold 以上なら pass です。

## 6. paper-preview artifact まで出す

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through paper-preview
```

追加出力は次です。

- `data/research/trial_ledger.jsonl`
- `data/research/paper_candidate_pack.json`
- `data/research/promotion_decision.json`
- `data/bot/paper_intent_preview.json`
- `data/reports/paper_intent_preview.md`

既定の `promotion.default_decision` は `hold` です。そのため `paper_intent_preview.json` は空配列になります。これは意図した安全側 default です。

## Rule DSL

`rules.entry.all` はすべて満たす条件、`rules.entry.any` は少なくとも 1 つ満たす条件です。両方がある場合は `all AND any` です。

対応 operator は次です。

- `gt`
- `gte`
- `lt`
- `lte`
- `eq`
- `neq`
- `is_true`
- `is_false`
- `between`

`between` の `value` は 2 要素配列です。

```yaml
- column: vix_level
  op: between
  value: [10, 30]
```

## Score

`rules.score.weighted_sum` は raw score を作ります。`rank_score` は raw score を `0.0` から `1.0` に clamp した値です。

```yaml
score:
  weighted_sum:
    - column: research_return_1d
      weight: 10
    - column: source_confidence
      weight: 0.5
```

## Safety Boundary

この authoring flow は paper-only research です。

- live order は送信しない
- wallet は使わない
- exchange write は行わない
- profitability claim は出さない
- `paper-preview` でも最新 quote による本番発注はしない
