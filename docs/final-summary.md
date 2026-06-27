<!--
作成日: 2026-06-27_11:32 JST
更新日: 2026-06-28_07:49 JST
-->

# Final Summary

## Latest Addendum: Crypto Perp Profit-Readiness Local Automation

Completed on branch `ai/crypto-perp-profit-readiness-local-automation-20260628-0000`.

Achieved:

- Added local inventory and planner artifacts for Crypto Perp profit-readiness.
- Added a local chain runner that writes source availability, replay slice, feature pack, edge score, rows-v2, bias guard, and run manifest in one run directory.
- Added `crypto-perp-cash-ledger` CLI around the existing cash ledger builder.
- Added ledger plus assignment based actual-cash rows builder. Trade actions require matching ledger entries; `NO_TRADE` can be explicit cash 0.
- Added actual-cash report/gate helper, tiny-live human review packet builder, and tiny-live shadow readiness checker.
- Added schemas for inventory, plan, run, actual-cash rows summary, actual-cash report/gate run, review packet, and shadow readiness.
- Updated runbook, implemented surfaces, and CLI catalog.

Main files changed:

- `src/sis/crypto_perp/profit_readiness.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `schemas/crypto_perp_profit_readiness_inventory.v1.schema.json`
- `schemas/crypto_perp_profit_readiness_plan.v1.schema.json`
- `schemas/crypto_perp_profit_readiness_run.v1.schema.json`
- `schemas/crypto_perp_actual_cash_rows_summary.v1.schema.json`
- `schemas/crypto_perp_actual_cash_report_gate_run.v1.schema.json`
- `schemas/crypto_perp_tiny_live_review_packet.v1.schema.json`
- `schemas/crypto_perp_tiny_live_shadow_readiness.v1.schema.json`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/plans/crypto-perp-profit-readiness-local-automation-2026-06-28.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

Verification run:

- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q`

Remaining work:

- Real event, matured outcome, and actual cash evidence collection remains outside this local automation slice.
- If current `data/crypto_perp` only contains dogfood/status/viewer artifacts, inventory and plan intentionally stop with blocker status.

User decisions required:

None for this local automation slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the new profit-readiness module, command additions, schemas, tests, and docs changes from this branch.

## Latest Addendum: PR-I1b Cash Metric Legacy Migration

Completed on branch `ai/cash-metric-legacy-migration-20260628-0721`.

Achieved:

- Added `cash_metric_value_usd` as the canonical tournament row / score comparison value.
- Kept legacy actual-cash rows readable by migrating missing `cash_metric_value_usd` from `actual_cash_result_usd` during validation.
- Made generated non-actual rows use `actual_cash_result_usd=null`.
- Moved tournament scoring and leader summaries to `cash_metric_value_usd`.
- Kept `actual_cash_result_usd` and `leader_actual_cash_result_usd` populated only for actual cash basis.
- Kept `crypto-perp-tournament-report` actual-cash-only and continued rejecting preview / non-actual rows.
- Updated v1 schemas with optional `cash_metric_value_usd` and nullable legacy actual-cash aliases.
- Updated runbook, vocabulary, implemented/current docs, Workbench README, and this summary.

Main files changed:

- `src/sis/crypto_perp/tournament.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `schemas/crypto_perp_tournament_report.v1.schema.json`
- `schemas/crypto_perp_tournament_rows_preview.v1.schema.json`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `docs/plans/cash-metric-legacy-migration-2026-06-28.md`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/final-summary.md`

Verification:

- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py`
- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_workbench_bridge.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q`

Pending final verification in this work session:

- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`

User decisions required:

None.

Destructive change:

No schema version bump and no required dependency change. Generated non-actual artifacts no longer populate `actual_cash_result_usd`; consumers should read `cash_metric_value_usd` plus `cash_metric_basis`.

Dependency change:

No.

Migration:

New producers should emit `cash_metric_value_usd`. Old actual-cash rows without that field remain accepted and are migrated from `actual_cash_result_usd`.

Rollback:

Revert this checkpoint's model/schema/test/docs changes. PR-I1a remains valid without I1b.

## Latest Addendum: PR-I1a Cash Metric Semantic Hotfix

Completed on branch `ai/actual-cash-semantic-repair-20260628-0645`.

Achieved:

- Added `cash_metric_basis` to `TournamentEventResult`, defaulting to `actual_cash` for backward compatibility.
- Made preview rows emit `cash_metric_basis=before_cost_proxy` in JSON and JSONL.
- Added `cash_metric_basis`, `primary_metric_display_name`, `actual_cash`, `leader_cash_metric_value_usd`, and `leader_actual_cash_result_usd` to `crypto_perp_tournament_report.v1` generation.
- Kept schema version v1 and added fields as optional schema extensions so older artifacts remain readable.
- Made report generation mark proxy / estimate known gaps as non-actual cash and mixed row basis as `INCONCLUSIVE_DATA`.
- Kept `crypto-perp-tournament-report` actual-cash-only by rejecting preview schema, proxy / estimate known gaps, and `cash_metric_basis != actual_cash` rows with `PREVIEW_ROWS_NOT_ACTUAL_CASH`.
- Made tournament gate block `actual_cash=false` or `cash_metric_basis != actual_cash` as `NEEDS_ACTUAL_CASH`.
- Made Workbench bridge and viewer carry cash basis summary fields and avoid treating non-actual basis as fills/slippage-included evidence.
- Updated runbook, vocabulary, surface inventory, implemented/current docs, Workbench README, and this summary.

Main files changed:

- `src/sis/crypto_perp/tournament.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/crypto_perp/tournament_gate.py`
- `src/sis/crypto_perp/workbench_bridge.py`
- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `src/sis/strategy_workbench_viewer/summary_fields.py`
- `schemas/crypto_perp_tournament_report.v1.schema.json`
- `schemas/crypto_perp_tournament_rows_preview.v1.schema.json`
- `schemas/strategy_workbench_viewer.v1.schema.json`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `tests/crypto_perp/test_tournament_gate.py`
- `tests/crypto_perp/test_workbench_bridge.py`
- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/final-summary.md`

Verification:

- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_workbench_bridge.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q`

Pending final verification in this work session:

- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`

User decisions required:

None.

Destructive change:

No. CLI behavior remains stricter for invalid non-actual cash report input, but no schema version was bumped and no existing artifact field was removed.

Dependency change:

No.

Migration:

Operators should include `cash_metric_basis=actual_cash` in manual actual-cash JSONL rows. Existing rows without the field are still interpreted as actual cash for compatibility, but preview / estimate rows must not be fed to `crypto-perp-tournament-report`.

Rollback:

Revert the cash basis model/schema/test/report/gate/Workbench changes from this addendum.

## Latest Addendum: Actual Cash Semantic Repair

Completed on branch `ai/actual-cash-semantic-repair-20260628-0645`.

Achieved:

- Added a `PREVIEW_ROWS_NOT_ACTUAL_CASH` guard to `crypto-perp-tournament-report`.
- Rejected `crypto_perp_tournament_rows_preview.v1` and rows carrying `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` before report generation.
- Kept caller-owned actual-cash JSONL / `TournamentEventResult` input working.
- Updated preview Markdown to display `outcome_before_cost_proxy_usd` instead of `actual_cash_result_usd`.
- Updated current docs and runbook wording so preview rows are display / dogfood only and cannot feed `crypto-perp-tournament-report`.

Main files changed:

- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/plans/actual-cash-semantic-repair-2026-06-28.md`
- `docs/final-summary.md`

Verification:

- `uv run pytest tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_rows.py`
- `git diff --check`

Not fully passed:

- `uv run python scripts/check_current_docs.py` failed on existing tracked plan routing: `plan/0628から/0628-0623.md: tracked plan file is outside current root plan or archive routing`. This file was not changed in this checkpoint.

Remaining work:

- Resolve the pre-existing plan routing checker failure separately if full current-doc validation is required.

User decisions required:

None.

Destructive change:

No. CLI behavior is stricter for invalid preview input, but no data or schema was deleted.

Dependency change:

No.

Migration:

Operators must stop feeding `tournament_rows_preview.json` into `crypto-perp-tournament-report`. Use actual-cash rows for reports and `crypto-perp-tournament-rows-v2` for estimates.

Rollback:

Revert the guard, test, preview Markdown wording, and docs changes from this addendum.

## Latest Addendum: Docs Triage Refresh

Completed on branch `main`.

Achieved:

- Refreshed `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` as the current docs triage artifact.
- Added explicit 判定基準 for 更新できる / 古い内容がある / 作り直したほうがいい / 削除・アーカイブしてもよい docs.
- Added next cleanup candidates without deleting, moving, or archiving files.
- Expanded the 抜け・漏れ・誤謬リスク section around docs checker limits, CLI catalog limits, runtime snapshots, archive docs, and intentionally thin low-level helper docs.
- Kept historical docs as context only and did not re-promote `docs/archive/**` or `plan/archive/**` into current proof.

Main files changed:

- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/plans/docs-triage-refresh-2026-06-28.md`
- `docs/final-summary.md`

Verification:

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

Not run:

- Full `./scripts/check`; this checkpoint only updated docs and did not change code, schema, CLI routing, or checker allowlists.

Remaining work:

- Execute cleanup candidates only as a separate task.

User decisions required:

None.

Destructive change:

No. No docs were deleted, moved, or archived.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert this docs triage refresh and remove the checkpoint plan.

## Latest Addendum: Docs Archive Triage Cleanup

Completed on branch `ai/docs-archive-triage-20260627-2341`.

Achieved:

- Moved superseded root audit docs to `docs/archive/2026-06-27-doc-routing/`.
- Moved completed 2026-06-27 work plans from `docs/plans/` to `docs/archive/2026-06-27-merged-plans/`.
- Updated current docs routing so `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` is the current docs triage entry.
- Removed archived audit docs from `scripts/check_current_docs.py` current-doc allowlist.
- Kept archive docs as historical snapshots, not current proof.

Main files changed:

- `README.md`
- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/DOCS_LINT_POLICY_2026-05-30.md`
- `docs/archive/README.md`
- `docs/final-summary.md`
- `scripts/check_current_docs.py`
- `docs/archive/2026-06-27-doc-routing/`
- `docs/archive/2026-06-27-merged-plans/`

Verification:

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

Not run:

- Full `./scripts/check`; this cleanup only moved docs and updated docs routing.

Remaining work:

- None for this cleanup.

User decisions required:

None.

Destructive change:

No. Files were moved to archive, not deleted.

Dependency change:

No.

Rollback:

Move the archived docs back to their previous paths and restore the current-doc allowlist entries.

## Latest Addendum: Crypto Perp Profit-Readiness Evidence Run Plan

Completed on branch `ai/crypto-perp-profit-readiness-20260627-1901`.

Achieved:

- Added `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md`.
- Confirmed the current local `data/crypto_perp` inventory has dogfood / status / Daily Brief / Workbench Viewer artifacts, but no real event, outcome, source availability, rows-v2, cash ledger, or live measurement artifact.
- Recorded the stop result as `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Kept dogfood / status artifacts out of profit evidence and actual cash evidence.
- Kept manual outcome prices, estimates, and actual cash result boundaries explicit.
- Did not run public network, credentialed read-only, exchange write, live order, tiny-live measurement, or automatic trading operations.

Main files changed:

- `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md`
- `docs/final-summary.md`

Verification:

- `uv run python scripts/check_current_docs.py`
- `git diff --check`

Not run:

- `uv run pytest tests/crypto_perp -q`, because no Crypto Perp implementation code changed.
- `uv run python scripts/check_cli_catalog.py`, because no CLI catalog or command implementation changed.
- External/public/credentialed/live operations.

Remaining work:

- Create or provide real event and matured outcome artifacts before trying source availability, replay slice, feature pack, rows-v2, or bias guard evidence generation.
- Decide separately whether to approve a public Bitget probe with `SIS_ALLOW_PUBLIC_NETWORK=1`.

User decisions required:

- Public probe approval is required before any network-backed Crypto Perp evidence collection.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Remove the new run plan and this addendum.

## Latest Addendum: Crypto Perp Profit-Readiness Evidence Layer

Completed on branch `ai/crypto-perp-profit-readiness-20260627-1901`.

Achieved:

- Added current plan, surface inventory, and acceptance vocabulary under `docs/crypto_perp/`.
- Added local source availability, replay slice, feature pack, deterministic edge score, cost-aware tournament rows v2, bias guard, and tiny-live shadow surfaces.
- Added public local CLI entries: `crypto-perp-source-availability`, `crypto-perp-replay-slice`, `crypto-perp-feature-pack`, `crypto-perp-edge-score`, `crypto-perp-tournament-rows-v2`, `crypto-perp-bias-guard`, and `crypto-perp-tiny-live-shadow`.
- Kept `actual_cash_result_usd` separate from `before_cost_proxy_usd`, `cost_adjusted_cash_estimate_usd`, and `stress_cash_estimate_usd`.
- Kept missing OFI / trade sign / depth sources as known gaps instead of zero-filling them.
- Added `operator_decision` summary support to `crypto_perp_truth_cycle_status.v1`.
- Updated Workbench bridge execution reality so proxy-gap reports are not marked as including fills/slippage.
- Updated current docs, CLI catalog, and the Crypto Perp runbook.
- Did not add dependencies, external API calls, credential writes, exchange writes, live orders, daemon behavior, or automatic trading.

Main files changed:

- `docs/crypto_perp/`
- `docs/archive/2026-06-27-merged-plans/crypto_perp_profit_readiness_execution_2026-06-27.md`
- `src/sis/crypto_perp/source_availability.py`
- `src/sis/crypto_perp/replay.py`
- `src/sis/crypto_perp/features.py`
- `src/sis/crypto_perp/edge_scorer.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/crypto_perp/bias_guards.py`
- `src/sis/crypto_perp/tiny_live_shadow.py`
- `src/sis/crypto_perp/truth_cycle_status.py`
- `src/sis/crypto_perp/workbench_bridge.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`

Verification:

- `uv run pytest tests/crypto_perp -q` -> 177 passed.
- `uv run python scripts/check_cli_catalog.py` -> checked 216 public CLI commands.
- `uv run python scripts/check_current_docs.py` -> checked 184 current docs.
- `uv run sis crypto-perp-source-availability --help`
- `uv run sis crypto-perp-tournament-rows-v2 --help`
- `uv run sis crypto-perp-tiny-live-shadow --help`
- `uv run sis crypto-perp-truth-cycle-status --help`
- `git diff --check`
- `./scripts/check` -> 2803 passed.

Not run:

- External Bitget/public network probes.
- Credentialed read-only calls.
- Exchange writes or live order calls.
- Real tiny-live measurement.

Remaining work:

- Feed real event/outcome/cash-ledger artifacts through the new estimate surfaces before any human tiny-live review.
- Use actual cash evidence only when cash ledger or live measurement artifacts exist.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required. Existing Truth-Cycle MVP v1 artifacts remain valid; profit-readiness artifacts are additional local surfaces.

Rollback:

Revert the profit-readiness docs, schema, model, CLI, tests, and status/workbench summary changes from this addendum.

## Latest Addendum: PR-AI-LOOP-01 Structured AI Review Findings

Completed on branch `ai/strategy-ai-review-structured-findings-20260627-1822`.

Achieved:

- Added `strategy_ai_review_structured_findings.v1` as a companion artifact to `strategy_ai_review_note.v1`.
- Added typed evidence refs with `ref_type`, `index`, and optional `entry_key`; arbitrary JSON pointers are not accepted.
- Split `severity` from `review_impact`.
- Added `strategy-ai-review-findings-structure` with `--structured-finding-json` as the main input path.
- Added note / packet lineage validation before recording structured findings.
- Auto-assigns `finding-001`, `finding-002`, etc. when `finding_id` is omitted.
- Kept `auto_applied=false`, `permission_allowed=false`, `paper_execution_allowed=false`, and `live_allowed=false`.
- Did not copy `model_reasoning_effort` into structured findings.
- Did not call external AI APIs, auto-classify AI output, auto-edit Strategy Authoring YAML, or connect to operator / stage / paper / live permission.

Main files changed:

- `schemas/strategy_ai_review_structured_findings.v1.schema.json`
- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/archive/2026-06-27-merged-plans/strategy_ai_review_structured_findings_2026-06-27.md`

Verification:

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-findings-structure --help`
- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`
- `./scripts/check`

Not run:

- External AI API calls.
- Automatic prompt execution.
- Paper/live operations.

Remaining work:

- Use at least one real recorded AI note as dogfood input before designing downstream viewer / daily brief structured findings display.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required. Existing packet and note artifacts remain valid.

Rollback:

Revert the `strategy_ai_review_structured_findings.v1` schema/model/service/rendering/CLI/test/docs changes and this addendum.

## Latest Addendum: Strategy AI Review Reasoning Effort

Completed on branch `ai/strategy-ai-review-reasoning-effort-20260627-1748`.

Achieved:

- Added optional `model_reasoning_effort` to `strategy_ai_review_note.v1`.
- Added `--model-reasoning-effort medium|xhigh` to `strategy-ai-review-note-record`.
- Kept `model` as the model id, for example `gpt-5.5`.
- Updated note Markdown rendering to show `model_reasoning_effort`.
- Re-recorded the local PR-AI-LOOP-00 runtime note as `provider=codex-cli`, `model=gpt-5.5`, `model_reasoning_effort=xhigh`.
- Kept `auto_applied=false`, `permission_allowed=false`, `paper_execution_allowed=false`, and `live_allowed=false`.

Main files changed:

- `schemas/strategy_ai_review_note.v1.schema.json`
- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`
- `docs/archive/2026-06-27-merged-plans/strategy_ai_review_reasoning_effort_2026-06-27.md`

Verification:

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-note-record --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python` schema validation for `data/strategy_ai_reviews/pr-ai-loop-00/strategy_ai_review_note.json`
- `./scripts/check`

Not run:

- External AI API calls.
- Automatic prompt execution beyond this manual Codex review session.
- Paper/live operations.

Remaining work:

- Decide whether PR-AI-LOOP-01 should promote `model_reasoning_effort` into structured findings metadata or keep it note-level only.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required. Existing notes without `model_reasoning_effort` remain valid.

Rollback:

Revert the `model_reasoning_effort` schema/model/service/CLI/rendering/test/docs changes and this addendum.

## Latest Addendum: PR-AI-LOOP-00 Safe AI Review Context Sections

Completed on branch `ai/strategy-idea-candidates-20260627-1116`.

Achieved:

- Added `context_sections` to `strategy_ai_review_packet.v1`.
- Added first allowlist extractor for `strategy_case_lite.v1` summary context only.
- Kept full source payload out of packet output.
- Kept unknown schema payload out of `context_sections`.
- Kept sensitive source behavior as `BLOCKED_SENSITIVE_SOURCE`.
- Kept `paper_execution_allowed=false`, `live_allowed=false`, and `permission_allowed=false`.
- Did not execute external AI API calls, auto prompt runs, auto fixes, paper operations, live operations, wallet, signing, or exchange write.

Main files changed:

- `schemas/strategy_ai_review_packet.v1.schema.json`
- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`
- `docs/archive/2026-06-27-merged-plans/strategy_ai_review_context_sections_pr_ai_loop_00_2026-06-27.md`

Verification:

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-packet-build --help`
- `uv run python scripts/check_current_docs.py`
- `uv run sis strategy-ai-review-packet-build --source data/strategy_cases/pr-ai-loop-00/strategy_case_lite.json --review-question "What should a human inspect next?" --out data/strategy_ai_reviews/pr-ai-loop-00`
- `./scripts/check`

Not run:

- `strategy-ai-review-note-record` execution.
- External AI API calls.

Remaining work:

- Decide later whether additional known schemas should get explicit `context_sections` allowlists.
- Note recording remains a separate step after an AI response exists.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the `strategy_ai_review` context section model/schema/service/rendering/test/docs changes and this addendum.

## Goal

Implement the first safe slices of the Strategy Idea Candidate Generation Pipeline: candidate-set contract, Python validation, C4 deterministic generator Python API, C5 split/leakage policy validation API, C6 metric disclosure in reports, C10 operator review Markdown surface, C11 fixture E2E, deterministic JSON/Markdown writer, input-evidence blocking, shortlist export sidecar, docs, and focused tests.

This summary covers the implemented candidate pipeline through `strategy-intake-validate`. It does not claim the downstream C9 Strategy Authoring / backtest / Strategy Review bridge is implemented.

## Branch

`ai/strategy-idea-candidates-20260627-1116`

## Achieved

- Added `strategy_idea_candidate_set.v1` JSON Schema and Pydantic models.
- Added `strategy_idea_candidate_export_manifest.v1` sidecar manifest schema and models.
- Added validation for count mismatch, selected/rejected ID mismatch, selected-only inventory, non-PASS input evidence, missing source summaries, sealed-test selection, and paper/live/auto-promote/final boundary flags.
- Added deterministic candidate-set JSON/Markdown writer.
- Added C4 deterministic generator Python API with fixed family IDs, finite parameter grids, stable `parameter_grid_hash`, candidate cap recording, duplicate rejection recording, and full candidate inventory.
- Added a PASS source evidence guard so inconsistent source-level evidence cannot produce a BUILT candidate set.
- Added `parameter_grids`, `candidate_cap`, and `cap_rejection_count` to `strategy_idea_candidate_set.v1`.
- Added C5 split/leakage policy validation API for time-window ordering, sealed-test non-use, source available-at boundary, and purge / embargo policy records.
- Added C6 report disclosure separating `raw_validation_metrics` from `selection_adjusted_metrics_status` and avoiding proof language.
- Added C10 operator review Markdown surface for exploration counts, rejection reasons, selection policy, known gaps, policy validation, and false boundary flags.
- Added C11 fixture E2E from input evidence through candidate set write, policy validation, operator review, shortlist export, and intake validation.
- Added blocked input-evidence candidate set builder for non-PASS input contract validation.
- Added shortlist export to strict `strategy_idea.v1` draft JSON while keeping candidate set path/hash in the sidecar manifest.
- Added tests for schema validation, Python invariant validation, writer determinism, export, and intake validation integration.
- Added docs for the implemented candidate contract and corrected the checkpoint doc so C3 starts with canonical JSON/Markdown only.

## Main Files Changed

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `schemas/strategy_idea_candidate_export_manifest.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c4_generator_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c5_policy_validation_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c6_metric_disclosure_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c10_operator_review_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c11_fixture_e2e_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_p0a_c2_c3_c8_2026-06-27.md`
- `docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `scripts/check_current_docs.py`

## Verification Run

- `uv run pytest tests/strategy_idea_candidates`
- `uv run ruff check src/sis/strategy_idea_candidates tests/strategy_idea_candidates`
- `uv run ruff format --check src/sis/strategy_idea_candidates tests/strategy_idea_candidates`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `./scripts/check`

## Not Run

None for this slice.

## Remaining Work

- JSONL / CSV search ledger rows after generator output exists.
- C5 full split engine beyond policy validation API.
- C6 selection-adjusted metrics beyond `NOT_IMPLEMENTED`.
- C9 Strategy Lab / backtest bridge.
- C10 richer review packet beyond Markdown surface.
- Public CLI after Python API behavior is stable.

## User Decisions Required

None for this slice.

## Destructive Change

No.

## Destructive Change Reason

Not applicable.

## Dependency Change

No dependency change. `pyproject.toml` and `uv.lock` were not modified.

## Migration

No migration is required.

## Rollback

Revert the new `strategy_idea_candidates` package, candidate schemas, tests, docs, and `scripts/check_current_docs.py` routing additions.

## Next Considerations

Start C5/C6 only after reviewing whether policy-record-only split/leakage fields are sufficient for the next bridge.
