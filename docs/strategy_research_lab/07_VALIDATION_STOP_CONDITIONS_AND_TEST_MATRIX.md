<!--
作成日: 2026-05-30_11:09 JST
更新日: 2026-06-23_22:39 JST
-->

# Validation Stop Conditions And Test Matrix

この文書は、Strategy Research Lab の停止条件と既存テストが守る契約をまとめます。

## Universal stop conditions

- `PaperIntentPreview` を live order と読んだら停止。
- `TradeCandidate` を order と読んだら停止。
- `PaperCandidatePack` を profitability / paper-ready / live-ready 証明として読んだら停止。
- `data/research/signals.csv` を Strategy Lab 正本として読んだら停止。
- JSON Schema だけで full validation 済みと扱ったら停止。
- `READ_ONLY_GO` を live-ready と読んだら停止。
- `wallet_used=true` または `exchange_write_used=true` を Strategy Lab path で許容しようとしたら停止。
- NDX/QQQ family を現行 paper candidate、`PaperIntentPreview`、raw `paper-from-intents` JSON、legacy `paper-step` へ通そうとしたら停止。

## Schema guard matrix

| Model | Guard |
|---|---|
| `StrategyRunProfile` | exchange write, wallet, live order submission disabled; current claim names required |
| `StrategyExperimentSpec` | non-empty strategy IDs; symbol bindings required; legacy claim names rejected |
| `SymbolBinding` | `XYZ100 -> QQQ`, `SP500 -> SPY`; symbols uppercase |
| `StrategySignalManifest` | generator metadata, symbol bindings, feature fingerprint, and non-negative signal count |
| `StrategySignalRecord` | symbol fields non-empty; signal IDs unique in the artifact; confidence / rank ranges |
| `EvaluationPlan` | positive horizon / purge / embargo / min trade count; stress multipliers >= 1.0 |
| `TrialRecord` | non-negative counts; parameter count > 0; claim flags false |
| `TradeCandidate` | identity fields non-empty; live order flag false; score ranges |
| `PaperCandidatePack` | selected / rejected IDs must exist and be unique; candidate IDs unique; selected/rejected overlap rejected; selected candidates must be candidate status, have no block reasons, and be venue-suitable; claim/live/wallet/exchange flags false |
| `PromotionDecision` | promote requires evidence and approval reason; hold/reject require rejection reason |
| `PaperIntentPreview` | revalidation required; paper-only; live conversion/wallet/exchange false; venue suitability checked at paper-intent stage |
| `DataSnapshotManifest` | data paths and non-empty symbols/venues; min_ts <= max_ts |
| `FeatureSnapshotManifest` | required identity/path fields; missing rates 0.0 to 1.0 |

## Existing test matrix

| Test file | Contract covered |
|---|---|
| `tests/test_strategy_run_profile.py` | strategy_lab profile blocks exchange write / wallet / live order; rejects legacy claim names |
| `tests/test_strategy_lab_specs.py` | symbol binding, proxy rule, StrategyExperimentSpec claim guard, StrategySignalRecord validation |
| `tests/test_strategy_lab_signal_registry.py` | generator registry fail-closed behavior; signal frame required columns and symbol binding |
| `tests/test_strategy_lab_evaluation_plan.py` | EvaluationPlan required profile, positive values, forbidden claim guard |
| `tests/test_strategy_lab_trial_ledger.py` | TrialRecord guard, JSONL append/read, EvaluationRunner appends records |
| `tests/test_strategy_lab_candidate_pack.py` | TradeCandidate and PaperCandidatePack selected/rejected ID validation, selected non-candidate rejection, venue suitability rejection, and live flag guard |
| `tests/test_strategy_lab_promotion_decision.py` | PromotionDecision promote/reject/hold validation and live guard |
| `tests/test_strategy_lab_paper_intent_preview.py` | PaperIntentPreview paper-only and live conversion guard |
| `tests/test_strategy_lab_schemas.py` | tracked JSON Schema files, including signal manifest, authoring backtest result, and bundle result, exist and paper-only const guards match |
| `tests/test_strategy_lab_commands.py` | CLI artifact chain, idempotent evaluation, rank threshold sweep, multi-signal candidate selection, and missing-pack stops |
| `tests/test_paper_from_intents.py` | paper-from-intents revalidates raw JSON, writes paper artifacts, blocks expired intent, and rejects NDX/QQQ venue-unsuitable intents |
| `tests/test_venue_suitability.py` | suitability catalog, NDX/QQQ family detection, and catalog-only future venue guards |
| `tests/test_paper_runner.py` | legacy `paper-step` skips NDX/QQQ family rows and records `legacy_paper_blocked_*` metrics |

## Verification commands

Targeted:

```bash
uv run pytest tests/test_strategy_lab_*.py tests/test_strategy_run_profile.py tests/test_paper_from_intents.py
uv run pytest tests/test_venue_suitability.py tests/test_paper_runner.py tests/test_strategy_lab_candidate_pack.py tests/test_paper_from_intents.py tests/test_strategy_lab_commands.py
```

Docs guard:

```bash
rg -n "signals.csv|DecisionContext|ExecutionPlan|PaperIntentPreview|StrategySignalRecord|TradeCandidate" docs/strategy_research_lab docs/archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29
rg -n "live_conversion_allowed=false|wallet_used=false|exchange_write_used=false|paper_only=true" docs/strategy_research_lab
```

Repo standard:

```bash
./scripts/check
```

## Acceptance criteria for docs

Docs are acceptable when:

- a reader can explain the full artifact chain without reading source code;
- every trading-related schema has purpose, key fields, validation, and forbidden interpretation;
- `signals.csv` is consistently described as legacy export;
- `PaperIntentPreview` is consistently described as paper-only preview;
- NDX/QQQ paper-path blocking is described as a venue suitability boundary, not as an alpha or Strategy Lab export conclusion;
- legacy docs no longer teach `DecisionContext` / `ExecutionPlan` as the Strategy Lab design entry point;
- no document claims production live trading readiness.
