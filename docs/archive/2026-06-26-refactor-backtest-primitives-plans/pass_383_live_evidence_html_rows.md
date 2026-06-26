<!--
作成日: 2026-06-26_18:14 JST
更新日: 2026-06-26_18:14 JST
-->

# Pass 383 Live Evidence HTML Rows

## Purpose

Extract deterministic HTML row and list item builders from `src/sis/reports/live_evidence_html.py` without changing report headings, table column order, escaping behavior, public CLI behavior, summary keys, schemas, dependencies, or paper/live safety boundaries.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- Baseline: `30e43d1`
- Existing uncommitted work to preserve: Pass 377, Pass 378, Pass 379, Pass 380, Pass 381, and Pass 382.
- Restart source: `./.ai_memory/HANDOFF.md` v42.

## Target Files

- `src/sis/reports/live_evidence_html.py`
- `src/sis/reports/live_evidence_html_rows.py`
- `tests/test_live_evidence_html_rows.py`
- `tests/test_live_evidence_html.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Plan

1. Add direct tests for venue, diagnostics, cost, backtest, blockers, next actions, validation, and log-tail escaping helpers.
2. Add `live_evidence_html_rows.py` with pure row/list/pre helpers.
3. Update `render_live_evidence_html()` to delegate only those row/list/pre builders.
4. Run focused row tests, existing live evidence HTML test, CLI smoke slice if available, lint/type/help checks, `git diff --check`, and `./scripts/check`.

## Constraints

- Do not alter HTML headings, table column order, CSS, or section order.
- Do not change escaping semantics. `None` should continue rendering as an empty string through the existing HTML escape behavior.
- Do not change data summaries, validation rules, JSON keys, artifact names, public CLI names/options, schemas, auth, DB, CI, dependencies, or external-service behavior.
- Do not claim paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness.

## Risk Review

- Risk: HTML escaping regressions can create unsafe report output. Mitigation: direct tests assert escaped output and absence of raw unsafe strings.
- Risk: Table column order is user-visible. Mitigation: row helper tests assert exact row strings for each table type.
- Risk: Broad HTML template refactor would be too large. Mitigation: this pass stops at deterministic row/list/pre builders and keeps section markup in `live_evidence_html.py`.

## Verification

- RED: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_html_rows.py`
- GREEN/focused: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_html_rows.py`
- Existing HTML: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_html.py`
- CLI smoke: `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'live_evidence'`
- Format: `uv run ruff format src/sis/reports/live_evidence_html.py src/sis/reports/live_evidence_html_rows.py tests/test_live_evidence_html_rows.py`
- Lint: `uv run ruff check src/sis/reports/live_evidence_html.py src/sis/reports/live_evidence_html_rows.py tests/test_live_evidence_html_rows.py`
- Type: `uv run ty check src --python-version 3.13 --output-format concise`
- CLI surface: `uv run sis --help | wc -l`
- Diff: `git diff --check`
- Full gate: `./scripts/check`

## Rollback

Remove `src/sis/reports/live_evidence_html_rows.py`, remove `tests/test_live_evidence_html_rows.py`, and restore the moved inline row/list/pre generation in `src/sis/reports/live_evidence_html.py`.
