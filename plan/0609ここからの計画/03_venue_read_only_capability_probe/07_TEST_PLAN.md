<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Test Plan

## Red Tests First

Before implementation, add failing tests for:

- `build_venue_read_only_probe_summary()` returns all four catalog venues
- future venues are `blocked_by_capability`
- top-level `external_api_used`, `credentials_used`, `wallet_used`,
  `exchange_write_used`, and `live_order_submitted` are false
- summary validates against `venue_read_only_probe_summary.v1.schema.json`
- `uv run sis venue-read-only-probe` writes summary/report with empty env
- Strategy Lab schemas and `VenueId` remain unchanged

## Focused Test Commands

Run after each task:

```bash
uv run pytest -q tests/test_venue_read_only_probe.py
uv run pytest -q tests/test_venue_read_only_probe_cli.py
uv run pytest -q tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py
```

Run after CLI/report integration:

```bash
uv run pytest -q tests/test_execution_snapshot_report.py tests/test_execution_venue_comparison_report.py tests/test_execution_venue_diagnostics_report.py
```

Run before completion:

```bash
uv run python scripts/check_current_docs.py
./scripts/check
```

## Negative Assertions

Tests must assert:

- no `bitget_futures` in `VenueId`
- no `hyperliquid_perp` in `VenueId`
- no future venues in `strategy_signal`, `trade_candidate`, or
  `paper_intent_preview` schema enums
- `evaluation_plan.mls.v1` remains `target_venue=trade_xyz`
- no generated summary field says `ready`, `approved`, `connected`,
  `account_ready`, or `live_ready`
- no secret env values are printed or serialized

## Manual Smoke

Optional local smoke after tests:

```bash
uv run sis venue-read-only-probe
```

Expected:

- exit code `0`
- writes `data/ops/venue_read_only_probe_summary.json`
- writes `data/reports/venue_read_only_probe.md`
- reports future venues as blocked, not ready

