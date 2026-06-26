<!--
作成日: 2026-06-26_21:37 JST
更新日: 2026-06-26_21:37 JST
-->

# Pass 404 Remediation Scoreboard Action Helpers

## Purpose

Extract pure remediation scoreboard action ordering, feedback priority, observed-source, next-action, and status helpers out of `src/sis/reports/remediation_scoreboard.py`.

## Scope

- Add `src/sis/reports/remediation_scoreboard_actions.py`.
- Add direct helper tests in `tests/test_remediation_scoreboard_actions.py`.
- Update `src/sis/reports/remediation_scoreboard.py` to delegate only the extracted pure helpers.

## Out Of Scope

- Public CLI command names or options.
- Markdown headings, line order, wording, or summary keys.
- JSON artifact key names.
- Path loading, JSON writing, navigation helpers, schemas, dependencies, CI, auth, DB, or external-service behavior.
- Paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness claims.

## RED

Run:

```bash
CI=true timeout 120 uv run pytest -q tests/test_remediation_scoreboard_actions.py
```

Expected before implementation: import failure for `sis.reports.remediation_scoreboard_actions`.

## GREEN

Move the following behavior-preserving pure helpers:

- integer coercion for priorities and counts
- observed-source extraction and counting
- action priority key construction
- feedback priority reason and rank
- feedback enrichment
- next-action selection
- scoreboard status classification

## Verification

- `CI=true timeout 120 uv run pytest -q tests/test_remediation_scoreboard_actions.py`
- `CI=true timeout 120 uv run pytest -q tests/test_remediation_scoreboard_actions.py tests/test_monitoring_comparison.py -k 'build_remediation_scoreboard'`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'remediation_scoreboard'`
- `uv run ruff format src/sis/reports/remediation_scoreboard.py src/sis/reports/remediation_scoreboard_actions.py tests/test_remediation_scoreboard_actions.py`
- `uv run ruff check src/sis/reports/remediation_scoreboard.py src/sis/reports/remediation_scoreboard_actions.py tests/test_remediation_scoreboard_actions.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- The helper cluster is pure and directly testable, so it is lower risk than command-module extraction.
- The extracted functions affect action selection and status classification, so tests lock retry-over-pending, feedback priority, priority ordering, and status outcomes.
- `remediation_scoreboard.py` keeps file loading, output assembly, Markdown, JSON writing, and navigation in place.
