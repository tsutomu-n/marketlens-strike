<!--
作成日: 2026-06-26_20:52 JST
更新日: 2026-06-26_20:52 JST
-->

# Pass 399 Remediation Evaluator Observation Fields

## Purpose

Extract repeated field-map observation collection from `src/sis/reports/remediation_evaluator_observations.py` into a focused helper module.

## Scope

- Add `src/sis/reports/remediation_evaluator_observation_fields.py`.
- Move only the side-effect-free mapping loop that copies source summary fields into observed fields and counts.
- Keep observation source order, path loading, aliasing, Markdown parsing, JSONL parsing, and remediation evaluator behavior unchanged.
- Add direct tests for existing target preservation, value coercion, count collection, and issue preview handling.

## Out Of Scope

- Planner path resolution.
- Observation source precedence.
- Alias rules.
- Markdown report parsing.
- Manifest note parsing.
- Public CLI command names or options.
- Summary/model field names.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_remediation_evaluator_observation_fields.py`
2. GREEN focused: same command passes.
3. Related observation tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_remediation_evaluator_observation_fields.py tests/test_remediation_evaluator_observation_core.py tests/test_remediation_evaluator_observations.py tests/test_remediation_evaluator_report_observations.py`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/remediation_evaluator_observations.py src/sis/reports/remediation_evaluator_observation_fields.py tests/test_remediation_evaluator_observation_fields.py`
   - `uv run ruff check src/sis/reports/remediation_evaluator_observations.py src/sis/reports/remediation_evaluator_observation_fields.py tests/test_remediation_evaluator_observation_fields.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: changing source precedence. Mitigation: helper preserves existing target fields by default and direct tests lock that behavior.
- Risk: changing type coercion. Mitigation: helper uses the existing remediation signal coercion function and tests bool/int/string cases.
- Risk: changing issue preview collection. Mitigation: helper supports explicit issue-preview source keys and direct tests lock empty-preview omission.

## Rollback

Delete the new helper/test files and restore the repeated field-map loops directly in `src/sis/reports/remediation_evaluator_observations.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
