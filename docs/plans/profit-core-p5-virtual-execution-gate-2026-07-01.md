<!--
作成日: 2026-07-01_14:54 JST
更新日: 2026-07-01_14:54 JST
-->

# Profit Core P5 Virtual Execution Gate V1 Implementation Plan

## Checkpoint ID

P5 Virtual Execution Gate V1 Local/Mock

## Purpose

Add a local/mock virtual execution gate after the P4 candidate factory and P1-P3
candidate / multiplicity / backtest kill-gate artifacts. The gate verifies order
lifecycle and reconciliation mechanics before any paper, live, tiny-live,
external venue, or actual-cash work. It does not evaluate PnL and must not be
used as profit evidence.

## Current State

- P4 writes a protocol-bound candidate bundle with candidate set, search ledger,
  rejection ledger, multiplicity account, and factory summary.
- P1-P3 can produce candidate-scoped `backtest_kill_gate.v1`; only
  `SHORTLIST_FOR_VIRTUAL` means a candidate can enter the next local/mock gate.
- No `virtual_execution_gate.v1` schema, model, CLI, or tests exist.

## Constraints

- No external venue adapters, Bitget demo, Hyperliquid, GRVT, network reads,
  credentials, dependency changes, paper orders, live orders, tiny-live, signing,
  wallet, exchange write, or actual-cash measurement.
- `SHORTLIST_FOR_VIRTUAL` is not permission. It only allows local/mock lifecycle
  inspection.
- `virtual_execution_gate.v1` must explicitly set `actual_cash=false`,
  `cash_metric_basis=virtual_exchange`, `production_exchange_write_used=false`,
  `live_order_submitted=false`, and `permits_live_order=false`.
- Unknown lifecycle state and reconciliation mismatch are blockers.
- Virtual PnL must not be emitted or described as profit evidence.

## Target Files

- `schemas/virtual_execution_gate.v1.schema.json`
- `src/sis/edge_candidates/virtual_execution_gate.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_virtual_execution_gate.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

Add a local state-machine artifact with two levels:

1. A pure builder that validates an eligible candidate plus lifecycle events.
2. A file-oriented writer / CLI that consumes candidate set, P4 factory summary,
   multiplicity account, and a candidate-scoped backtest kill gate.

The default CLI lifecycle is a deterministic local/mock sequence:
`SUBMIT_ACK` -> `PARTIAL_FILL` -> `CANCEL_ACK` -> `RECONCILED_FLAT`.

The gate returns `LOCAL_MOCK_VERIFIED` only when:

- the candidate exists and is shortlisted;
- the kill gate state is `SHORTLIST_FOR_VIRTUAL`;
- multiplicity accounting does not use sealed test or success-only reporting;
- the P4 factory summary references the same candidate set / multiplicity
  artifacts by sha256 when those refs are present;
- submit ack, partial fill, cancel ack, duplicate prevention, and flat
  reconciliation all pass.

All other cases produce a blocked gate artifact with explicit blocker codes.

## Test Policy

- Focused:
  `uv run pytest tests/edge_candidates/test_virtual_execution_gate.py -q`
- Related:
  `uv run pytest tests/edge_candidates/test_factory.py tests/edge_candidates/test_backtest_kill_gate.py tests/edge_candidates/test_multiplicity_account.py -q`
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

- `virtual_execution_gate.v1` validates output shape.
- An eligible shortlisted candidate with `SHORTLIST_FOR_VIRTUAL` and valid local
  lifecycle events can produce a virtual gate artifact.
- Killed, inconclusive, rejected, unexecutable, duplicate-submit, unknown-state,
  and reconcile-mismatch cases cannot advance to `LOCAL_MOCK_VERIFIED`.
- CLI writes the gate artifact without network or exchange side effects.
- Docs / CLI catalog / final summary are updated if a public command is added.
- Focused and relevant regression checks pass.

## Failure Conditions

- The gate reads from or writes to an external venue.
- The gate reports virtual PnL as profit evidence.
- The gate grants paper, live, tiny-live, exchange-write, signing, wallet, or
  actual-cash permission.
- Non-`SHORTLIST_FOR_VIRTUAL` backtest gates advance.
- Unknown lifecycle state or reconcile mismatch is ignored.

## Impact Scope

Adds one schema, one local model module, one public CLI command, and focused
tests. Existing P4 factory, P1-P3 backtest kill gate, and candidate schemas
should remain compatible.

## Rollback Policy

Remove the new schema, module, tests, CLI command, plan doc, and docs/catalog
summary updates. No data migration is required because P5 writes a new sidecar
artifact.

## Alternatives

- Start with an external demo/testnet venue: rejected because P5 explicitly
  starts local/mock and external venue verification is a later checkpoint.
- Fold virtual gate fields into backtest kill gate: rejected because backtest
  evidence and order lifecycle evidence have different evidence bases.

## Unresolved Items

- P6 evidence packet may later standardize how P5 artifact refs are bundled with
  claims.
- External venue adapters remain future work and require current official docs,
  credentials, and explicit approval.

## Destructive Change

No.

## Branch

`ai/profit-core-p5-virtual-gate-20260701-1454`

## Migration

None.

## Grill Verdict

Ready with assumptions: implement local/mock lifecycle and reconciliation only,
with artifact lineage to P4/P1-P3 and explicit false permission fields.
