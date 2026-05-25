# 09. Storage / Reporting Spec

## Storage policy

### Raw JSONL

```txt
data/raw/quotes/{venue}/YYYY-MM-DD.jsonl
```

raw payloadを必ず保存する。

### Normalized Parquet

```txt
data/normalized/quotes.parquet
```

### DuckDB

```txt
data/normalized/sis.duckdb
```

## DuckDB schema

```sql
CREATE TABLE IF NOT EXISTS quotes (
  ts_client TIMESTAMP,
  venue TEXT,
  chain TEXT,
  canonical_symbol TEXT,
  venue_symbol TEXT,
  pair_index INTEGER,
  mark_price DOUBLE,
  index_price DOUBLE,
  oracle_price DOUBLE,
  bid_price DOUBLE,
  ask_price DOUBLE,
  exec_buy_price DOUBLE,
  exec_sell_price DOUBLE,
  spread_bps DOUBLE,
  oracle_ts_ms BIGINT,
  market_status TEXT,
  is_tradable BOOLEAN,
  source TEXT,
  raw_payload_sha256 TEXT
);

CREATE TABLE IF NOT EXISTS cost_snapshots (
  ts_client TIMESTAMP,
  venue TEXT,
  canonical_symbol TEXT,
  open_fee_bps DOUBLE,
  close_fee_bps DOUBLE,
  fixed_spread_bps DOUBLE,
  spread_p50_bps DOUBLE,
  spread_p90_bps DOUBLE,
  holding_cost_4h_bps DOUBLE,
  holding_cost_24h_bps DOUBLE,
  holding_cost_72h_bps DOUBLE,
  stale_rate DOUBLE,
  tradable_rate DOUBLE
);
```

## Reports

### daily_probe_report.md

内容:

```txt
- 取得期間
- 対象venue/symbol
- stale率
- tradable率
- spread p50/p90/p99
- market close/reopen時の取得状況
- parser error
- Go/No-Go provisional status
```

### venue_cost_matrix.csv

列:

```txt
venue
symbol
asset_class
open_fee_bps
close_fee_bps
spread_p50_bps
spread_p90_bps
spread_p99_bps
holding_cost_4h_bps
holding_cost_24h_bps
holding_cost_72h_bps
stale_rate
tradable_rate
notes
```

### go_no_go_report.md

- decision
- venue decisions table
- criteria table
- blockers
- next actions
- evidence links
