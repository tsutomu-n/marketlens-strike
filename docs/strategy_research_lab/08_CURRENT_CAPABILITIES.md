# Current Capabilities

この文書は、2026-05-30 時点の Strategy Research Lab で実際にできることを記録します。

正本はコードです。特に `src/sis/commands/research.py`, `src/sis/research/strategy_lab/`, `src/sis/research_protocol/`, `src/sis/paper/runner.py`, `tests/test_strategy_lab_commands.py` を優先します。

より具体的な説明と専門用語の言い換えは [08_CURRENT_CAPABILITIES_EXPLAINED.html](08_CURRENT_CAPABILITIES_EXPLAINED.html) で読めます。

## 結論

今の Strategy Research Lab は、登録済み generator から signal artifact を作り、paper-only の trial / candidate / promotion / intent preview まで進められます。加えて、`strategy_authoring_spec.v1` YAML から宣言型 rule を signal artifact / fixed-horizon backtest / paper-preview artifact へ進められます。

ただし、これは live-ready 証明ではありません。現行 authoring backtest は fixed-horizon の研究用 metrics であり、position sizing、wallet / signing / exchange write は含みません。

## できるようになったこと

### 1. 登録済み generator から signal artifact を作れる

```bash
uv run sis strategy-preview
uv run sis strategy-preview --generator-id sp500_trend_rates_vix
```

できること:

- default generator `qqq_trend_rates_vix` で `XYZ100 -> QQQ` の Strategy Lab signal artifact を作れる。
- registered generator `sp500_trend_rates_vix` で `SP500 -> SPY` の signal artifact を作れる。
- no-signal 時も empty schema 付き `strategy_signals.parquet` と `strategy_signal_manifest.json` を残せる。
- legacy export `data/research/signals.csv` も出るが、Strategy Lab の正本は `data/research/strategy_signals.parquet`。

主要 artifact:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/research/strategy_signals.jsonl`
- `data/research/signals.csv`
- `data/reports/strategy_signals_preview.md`

### 1.5. YAML でユーザー定義 rule を作れる

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

できること:

- `strategy_authoring_spec.v1` YAML で entry 条件、side、timeframe、score、backtest horizon を書ける。
- rule が参照する feature column と symbol binding を validate できる。
- `data/research/strategy_signals.parquet` を正本として出せる。
- Strategy Lab signal を直接 backtest bridge に渡し、legacy `signals.csv` を正本にしない。
- `--through paper-preview` で paper-only の `trial_ledger.jsonl`, `paper_candidate_pack.json`, `promotion_decision.json`, `paper_intent_preview.json` まで出せる。

主要 artifact:

- `data/research/strategy_authoring_run.json`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_authoring_explain.md`
- `data/reports/strategy_backtest_report.md`

### 2. signal artifact を TrialRecord に評価記録できる

```bash
uv run sis evaluate-strategy-lab
```

できること:

- `data/research/trial_ledger.jsonl` に `TrialRecord` を append-only に記録できる。
- 同じ signal artifact と同じ parameter set の `trial_id` を重複追記しない。
- `signal_artifact_run_id` で signal artifact と trial を接続できる。
- 1 artifact に複数の strategy / symbol identity が混ざる場合は exit code 2 で止まる。
- 空または重複した `signal_id` を含む signal artifact は exit code 2 で止まる。
- empty signal artifact は manifest lineage がある場合だけ no-signal trial として記録できる。

主要 artifact:

- `data/research/trial_ledger.jsonl`
- `data/reports/strategy_trial_report.md`

### 3. rank threshold sweep を paper-only に記録できる

```bash
uv run sis evaluate-strategy-lab --rank-thresholds 0.2,0.8
```

できること:

- comma-separated の `rank_score` threshold ごとに `TrialRecord` を作れる。
- threshold 別 trial は同じ `trial_group_id` にまとまる。
- threshold / `--candidate-limit` / `--split-method` / `--era-unit` ごとに `parameter_hash` と `trial_id` が分かれる。
- default evaluation は互換性のため `generator-default-{run_id}` と `trial-{run_id}` を維持する。

注意:

- threshold sweep は paper-only の比較記録です。
- `rank_threshold` は新しい `strategy_id` ではなく、同じ strategy の parameter variant として扱う。

### 4. 複数 selected signal を candidate 化できる

```bash
uv run sis evaluate-strategy-lab --candidate-limit 0
uv run sis build-paper-candidate-pack
```

できること:

