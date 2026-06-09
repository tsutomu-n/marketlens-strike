<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Research Findings

## Code Truth Checked

- `src/sis/venues/ids.py`
- `src/sis/venues/suitability.py`
- `src/sis/execution/bitget_demo_adapter.py`
- `src/sis/execution/base.py`
- `src/sis/commands/execution.py`
- `src/sis/commands/execution_artifacts.py`
- `schemas/strategy_signal.v1.schema.json`
- `schemas/trade_candidate.v1.schema.json`
- `schemas/paper_intent_preview.v1.schema.json`
- `schemas/evaluation_plan.mls.v1.schema.json`
- `tests/test_bitget_demo_adapter.py`
- `tests/test_bitget_demo_cli.py`
- `tests/test_paper_from_intents.py`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md`
- `docs/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md`

## Observed Facts

- Current `VenueId` is `Literal["trade_xyz", "bitget_demo"]`.
- `strategy_signal`, `trade_candidate`, and `paper_intent_preview` schemas allow
  `trade_xyz` and `bitget_demo`.
- `evaluation_plan.mls.v1` still has `target_venue` fixed to `trade_xyz`.
- `VENUE_SUITABILITY_CATALOG` already contains `trade_xyz`, `bitget_demo`,
  `bitget_futures`, and `hyperliquid_perp`.
- `bitget_futures` and `hyperliquid_perp` are catalog-only and not current
  schema values.
- `bitget_demo` has local credential detection, signature/header helpers,
  response parsers, and fail-closed non-writing adapter methods.
- `bitget-demo-smoke` writes local artifacts but keeps
  `read_only_network_probe=not_executed`, `external_write_enabled=false`, and
  `exchange_write_used=false`.
- Hyperliquid is currently present mostly through Trade[XYZ] registry,
  historical archive, quotes, websocket, and read-only collection surfaces.
  There is no general `hyperliquid_perp` execution venue adapter.
- NDX/QQQ family rows are intentionally blocked from selected candidates,
  `PaperIntentPreview`, raw `paper-from-intents` JSON, and legacy `paper-step`.

## Risk Findings

- Widening only `VenueId` is insufficient because `evaluation_plan.mls.v1`
  remains `target_venue=trade_xyz`.
- Reusing `bitget_demo` for production Bitget would conflate demo credentials,
  paper-only fixtures, and production live behavior.
- Reusing Trade[XYZ] Hyperliquid code as `hyperliquid_perp` would conflate
  index-proxy data collection with direct crypto perp venue support.
- Adding exchange-write methods before read-only evidence would bypass the
  repo's existing read-only / paper / live separation.
- Adding NDX/QQQ support through Bitget or Hyperliquid is not a realistic near
  term path because those venues are crypto perp venues in the current design.

## Better Plan Adjustment

The better next step is not "implement Bitget and Hyperliquid". The next step is
to create a venue capability contract and a fixture-first read-only gate. Only
after that should the repo widen `VenueId` or Strategy Lab schemas.
