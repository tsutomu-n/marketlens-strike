<!--
作成日: 2026-06-26_21:52 JST
更新日: 2026-06-26_21:52 JST
-->

# Pass 406 Operations Bundle Artifacts

## Purpose

Extract Operations Bundle artifact path projection and recommended read-order construction from `src/sis/reports/operations_bundle.py`.

## Scope

- Add `src/sis/reports/operations_bundle_artifacts.py`.
- Add direct tests in `tests/test_operations_bundle_artifacts.py`.
- Update `src/sis/reports/operations_bundle.py` to delegate only artifact path and read-order helpers.

## Out Of Scope

- Public CLI command names or options.
- Markdown headings, line order, wording, or summary key names.
- Manifest key names.
- File loading, summary normalization, navigation helpers, schemas, dependencies, CI, auth, DB, or external-service behavior.
- Paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness claims.

## RED

Run:

```bash
CI=true timeout 120 uv run pytest -q tests/test_operations_bundle_artifacts.py
```

Expected before implementation: import failure for `sis.reports.operations_bundle_artifacts`.

## GREEN

Move only:

- Operations Bundle `artifacts` dictionary construction.
- Operations Bundle `recommended_read_order` item construction.

## Verification

- `CI=true timeout 120 uv run pytest -q tests/test_operations_bundle_artifacts.py`
- `CI=true timeout 120 uv run pytest -q tests/test_operations_bundle_artifacts.py tests/test_monitoring_comparison.py -k 'operations_bundle'`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'operations_bundle'`
- `uv run ruff format src/sis/reports/operations_bundle.py src/sis/reports/operations_bundle_artifacts.py tests/test_operations_bundle_artifacts.py`
- `uv run ruff check src/sis/reports/operations_bundle.py src/sis/reports/operations_bundle_artifacts.py tests/test_operations_bundle_artifacts.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- The extracted logic is pure path projection and list construction, so it is low risk and easy to test directly.
- The main risk is changing manifest artifact key names or read-order item order. Direct tests lock both.
- `operations_bundle.py` keeps file loading, summary normalization, navigation, Markdown rendering, and JSON writing.
