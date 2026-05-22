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
| Epic 4 | gTrade registry and initial cost matrix | PARTIAL | holding/borrowing costs are not complete |
| Epic 4 | stale/tradable/spread aggregate calculations | DONE | implemented for normalized quote logs |
| Epic 5 | scalping policy | DONE | src/sis/risk/scalping_policy.py |
| Epic 5 | halt policy config loader | DONE | src/sis/risk/halt_policy.py |
| Epic 5 | session/stale/spread/mark-index guards | DONE | quote-level guards implemented |
| Epic 5 | liquidation guard | PARTIAL | position-aware guard implemented; venue liquidation reference still required |
| Epic 6 | Ostium read-only price probe | PARTIAL | symbol and quote probe only |
| Epic 6 | Ostium fees/OI caps/liquidation reference | NOT_DONE | requires SDK/API probe |
| Epic 7 | Backtest bridge | PARTIAL | venue quote virtual execution and metrics implemented |
| Epic 8 | Go/No-Go markdown and evidence card | PARTIAL | metrics are included but final evaluator is not complete |

## Not Yet Complete

- Ostium fees, OI caps, trading hours detail, and liquidation reference probe.
- Research signal generation and final Go/No-Go metrics evaluator.
