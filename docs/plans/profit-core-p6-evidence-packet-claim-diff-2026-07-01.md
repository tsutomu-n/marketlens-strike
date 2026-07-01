<!--
作成日: 2026-07-01_15:07 JST
更新日: 2026-07-01_15:07 JST
-->

# Profit Core P6 Evidence Packet And Claim Diff Implementation Plan

## Checkpoint ID

P6 Evidence Packet And Claim Diff

## Purpose

Create a machine-readable evidence packet that separates strategy claims from
the artifacts that can prove them. The packet should detect overclaims before
LLM review, paper, live, tiny-live, external venue work, or actual-cash
measurement.

## Current State

- P4 writes a protocol-bound candidate factory bundle.
- P1-P3 provide protocol / multiplicity / backtest kill-gate artifacts and
  authoring bridge refs.
- P5 writes `virtual_execution_gate.v1` local/mock lifecycle evidence.
- There is no single packet that gathers protocol, candidate set, bridge,
  multiplicity, kill gate, virtual gate, risk-review refs, and human-facing
  claims.

## Constraints

- No LLM API integration.
- Human prose is never the source of truth.
- The packet must not grant paper, live, tiny-live, exchange-write, signing,
  wallet, or actual-cash permission.
- Findings must include severity for unsupported claims, missing comparisons,
  evidence-basis mismatch, and actual-cash overclaim.
- Backtest, virtual exchange, paper, demo/testnet, and actual cash remain
  distinct evidence bases.

## Target Files

- `schemas/profit_core_evidence_packet.v1.schema.json`
- `src/sis/edge_candidates/evidence_packet.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_evidence_packet.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

Add `profit_core_evidence_packet.v1` with:

- source refs for protocol, candidate set, bridge manifest, multiplicity account,
  backtest kill gate, virtual gate, and optional risk review source refs;
- machine summary fields derived from artifacts;
- claim inputs as structured records, not free-form authority;
- claim findings with severity and codes for `UNSUPPORTED_CLAIM`,
  `MISSING_COMPARISON`, `EVIDENCE_BASIS_MISMATCH`, and
  `ACTUAL_CASH_OVERCLAIM`;
- explicit false permission boundary fields.

The first CLI will be `edge-candidate-evidence-packet-build`.

## Test Policy

- Focused:
  `uv run pytest tests/edge_candidates/test_evidence_packet.py -q`
- Related:
  `uv run pytest tests/edge_candidates/test_virtual_execution_gate.py tests/edge_candidates/test_factory.py tests/edge_candidates/test_backtest_kill_gate.py tests/edge_candidates/test_multiplicity_account.py -q`
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

- Packet schema validates generated packet output.
- CLI consumes P1-P5 artifact paths and optional claim JSON.
- Packet includes artifact refs with sha256 for protocol, candidate set, bridge,
  multiplicity, backtest kill gate, virtual gate, and risk review source refs.
- Claim diff flags unsupported claim, missing comparison, basis mismatch, and
  actual-cash overclaim with severity.
- No paper/live/tiny-live/exchange-write/actual-cash permission is granted.

## Failure Conditions

- LLM API or external venue integration appears.
- Human claim text overrides machine summary.
- Actual cash, paper, live, or tiny-live permission is inferred from backtest or
  virtual evidence.
- Findings do not distinguish evidence basis.

## Impact Scope

Adds one schema, one local model module, one CLI command, tests, and docs updates.
Existing P1-P5 artifacts remain compatible.

## Rollback Policy

Remove the new schema, module, tests, CLI command, plan doc, and docs/catalog
summary updates. No data migration is required.

## Alternatives

- Put P6 into the existing strategy idea review packet: rejected because P6 is
  Profit Core evidence/claim diff, not human review.
- Use LLM review directly: rejected because P6 precedes P7 and should be
  machine-checkable.

## Destructive Change

No.

## Branch

`ai/profit-core-p6-evidence-packet-20260701-1507`

## Migration

None.

## Grill Verdict

Ready with assumptions: build a machine-readable packet and structured claim
diff only; leave LLM review, paper/live/tiny-live, external venue, and actual
cash out of scope.
