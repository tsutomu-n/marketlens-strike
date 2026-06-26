<!--
作成日: 2026-06-26_19:41 JST
更新日: 2026-06-26_19:41 JST
-->

# Pass 392 Remediation Execution Plan Verification Helpers

## Purpose

Extract side-effect-free remediation execution plan verification helpers from
`src/sis/reports/remediation_execution_plan.py` into a focused helper module.

## Scope

- Add `src/sis/reports/remediation_execution_plan_verification.py`.
- Move observed-source flattening, verification confidence, and verification ordering helpers.
- Keep existing private helper names available from `remediation_execution_plan.py` by explicit alias.
- Add direct tests for nested observed source flattening, worst-confidence selection, and confidence-based verification ordering.

## Out Of Scope

- Public CLI command names or options.
- Summary JSON key names.
- Markdown report text or ordering.
- Planner entry/action assembly shape.
- File loading, artifact writing, schemas, CI, dependencies, auth, DB, or paper/live safety boundary changes.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_remediation_execution_plan_verification.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_remediation_execution_plan_verification.py tests/test_remediation_execution_plan_navigation.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'remediation_execution_plan'`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'remediation_execution_plan'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/remediation_execution_plan.py src/sis/reports/remediation_execution_plan_verification.py tests/test_remediation_execution_plan_verification.py`
   - `uv run ruff check src/sis/reports/remediation_execution_plan.py src/sis/reports/remediation_execution_plan_verification.py tests/test_remediation_execution_plan_verification.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: stage confidence ordering could change. Mitigation: direct tests lock ordering by low, medium, high confidence.
- Risk: nested observed source payloads could flatten differently. Mitigation: direct tests include nested dict and list payloads.
- Risk: existing imports from `remediation_execution_plan.py` could break. Mitigation: keep explicit private aliases in the original module.

## Rollback

Delete the new helper/test files and restore the moved helper definitions in
`src/sis/reports/remediation_execution_plan.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving
helper extraction and does not require a new branch under AGENTS.md.
