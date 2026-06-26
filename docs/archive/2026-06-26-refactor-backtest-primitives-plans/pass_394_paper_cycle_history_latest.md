<!--
作成日: 2026-06-26_19:59 JST
更新日: 2026-06-26_19:59 JST
-->

# Pass 394 Paper Cycle History Latest Helpers

## Purpose

Extract latest-note field assembly from `src/sis/reports/paper_cycle_history.py` into a focused helper module.

## Scope

- Add `src/sis/reports/paper_cycle_history_latest.py`.
- Move latest execution, readiness, phase gate, and phase gate issue preview extraction from latest cycle notes.
- Keep report summary key names and Markdown text/order unchanged.
- Add direct tests for latest note field extraction and empty/malformed note handling.

## Out Of Scope

- Paper cycle history Markdown text or section ordering.
- Navigation maps, related reports, or report path behavior.
- Summary JSON key names or artifact key names.
- Public CLI command names or options.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_paper_cycle_history_latest.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_paper_cycle_history_latest.py tests/test_paper_cycle_history_notes.py tests/test_paper_cycle_history_navigation.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'paper_cycle_history'`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'paper_cycle_history'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/paper_cycle_history.py src/sis/reports/paper_cycle_history_latest.py tests/test_paper_cycle_history_latest.py`
   - `uv run ruff check src/sis/reports/paper_cycle_history.py src/sis/reports/paper_cycle_history_latest.py tests/test_paper_cycle_history_latest.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: latest summary key drift. Mitigation: direct tests assert exact helper keys and existing report test checks
  generated summary/report values.
- Risk: phase gate issue previews changing. Mitigation: direct test includes `phase_gate_issue_1=` note.
- Risk: invalid latest notes changing from `None` to empty strings. Mitigation: direct test covers empty helper input.

## Rollback

Delete the new helper/test files and restore latest note extraction directly in `src/sis/reports/paper_cycle_history.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving
helper extraction and does not require a new branch under AGENTS.md.
