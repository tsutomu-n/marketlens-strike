<!--
作成日: 2026-06-17_06:32 JST
更新日: 2026-06-28_07:07 JST
-->

# Implemented Surfaces

この文書は現行コードで使える主要 surface を読むための入口です。技術寄りの capability index は [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md) を読む。実務的な次方向は [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) を読む。

## 結論

現在の主軸は backtest-first / venue-neutral。実装済み surface は、Crypto Perp Truth-Cycle MVP artifact chain / Strategy Input Contract / Idea Intake / Strategy Input Feedback / Stage Policy / Stage Decision / Paper Smoke Plan / Runtime Observation Ingest / Paper vs Backtest Drift Review / Strategy Learning / Authoring Update Handoff / Strategy Case Lite / Strategy Case Index / Strategy Daily Brief / Strategy AI Review / Strategy Model Loop / Strategy Micro Live Plan Gate / Strategy Next Scale Plan / Strategy Live Observation / Strategy Scale Decision / Strategy Workbench Viewer / Strategy Lab / Strategy Authoring / backtest pack / Strategy Review / NDX local research gates / read-only Trade[XYZ] / paper operation / operations audit である。

production live trading、wallet、signing、exchange write は現行 operator path では許可しない。

## Core Runtime

| Surface | Status | Primary Evidence |
|---|---|---|
| Python 3.13 CLI workspace | implemented | `pyproject.toml`, `.python-version`, `uv.lock`, `src/sis/cli.py` |
| aggregate local gate | implemented | `scripts/check`, `uv run python scripts/check_current_docs.py` |
| command registration split | implemented | `src/sis/cli.py`, `src/sis/commands/` |
| current-doc checker | implemented | `scripts/check_current_docs.py` |

## Strategy And Backtest

