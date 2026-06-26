<!--
作成日: 2026-06-26_19:14 JST
更新日: 2026-06-26_19:14 JST
-->

# Pass 389: Remediation Signal Core Helpers

## Purpose

Reduce `src/sis/reports/remediation_signal_evaluator.py` by extracting side-effect-free signal preview, basic signal evaluation, and result aggregation helpers into a focused core module.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- HEAD: `30e43d1`
- Preserve: Pass 377 through Pass 388 uncommitted changes.
- Latest broad verification before this pass: Pass 388 `./scripts/check` passed with `2695 passed in 82.26s`.

## Target Files

- `src/sis/reports/remediation_signal_evaluator.py`
- `src/sis/reports/remediation_signal_core.py`
- `tests/test_remediation_signal_core.py`

## Scope

- Move `issue_preview_values()`, `evaluate_signal()`, `action_result()`, and `evaluator_status()` to a new core helper module.
- Keep existing imports from `sis.reports.remediation_signal_evaluator` working through explicit aliases.
- Keep observed stdout/stderr parsing and observation-aware signal evaluation in `remediation_signal_evaluator.py`.

## Out Of Scope

- Signal language changes.
- Status string changes.
- Summary key names, artifact keys, Markdown/report text/order.
- Public CLI names/options.
- Schemas, auth, DB, CI, dependencies, paper/live safety boundaries.

## Red-Green-Refactor

1. RED: Add direct tests importing the new core module.
2. GREEN: Move only side-effect-free core helpers and regexes.
3. REFACTOR: Run focused core tests, existing remediation signal tests, related remediation evaluator tests, lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Verification Plan

- `CI=true timeout 120 uv run pytest -q tests/test_remediation_signal_core.py`
- `CI=true timeout 120 uv run pytest -q tests/test_remediation_signal_core.py tests/test_remediation_signal_evaluator.py tests/test_remediation_signal_observations.py`
- `CI=true timeout 120 uv run pytest -q tests/test_remediation_evaluator_paths.py tests/test_remediation_evaluator_observations.py tests/test_remediation_evaluator_report_observations.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'remediation'`
- `uv run ruff format src/sis/reports/remediation_signal_evaluator.py src/sis/reports/remediation_signal_core.py tests/test_remediation_signal_core.py`
- `uv run ruff check src/sis/reports/remediation_signal_evaluator.py src/sis/reports/remediation_signal_core.py tests/test_remediation_signal_core.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- Best next target: `remediation_signal_evaluator.py` is 465 lines and contains a clear pure core subset already covered by tests.
- Safer boundary: keep observation-aware behavior in place and only move reusable core helpers.
- Main risk: breaking existing imports from `remediation_signal_evaluator`. Mitigation: keep explicit aliases and run existing tests.
- Stop condition: if the split changes any signal status, expected/observed value, or observed source behavior, revert to a smaller boundary.

## Branch Decision

Continue on `refactor/backtest-primitives`. This is the existing dedicated refactor branch, and this pass is a small behavior-preserving split.
