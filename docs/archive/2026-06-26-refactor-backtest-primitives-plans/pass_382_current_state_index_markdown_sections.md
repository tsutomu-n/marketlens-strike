<!--
作成日: 2026-06-26_18:04 JST
更新日: 2026-06-26_18:04 JST
-->

# Pass 382 Current State Index Markdown Sections

## Purpose

Extract deterministic top Markdown section line builders from `src/sis/reports/current_state_index_markdown.py` without changing public CLI behavior, summary keys, artifact keys, Markdown text/order, schemas, dependencies, or paper/live safety boundaries.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- Baseline: `30e43d1`
- Existing uncommitted work to preserve: Pass 377, Pass 378, Pass 379, Pass 380, and Pass 381.
- Restart source: `./.ai_memory/HANDOFF.md` v41.

## Target Files

- `src/sis/reports/current_state_index_markdown.py`
- `src/sis/reports/current_state_index_markdown_sections.py`
- `tests/test_current_state_index_markdown_sections.py`
- `tests/test_current_state_index_markdown.py`
- `.codex/SP_STATE.md`
- `.codex/refactor_loop_2026-06-24.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`
- `./.ai_memory/HANDOFF.md`

## Plan

1. Add direct tests for exact `Overview` and `Research And Backtest` section line output.
2. Add `current_state_index_markdown_sections.py` with `overview_section_lines()` and `research_and_backtest_section_lines()`.
3. Update `render_current_state_index_markdown()` to compose those helpers.
4. Run focused section tests, existing current-state-index Markdown test, CLI smoke for current state index, lint/type/help checks, `git diff --check`, and `./scripts/check`.

## Constraints

- Do not alter Markdown heading text, bullet text, or ordering.
- Do not touch Execution Adapter Surfaces, State And Daemon Surfaces, Live Evidence, navigation, artifacts, or recommended read order in this pass.
- Do not change JSON summary key names, artifact names, public CLI command names/options, schemas, auth, DB, CI, dependencies, or external-service behavior.
- Do not claim paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness.

## Risk Review

- Risk: Markdown text/order is user-facing. Mitigation: direct tests assert exact line lists and existing rendered Markdown tests continue to run.
- Risk: Overview includes execution lineage and remediation timeline fields. Mitigation: helper delegates to existing `latest_execution_lineage_flat_lines()` and only moves current line assembly.
- Risk: The extraction could expand into the large Execution Adapter section. Mitigation: this pass stops at `Overview` and `Research And Backtest` only.

## Verification

- RED: `CI=true timeout 120 uv run pytest -q tests/test_current_state_index_markdown_sections.py`
- GREEN/focused: `CI=true timeout 120 uv run pytest -q tests/test_current_state_index_markdown_sections.py`
- Existing Markdown: `CI=true timeout 120 uv run pytest -q tests/test_current_state_index_markdown.py`
- CLI smoke: `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'current_state_index'`
- Format: `uv run ruff format src/sis/reports/current_state_index_markdown.py src/sis/reports/current_state_index_markdown_sections.py tests/test_current_state_index_markdown_sections.py`
- Lint: `uv run ruff check src/sis/reports/current_state_index_markdown.py src/sis/reports/current_state_index_markdown_sections.py tests/test_current_state_index_markdown_sections.py`
- Type: `uv run ty check src --python-version 3.13 --output-format concise`
- CLI surface: `uv run sis --help | wc -l`
- Diff: `git diff --check`
- Full gate: `./scripts/check`

## Rollback

Remove `src/sis/reports/current_state_index_markdown_sections.py`, remove `tests/test_current_state_index_markdown_sections.py`, and restore the moved inline line assembly in `src/sis/reports/current_state_index_markdown.py`.
