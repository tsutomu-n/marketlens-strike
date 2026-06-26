<!--
作成日: 2026-06-26_19:31 JST
更新日: 2026-06-26_19:31 JST
-->

# Pass 391: Remediation Evaluator Observation Core Helpers

## Purpose

Reduce `src/sis/reports/remediation_evaluator_observations.py` by extracting side-effect-free aliasing and observation-source merge helpers into a focused core module.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- HEAD: `30e43d1`
- Preserve: Pass 377 through Pass 390 uncommitted changes.
- Latest broad verification before this pass: Pass 390 `./scripts/check` passed with `2700 passed in 81.99s`.

## Target Files

- `src/sis/reports/remediation_evaluator_observations.py`
- `src/sis/reports/remediation_evaluator_observation_core.py`
- `tests/test_remediation_evaluator_observation_core.py`

## Scope

- Move `apply_aliases()` and `merge_observation_sources()` to a new core helper module.
- Keep existing imports from `sis.reports.remediation_evaluator_observations` working through explicit aliases.
- Do not move any file-reading observation collectors in this pass.

## Out Of Scope

- Observation source priority changes.
- Field name, count name, or alias map changes.
- Summary key names, artifact keys, Markdown/report text/order.
- Public CLI names/options.
- Schema, auth, DB, CI, dependencies, paper/live safety boundaries.

## Red-Green-Refactor

1. RED: Add direct tests importing the new core module.
2. GREEN: Move only alias/merge helpers and update aliases.
3. REFACTOR: Run focused core tests, existing remediation evaluator observation tests, related report observation tests, CLI smoke, lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Verification Plan

- `CI=true timeout 120 uv run pytest -q tests/test_remediation_evaluator_observation_core.py`
- `CI=true timeout 120 uv run pytest -q tests/test_remediation_evaluator_observation_core.py tests/test_remediation_evaluator_observations.py tests/test_remediation_evaluator_report_observations.py`
- `CI=true timeout 120 uv run pytest -q tests/test_remediation_evaluator_paths.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'remediation'`
- `uv run ruff format src/sis/reports/remediation_evaluator_observations.py src/sis/reports/remediation_evaluator_observation_core.py tests/test_remediation_evaluator_observation_core.py`
- `uv run ruff check src/sis/reports/remediation_evaluator_observations.py src/sis/reports/remediation_evaluator_observation_core.py tests/test_remediation_evaluator_observation_core.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- Best next target: `remediation_evaluator_observations.py` is a large report helper module with a small pure core subset.
- Safer boundary: aliasing and source merge do not read files and are already covered by tests.
- Main risk: changing source precedence. Mitigation: direct tests assert first-source wins for fields and counts.
- Stop condition: if the split changes any observed field, count, source map, or alias behavior, revert to a smaller boundary.

## Branch Decision

Continue on `refactor/backtest-primitives`. This is the existing dedicated refactor branch, and this pass is a small behavior-preserving split.
