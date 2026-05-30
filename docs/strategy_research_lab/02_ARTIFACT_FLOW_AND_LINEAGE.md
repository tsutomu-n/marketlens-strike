# Artifact Flow And Lineage

この文書は、Strategy Research Lab の artifact がどの順番で生成され、どの ID でつながるかを固定します。

## 全体 flow

```text
research feature data
  -> StrategyExperimentSpec
  -> signal generator
  -> StrategySignalRecord rows
  -> data/research/strategy_signals.parquet
  -> data/research/strategy_signal_manifest.json
  -> EvaluationPlan
  -> TrialRecord rows
  -> data/research/trial_ledger.jsonl
  -> TradeCandidate rows
  -> PaperCandidatePack
  -> data/research/paper_candidate_pack.json
  -> PromotionDecision
  -> data/research/promotion_decision.json
  -> PaperIntentPreview list
  -> data/bot/paper_intent_preview.json
  -> paper-from-intents revalidation
  -> paper orders/fills/positions
```

## Artifact table

| Step | Artifact | Producer | Consumer | Main IDs |
|---|---|---|---|---|
| experiment definition | `StrategyExperimentSpec` | human / future spec runner | generator / evaluator | `strategy_id`, `strategy_version`, `evaluation_plan_id` |
| signal rows | `data/research/strategy_signals.parquet` | `uv run sis strategy-preview` / `build-signals` | `evaluate-strategy-lab` | `signal_id`, `strategy_id`, `parameter_hash` |
| signal manifest | `data/research/strategy_signal_manifest.json` | `uv run sis strategy-preview` / `build-signals` | `evaluate-strategy-lab`, `build-paper-candidate-pack` | `generator_id`, `signal_artifact_run_id` |
| evaluation definition | `EvaluationPlan` | human / future runner | evaluation runner | `evaluation_plan_id` |
| trial ledger | `data/research/trial_ledger.jsonl` | `uv run sis evaluate-strategy-lab` | `build-paper-candidate-pack` | `trial_id`, `trial_group_id`, `data_snapshot_id`, `feature_snapshot_id` |
| candidate pack | `data/research/paper_candidate_pack.json` | `uv run sis build-paper-candidate-pack` | `promotion-decision`, `build-paper-intent-preview` | `pack_id`, `candidate_id` |
| promotion decision | `data/research/promotion_decision.json` | `uv run sis promotion-decision` | `build-paper-intent-preview` | `promotion_id`, `source_pack_id` |
| paper preview | `data/bot/paper_intent_preview.json` | `uv run sis build-paper-intent-preview` | `paper-from-intents` | `intent_id`, `candidate_id`, `source_pack_id` |
| paper observation | `data/paper/*`, `data/paper/paper_observation_ledger.jsonl` | `uv run sis paper-from-intents` | reports / review | `order_id`, `fill_id`, `intent_id` |

## Lineage keys

Minimum useful lineage:

```text
strategy_id
strategy_family
strategy_version
evaluation_plan_id
data_snapshot_id
feature_snapshot_id
trial_group_id
trial_id
signal_artifact_run_id
candidate_id
pack_id
promotion_id
intent_id
```

When reviewing a result, do not start from PnL. Start from lineage:

1. Which `strategy_id` and `strategy_version` generated the signal?
2. Which `generator_id` and parameter set produced it?
3. Which data snapshot and feature snapshot were used?
4. Which `EvaluationPlan` decided the evaluation horizon and leakage guard?
5. Which trial selected the candidate?
6. Which `PaperCandidatePack` included it?
7. Which human `PromotionDecision` allowed preview generation?
8. Which latest quote and paper broker state revalidated it at `paper-from-intents` time?

## Current CLI flow

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

Important behavior:

