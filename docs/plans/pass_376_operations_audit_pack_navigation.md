<!--
作成日: 2026-06-26_17:14 JST
更新日: 2026-06-26_17:14 JST
-->

# Pass 376 Operations Audit Pack Navigation Plan

## Checkpoint ID

Pass 376

## Purpose

`src/sis/reports/operations_audit_pack.py` から、レポートパス計算と navigation map 組み立てだけを分離し、本文レンダリングと manifest 生成を読みやすくする。

## Current State

- Current branch: `refactor/backtest-primitives`
- Current baseline: `03bb109`
- Tracked worktree at planning time: clean
- `operations_audit_pack.py` is 384 lines and currently contains:
  - `_report_path_for_summary()`
  - `_quick_navigation()`
  - `_related_reports()`
  - manifest field assembly
  - Markdown rendering
  - file writes

## Constraints

- Do not change public CLI command names or options.
- Do not change manifest key names.
- Do not change Markdown heading order, bullet text, or table text.
- Do not change schemas, auth, DB, CI, dependencies, or external-service behavior.
- Do not claim paper/live/account/wallet/signing/exchange-write readiness.
- Do not run `git push`.

## Target Files

- `src/sis/reports/operations_audit_pack.py`
- `src/sis/reports/operations_audit_pack_navigation.py`
- `tests/test_operations_audit_pack_navigation.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Implementation Approach

Create `src/sis/reports/operations_audit_pack_navigation.py` with:

- `report_path_for_summary(path: Path | None, report_name: str) -> str | None`
- `quick_navigation(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]`
- `related_reports(phase_gate_summary_path: Path | None, out_path: Path | None) -> dict[str, str]`

Then update `operations_audit_pack.py` to import the module and keep the existing private helper names as aliases:

- `_report_path_for_summary`
- `_quick_navigation`
- `_related_reports`

## Implementation Steps

1. RED: add direct tests importing `sis.reports.operations_audit_pack_navigation`.
2. Confirm the tests fail because the module does not exist.
3. GREEN: add the helper module and alias the old private helper names.
4. Run focused and related tests.
5. Run lint/type/CLI/diff checks.
6. Run `./scripts/check` if no AGENTS.md constraint is violated.
7. Record the result in `.codex`, `.ai-work`, and `HANDOFF.md`.

## Test Plan

- `CI=true timeout 120 uv run pytest -q tests/test_operations_audit_pack_navigation.py`
- `CI=true timeout 120 uv run pytest -q tests/test_operations_audit_pack_navigation.py tests/test_monitoring_comparison.py -k 'operations_audit_pack'`
- `uv run ruff check src/sis/reports/operations_audit_pack.py src/sis/reports/operations_audit_pack_navigation.py tests/test_operations_audit_pack_navigation.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Done Condition

- The new navigation helper tests pass.
- Existing operations audit pack behavior still passes related tests.
- Full repository check passes.
- The main module delegates navigation only and keeps old private helper aliases.
- No public CLI, schema, report text/order, or safety-boundary changes are introduced.

## Failure Conditions

- Any public CLI or report output text changes unexpectedly.
- Manifest key order or key names change.
- The helper import creates a circular import.
- Full check fails and cannot be resolved without expanding scope.

## Impact Scope

Internal report helper structure only. Runtime behavior should remain unchanged.

## Rollback Plan

Revert the new helper module and restore the original helper functions in `operations_audit_pack.py`. Remove the new direct tests and checkpoint notes.

## Alternatives

- Extract Markdown rendering sections. Rejected because it is a larger user-facing text/order surface.
- Extract manifest field assembly. Rejected because it touches many summary keys and would require broader fixtures.
- Leave the file as-is. Rejected because the navigation helper boundary is already clear and consistent with nearby report modules.

## Unresolved Items

None.

## Destructive Changes

None.

## Branch Name

`refactor/backtest-primitives`

## Migration Steps

None.

## Critique

- This directly supports the refactor goal by removing a repeated path/navigation concern from a mixed-purpose report module.
- It is not a broad architecture change and does not require a new branch because the existing branch is already the dedicated refactor branch.
- The main risk is accidentally changing navigation map order. Direct tests must assert exact dictionary order.
- The plan avoids Markdown body extraction because that is more likely to create untested text-order regressions.
- The plan is implementation-ready for another coder because target files, helper signatures, test commands, and stop conditions are explicit.