| Surface | Status | Primary Evidence |
|---|---|---|
| Strategy Research Lab artifact chain | implemented | `src/sis/research/strategy_lab/`, Strategy Lab schemas, `tests/` |
| Strategy Authoring YAML flow | implemented | `strategy-author-*`, `src/sis/research/strategy_lab/authoring/`, `tests/strategy_authoring/` |
| Strategy backtest suite / comparison / robustness artifacts | implemented | `strategy-backtest-suite`, `strategy-backtest-compare`, `strategy-backtest-stress`, `strategy-backtest-regime-split`, `strategy-backtest-rolling-stability`, `strategy-backtest-benchmark-relative` |
| Strategy backtest pack and validation | implemented | `strategy-backtest-pack`, `strategy-backtest-pack-validate`, `schemas/strategy_backtest_pack*.json`, `docs/backtest/` |
| optional framework surfaces | implemented as optional / no-live | `strategy-backtest-framework-run`, `vectorbt`, `bt`, `metrics`, `reports` optional extras |
| Strategy Input Contract / Idea Intake first gate | implemented as local artifact validation, no permission | `strategy-input-contract-validate`, `strategy-intake-validate`, `src/sis/strategy_inputs/`, `schemas/strategy_input_contract.v1.schema.json`, `schemas/strategy_input_contract_validation.v1.schema.json`, `schemas/strategy_idea.v1.schema.json`, `schemas/strategy_intake_decision.v1.schema.json`, `tests/strategy_inputs/`, `docs/strategy_inputs/` |
| Strategy Input Feedback proposal / review | implemented as local update-candidate and human-review artifacts, no direct contract edit or auto-apply | `strategy-input-feedback-proposal-build`, `strategy-input-feedback-proposal-review`, `src/sis/strategy_input_feedback/`, `schemas/strategy_input_contract_update_proposal.v1.schema.json`, `schemas/strategy_input_contract_update_review.v1.schema.json`, `tests/strategy_input_feedback/`, `docs/strategy_input_feedback/` |
| Strategy Stage Policy / Decision first slice | implemented as local policy validation and non-permission planning decision | `strategy-stage-policy-validate`, `strategy-stage-decision`, `src/sis/strategy_stage/`, `schemas/strategy_stage_policy.v1.schema.json`, `schemas/strategy_stage_policy_validation.v1.schema.json`, `schemas/strategy_stage_decision.v1.schema.json`, `tests/strategy_stage/`, `docs/strategy_stage/` |
| Strategy Paper Smoke Plan first slice | implemented as read-only smoke plan/report, no paper execution by itself | `strategy-paper-smoke-plan`, `src/sis/strategy_paper_smoke/`, `schemas/strategy_paper_smoke_plan.v1.schema.json`, `tests/strategy_paper_smoke/`, `docs/strategy_paper_smoke/` |
| Strategy Runtime Observation Ingest first slice | implemented as read-only paper runtime ledger ingest for drift inputs | `strategy-runtime-observation-ingest`, `src/sis/strategy_runtime_observation/`, `schemas/strategy_runtime_observation_manifest.v1.schema.json`, `tests/strategy_runtime_observation/`, `docs/strategy_runtime_observation/` |
| Paper vs Backtest Drift Review first slice | implemented as read-only drift review artifact, no paper/live permission | `strategy-drift-review`, `src/sis/strategy_drift_review/`, `schemas/paper_vs_backtest_drift_review.v1.schema.json`, `tests/strategy_drift_review/`, `docs/strategy_drift_review/` |
| Strategy Learning / Revision Request / Authoring Update Handoff first slice | implemented as learning ledger, revision request, human review artifact, and human authoring update handoff, no automatic spec edit | `strategy-learning-ledger-update`, `strategy-revision-request-build`, `strategy-revision-request-review`, `strategy-authoring-update-handoff`, `src/sis/strategy_learning/`, `schemas/strategy_learning_event.v1.schema.json`, `schemas/strategy_revision_request.v1.schema.json`, `schemas/strategy_revision_request_review.v1.schema.json`, `schemas/strategy_authoring_update_handoff.v1.schema.json`, `tests/strategy_learning/`, `docs/strategy_learning/` |
| Strategy Case Lite first slice | implemented as read-only per-strategy artifact timeline, no paper/live permission | `strategy-case-lite-update`, `src/sis/strategy_case_lite/`, `schemas/strategy_case_lite.v1.schema.json`, `tests/strategy_case_lite/`, `docs/strategy_case_lite/` |
| Strategy Case Index | implemented as read-only multi-case index over `strategy_case_lite.v1`, no DB registry or paper/live permission | `strategy-case-index-build`, `src/sis/strategy_case_index/`, `schemas/strategy_case_index.v1.schema.json`, `tests/strategy_case_index/`, `docs/strategy_case_index/` |
| Strategy Daily Brief first slice | implemented as read-only daily artifact index, including Crypto Perp tournament gate, truth-cycle next step, and first stage blocker follow-up, no paper/live permission | `strategy-daily-brief`, `src/sis/strategy_daily_brief/`, `schemas/strategy_daily_brief.v1.schema.json`, `tests/strategy_daily_brief/`, `docs/strategy_daily_brief/` |
| Strategy AI Review first slice | implemented as safe summary packet, AI note recorder, and structured human-review findings, no auto-apply or permission | `strategy-ai-review-packet-build`, `strategy-ai-review-note-record`, `strategy-ai-review-findings-structure`, `src/sis/strategy_ai_review/`, `schemas/strategy_ai_review_packet.v1.schema.json`, `schemas/strategy_ai_review_note.v1.schema.json`, `schemas/strategy_ai_review_structured_findings.v1.schema.json`, `tests/strategy_ai_review/`, `docs/strategy_ai_review/` |
| Strategy Model / Optimizer Loop first slice | implemented as generic model run and all-trial ledger, no optimizer execution or auto-apply | `strategy-model-run-record`, `src/sis/strategy_model_loop/`, `schemas/strategy_model_run.v1.schema.json`, `schemas/strategy_optimizer_trial_ledger.v1.schema.json`, `tests/strategy_model_loop/`, `docs/strategy_model_loop/` |
| Strategy Micro Live Plan Gate first slice | implemented as read-only micro live plan artifact, no live execution permission | `strategy-micro-live-plan`, `src/sis/strategy_micro_live_plan/`, `schemas/strategy_micro_live_plan.v1.schema.json`, `tests/strategy_micro_live_plan/`, `docs/strategy_micro_live_plan/` |
| Strategy Next Scale Plan first slice | implemented as read-only post-scale-decision planning artifact, no next-scale execution permission | `strategy-next-scale-plan`, `src/sis/strategy_next_scale_plan/`, `schemas/strategy_next_scale_plan.v1.schema.json`, `tests/strategy_next_scale_plan/`, `docs/strategy_next_scale_plan/` |
| Strategy Live Observation first slice | implemented as read-only micro live canary evidence ingest, no live execution or scale-up permission | `strategy-live-observation-ingest`, `src/sis/strategy_live_observation/`, `schemas/strategy_live_observation_manifest.v1.schema.json`, `tests/strategy_live_observation/`, `docs/strategy_live_observation/` |
| Strategy Scale Decision first slice | implemented as read-only post-canary decision artifact, no scale-up execution permission | `strategy-scale-decision`, `src/sis/strategy_scale_decision/`, `schemas/strategy_scale_decision.v1.schema.json`, `tests/strategy_scale_decision/`, `docs/strategy_scale_decision/` |
| Strategy Workbench Viewer first slice | implemented as static HTML artifact viewer, including Crypto Perp tournament gate, truth-cycle status, next-step, first-stage-blocker, and Strategy Case Index summaries, no paper/live permission | `strategy-workbench-viewer-build`, `src/sis/strategy_workbench_viewer/`, `schemas/strategy_workbench_viewer.v1.schema.json`, `tests/strategy_workbench_viewer/`, `docs/strategy_workbench_viewer/` |
| Strategy Lifecycle review / status | implemented as local artifact review and read-only status summary | `strategy-backtest-acceptance`, `strategy-paper-observation-cycle`, `strategy-lifecycle-review`, `strategy-paper-observation-status`, `docs/strategy_lifecycle/` |
| Strategy Review packet / operator decision record | implemented as read-only human-review packet plus non-permission decision artifact; can include optional input contract / strategy idea source artifacts | `strategy-review-build`, `strategy-review-record`, `src/sis/strategy_review/`, `schemas/strategy_review_manifest.v1.schema.json`, `schemas/operator_strategy_review.v1.schema.json`, `tests/strategy_review/`, `docs/strategy_review/` |

