<!--
作成日: 2026-07-01_06:25 JST
更新日: 2026-07-01_06:25 JST
-->

# Profit Core P1-P3 Pipeline Attachment Plan

## Checkpoint ID

P1-P3 from `docs/plans/profit-core-long-horizon-goal-checkpoints-2026-06-30.md`.

## Purpose

Connect the implemented Profit Core contract parts to the existing `strategy_idea_candidates` and C9 authoring bridge path without widening execution permission.

Scope:

- P1: generate a `trial_multiplicity_account.v1` from an existing candidate set plus search ledger, and preserve protocol / multiplicity refs for downstream bridge artifacts.
- P2: split C9 `BRIDGED` into `BRIDGED_TECHNICAL_ONLY` and Profit Core blocker vocabulary.
- P3: write a thin `backtest_kill_gate.v1` artifact from candidate-scoped backtest pack outputs and attach the decision to the bridge manifest.

## Current State

- `candidate_protocol_manifest.v1`, `trial_multiplicity_account.v1`, and thin `backtest_kill_gate.v1` models / schemas exist.
- Existing `strategy_idea_candidate_set.v1` has `additionalProperties=false`; adding mandatory fields would break existing fixtures and current artifacts.
- Existing authoring bridge emits `BRIDGED`, writes candidate-scoped C9 artifacts, and runs `strategy_backtest_pack`, but does not trace protocol / multiplicity or write a kill-gate artifact.
- Existing backtest pack output includes baseline, stress, benchmark-relative, and validation artifacts that can feed a conservative thin kill gate.

## Constraints

- Do not add external network, credentials, venue adapters, LLM API, dependency changes, paper/live/tiny-live, or actual-cash execution.
- Do not treat `BRIDGED_TECHNICAL_ONLY`, `AVAILABLE`, `SHORTLIST_FOR_VIRTUAL`, or backtest pack validation as profit proof.
- Keep `actual_cash=false` and all live / paper / exchange write permissions false.
- Preserve existing candidate set schema compatibility by using sidecar / bridge refs first.
- Stop if multiplicity cannot be checked against the search ledger.

## Target Files

- `src/sis/strategy_idea_candidates/profit_core.py`
- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `schemas/strategy_idea_candidate_authoring_bridge.v1.schema.json`
- `tests/strategy_idea_candidates/test_profit_core_attachment.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

1. Add Red tests for multiplicity account generation from candidate set + ledger.
2. Implement a small `profit_core.py` helper that validates ledger consistency, builds `TrialMultiplicityAccount`, writes `trial_multiplicity_account.json`, and provides artifact refs.
3. Add an optional CLI command to build that multiplicity sidecar for existing candidate runs.
4. Add Red tests for authoring bridge protocol / multiplicity refs, `BRIDGED_TECHNICAL_ONLY`, and backtest kill gate attachment.
5. Update authoring bridge status vocabulary and schema.
6. When bridge inputs include protocol / multiplicity refs, carry their path / sha256 into the bridge manifest and candidate outputs.
7. After a candidate-scoped backtest pack succeeds, build `backtest_kill_gate.json` from local pack artifacts and attach the path / state.
8. Keep legacy operation usable, but make manifest summary show missing Profit Core refs when they are not supplied.

## Test Plan

Focused:

```bash
uv run pytest tests/strategy_idea_candidates/test_profit_core_attachment.py -q
uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q
uv run pytest tests/edge_candidates/test_multiplicity_account.py tests/edge_candidates/test_backtest_kill_gate.py -q
```

Regression:

```bash
uv run pytest tests/strategy_idea_candidates/test_candidate_set_validation.py tests/strategy_idea_candidates/test_candidate_generator.py tests/strategy_idea_candidates/test_candidate_cli.py -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
uv run ruff check src/sis/strategy_idea_candidates src/sis/commands/strategy_idea_candidates.py tests/strategy_idea_candidates
uv run ruff format --check src/sis/strategy_idea_candidates src/sis/commands/strategy_idea_candidates.py tests/strategy_idea_candidates
git diff --check
```

## Completion Conditions

- Search ledger rows are checked against candidate set ids and counts before a multiplicity account is written.
- `raw_p_value_count=0` produces BH/FDR `NOT_ESTIMABLE`, not `AVAILABLE`.
- Authoring bridge manifest can trace candidate set hash, ledger hash, protocol hash, and multiplicity account hash.
- Bridged technical candidates use `BRIDGED_TECHNICAL_ONLY`, not `BRIDGED`.
- Candidate-scoped backtest output includes `backtest_kill_gate.json`.
- Kill gate output never grants paper, live, or actual-cash permission.

## Failure Conditions

- The implementation requires changing existing candidate set payloads in a breaking way.
- The bridge can emit a technical success without saying whether Profit Core refs are missing.
- The kill gate cannot identify whether a `NO_TRADE` / cash baseline comparison exists.
- Any change introduces external service calls, credentials, dependency changes, or execution permission.

## Impact Range

Expected impact is limited to `strategy_idea_candidates` bridge / CLI, the authoring bridge manifest schema, focused tests, and docs routing / summary.

## Rollback

Remove the new `profit_core.py` helper and tests, revert authoring bridge / CLI / schema changes, and remove this plan plus final-summary addendum. No runtime data migration is required.

## Alternatives Considered

- Add mandatory protocol / multiplicity fields to `strategy_idea_candidate_set.v1`: rejected for this slice because it breaks current schema fixtures and artifacts.
- Make authoring bridge require protocol / multiplicity immediately: rejected for this slice because old candidate sets need compatibility diagnostics before a hard migration.
- Start with external virtual venue adapters: rejected because P5 is explicitly later and requires current external docs / credentials / opt-in.

## Unresolved Items

- Whether `strategy_idea_candidate_set.v2` should later make protocol refs mandatory.
- Whether `BRIDGED_TECHNICAL_ONLY` should become the only accepted bridge success status after a migration window.
- Whether PBO / DSR / White Reality Check inputs should be generated from backtest pack artifacts in a later checkpoint.

## Destructive Change

No.

## Branch

`ai/profit-core-p1-p3-20260701-0622`

## Migration

No data migration in this checkpoint. Existing candidate sets remain valid; Profit Core attachment starts as sidecar and bridge manifest refs.

## Grill Verdict

Ready with assumptions:

- Sidecar / bridge refs are acceptable for P1 compatibility.
- P3 may use the existing cash/no-trade baseline comparison as the first local `NO_TRADE` comparison signal.
- Selection adjustment statuses outside `AVAILABLE` are conservatively treated as `NOT_ESTIMABLE` by the kill gate.
