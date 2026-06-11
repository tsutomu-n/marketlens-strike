<!--
作成日: 2026-06-11_21:34 JST
更新日: 2026-06-11_21:34 JST
-->

# Live Canary Plan Gate

## 結論

`ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live 実装の許可ではありません。別計画として live canary の仕様検討を始めてよい、という計画 gate です。

## Required Separation

Strategy Lifecycle が扱うもの:

- backtest acceptance artifact
- paper observation review artifact
- phase gate summary
- execution blocker count
- boundary violation detection

Strategy Lifecycle が扱わないもの:

- live order submit
- wallet / signing
- exchange write
- credentials
- production account enablement
- external API execution

## Invariant

`strategy-lifecycle-review` は、どの decision でも次を維持します。

- `permits_live_order=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `venue_write_used=false`
- `exchange_write_used=false`

## Next Plan Requirements

live canary を本当に実装する場合は、この計画とは別に少なくとも次を定義します。

- credential handling
- wallet / signing boundary
- exchange write permission
- venue-specific account boundary
- canary notional and frequency limits
- kill switch
- rollback
- operator approval
- post-trade reconciliation

