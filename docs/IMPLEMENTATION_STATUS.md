# Implementation Status

The handoff implementation is complete; current Go/No-Go may still be conditional because it depends on live quote evidence.

| Area | Item | Status | Evidence |
|---|---|---|---|
| Epic 0 | Repository setup | DONE | pyproject.toml, README.md, sidecars/gtrade |
| Epic 1 | InstrumentSpec / QuoteLog / CostSnapshot / MarketSession | DONE | src/sis/models.py |
| Epic 1 | Static JSON schemas from handoff | DONE | schemas/*.schema.json |
| Epic 2 | gTrade /trading-variables sidecar | DONE | sidecars/gtrade/src/emit_jsonl.ts |
| Epic 2 | gTrade SPY/QQQ/XAU extraction | DONE | sidecars/gtrade/src/emit_jsonl.test.ts |
| Epic 2 | Quote raw payload preservation | DONE | QuoteLog raw_payload plus raw_payload_ref/hash are stored in raw JSONL |
| Epic 3 | JSONL to Parquet and DuckDB normalization | DONE | src/sis/storage/normalize.py |
| Epic 4 | gTrade registry and initial cost matrix | DONE | sidecar fee/spread metadata plus gTrade/Ostium 4h/24h/72h holding costs are reflected |
| Epic 4 | stale/tradable/spread aggregate calculations | DONE | implemented for normalized quote logs |
| Epic 5 | scalping policy | DONE | src/sis/risk/scalping_policy.py |
| Epic 5 | halt policy config loader | DONE | src/sis/risk/halt_policy.py |
| Epic 5 | session/stale/event/spread/cost/registry/mark-index guards | DONE | all FR-006 BLOCK reasons are implemented |
| Epic 5 | liquidation guard | DONE | position-aware guard plus Ostium liquidation reference sidecar are implemented |
| Epic 6 | Ostium read-only price probe | DONE | Builder API prices plus SDK getPairs metadata |
| Epic 6 | Ostium fees/OI caps/trading metadata | DONE | SDK getPairs sidecar metadata merged into registry |
| Epic 6 | Ostium liquidation reference | DONE | read-only getOpenPositions sidecar supports trader address and bounded ALL sampling |
| Epic 7 | Backtest bridge | DONE | research signal CSV input, venue quote virtual execution, and metrics implemented |
| Epic 8 | Go/No-Go markdown and evidence card | DONE | metrics evaluator, thresholds, blockers, and evidence digests implemented |

## Live Evidence Still Required

- Recollect a sufficient quote window with fresh venue timestamps until `stale_rate` satisfies the Go/No-Go threshold.
- Recollect during tradable sessions until `tradable_rate` satisfies the Go/No-Go threshold.
