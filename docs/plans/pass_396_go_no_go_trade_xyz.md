<!--
作成日: 2026-06-26_20:22 JST
更新日: 2026-06-26_20:22 JST
-->

# Pass 396 Go/No-Go Trade XYZ Helpers

## Purpose

Extract the Trade[XYZ] supplemental Go/No-Go artifact report builder from `src/sis/reports/go_no_go.py` into a focused helper module.

## Scope

- Add `src/sis/reports/go_no_go_trade_xyz.py`.
- Move Trade[XYZ] artifact detection, latest quote selection, summary row count parsing, and supplemental report assembly.
- Keep the public `build_go_no_go_report()` behavior unchanged when Trade[XYZ] artifacts are present.
- Keep gTrade/Ostium main decision logic, cost threshold logic, Markdown output, and public CLI unchanged.
- Add direct tests for the new helper module.

## Out Of Scope

- Normal gTrade/Ostium Go/No-Go criteria or decision logic.
- Cost matrix parsing, threshold evaluation, or holding cost rules.
- Markdown report rendering or navigation.
- Public CLI command names or options.
- Summary/model field names.
- Schemas, CI, dependencies, auth, DB, or paper/live safety boundary wording.

## Test Plan

1. RED: `CI=true timeout 120 uv run pytest -q tests/test_go_no_go_trade_xyz.py`
2. GREEN focused: same command passes.
3. Related report tests:
   - `CI=true timeout 120 uv run pytest -q tests/test_go_no_go_trade_xyz.py tests/test_go_no_go.py tests/test_go_no_go_costs.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_go_no_go_markdown.py tests/test_go_no_go_markdown_navigation.py`
   - `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'check_go_no_go'`
4. Static and broad checks:
   - `uv run ruff format src/sis/reports/go_no_go.py src/sis/reports/go_no_go_trade_xyz.py tests/test_go_no_go_trade_xyz.py`
   - `uv run ruff check src/sis/reports/go_no_go.py src/sis/reports/go_no_go_trade_xyz.py tests/test_go_no_go_trade_xyz.py`
   - `uv run ty check src --python-version 3.13 --output-format concise`
   - `uv run sis --help | wc -l`
   - `git diff --check`
   - `./scripts/check`

## Practical Review

- Risk: changing Trade[XYZ] artifact precedence. Mitigation: keep `build_go_no_go_report()` early return and add direct helper tests for artifact detection.
- Risk: changing supplemental blockers or next actions. Mitigation: direct tests assert GO and missing-artifact paths.
- Risk: accidentally touching main Go/No-Go behavior. Mitigation: leave cost and venue decision helpers in `go_no_go.py` and run existing Go/No-Go and CLI tests.

## Rollback

Delete the new helper/test files and restore Trade[XYZ] helper functions directly in `src/sis/reports/go_no_go.py`.

## Branch Decision

Continue on existing dedicated refactor branch `refactor/backtest-primitives`. This is a small, behavior-preserving helper extraction and does not require a new branch under AGENTS.md.