- `strategy-preview` calls `build_signals()`.
- `build_signals()` defaults to generator `qqq_trend_rates_vix`.
- `build-signals --generator-id sp500_trend_rates_vix` and `strategy-preview --generator-id sp500_trend_rates_vix` select the registered SP500 generator.
- `build_signals()` writes canonical `data/research/strategy_signals.parquet`, `strategy_signal_manifest.json`, JSONL export, and legacy `signals.csv`.
- no-signal artifacts keep an empty schema plus manifest lineage instead of becoming `unknown_strategy`.
- `evaluate-strategy-lab` exits with code 2 if `strategy_signals.parquet` is missing.
- `evaluate-strategy-lab` exits with code 2 if one `strategy_signals.parquet` mixes multiple `(strategy_id, strategy_family, strategy_version, execution_venue, execution_symbol, real_market_symbol)` identities.
- `evaluate-strategy-lab` does not append duplicate `trial_id` rows for the same artifact.
- `evaluate-strategy-lab --rank-thresholds 0.2,0.8` appends one paper-only `TrialRecord` per rank threshold in the same `trial_group_id`.
- `evaluate-strategy-lab --candidate-limit 0` records every threshold-passing selected signal ID; the default selects only the latest `ts_signal` row.
- `--split-method` and `--era-unit` record era signal count metrics only. They do not turn the CLI into a full walk-forward backtester.
- v1 lineage IDs are deterministic from the signal artifact content: `trial-{run_id}`, `trial-group-{run_id}`, `paper-pack-{run_id}`, `promotion-{run_id}`.
- `build-paper-candidate-pack` reads the latest trial group by default, or a specific group via `--trial-group-id`.
- selected paper candidates are built from `TrialRecord.metrics.selected_signal_ids`; default evaluation records the latest `ts_signal` row only.
- `promotion-decision` records the actual `PaperCandidatePack.pack_id` as `source_pack_id`.
- `build-paper-intent-preview` exits with code 2 if `PromotionDecision.source_pack_id` does not match `PaperCandidatePack.pack_id`.
- `promotion-decision` and `build-paper-intent-preview` exit with code 2 when the source pack is missing.
- `promotion-decision --decision promote` fails validation unless required evidence is observed.
- `build-paper-intent-preview` exits with code 2 if `promotion_decision.json` is missing.
- `paper-from-intents` loads the preview and revalidates against latest quotes.

## Why `signals.csv` is not the Strategy Lab source of truth

`data/research/signals.csv` remains as a legacy thin export for old paper path compatibility. It cannot carry the full Strategy Lab contract:

- no full symbol binding context;
- no full source / venue quality fields;
- no trial / parameter lineage;
- no candidate selection state;
- no promotion decision;
- no paper-only guard.

Use `data/research/strategy_signals.parquet` for Strategy Lab review.

## Paper execution boundary

`paper-from-intents` creates paper orders and fills only after revalidation. It may block:

- expired intent: `INTENT_EXPIRED`
- no latest quote: `LATEST_QUOTE_MISSING`
- paper broker block: `PAPER_BROKER_REVALIDATION_BLOCKED`

Paper artifacts:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

The observation ledger explicitly records:

- `live_order_submitted=false`
- `wallet_used=false`
- `exchange_write_used=false`

## Review checklist

Before accepting a Strategy Lab result:

- Confirm `strategy_signals.parquet` exists and contains Strategy Lab columns.
- Confirm every signal's `execution_symbol` / `real_market_symbol` matches a `SymbolBinding`.
- Confirm one signal artifact contains only one strategy / symbol identity before evaluation.
- Confirm `trial_ledger.jsonl` records all trials, including rejected trials.
- Confirm selected and rejected IDs in `PaperCandidatePack` refer to existing candidates.
- Confirm `PromotionDecision.source_pack_id` matches `PaperCandidatePack.pack_id`.
- Confirm `PromotionDecision` exists before preview generation.
- Confirm `PaperIntentPreview` has `requires_revalidation=true`, `paper_only=true`, `live_conversion_allowed=false`.
- Confirm paper observation ledger does not show wallet or exchange writes.
