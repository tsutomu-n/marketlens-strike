# 14. Test Plan

## Unit tests

### models

- [ ] InstrumentSpec validates required fields
- [ ] QuoteLog accepts null bid/ask
- [ ] CostSnapshot validates bps fields

### scalping policy

- [ ] `1m` is blocked
- [ ] `5m` is blocked
- [ ] `4h` is allowed
- [ ] unknown timeframe is rejected or flagged

### cost model

- [ ] gTrade XAU min round trip = 11 bps excluding holding
- [ ] gTrade SPY/QQQ min round trip = 10 bps + spread excluding holding
- [ ] missing spread returns incomplete status

### stale guard

- [ ] stale above threshold blocks
- [ ] fresh quote allows

### session guard

- [ ] gTrade indices closed blocks open/close/edit
- [ ] commodities daily break blocks entries

## Integration tests

- [ ] gTrade sidecar fetches `/trading-variables`
- [ ] sidecar emits JSONL
- [ ] Python reads sidecar JSONL
- [ ] Parquet output is generated
- [ ] DuckDB can query quotes

## Replay tests

- [ ] raw JSONL → normalized Parquet is deterministic
- [ ] normalized Parquet → cost matrix is deterministic
- [ ] cost matrix → Go/No-Go report is deterministic

## Manual tests

- [ ] market open時のgTrade取得
- [ ] market close時のgTrade取得
- [ ] XAU daily break前後の取得
- [ ] Ostium symbol search
- [ ] Ostium latest price
- [ ] Ostium trading hours