## Crypto Perp Truth-Cycle

| Surface | Status | Primary Evidence |
|---|---|---|
| Crypto Perp Truth-Cycle MVP artifact chain | implemented as local / fixture-first artifact chain, no automatic trading | `crypto-perp-probe-audit`, `crypto-perp-raw-refresh`, `crypto-perp-decision-record`, `crypto-perp-outcome-record`, `crypto-perp-truth-cycle-status`, `src/sis/crypto_perp/`, `schemas/crypto_perp_*.schema.json`, `tests/crypto_perp/`, `crypto-perp-*` read-only/mock-first CLI commands |
| Outcome-to-tournament rows preview | implemented as matured outcome to 3action before-cost proxy rows with `cash_metric_basis=before_cost_proxy`, no actual cash claim | `crypto-perp-tournament-rows-preview`, `src/sis/crypto_perp/tournament_rows.py`, `schemas/crypto_perp_tournament_rows_preview.v1.schema.json`, `tests/crypto_perp/test_tournament_rows.py` |
| Profit-readiness source / replay / feature / edge layer | implemented as local evidence artifacts, no ML claim and no source zero-fill | `crypto-perp-source-availability`, `crypto-perp-replay-slice`, `crypto-perp-feature-pack`, `crypto-perp-edge-score`, `src/sis/crypto_perp/source_availability.py`, `src/sis/crypto_perp/replay.py`, `src/sis/crypto_perp/features.py`, `src/sis/crypto_perp/edge_scorer.py`, `schemas/crypto_perp_source_availability.v1.schema.json`, `schemas/crypto_perp_replay_slice.v1.schema.json`, `schemas/crypto_perp_feature_pack.v1.schema.json`, `schemas/crypto_perp_edge_score.v1.schema.json`, `tests/crypto_perp/` |
| Cost-aware tournament rows and bias guard | implemented as estimate/stress rows and sample/bias guard, not actual cash proof | `crypto-perp-tournament-rows-v2`, `crypto-perp-bias-guard`, `src/sis/crypto_perp/tournament_rows.py`, `src/sis/crypto_perp/bias_guards.py`, `schemas/crypto_perp_tournament_rows.v2.schema.json`, `schemas/crypto_perp_bias_guard.v1.schema.json`, `tests/crypto_perp/test_tournament_rows.py`, `tests/crypto_perp/test_bias_guards.py` |
| Tiny-live shadow measurement | implemented as non-order preflight artifact, always false for live permission and exchange write | `crypto-perp-tiny-live-shadow`, `src/sis/crypto_perp/tiny_live_shadow.py`, `schemas/crypto_perp_tiny_live_shadow.v1.schema.json`, `tests/crypto_perp/test_tiny_live_shadow.py` |
| Hypothesis tournament and Workbench bridge | tournament report implemented as local CLI with explicit cash metric basis; Workbench bridge treats non-actual basis as no fills/slippage evidence | `crypto-perp-tournament-report`, `src/sis/crypto_perp/tournament.py`, `src/sis/crypto_perp/workbench_bridge.py`, `schemas/crypto_perp_tournament_report.v1.schema.json`, `tests/crypto_perp/test_tournament.py`, `tests/crypto_perp/test_workbench_bridge.py` |
| Tournament gate decision | implemented as local threshold gate; blocks non-actual cash basis as `NEEDS_ACTUAL_CASH`, no tiny live execution permission | `crypto-perp-tournament-gate`, `src/sis/crypto_perp/tournament_gate.py`, `schemas/crypto_perp_tournament_gate.v1.schema.json`, `tests/crypto_perp/test_tournament_gate.py` |

