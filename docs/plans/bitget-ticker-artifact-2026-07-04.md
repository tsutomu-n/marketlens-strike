<!--
作成日: 2026-07-04_23:41 JST
更新日: 2026-07-04_23:41 JST
-->

# Bitget Ticker Artifact Plan

## Checkpoint ID

BITGET-TICKER-ARTIFACT-2026-07-04

## Purpose

Move beyond the G3 local ticker proxy by adding a repo-native Bitget current
ticker artifact that can later be consumed by source availability and
pre-actual-cash evidence packs.

## Current State

`strategy-idea-candidates-bitget-source-refresh` already fetches Bitget public
contracts, current tickers, and closed 5m candles. It writes `scanner.duckdb`,
`candles_5m` parquet, and `latest.json`, but it does not persist the full ticker
row as a first-class `ticker_rows` dataset with bid/ask, mark, index, funding,
coverage class, and a manifest.

The current G3 dogfood uses local `crypto_perp_ticker_proxy.v1` refs. That is a
useful blocker removal, but it is not a native exchange ticker source.

## Constraints

- Bitget first.
- No authenticated API, credentials, wallet/signing, exchange write, live order,
  tiny-live, actual cash, trades/books/replay expansion, or 30-event expansion.
- Do not run live public network calls during implementation; use existing
  mocked transport tests.
- Keep native current ticker distinct from historical backfill and reconstructed
  ticker sources.
- Preserve existing C9 source-root compatibility.

## Target Files

- `src/sis/crypto_perp/bitget/normalizers.py`
- `src/sis/strategy_idea_candidates/bitget_public_source.py`
- `tests/strategy_idea_candidates/test_bitget_public_source.py`
- `schemas/crypto_perp_ticker_manifest.v1.schema.json`
- `docs/final-summary.md`

## Implementation Approach

1. Extend Bitget mix ticker normalization to retain bid/ask size, mark price,
   index price, base/quote volume, and current holding amount.
2. Materialize `ticker_rows.parquet` under the existing source root with a
   normalized, venue-neutral column set.
3. Emit `ticker_manifest.json` with coverage class, fields present, row counts,
   safety boundary flags, raw source endpoint ids, and support flags.
4. Keep `scanner.duckdb` behavior backward compatible.
5. Add tests that inspect the parquet and manifest from the mocked Bitget public
   refresh path.

## Test Plan

- `uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py`
- `uv run pytest tests/crypto_perp/test_bitget_normalizers.py`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`

## Completion Conditions

- Mocked Bitget refresh writes one `ticker_rows.parquet` row for BTCUSDT.
- Row includes `bid_px`, `ask_px`, `mid_px`, `mark_px`, `index_px`,
  `funding_rate`, `coverage_class=native`, and `is_snapshot=true`.
- `ticker_manifest.json` reports `coverage_class=native`,
  `supports_cost_adjusted_estimate=true`, `supports_edge_action=true`,
  `exchange_write_used=false`, `live_order_submitted=false`, and row counts.
- Existing source-root tests remain green.

## Failure Conditions

- The ticker row drops bid/ask or mark/index fields available in the Bitget
  response.
- A last-price-only row is marked as supporting edge action.
- The implementation requires network in tests.
- The change claims actual cash, live readiness, or profit proof.

## Critique

This does not solve historical event backfill by itself. Bitget current ticker is
native for the capture time only. Historical 10-event backfill still needs either
reconstructed Bitget coverage or a separate OKX historical adapter. That is out
of this checkpoint.

## Branch

`ai/bitget-ticker-artifact-20260704-2339`
