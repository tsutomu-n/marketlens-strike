<!--
作成日: 2026-06-26_17:22 JST
更新日: 2026-06-26_17:22 JST
-->

# Pass 377 Lifecycle Navigation Plan

## Checkpoint ID

Pass 377

## Purpose

`src/sis/reports/lifecycle.py` から、Strategy Lifecycle Report の quick navigation / related reports / nested report path 取得だけを分離し、Markdown rendering と summary normalization を読みやすくする。

## Current State

- Current branch: `refactor/backtest-primitives`
- Current baseline: `30e43d1`
- Tracked worktree at planning time: clean
- `lifecycle.py` is 389 lines and currently contains:
  - `_quick_navigation()`
  - `_nested_report_path()`
  - `_related_reports()`
  - decision summary rendering
  - weekly review embedding
  - paper last-run summary normalization
  - Markdown rendering and file write

## Constraints

- Do not change public CLI command names or options.
- Do not change Markdown heading order, bullet text, or report path strings.
- Do not change summary key names or artifact key names.
- Do not change schemas, auth, DB, CI, dependencies, or external-service behavior.
- Do not claim paper/live/account/wallet/signing/exchange-write readiness.
- Do not run `git push` manually.

## Target Files

- `src/sis/reports/lifecycle.py`
- `src/sis/reports/lifecycle_navigation.py`
- `tests/test_lifecycle_navigation.py`
- `docs/plans/pass_377_lifecycle_navigation.md`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Implementation Approach

Create `src/sis/reports/lifecycle_navigation.py` with:

- `quick_navigation(out_path: Path | None, payload: dict[str, object]) -> dict[str, str]`
- `nested_report_path(payload: dict[str, object], section: str, flat_key: str) -> str | None`
- `related_reports(out_path: Path | None, payload: dict[str, object]) -> dict[str, str]`

Then update `lifecycle.py` to import the module and keep the existing private helper names as aliases:

- `_quick_navigation`
- `_nested_report_path`
- `_related_reports`

## Implementation Steps

1. RED: add direct tests importing `sis.reports.lifecycle_navigation`.
2. Confirm the tests fail because the module does not exist.
3. GREEN: add the helper module and alias the old private helper names.
4. Run focused and related lifecycle report tests.
5. Run lint/type/CLI/diff checks.
6. Run `./scripts/check` after confirming it does not require forbidden `git push`.
7. Record the result in `.codex`, `.ai-work`, and `HANDOFF.md`.

## Test Plan

- `CI=true timeout 120 uv run pytest -q tests/test_lifecycle_navigation.py`
- `CI=true timeout 120 uv run pytest -q tests/test_lifecycle_navigation.py tests/test_recovery_lifecycle.py -k 'lifecycle_report'`
- `uv run ruff check src/sis/reports/lifecycle.py src/sis/reports/lifecycle_navigation.py tests/test_lifecycle_navigation.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Done Condition

- The new lifecycle navigation tests pass.
- Existing lifecycle report tests still pass.
- Full repository check passes.
- `lifecycle.py` delegates navigation only and keeps old private helper aliases.
- No public CLI, schema, report text/order, or safety-boundary changes are introduced.

## Failure Conditions

- Any Strategy Lifecycle Report Markdown output changes unexpectedly.
- Related report path order changes.
- The helper import creates a circular import.
- Full check fails and cannot be resolved without expanding scope.

## Impact Scope

Internal report helper structure only. Runtime behavior should remain unchanged.

## Rollback Plan

Revert the new helper module and restore the original helper functions in `lifecycle.py`. Remove the new direct tests and checkpoint notes.

## Alternatives

- Extract paper last-run execution sections. Rejected because it is a broad Markdown text/order surface.
- Extract summary normalization blocks. Rejected because it touches many report fields and requires broader fixtures.
- Leave the file as-is. Rejected because the navigation boundary is already clear and consistent with nearby report modules.

## Unresolved Items

None.

## Destructive Changes

None.

## Branch Name

`refactor/backtest-primitives`

## Migration Steps

None.

## Critique

- This directly supports the refactor goal by removing path/navigation responsibility from a mixed-purpose report renderer.
- It is small and behavior-preserving, so the existing refactor branch remains appropriate.
- The largest risk is accidentally changing report link order. Direct tests must assert exact dictionary order.
- The plan intentionally avoids Markdown body extraction because that would be higher-risk and less directly covered.
- The plan is implementation-ready because target files, helper signatures, test commands, stop conditions, and rollback are explicit.