## NDX Research Gates

| Surface | Status | Primary Evidence |
|---|---|---|
| Layer 2.2 DAG foundation | implemented local-only | `research-layer22-validate`, `research-layer22-export`, `configs/research_layer_2_2/ndx/` |
| Layer 2.2 review harness | implemented manual/local | `research-layer22-review-pack`, `research-layer22-review-import`, `research-layer22-exit-gate` |
| Layer 2.3 preflight / feature panel / residual | implemented fixture-first/local | `research-ndx-source-resolve`, `research-ndx-feature-panel`, `research-ndx-residual`, `research-ndx-diagnostics` |
| Layer 2.4 residual validation | implemented local gate | `research-ndx-residual-validate`, `schemas/ndx_residual_validation*.json` |
| Layer 2.5-2.8 paper-observation path | implemented local artifact gates | `research-ndx-strategy-lab-export`, `research-ndx-paper-observation-gate`, `research-ndx-operator-promotion`, `research-ndx-paper-observation-review` |

NDX approvals do not prove alpha, backtest readiness, paper readiness, live readiness, account readiness, wallet readiness, or exchange-write readiness.

## Venue / Execution / Operations

| Surface | Status | Primary Evidence |
|---|---|---|
| Trade[XYZ] registry / quote collection / normalization | implemented read-only | `collect-trade-xyz-*`, `src/sis/venues/trade_xyz/`, `tests/test_trade_xyz_*` |
| Trade[XYZ] data readiness / phase gate | implemented read-only | `validate-artifacts`, `phase-gate-review`, `trade-xyz-collection-status` |
| Trade[XYZ] read-only execution state collector | implemented opt-in / no-write | `src/sis/venues/trade_xyz/execution_state.py`, `execution-read-only-surfaces`, `execution-snapshot`, `tests/test_trade_xyz_execution_state.py` |
| Trade[XYZ] pure backtest v0.1 | implemented Python API, no public CLI | `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/`, `tests/backtest/` |
| Bitget demo smoke | implemented local/mock-first | `bitget-demo-smoke`, `src/sis/execution/bitget_demo_adapter.py` |
| Venue read-only capability probe | implemented fixture-first / no-network | `venue-read-only-probe`, `src/sis/venues/read_only_probe.py`, `schemas/venue_read_only_probe_summary.v1.schema.json`, `docs/venues/read_only_capability_probe.md` |
| paper operations | implemented paper/read-only | `paper-step`, `paper-from-intents`, `paper-report`, `paper-operations-cycle` |
| operations / audit / remediation surfaces | implemented | `operations-dashboard`, `operations-bundle`, `audit-*`, `remediation-*`, `current-state-index`, `readiness-snapshot` |

## Known Boundaries

