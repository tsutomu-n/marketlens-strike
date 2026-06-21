<!--
作成日: 2026-06-21_15:07 JST
更新日: 2026-06-21_15:07 JST
-->

# Tardis Fixture Provenance

This directory contains a synthetic miniature fixture that follows the documented Tardis downloadable CSV column contracts for Bitget Futures trades, incremental L2 book updates, and derivative ticker rows.

No vendor dataset rows are committed here. Use `scripts/download_tardis_bitget_fixture.py download --url ... --out ...` to fetch a real public sample manually after reviewing Tardis terms.

Reference URLs:

- https://docs.tardis.dev/historical-data-details/bitget-futures
- https://docs.tardis.dev/downloadable-csv-files/data-types
- https://docs.tardis.dev/downloadable-csv-files/api

Fixture details:

- exchange: `bitget-futures`
- symbol: `BTCUSDT`
- date label: `2024-12-01`
- rows: synthetic hand-written rows for deterministic parser, book reconstruction, and VWAP tests
- expected trade VWAP: `100.25`
- expected final best bid / ask: `100.5` / `101.5`
