<!--
作成日: 2026-07-04_23:57 JST
更新日: 2026-07-04_23:57 JST
-->

# Ticker Coverage Metadata Plan

## Checkpoint ID

C1-TICKER-COVERAGE-METADATA-2026-07-04

## Purpose

Remove the necessary remaining risk in the Bitget ticker artifact work: ticker
availability must not be row-count-only. The run-local source availability and
pre-actual-cash summary should carry the manifest's coverage class, field set,
window, support flags, and warnings.

## Current State

`strategy-idea-candidates-bitget-source-refresh` emits `ticker_rows.parquet` and
`ticker_manifest.json`. `crypto-perp-profit-readiness-run-local
--ticker-manifest` can mark ticker available and pass deduped row count into
`source_availability.json`.

The remaining necessary gap is explanatory metadata. `source_availability.json`
currently shows ticker availability and row count, but not coverage class,
window, fields present, missing fields, exchange, market type, symbols, or
support flags.

## Constraints

- Do not add OKX historical backfill.
- Do not add WS always-on collection.
- Do not change trades/books/replay/event definition/actual cash/live paths.
- Keep schema expansion backward compatible for callers that do not provide
  ticker metadata.
- Preserve existing safety flags and no exchange write behavior.

## Target Files

- `src/sis/crypto_perp/source_availability.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `src/sis/crypto_perp/pre_actual_cash.py`
- `schemas/crypto_perp_source_availability.v1.schema.json`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/final-summary.md`

## Implementation Approach

1. Add optional `metadata` to each source status.
2. Parse ticker manifest metadata in `--ticker-manifest`.
3. Pass ticker metadata into `build_source_availability()`.
4. Include per-source metadata in the pre-actual-cash source matrix.
5. Extend schema and focused tests.

## Test Plan

- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py::test_profit_readiness_run_local_accepts_ticker_manifest_row_count`
- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py::test_pre_actual_cash_pack_reads_existing_run_manifest`
- `uv run pytest tests/crypto_perp/test_source_availability.py tests/crypto_perp/test_profit_readiness_local_automation.py`
- `./scripts/check`

## Completion Conditions

- Ticker source status includes metadata from ticker manifest.
- Source matrix surfaces ticker metadata.
- Existing no-ticker flows remain schema-valid.
- Full check passes.

## Failure Conditions

- A last-only ticker can appear as edge-action-ready without bid/ask metadata.
- Schema validation breaks for existing source availability artifacts.
- The work introduces external API calls, exchange writes, actual cash, OKX, or
  WS collection.

## Rollback

Revert this branch's commit; it is an additive schema/metadata change.
