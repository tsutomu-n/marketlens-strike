# 10. Risk / Halt Policy

## 基本方針

短期スキャルピングは禁止する。

```txt
禁止: 1s, 5s, 15s, 1m, 5m
最低許容: 30m
推奨: 4h, 1d, 3d
```

## BLOCK reasons

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

## Scalping policy

```yaml
scalping_policy:
  default: prohibited
  prohibited_timeframes:
    - "1s"
    - "5s"
    - "15s"
    - "1m"
    - "5m"
  minimum_allowed_timeframe: "30m"
  preferred_timeframes:
    - "4h"
    - "1d"
    - "3d"
```

## Halt policy初期値

```yaml
halt_policy:
  stale_price:
    gtrade_max_age_ms: 3000
    ostium_max_age_ms: 5000
  session:
    block_before_close_minutes: 30
    block_after_open_minutes: 15
  events:
    major_usd_event:
      before_minutes: 60
      after_minutes: 15
  spread:
    max_spread_p90_bps:
      SPY: 8
      QQQ: 10
      XAU: 12
```

## gTrade固有

```txt
- indices closed中はopen/close/edit不可
- mark priceは実行/PnL
- index priceは清算
- market close前はspread拡大/レバ制限を考慮
```

## Ostium固有

```txt
- RWA oracle metadataを保存
- bid/askまたはprice-after-impactを実行価格として扱う
- liquidation referenceはprobeで確定
- dynamic spread対象か確認
```
