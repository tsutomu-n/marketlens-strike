<!--
作成日: 2026-06-26_20:59 JST
更新日: 2026-06-26_20:59 JST
-->

# Pass 400 Phase Gate Review Diagnostics

## Purpose

Extract Phase Gate Review quote diagnostics row collection from `src/sis/reports/phase_gate_review.py` into a focused helper module.

## Scope

- Add `src/sis/reports/phase_gate_review_diagnostics.py`.
- Move only the loop that builds Trade[XYZ] quote diagnostic rows for configured symbols.
- Keep Phase Gate decision logic, strict validation, remediation assembly, Markdown rendering, and public CLI unchanged.
- Add direct tests for available/missing symbols and latest-only quote file behavior.

## Out Of Scope

- Trade[XYZ] diagnostic health or blocker decisions.
- Stale/spread threshold definitions.
- Strict artifact validation.
- Remediation order, recovery command, or recommendation generation.
- Markdown report text/order.
- Public CLI command names or options.
- Summary/model field names.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_diagnostics.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_diagnostics.py tests/test_phase_gate_review.py tests/test_phase_gate_review_decisions.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'phase_gate_review'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/phase_gate_review.py src/sis/reports/phase_gate_review_diagnostics.py tests/test_phase_gate_review_diagnostics.py`
   - `uv run ruff check src/sis/reports/phase_gate_review.py src/sis/reports/phase_gate_review_diagnostics.py tests/test_phase_gate_review_diagnostics.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: diagnostics availability changes. Mitigation: direct tests cover available and missing symbols.
- Risk: accidentally using older quote files. Mitigation: direct tests cover latest-only file selection through the helper.
- Risk: changing Phase Gate decision behavior. Mitigation: only replace diagnostics row construction and run existing Phase Gate and CLI tests.

## Rollback

Delete the new helper/test files and restore the diagnostics loop directly in `src/sis/reports/phase_gate_review.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
