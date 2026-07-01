<!--
作成日: 2026-07-01_15:50 JST
更新日: 2026-07-01_15:50 JST
-->

# Profit Core P8 Risk-Taker Sprint Isolation Implementation Plan

## Checkpoint ID

P8 Risk-Taker Sprint Isolation

## Purpose

Prevent `risk_taker_sprint` outputs from contaminating the default
`verification_throughput` performance path, and attach explicit promotion debt
before any sprint candidate can be reconsidered for actual-cash readiness.

## Current State

- `candidate_protocol_manifest.v1` already supports `risk_taker_sprint` with
  `mode_isolation=true`.
- P4 intentionally rejects `risk_taker_sprint` factory runs.
- `trial_multiplicity_account.v1` supports `risk_taker_sprint`.
- There is no Profit Core artifact that records separate sprint ledger,
  separate holdout, separate multiplicity account, default aggregate exclusion,
  or promotion debt.

## Constraints

- Do not implement broad sprint candidate generation, GA engine, ML model, or
  random search engine in this slice.
- Do not weaken P4 `risk_taker_sprint` rejection.
- Do not allow sprint output into default aggregate.
- Do not allow sprint candidates to move directly to paper, live, tiny-live, or
  actual cash.
- If `light_ga` or broad sprint generators are present in protocol metadata,
  constrain them to ranking / no-trade filter semantics only.

## Target Files

- `schemas/profit_core_risk_taker_sprint_isolation.v1.schema.json`
- `src/sis/edge_candidates/risk_taker_sprint_isolation.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_risk_taker_sprint_isolation.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

Add `profit_core_risk_taker_sprint_isolation.v1` as a local isolation record:

- input refs for sprint protocol, candidate set, search ledger, and sprint
  multiplicity account;
- validation that protocol and multiplicity account are both
  `risk_taker_sprint`;
- validation that candidate counts match between candidate set, ledger, and
  multiplicity account;
- explicit `output_label=SPECULATIVE_SPRINT`;
- explicit `default_aggregate_inclusion_allowed=false` and
  `default_aggregate_candidate_count=0`;
- explicit promotion debt list, including re-registration under
  `verification_throughput`, no holdout reuse, default multiplicity, default
  kill gate, virtual gate, and risk-taker review without live permission;
- false permission boundary fields for paper/live/tiny-live/actual cash.

The first CLI will be
`edge-candidate-risk-taker-sprint-isolation-record`.

## Test Policy

- Focused:
  `uv run pytest tests/edge_candidates/test_risk_taker_sprint_isolation.py -q`
- Related:
  `uv run pytest tests/edge_candidates/test_protocol_manifest.py tests/edge_candidates/test_multiplicity_account.py tests/edge_candidates/test_factory.py tests/edge_candidates/test_adversarial_review.py tests/edge_candidates/test_evidence_packet.py -q`
- CLI catalog:
  `uv run python scripts/check_cli_catalog.py`
- Current docs:
  `uv run python scripts/check_current_docs.py`
- Ruff:
  `uv run ruff check src/sis/edge_candidates src/sis/commands/edge_candidates.py tests/edge_candidates`
  and matching `ruff format --check`
- Whitespace:
  `git diff --check`
- Standard check if feasible:
  `./scripts/check`

## Completion Conditions

- Isolation schema validates generated output.
- CLI consumes sprint protocol, sprint candidate set, sprint search ledger, and
  sprint multiplicity account.
- `risk_taker_sprint` artifacts are marked as excluded from default aggregate.
- Promotion debt is present and blocks direct actual-cash / tiny-live movement.
- Separate ledger / holdout / multiplicity assertions are recorded.
- P4 factory still rejects `risk_taker_sprint`.
- Boundary fields preserve no paper/live/tiny-live/actual-cash permission.

## Failure Conditions

- P8 enables broad sprint generation before isolation.
- P8 permits a sprint winner to go directly to tiny-live or actual cash.
- P8 mixes sprint positive results into default performance.
- P8 weakens existing P4 `risk_taker_sprint` rejection.

## Impact Scope

Adds one schema, one local model module, one CLI command, tests, and docs
updates. Existing P1-P7 artifacts remain compatible.

## Rollback Policy

Remove the new schema, module, tests, CLI command, plan doc, and docs/catalog
summary updates. No data migration is required.

## Alternatives

- Enable `risk_taker_sprint` in P4 factory now: rejected because P8's purpose is
  isolation first, not search expansion.
- Store only a doc note: rejected because mode contamination and promotion debt
  need a machine-readable artifact.

## Destructive Change

No.

## Branch

`ai/profit-core-p8-risk-sprint-isolation-20260701-1538`

## Migration

None.

## Grill Verdict

Ready with assumptions: implement isolation and promotion-debt recording only;
do not add candidate generation, GA/ML execution, external venues, paper/live,
tiny-live, or actual-cash permission.
