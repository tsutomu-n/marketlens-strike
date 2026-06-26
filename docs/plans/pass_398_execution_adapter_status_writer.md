<!--
作成日: 2026-06-26_20:45 JST
更新日: 2026-06-26_20:45 JST
-->

# Pass 398 Execution Adapter Status Writer

## Purpose

Extract the shared Execution Adapter status Markdown/JSON writer from `src/sis/reports/execution_adapter_status.py` into a focused helper module.

## Scope

- Add `src/sis/reports/execution_adapter_status_writer.py`.
- Move only the common report writer used by Execution Adapter status report builders.
- Keep individual balance, fill, order, action, reconcile, and read-only surfaces summary/detail assembly unchanged.
- Keep public CLI, summary keys, Markdown section order, and safety boundary wording unchanged.
- Add direct tests for the writer module.

## Out Of Scope

- Execution adapter command behavior.
- Balance/fill/order/action/reconcile summary field selection.
- Execution read-only surfaces summary aggregation.
- Navigation link generation.
- Markdown text/order beyond preserving the existing shared writer output.
- Public CLI command names or options.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_execution_adapter_status_writer.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_execution_adapter_status_writer.py tests/test_monitoring_comparison.py -k 'execution_balance_status_report or execution_fill_status_report or execution_order_and_action_reports or execution_reconcile_positions_report'`
   - `CI=true timeout 120 uv run pytest -q tests/test_execution_adapter_status_navigation.py tests/test_execution_adapter_status_surfaces.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'execution_'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/execution_adapter_status.py src/sis/reports/execution_adapter_status_writer.py tests/test_execution_adapter_status_writer.py`
   - `uv run ruff check src/sis/reports/execution_adapter_status.py src/sis/reports/execution_adapter_status_writer.py tests/test_execution_adapter_status_writer.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: Markdown section order changes. Mitigation: direct writer tests assert Quick Navigation, Related Reports, Overview, and Recommended Read Order order.
- Risk: summary JSON writing changes. Mitigation: direct writer test writes and reads a summary file.
- Risk: broader execution adapter report regressions. Mitigation: run existing report builder and CLI tests.

## Rollback

Delete the new helper/test files and restore the shared writer function directly in `src/sis/reports/execution_adapter_status.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
