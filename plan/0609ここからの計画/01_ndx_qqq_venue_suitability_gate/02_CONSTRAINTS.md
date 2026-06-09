<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_15:07 JST
-->

# Constraints

Do not:

- call external APIs
- use credentials
- add dependencies
- update `pyproject.toml` or `uv.lock`
- generate or update `data/research/strategy_signals.parquet`
- regenerate NDX Layer 2.3/2.4 artifacts
- run a backtest
- submit paper/live orders
- add wallet, signing, or exchange-write paths
- add `bitget_futures` or `hyperliquid_perp` to `VenueId`
- add `bitget_futures` or `hyperliquid_perp` to Strategy Lab artifact schemas
- widen `schemas/evaluation_plan.mls.v1.schema.json` in this slice

Allowed:

- add a pure suitability catalog and helper functions
- add fail-closed guards for selected candidates and paper intents
- update tests and README boundary wording
- create this plan package
