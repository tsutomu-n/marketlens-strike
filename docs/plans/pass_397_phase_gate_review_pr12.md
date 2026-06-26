<!--
作成日: 2026-06-26_20:38 JST
更新日: 2026-06-26_20:38 JST
-->

# Pass 397 Phase Gate Review PR12 Helpers

## Purpose

Extract the PR12 fresh read-only smoke completion and next-action decision from `src/sis/reports/phase_gate_review.py` into a focused helper module.

## Scope

- Add `src/sis/reports/phase_gate_review_pr12.py`.
- Move only the PR12 completion check and `run_pr12_fresh_read_only_smoke` next-action selection.
- Keep Phase Gate decision logic, Trade[XYZ] diagnostics, remediation assembly, Markdown rendering, and public CLI unchanged.
- Add direct tests for PR12 boundary behavior, including bool values not being accepted as numeric observed windows.

## Out Of Scope

- Phase Gate venue decision logic.
- Trade[XYZ] quote diagnostics or spread/stale thresholds.
- Strict artifact validation.
- Remediation order, recovery command, or recommendation generation.
- Markdown report text/order.
- Public CLI command names or options.
- Summary/model field names.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_pr12.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_pr12.py tests/test_phase_gate_review.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'phase_gate_review'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/phase_gate_review.py src/sis/reports/phase_gate_review_pr12.py tests/test_phase_gate_review_pr12.py`
   - `uv run ruff check src/sis/reports/phase_gate_review.py src/sis/reports/phase_gate_review_pr12.py tests/test_phase_gate_review_pr12.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: changing PR12 completion semantics. Mitigation: direct tests lock required `final_decision`, one-hour numeric observed window, and `next_action`.
- Risk: accepting bool as a numeric observed window. Mitigation: direct regression test keeps bool excluded.
- Risk: changing Phase Gate decision behavior outside PR12. Mitigation: only replace the local PR12 block and run existing Phase Gate and CLI tests.

## Rollback

Delete the new helper/test files and restore the PR12 completion block directly in `src/sis/reports/phase_gate_review.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
