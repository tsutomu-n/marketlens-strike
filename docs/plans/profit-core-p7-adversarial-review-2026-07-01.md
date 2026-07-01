<!--
作成日: 2026-07-01_15:28 JST
更新日: 2026-07-01_15:28 JST
-->

# Profit Core P7 LLM Adversarial Review Implementation Plan

## Checkpoint ID

P7 LLM Adversarial Review

## Purpose

Record adversarial review findings against `profit_core_evidence_packet.v1`
without turning LLM or human text into an approval engine.

## Current State

- P6 writes `profit_core_evidence_packet.json` with source refs, claims,
  machine summary, claim findings, and false boundary fields.
- Existing generic Strategy AI Review artifacts support manual packet/note/finding
  flows, but they are not Profit Core evidence-packet specific.
- The long-horizon checkpoint allows API integration only with opt-in,
  redaction, artifact boundary, and external-send records. This slice avoids API
  integration entirely.

## Constraints

- No LLM API call, network send, dependency change, external venue, paper/live,
  tiny-live, demo/testnet, or actual-cash scope.
- Output status vocabulary is limited to `ADVERSARIAL_FINDING`,
  `NEEDS_MORE_EVIDENCE`, `OVERCLAIM_FLAG`, `HUMAN_REVIEW_REQUIRED`, and
  `NO_ADDITIONAL_BLOCKER_FOUND`.
- `NO_ADDITIONAL_BLOCKER_FOUND` is never approval.
- LLM/manual findings cannot compute PnL, define official metrics, decide
  `actual_cash`, override gates, rewrite strategies, or grant paper/live/tiny-live
  permission.
- Hard blockers come only from machine-checkable P6 blocker findings.

## Target Files

- `schemas/profit_core_adversarial_review.v1.schema.json`
- `src/sis/edge_candidates/adversarial_review.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_adversarial_review.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

Add `profit_core_adversarial_review.v1` as a local/manual review record:

- source ref to one P6 evidence packet with sha256;
- automatic findings derived from P6 `claim_findings`;
- optional manually structured adversarial findings imported from JSON/YAML;
- a top-level status derived only from the allowed status set;
- explicit non-approval and false permission boundary fields;
- `llm_api_used=false`, `external_send_performed=false`, and a local-only
  redaction/API policy note.

The first CLI will be `edge-candidate-adversarial-review-record`.

## Test Policy

- Focused:
  `uv run pytest tests/edge_candidates/test_adversarial_review.py -q`
- Related:
  `uv run pytest tests/edge_candidates/test_evidence_packet.py tests/edge_candidates/test_virtual_execution_gate.py tests/edge_candidates/test_factory.py tests/edge_candidates/test_backtest_kill_gate.py tests/edge_candidates/test_multiplicity_account.py -q`
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

- Review schema validates generated review output.
- CLI consumes a P6 evidence packet and optional manual finding JSON/YAML.
- Output status vocabulary is limited to the P7 allowed set.
- P6 claim findings are converted into adversarial review findings without
  granting permission.
- `NO_ADDITIONAL_BLOCKER_FOUND` appears only as non-approval.
- Manual review findings cannot set hard blockers unless they are
  machine-checkable; this slice keeps manual findings non-hard-blocking.
- Boundary fields preserve no LLM API, external send, paper/live/tiny-live,
  gate override, strategy rewrite, or actual-cash permission.

## Failure Conditions

- Any network/API/LLM call is made.
- Review text decides PnL, official metric, actual cash, paper/live/tiny-live
  permission, or gate override.
- `NO_ADDITIONAL_BLOCKER_FOUND` is represented as approval.
- A manual-only finding becomes a hard blocker.

## Impact Scope

Adds one Profit Core review schema, one local model module, one CLI command,
tests, and docs updates. Existing P1-P6 artifacts remain compatible.

## Rollback Policy

Remove the new schema, module, tests, CLI command, plan doc, and docs/catalog
summary updates. No data migration is required.

## Alternatives

- Reuse generic `strategy_ai_review_*` artifacts directly: rejected for this
  slice because P7 needs Profit Core-specific boundary fields and status
  semantics around P6 claim findings.
- Call an LLM provider directly: rejected for this slice because P7 can satisfy
  the pipeline checkpoint with local/manual import and no external send.

## Destructive Change

No.

## Branch

`ai/profit-core-p7-adversarial-review-20260701-1524`

## Migration

None.

## Grill Verdict

Ready with assumptions: implement a local/manual adversarial review artifact
only; no API integration, no external send, no permission grants, and no
actual-cash decision.
