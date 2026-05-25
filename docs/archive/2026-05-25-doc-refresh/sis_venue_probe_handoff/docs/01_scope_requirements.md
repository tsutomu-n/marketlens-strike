# 01. Scope / Requirements

## Goal

研究用に、Ostium/gTradeでQQQ・SPY・XAUを4時間〜3日の短期スイング対象として扱えるかを判定する。

## Barrier

RWA Perp/合成Perpでは、通常のOHLCバックテストだけでは不十分。

必ず扱うべき要素:

- mark/index price
- bid/askまたは実行価格
- session open/close
- spread
- holding/borrowing/rollover cost
- stale price
- market close / gap risk
- liquidation reference price
- event blackout
- timeframe policy

## Action

以下を作る。

1. `instrument_registry.json`
2. `quote_log_v1.jsonl`
3. `quotes.parquet`
4. `venue_cost_matrix.csv`
5. `scalping_policy.yaml`
6. `halt_policy.yaml`
7. `go_no_go_report.md`
8. `evidence_card.json`

## Functional Requirements

### FR-001 Registry生成

gTradeとOstiumの対象instrumentをregistry化する。

gTradeの初期対象:

```txt
SPY/USD pairIndex 86
QQQ/USD pairIndex 87
XAU/USD pairIndex 90
```

Ostiumの初期対象:

```txt
US500/SPX相当
NDX/Nasdaq相当
XAU/Gold相当
```

Ostiumは現行symbolをprobeで確定する。

### FR-002 Quote logging

Quote logはraw JSONLとして保存する。

最低保存項目:

```txt
ts_client
venue
canonical_symbol
venue_symbol
pair_index_or_pair_id
mark_price
index_price
oracle_price
bid_price
ask_price
exec_buy_price
exec_sell_price
spread_bps
oracle_ts_ms
market_status
is_tradable
raw_payload_sha256
raw_payload
```

### FR-003 Normalize

raw JSONLをParquetへ変換する。

### FR-004 Cost matrix

4h/24h/72hのコスト見積もりを作る。

### FR-005 Scalping prohibition

`1s`, `5s`, `15s`, `1m`, `5m` は原則BLOCKする。

### FR-006 Trading halt

以下のBLOCK理由を実装する。

```txt
BLOCK_SCALPING_TIMEFRAME
BLOCK_MARKET_CLOSED
BLOCK_SESSION_END_NEAR
BLOCK_EVENT_WINDOW
BLOCK_SPREAD_TOO_WIDE
BLOCK_PRICE_STALE
BLOCK_MARK_INDEX_DIVERGENCE
BLOCK_COST_TOO_HIGH
BLOCK_NEAR_LIQUIDATION
BLOCK_WEEKEND_HOLD
BLOCK_UNKNOWN_PRICE_REFERENCE
BLOCK_REGISTRY_INCOMPLETE
```

### FR-007 Go/No-Go

以下を自動判定する。

GO条件:

```txt
- quote取得が安定
- spread/stale/tradable率が許容範囲
- 4h〜3dでコスト控除後の期待値が残る
- 短期スキャルなしで成立
- price referenceが保存できる
```

NO-GO条件:

```txt
- quote取得不能
- price reference不明
- holding/borrowing/rollover costを再現不能
- 4h〜3dで優位性なし
- 短期スキャルでしか期待値が出ない
```

## Non-functional Requirements

- Pythonは `uv` 前提
- raw dataを必ず保存し、後からparser変更で再処理できること
- pydanticでschemaを固定すること
- Parquet/DuckDBで再現性を持たせること
- SDK/API breaking changeに備えてsource payload hashを保存すること
- 売買注文は初期実装に含めないこと
