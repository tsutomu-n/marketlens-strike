<!--
作成日: 2026-06-29_19:27 JST
更新日: 2026-06-29_19:27 JST
-->

# Pyrefly Prompt Hash Type Fix Plan

## Checkpoint ID

CP3 pyrefly prompt-hash type fix

## Purpose

Make full `./scripts/check` green after CP2 by fixing the remaining pyrefly blocker in `src/sis/strategy_idea_candidates/ai.py`.

## Current State

- Branch: `ai/risk-taker-review-artifact-20260628-1721`.
- CP2 format cleanup is applied.
- Full `./scripts/check` passes Ruff, current-docs, and CLI catalog, then fails at `uv run pyrefly check`.
- Error: `dict[str, str]` is passed to `prompt_hash_by_candidate_id: dict[str, str | None] | None` at `src/sis/strategy_idea_candidates/ai.py:359`.

## Constraints

- Keep behavior unchanged.
- Do not change ledger schema or output fields.
- Do not touch `codex_diag.sh`.
- Do not broaden this checkpoint beyond the type error unless full check reveals a directly related follow-on type failure.

## Target Files

- `src/sis/strategy_idea_candidates/ai.py`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `docs/final-summary.md`

## Implementation Approach

Annotate `prompt_hash_by_candidate_id` as `dict[str, str | None]` when constructing the mapping. This matches the ledger API and avoids `dict` invariance without changing runtime values.

## Implementation Steps

1. Add CP3 work records and this plan.
2. Add the local type annotation in `ai.py`.
3. Run focused pyrefly, ty, Ruff, and related pytest checks.
4. Run full `./scripts/check`.
5. Update work records and final summary.

## Test Plan

- `uv run pyrefly check src/sis/strategy_idea_candidates/ai.py`
- `uv run ty check src/sis/strategy_idea_candidates/ai.py`
- `uv run ruff check src/sis/strategy_idea_candidates/ai.py`
- `uv run ruff format --check src/sis/strategy_idea_candidates/ai.py`
- `uv run pytest tests/strategy_idea_candidates/test_ai_packet_import.py -q`
- `./scripts/check`
- `git diff --check`

## Completion Conditions

- Full `./scripts/check` exits 0.
- Targeted checks pass.
- `git diff --check` exits 0.
- The fix is limited to the type repair plus work documentation.

## Failure Conditions

- Full check exposes an unrelated failure outside this type boundary.
- Tests show changed ledger or AI import behavior.

## Impact Scope

Low. This is a type-checker compatibility fix for a local mapping.

## Rollback Plan

Remove the annotation change and CP3 work-summary additions.

## Alternatives

- Change the ledger API to accept `Mapping[str, str | None]`: broader API change, not needed for this checkpoint.
- Cast the value at the call site: works, but an explicit variable annotation is simpler and avoids importing `cast`.

## Unresolved Items

None.

## Destructive Change

No.

## Branch

`ai/risk-taker-review-artifact-20260628-1721`

## Migration

No migration is required.

## Critique

The chosen fix targets the actual pyrefly complaint without broadening the API or changing behavior. The main risk is that full pyrefly may reveal a second unrelated type issue after this one; if that occurs, it should be treated as a new smallest checkpoint unless directly caused by this change.