- `VenueId` currently allows `trade_xyz` and `bitget_demo`.
- `bitget_futures` and `hyperliquid_perp` are catalog-only / disabled for current Strategy Lab schemas.
- `venue-read-only-probe` is a local fixture-first boundary artifact. It does not prove network readiness, credential readiness, paper readiness, or live readiness.
- `bitget_demo` is a demo execution surface, not production Bitget readiness.
- Trade[XYZ] read-only execution state collection requires a public user address and explicit opt-in. Without them, it records `trade_xyz_execution_state_user_address_missing` or opt-in-required status and does not call external API.
- `PaperIntentPreview` is paper-only and requires revalidation before paper flow use.
- `strategy-input-contract-validate` and `strategy-intake-validate` create local validation artifacts only. `READY_FOR_AUTHORING_DRAFT` is not paper permission or live readiness.
- `strategy-input-feedback-proposal-build` and `strategy-input-feedback-proposal-review` create update-candidate and human-review artifacts only. They do not edit Strategy Input Contract, generate patches, auto-apply changes, or permit paper/live execution.
- `strategy-stage-policy-validate` and `strategy-stage-decision` create local policy / decision artifacts only. `READY_FOR_PAPER_SMOKE_PLAN`, `READY_FOR_NORMAL_PAPER_OBSERVATION`, `READY_FOR_DRIFT_REVIEW`, and `READY_FOR_MICRO_LIVE_PLAN` are not paper execution or live execution permission.
- `strategy-paper-smoke-plan` creates a plan/report only. `READY_TO_RUN_SMOKE_CYCLE` is not normal paper pass, live readiness, or automatic paper execution.
- `strategy-runtime-observation-ingest` reads paper runtime artifacts only. It does not create orders and does not prove paper pass or live readiness.
- `strategy-drift-review` reads backtest and runtime observation artifacts only. It does not create paper orders, permit micro live, or prove live readiness. PnL drift is used only when runtime observation includes realized paper PnL and filled notional.
- `strategy-learning-ledger-update`, `strategy-revision-request-build`, `strategy-revision-request-review`, and `strategy-authoring-update-handoff` create learning, revision-request, review, and handoff artifacts only. They do not edit Strategy Authoring YAML and keep `auto_applied=false`.
- `strategy-case-lite-update` creates a per-strategy timeline artifact only. It does not permit paper or live execution.
- `strategy-case-index-build` creates a read-only index over `strategy_case_lite.v1` artifacts only. It does not persist a DB registry, merge cases, edit source cases, or permit paper/live execution.
- `strategy-daily-brief` creates a daily read-only index of actionable artifacts only. It does not permit paper or live execution.
- `strategy-ai-review-packet-build`, `strategy-ai-review-note-record`, and `strategy-ai-review-findings-structure` create AI review support artifacts only. They do not auto-apply changes or permit paper/live execution.
- `strategy-model-run-record` records model / optimizer results only. It does not run optimizers, edit Strategy Authoring YAML, or permit paper/live execution.
- `strategy-micro-live-plan`, `strategy-scale-decision`, and `strategy-next-scale-plan` create human-review planning artifacts only. `READY_FOR_HUMAN_MICRO_LIVE_REVIEW`, `READY_FOR_HUMAN_SCALE_REVIEW`, and `READY_FOR_HUMAN_NEXT_SCALE_REVIEW` are reported as `status=needs_human_approval` with `requires_explicit_approval=true` and `permits_live_order=false`, not `status=pass`; blocked paths report `status=blocked`, `requires_explicit_approval=false`, and `permits_live_order=false`.
- `strategy-next-scale-plan` creates a next scale planning artifact only. It does not permit next-scale execution or live execution.
- `strategy-workbench-viewer-build` creates a static HTML viewer from existing artifacts only. It can summarize `strategy_case_index.v1`, but does not edit artifacts, persist registry state, or permit paper/live execution.
- Crypto Perp tournament compares `REVERSAL_SHORT`, `CONTINUATION_LONG`, and `NO_TRADE` on the same event set. `actual_cash_result_usd` is the legacy primary field, but `cash_metric_basis`, `primary_metric_display_name`, and `actual_cash` are the semantic guard. Insufficient data remains `INCONCLUSIVE_DATA`. Rows produced by `crypto-perp-tournament-rows-preview` are `cash_metric_basis=before_cost_proxy`, not actual cash evidence, and `crypto-perp-tournament-report` rejects preview / non-actual rows with `PREVIEW_ROWS_NOT_ACTUAL_CASH`.
- Crypto Perp profit-readiness rows v2 use `cost_adjusted_cash_estimate_usd` and `stress_cash_estimate_usd`. They do not populate `actual_cash_result_usd` unless actual cash evidence is supplied.
- `crypto-perp-truth-cycle-status` reads existing Crypto Perp artifacts and reports the next missing local step, stop reasons, and known gaps. It does not fetch network data or permit live execution.
- `crypto-perp-tournament-gate` creates a local gate artifact only. Reports with `actual_cash=false` or `cash_metric_basis != actual_cash` are blocked as `NEEDS_ACTUAL_CASH`. `READY_FOR_HUMAN_TINY_LIVE_REVIEW` is not live execution permission and still requires separate explicit approval; CLI stdout reports this as `status=needs_human_approval`, not `status=pass`.
- `strategy-review-build` creates review artifacts only. Optional `--input-contract` and `--strategy-idea` add read-only source summaries. `strategy-review-record` records human decisions against those artifacts. Neither authorizes paper execution or live trading.
- `READ_ONLY_GO` is not live trading ready.
- `data/` is git-ignored runtime state and may be absent in a fresh checkout.

## Verification

```bash
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```
