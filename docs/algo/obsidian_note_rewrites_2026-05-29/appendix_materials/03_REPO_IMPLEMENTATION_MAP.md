# Repo Implementation Map

この付録は、Strategy Research Lab の現行実装を repo path で辿るための map です。旧 legacy paper path ではなく、`StrategyExperimentSpec -> PaperIntentPreview -> paper-from-intents` を中心に読む。

## 正本 code paths

| Area | Path | Role |
|---|---|---|
| strategy lab models | `src/sis/research/strategy_lab/` | Strategy Lab の Pydantic runtime contract |
| research protocol | `src/sis/research_protocol/` | data / feature snapshot manifests |
| research commands | `src/sis/commands/research.py` | Strategy Lab artifact chain commands |
| paper commands | `src/sis/commands/paper.py` | paper-from-intents command |
| paper runner | `src/sis/paper/runner.py` | intent revalidation and paper artifacts |
| schemas | `schemas/*.v1.schema.json` | thin JSON Schema guard |
| tests | `tests/test_strategy_lab_*.py` | schema / command chain validation |
| paper intent tests | `tests/test_paper_from_intents.py` | paper-from-intents revalidation |

## Model files

| Model | File |
|---|---|
| `StrategyExperimentSpec` | `src/sis/research/strategy_lab/specs.py` |
| `SymbolBinding` | `src/sis/research/strategy_lab/specs.py` |
| `StrategySignalRecord` | `src/sis/research/strategy_lab/specs.py` |
| `EvaluationPlan` | `src/sis/research/strategy_lab/evaluation_plan.py` |
| `TrialRecord`, `TrialLedger` | `src/sis/research/strategy_lab/trial_ledger.py` |
| `TradeCandidate` | `src/sis/research/strategy_lab/candidates.py` |
| `PaperCandidatePack` | `src/sis/research/strategy_lab/paper_candidate_pack.py` |
| `PromotionDecision` | `src/sis/research/strategy_lab/promotion_decision.py` |
| `PaperIntentPreview` | `src/sis/research/strategy_lab/paper_intent_preview.py` |
| `StrategyRunProfile` | `src/sis/research/strategy_lab/run_profile.py` |
| `SignalGeneratorRegistry` | `src/sis/research/strategy_lab/signal_registry.py` |
| `DataSnapshotManifest` | `src/sis/research_protocol/data_snapshot.py` |
| `FeatureSnapshotManifest` | `src/sis/research_protocol/feature_snapshot.py` |

## Command map

| Command | Code | Main output |
|---|---|---|
| `uv run sis strategy-preview` | `src/sis/commands/research.py` | `strategy_signals.parquet`, JSONL, legacy CSV, preview report |
| `uv run sis evaluate-strategy-lab` | `src/sis/commands/research.py` | `trial_ledger.jsonl`, strategy trial report |
| `uv run sis build-paper-candidate-pack` | `src/sis/commands/research.py` | `paper_candidate_pack.json`, pack report |
| `uv run sis promotion-decision` | `src/sis/commands/research.py` | `promotion_decision.json`, decision report |
| `uv run sis build-paper-intent-preview` | `src/sis/commands/research.py` | `paper_intent_preview.json`, preview report |
| `uv run sis paper-from-intents` | `src/sis/commands/paper.py`, `src/sis/paper/runner.py` | paper orders/fills/positions/observation ledger |

## Artifact map

| Artifact | Meaning |
|---|---|
| `data/research/strategy_signals.parquet` | Strategy Lab canonical signal artifact |
| `data/research/strategy_signals.jsonl` | line-delimited export |
| `data/research/signals.csv` | legacy thin export, not Strategy Lab source of truth |
| `data/research/trial_ledger.jsonl` | append-only trial records |
| `data/research/paper_candidate_pack.json` | candidate bundle before paper promotion |
| `data/research/promotion_decision.json` | human decision artifact |
| `data/bot/paper_intent_preview.json` | paper-only intent preview |
| `data/paper/orders.parquet` | paper orders only |
| `data/paper/fills.parquet` | paper fills only |
| `data/paper/positions.parquet` | paper positions only |
| `data/paper/paper_observation_ledger.jsonl` | paper revalidation observation trail |

## Schema map

| Schema | File |
|---|---|
| `strategy_experiment_spec.v1` | `schemas/strategy_experiment_spec.v1.schema.json` |
| `strategy_signal.v1` | `schemas/strategy_signal.v1.schema.json` |
| `evaluation_plan.mls.v1` | `schemas/evaluation_plan.mls.v1.schema.json` |
| `trial_record.v1` | `schemas/trial_record.v1.schema.json` |
| `trade_candidate.v1` | `schemas/trade_candidate.v1.schema.json` |
| `paper_candidate_pack.v1` | `schemas/paper_candidate_pack.v1.schema.json` |
| `promotion_decision.v1` | `schemas/promotion_decision.v1.schema.json` |
| `paper_intent_preview.v1` | `schemas/paper_intent_preview.v1.schema.json` |
| `data_snapshot_manifest.v1` | `schemas/data_snapshot_manifest.v1.schema.json` |
| `feature_snapshot_manifest.v1` | `schemas/feature_snapshot_manifest.v1.schema.json` |

## Test map

| Test | Role |
|---|---|
| `tests/test_strategy_run_profile.py` | strategy lab live-surface guards |
| `tests/test_strategy_lab_specs.py` | experiment spec, symbol binding, signal record |
| `tests/test_strategy_lab_signal_registry.py` | generator registry and signal frame validation |
| `tests/test_strategy_lab_evaluation_plan.py` | evaluation plan guard |
| `tests/test_strategy_lab_trial_ledger.py` | trial ledger append/read |
| `tests/test_strategy_lab_candidate_pack.py` | trade candidate and pack validation |
| `tests/test_strategy_lab_promotion_decision.py` | promotion decision validation |
| `tests/test_strategy_lab_paper_intent_preview.py` | paper intent preview guard |
| `tests/test_strategy_lab_schemas.py` | JSON schema presence and thin guards |
| `tests/test_strategy_lab_commands.py` | CLI artifact chain |
| `tests/test_paper_from_intents.py` | paper runner revalidation |

## Read order for implementers

1. `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
2. `docs/strategy_research_lab/README.md`
3. `docs/strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md`
4. `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md`
5. `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
6. `src/sis/research/strategy_lab/`
7. `src/sis/commands/research.py`
8. `src/sis/paper/runner.py`
