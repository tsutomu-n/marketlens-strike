# Artifact Examples

実装や検証で出てくる成果物の形です。すべて説明用の例であり、実データではありません。

## 1. Signal CSV

```csv
ts_signal,canonical_symbol,side,timeframe,signal_strength
2026-01-01T00:00:00+00:00,QQQ,long,4h,0.42
2026-01-02T04:00:00+00:00,QQQ,long,4h,0.31
```

必要条件:

- `ts_signal` はdecision時点で既知。
- `canonical_symbol` はrepo内標準名。
- `side` はlong/shortへ正規化可能。
- `timeframe` はrisk policyで許可される。

## 2. Feature Frame

| ts | canonical_symbol | close | sma_20 | sma_50 | sma_50_slope | regime | data_status | trade_allowed | is_event_blackout |
|---|---|---:|---:|---:|---:|---|---|---|---|
| 2026-01-01T00:00:00Z | QQQ | 100.0 | 99.2 | 96.0 | 0.12 | trend | valid | true | false |

注意:

- `regime` は方向予測ではなく稼働条件。
- `data_status != valid` は原則signalを出さない。
- rolling指標は未来を見ていないことを小データで検査する。

## 3. Normalized Quote

| ts_client | venue | canonical_symbol | mark_price | exec_buy_price | exec_sell_price | spread_bps | oracle_ts_ms | market_status | is_tradable |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| 2026-01-01T00:01:00Z | trade_xyz | QQQ | 100.1 | 100.2 | 100.0 | 2.0 | 1767225660000 | open | true |

最低限見る点:

- `oracle_ts_ms` が欠落していない。
- `market_status == open`。
- `is_tradable == true`。
- entry/exitに使う価格列がある。

## 4. Decision Log JSONL

```jsonl
{"context":{"decision_ts":"2026-01-01T00:00:00Z","venue":"trade_xyz","canonical_symbol":"QQQ","timeframe":"4h","quote_ts":"2026-01-01T00:01:00Z","signal_side":"long","signal_strength":0.42,"strategy_name":"trend_pullback","market_status":"open","is_tradable":true},"strategy_decision":{"strategy_name":"trend_pullback","should_enter":true,"side":"long","timeframe":"4h","reason":"trend_pullback_resume","score":0.42},"risk_decision":{"allowed":true,"blocked_reasons":[]},"execution_plan":{"action":"enter_long","venue":"trade_xyz","canonical_symbol":"QQQ","timeframe":"4h","price_reference":"mark_or_exec","notes":["trend_pullback_resume"]}}
```

レビュー観点:

- `context` と `strategy_decision` が分かれている。
- `risk_decision.blocked_reasons` が空か、説明可能。
- `execution_plan.action` が `enter_*` か `skip` か明確。

## 5. Paper Output

| artifact | 見ること |
|---|---|
| `data/paper/orders.parquet` | 注文意図が出たか |
| `data/paper/fills.parquet` | 仮想約定価格と手数料 |
| `data/paper/positions.parquet` | position state |
| `data/paper/daily_pnl.parquet` | 日次損益 |
| `data/reports/daily_paper_report.md` | 人間が読むreport |

fillが0でも失敗とは限らない。riskで落ちたのか、quote lookupで落ちたのか、price missingなのかを見る。

## 6. Scorecard Row

| metric | baseline | candidate | required | result |
|---|---:|---:|---:|---|
| net return | 0.03 | 0.04 | better after costs | pending |
| max drawdown | -0.12 | -0.08 | lower | pending |
| trade count | 120 | 80 | enough | pending |
| slippage x2 | 0.01 | 0.02 | positive | pending |
| rejected reasons | - | stale=4, halt=2 | explainable | pending |
