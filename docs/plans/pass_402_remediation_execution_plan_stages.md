<!--
作成日: 2026-06-26_21:20 JST
更新日: 2026-06-26_21:20 JST
-->

# Pass 402 Remediation Execution Plan Stages

## Purpose

Extract remediation execution plan stage ordering, execution status, and feedback priority ranking helpers from `src/sis/reports/remediation_execution_plan.py` into a focused pure helper module.

## Scope

- Add `src/sis/reports/remediation_execution_plan_stages.py`.
- Move only:
  - stage order decision logic.
  - execution plan status derivation from planned entries.
  - feedback priority rank ordering.
- Keep `build_remediation_execution_plan()` output keys, Markdown text/order, sorting semantics, public CLI, and writer behavior unchanged.
- Add direct tests for the new helper module.

## Out Of Scope

- Source summary loading.
- Reason command extraction.
- Verification ordering or confidence calculation.
- Planned entry/action assembly.
- Recommended execution chain generation.
- Markdown report body text/order.
- Public CLI command names or options.
- Summary/model field names, schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_remediation_execution_plan_stages.py`
2. GREEN focused: same command passes.
3. Related remediation execution plan tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_remediation_execution_plan_stages.py tests/test_remediation_execution_plan_verification.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'remediation_execution_plan_cli'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/remediation_execution_plan.py src/sis/reports/remediation_execution_plan_stages.py tests/test_remediation_execution_plan_stages.py`
   - `uv run ruff check src/sis/reports/remediation_execution_plan.py src/sis/reports/remediation_execution_plan_stages.py tests/test_remediation_execution_plan_stages.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: action sorting changes. Mitigation: keep feedback priority rank values identical and run the remediation execution plan CLI smoke test.
- Risk: stage order changes. Mitigation: direct tests cover matched, weak signal confidence, regressed, improving, and default cases.
- Risk: status derivation changes. Mitigation: direct tests cover no actions, regressed, stalled, improving, matched, and planned fallback.

## Rollback

Delete the new helper/test files and restore the moved functions directly in `src/sis/reports/remediation_execution_plan.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
