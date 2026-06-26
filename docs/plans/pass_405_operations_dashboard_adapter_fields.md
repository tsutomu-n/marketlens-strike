<!--
作成日: 2026-06-26_21:45 JST
更新日: 2026-06-26_21:45 JST
-->

# Pass 405 Operations Dashboard Adapter Fields

## Purpose

Extract the repeated Execution adapter field assembly from `src/sis/reports/operations_dashboard.py` into `src/sis/reports/operations_dashboard_fields.py`.

## Scope

- Add a high-level `execution_adapter_status_fields(...)` helper in `operations_dashboard_fields.py`.
- Add direct tests in `tests/test_operations_dashboard_fields.py`.
- Update `operations_dashboard.py` to call the new helper and keep existing summary keys unchanged.

## Out Of Scope

- Public CLI command names or options.
- Markdown headings, line order, wording, or summary key names.
- JSON artifact key names.
- Navigation helpers, file loading, schemas, dependencies, CI, auth, DB, or external-service behavior.
- Paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness claims.

## RED

Run:

```bash
CI=true timeout 120 uv run pytest -q tests/test_operations_dashboard_fields.py
```

Expected before implementation: import failure or missing-name failure for `execution_adapter_status_fields`.

## GREEN

Move only the six repeated adapter field mapping calls:

- balance status
- fill status
- order status
- cancel order
- close position
- reconcile positions

Keep the existing lower-level `execution_adapter_fields(...)` helper public and unchanged.

## Verification

- `CI=true timeout 120 uv run pytest -q tests/test_operations_dashboard_fields.py`
- `CI=true timeout 120 uv run pytest -q tests/test_operations_dashboard_fields.py tests/test_monitoring_comparison.py -k 'build_operations_dashboard'`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'operations_dashboard'`
- `uv run ruff format src/sis/reports/operations_dashboard.py src/sis/reports/operations_dashboard_fields.py tests/test_operations_dashboard_fields.py`
- `uv run ruff check src/sis/reports/operations_dashboard.py src/sis/reports/operations_dashboard_fields.py tests/test_operations_dashboard_fields.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- This is a narrow field-projection extraction inside an already existing field helper module.
- The main risk is changing flattened summary key names. Direct tests lock representative keys across all six adapter summaries.
- The dashboard still owns loading, status computation, navigation, Markdown rendering, and JSON writing.
