<!--
作成日: 2026-06-26_18:23 JST
更新日: 2026-06-26_18:23 JST
-->

# Pass 384 Live Evidence Navigation Sections

## Purpose

Extract Live Evidence restart pointer, quick navigation, and related report Markdown/HTML helper functions from `src/sis/reports/live_evidence_sections.py` without changing existing imports, rendered text/order, HTML escaping, public CLI behavior, summary keys, schemas, dependencies, or paper/live safety boundaries.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- Baseline: `30e43d1`
- Existing uncommitted work to preserve: Pass 377, Pass 378, Pass 379, Pass 380, Pass 381, Pass 382, and Pass 383.
- Restart source: `./.ai_memory/HANDOFF.md` v43.

## Target Files

- `src/sis/reports/live_evidence_sections.py`
- `src/sis/reports/live_evidence_navigation_sections.py`
- `tests/test_live_evidence_navigation_sections.py`
- `tests/test_live_evidence_sections.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Plan

1. Add direct tests for exact restart pointer, quick navigation, and related report Markdown/HTML output.
2. Add `live_evidence_navigation_sections.py` with the navigation/restart helper functions.
3. Update `live_evidence_sections.py` to import/re-export those functions so existing callers keep working.
4. Run focused navigation section tests, existing live evidence section tests, related HTML/Markdown tests, lint/type/help checks, `git diff --check`, and `./scripts/check`.

## Constraints

- Do not alter Markdown line text/order.
- Do not alter HTML metric labels, value escaping, or filtering of `None` values.
- Do not change remediation helpers, latest execution lineage helpers, report templates, JSON keys, public CLI names/options, schemas, auth, DB, CI, dependencies, or external-service behavior.
- Do not claim paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness.

## Risk Review

- Risk: Existing imports from `sis.reports.live_evidence_sections` could break. Mitigation: keep imported names available from the original module.
- Risk: Navigation order is user-facing. Mitigation: direct tests assert exact list order and HTML order.
- Risk: Broad split of `live_evidence_sections.py` could cross behavior boundaries. Mitigation: this pass only moves restart/quick/related report helpers.

## Verification

- RED: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_navigation_sections.py`
- GREEN/focused: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_navigation_sections.py`
- Existing sections: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_sections.py`
- Related HTML/Markdown: `CI=true timeout 120 uv run pytest -q tests/test_live_evidence_html.py tests/test_live_evidence_markdown_sections.py`
- Format: `uv run ruff format src/sis/reports/live_evidence_sections.py src/sis/reports/live_evidence_navigation_sections.py tests/test_live_evidence_navigation_sections.py`
- Lint: `uv run ruff check src/sis/reports/live_evidence_sections.py src/sis/reports/live_evidence_navigation_sections.py tests/test_live_evidence_navigation_sections.py`
- Type: `uv run ty check src --python-version 3.13 --output-format concise`
- CLI surface: `uv run sis --help | wc -l`
- Diff: `git diff --check`
- Full gate: `./scripts/check`

## Rollback

Remove `src/sis/reports/live_evidence_navigation_sections.py`, remove `tests/test_live_evidence_navigation_sections.py`, and restore the moved helper bodies in `src/sis/reports/live_evidence_sections.py`.