- default evaluation は最新 `ts_signal` の 1 signal を `metrics.selected_signal_ids` に記録する。
- `--candidate-limit 0` で threshold 通過 signal 全件を `selected_signal_ids` に記録できる。
- `build-paper-candidate-pack` は `TrialRecord.metrics.selected_signal_ids` から複数 `TradeCandidate` を作れる。
- selected trial の `signal_artifact_run_id` が現在の signal artifact と一致しない場合は exit code 2 で止まる。
- selected signal ID が現在の signal artifact に見つからない場合は exit code 2 で止まる。

主要 artifact:

- `data/research/paper_candidate_pack.json`
- `data/reports/paper_candidate_pack.md`

### 5. era 別 signal count metrics を残せる

```bash
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit trading_day
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit week
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit month
```

できること:

- `metrics.split_method` に `single_window`, `walk_forward`, `purged_walk_forward` を記録できる。
- `metrics.era_unit` に `session`, `trading_day`, `week`, `month` を記録できる。
- `metrics.era_signal_counts` と `metrics.era_count` を残せる。

注意:

- これは era 別 signal count metrics です。
- PnL 計算や walk-forward 検証 engine ではありません。

### 6. paper-only preview まで artifact chain を進められる

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
```

できること:

- `PaperCandidatePack` から `PromotionDecision` を作れる。
- `hold` / `reject` / `promote` の判断 artifact を残せる。
- required evidence が揃わない `promote` は validation で止まる。
- `PromotionDecision.source_pack_id` と `PaperCandidatePack.pack_id` の不一致を exit code 2 で止められる。
- `PaperIntentPreview` は `paper_only=true`, `live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` のまま出せる。

主要 artifact:

- `data/research/promotion_decision.json`
- `data/bot/paper_intent_preview.json`
- `data/reports/promotion_decision.md`
- `data/reports/paper_intent_preview.md`

### 7. paper runner で preview を再検証できる

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

できること:

- `PaperIntentPreview` を最新 quote と paper broker state で再検証できる。
- expired intent, latest quote missing, paper broker block を stop reason として残せる。
- paper order / fill / position artifact と observation ledger を書ける。
- observation ledger は `live_order_submitted=false`, `wallet_used=false`, `exchange_write_used=false` を明示する。

主要 artifact:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

## よく使う実行例

Default signal から paper candidate pack まで:

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
```

SP500 generator:

```bash
uv run sis strategy-preview --generator-id sp500_trend_rates_vix
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
```

Threshold sweep と複数 candidate:

```bash
uv run sis evaluate-strategy-lab --rank-thresholds 0.2,0.8 --candidate-limit 0
uv run sis build-paper-candidate-pack
```

Era metrics 付き sweep:

```bash
uv run sis evaluate-strategy-lab \
  --rank-thresholds 0.2,0.8 \
  --candidate-limit 0 \
  --split-method walk_forward \
  --era-unit trading_day
```

## まだできないこと

- 任意の `StrategyExperimentSpec` YAML / JSON を CLI から直接読む汎用 runner。
- `parameter_grid` 全体を実行する full experiment engine。
- PnL / drawdown / Sharpe / slippage-adjusted return の backtest。
- full walk-forward / purged walk-forward の検証 engine。
- candidate score から position size / notional / risk budget を決める sizing engine。
- live order, wallet signing, exchange write。
- `PromotionDecision.decision=promote` から live trading へ進む導線。
- Strategy Lab artifact だけを根拠にした profitability / paper-ready / live-ready claim。

## 受け入れ済みの検証

2026-05-30 時点で、次を確認済みです。

```bash
uv run pytest tests/test_strategy_lab_commands.py -q
uv run pytest tests/test_strategies.py tests/test_strategy_lab_signal_registry.py tests/test_research_signals_artifact.py tests/test_strategy_lab_commands.py tests/test_strategy_lab_candidate_pack.py tests/test_strategy_lab_schemas.py -q
uv run pytest tests/test_research_pipeline.py tests/test_cli_smoke.py -q
uv run python scripts/check_current_docs.py
./scripts/check
git diff --check
```

確認済み結果:

- `tests/test_strategy_lab_commands.py`: 15 passed
- Strategy Lab related targeted suite: 39 passed
- Research pipeline / CLI smoke: 71 passed
- `scripts/check_current_docs.py`: checked 74 current docs
- `./scripts/check`: 384 passed, pyrefly 0 errors
- `git diff --check`: pass
