# Artifact Flow And Lineage

この文書は、Strategy Research Lab の artifact がどの順番で生成され、どの ID でつながるかを固定します。

## 全体 flow

```text
research feature data
  -> StrategyExperimentSpec
  -> signal generator
  -> StrategySignalRecord rows
  -> data/research/strategy_signals.parquet
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
- `build_signals()` currently uses default generator `qqq_trend_rates_vix`.
- `build_signals()` writes canonical `data/research/strategy_signals.parquet`, JSONL export, and legacy `signals.csv`.
- `evaluate-strategy-lab` exits with code 2 if `strategy_signals.parquet` is missing.
- `build-paper-candidate-pack` reads `trial_ledger.jsonl`.
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
- Confirm `trial_ledger.jsonl` records all trials, including rejected trials.
- Confirm selected and rejected IDs in `PaperCandidatePack` refer to existing candidates.
- Confirm `PromotionDecision` exists before preview generation.
- Confirm `PaperIntentPreview` has `requires_revalidation=true`, `paper_only=true`, `live_conversion_allowed=false`.
- Confirm paper observation ledger does not show wallet or exchange writes.
