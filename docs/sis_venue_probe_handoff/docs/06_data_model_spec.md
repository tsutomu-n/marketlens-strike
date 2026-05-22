# 06. Data Model Spec

## InstrumentSpec

```json
{
  "venue": "gtrade",
  "canonical_symbol": "QQQ",
  "venue_symbol": "QQQ/USD",
  "pair_index": 87,
  "asset_class": "index",
  "chain": "arbitrum",
  "collateral": "requires_live_probe",
  "api_readable": true,
  "api_orderable": true,
  "execution_price_ref": "mark",
  "liquidation_price_ref": "index",
  "active": true,
  "notes": []
}
```

## QuoteLog v1

```json
{
  "ts_client": "2026-05-21T12:00:00.000+09:00",
  "venue": "gtrade",
  "chain": "arbitrum",
  "canonical_symbol": "QQQ",
  "venue_symbol": "QQQ/USD",
  "pair_index": 87,
  "price_ref_type": "mark_index",
  "mark_price": 523.41,
  "index_price": 523.41,
  "oracle_price": null,
  "bid_price": null,
  "ask_price": null,
  "mid_price": null,
  "exec_buy_price": 523.41,
  "exec_sell_price": 523.41,
  "spread_bps": 1.2,
  "oracle_ts_ms": 1779322800000,
  "market_status": "open",
  "is_tradable": true,
  "source": "gtrade_sidecar_v1",
  "raw_payload_sha256": "...",
  "raw_payload_ref": "data/raw/..."
}
```

## CostSnapshot

```json
{
  "venue": "gtrade",
  "canonical_symbol": "XAU",
  "open_fee_bps": 5,
  "close_fee_bps": 5,
  "fixed_spread_bps": 1,
  "spread_p50_bps": null,
  "spread_p90_bps": null,
  "holding_cost_4h_bps": null,
  "holding_cost_24h_bps": null,
  "holding_cost_72h_bps": null,
  "stale_rate": null,
  "tradable_rate": null
}
```

## GoNoGoResult

```json
{
  "decision": "CONDITIONAL_GO",
  "reasons": [
    "gTrade quote logger stable",
    "Ostium symbol unresolved"
  ],
  "blocked_by": [],
  "next_actions": [
    "Run Ostium symbol probe",
    "Collect 48h quote logs"
  ]
}
```
