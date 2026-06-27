<!--
作成日: 2026-06-27_11:16 JST
更新日: 2026-06-27_11:16 JST
-->

# Strategy Idea Candidates P0A/C2/C3/C8 Implementation Plan

## Checkpoint ID

CP-01 to CP-06.

## Purpose

Add the first safe slice of the candidate generation pipeline: a strict pre-intake candidate-set contract, Python validation, deterministic JSON/Markdown writing, input-evidence blocking, and shortlist export into existing `strategy_idea.v1` drafts with sidecar provenance.

## Current State

The repo has strategy input contracts and intake validation, but no `strategy_idea_candidate_set.v1` schema, no `src/sis/strategy_idea_candidates/` package, no candidate-set writer, and no candidate-set export sidecar. `strategy_idea.v1` is strict and must not be expanded with exploration provenance.

## Constraints

- No dependency additions.
- No public CLI in this slice.
- No real market data, credentials, external API, paper execution, or live readiness.
- Output remains `UNVERIFIED_CANDIDATE`.
- `strategy_idea.v1` remains unchanged.
- Candidate-set provenance goes to a sidecar manifest.
- Initial C3 writer emits canonical JSON and Markdown only.

## Target Files

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `schemas/strategy_idea_candidate_export_manifest.v1.schema.json`
- `src/sis/strategy_idea_candidates/__init__.py`
- `src/sis/strategy_idea_candidates/models.py`
- `src/sis/strategy_idea_candidates/rendering.py`
- `src/sis/strategy_idea_candidates/service.py`
- `src/sis/strategy_idea_candidates/export.py`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/README.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `scripts/check_current_docs.py`
- `docs/final-summary.md`

## Implementation Approach

Create new candidate-specific models instead of reusing `TradeCandidate`, `PaperCandidatePack`, or `strategy_idea.v1`. Use Pydantic for cross-field validation and JSON Schema for structural validation only. Reuse existing artifact I/O helpers so JSON is stable and Markdown is deterministic.

## Implementation Steps

1. Add failing tests for valid schema payloads, invalid boundary flags, invalid hashes/status, count mismatches, duplicate selected/rejected IDs, selected-only reporting, non-PASS input evidence blocking, stable writer output, and shortlist export.
2. Add Pydantic models and JSON Schema for candidate sets and export manifests.
3. Add validation rules for counts, selected/rejected ID inventory, source evidence summaries, PASS-only build status, blocked input evidence status, sealed-test selection flags, and false boundary flags.
4. Add deterministic JSON/Markdown writer using `write_json_artifact` and `write_text_artifact`.
5. Add blocked input-evidence builder from `StrategyInputContract` plus `StrategyInputContractValidation`.
6. Add shortlist export that writes strict `strategy_idea.v1` drafts and a sidecar manifest containing candidate-set path/hash.
7. Add docs and current-doc routing.
8. Run targeted pytest and repository checks.

## Test Approach

- `uv run pytest tests/strategy_idea_candidates`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

Additional focused tests may be run around existing strategy input intake if export touches that flow.

## Completion Conditions

- Candidate-set schema and Pydantic model accept a complete valid artifact.
- Invalid status/hash/boundary payloads fail.
- Python validation catches cross-field invariant failures.
- Non-PASS input validation creates a `BLOCKED_INPUT_EVIDENCE` candidate set without candidates.
- Writer output is deterministic.
- Shortlist export produces strict `strategy_idea.v1` JSON and sidecar manifest; candidate-set provenance is absent from the strategy idea draft.
- Current-doc checks pass.

## Failure Conditions

- `strategy_idea.v1` is expanded for candidate provenance.
- Candidate output can be mistaken for alpha proof, paper readiness, or live readiness.
- Selected-only inventory passes as a successful candidate set.
- Non-PASS input validation can produce a built candidate set.
- Any dependency is added for P0/P1.

## Impact

New artifact contract and internal Python API only. No public CLI, no dependency, no external side effects.

## Rollback

Revert the new candidate-set schemas, package, tests, and docs/checker additions. No data migration is required.

## Alternatives

- Reuse `strategy_idea.v1`: rejected because it drops exploration and rejection evidence.
- Reuse optimizer trial ledger directly: rejected for P0 because pre-intake candidate artifacts need source evidence and rejection inventory fields not present there.
- Add public CLI immediately: deferred until writer and export behavior are stable.

## Unresolved Items

No user decision is required for this slice. Real generator families and JSONL/CSV row ledgers remain later work.

## Destructive Change

No.

## Branch

`ai/strategy-idea-candidates-20260627-1116`

## Migration

No migration is required.
