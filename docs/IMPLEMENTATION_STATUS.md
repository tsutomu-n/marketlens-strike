# Implementation Status

The handoff zip is not fully implemented. This file separates completed scaffold work from remaining research-engine work.

| Area | Item | Status | Evidence |
|---|---|---|---|
| Epic 0 | Repository setup | DONE | pyproject.toml, README.md, sidecars/gtrade |
| Epic 1 | InstrumentSpec / QuoteLog / CostSnapshot / MarketSession | DONE | src/sis/models.py |
| Epic 1 | Static JSON schemas from handoff | DONE | schemas/*.schema.json |
| Epic 2 | gTrade /trading-variables sidecar | DONE | sidecars/gtrade/src/emit_jsonl.ts |
| Epic 2 | gTrade SPY/QQQ/XAU extraction | DONE | sidecars/gtrade/src/emit_jsonl.test.ts |
| Epic 3 | JSONL to Parquet and DuckDB normalization | DONE | src/sis/storage/normalize.py |
| Epic 4 | gTrade registry and initial cost matrix | DONE | sidecar fee/spread metadata plus gTrade/Ostium 4h/24h/72h holding costs are reflected |
| Epic 4 | stale/tradable/spread aggregate calculations | DONE | implemented for normalized quote logs |
| Epic 5 | scalping policy | DONE | src/sis/risk/scalping_policy.py |
| Epic 5 | halt policy config loader | DONE | src/sis/risk/halt_policy.py |
| Epic 5 | session/stale/spread/mark-index guards | DONE | quote-level guards implemented |
| Epic 5 | liquidation guard | PARTIAL | position-aware guard implemented; venue liquidation reference still required |
| Epic 6 | Ostium read-only price probe | DONE | Builder API prices plus SDK getPairs metadata |
| Epic 6 | Ostium fees/OI caps/trading metadata | DONE | SDK getPairs sidecar metadata merged into registry |
| Epic 6 | Ostium liquidation reference | PARTIAL | read-only open-position sidecar implemented; requires trader position data |
| Epic 7 | Backtest bridge | DONE | research signal CSV input, venue quote virtual execution, and metrics implemented |
| Epic 8 | Go/No-Go markdown and evidence card | DONE | metrics evaluator, thresholds, blockers, and evidence digests implemented |

## Not Yet Complete

- Ostium liquidation reference verification requires `bun run ostium:probe:positions -- --user 0x...` with a trader that has real open positions.
