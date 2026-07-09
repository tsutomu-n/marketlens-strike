<!--
作成日: 2026-07-09_20:05 JST
更新日: 2026-07-09_20:05 JST
-->

# NO_TRADE Kill Report V1

## 結論

`crypto-perp-no-trade-kill-report` は、`NO_CASH_BACKTEST_HOLD` 候補を human review に渡す前に、`NO_TRADE`、after-cost、stress、集中リスクで fail-closed に落とす local review artifact です。

これは Paper Observation permission、paper order permission、profit proof、actual cash readiness、live readiness ではありません。

## CLI

```bash
uv run sis crypto-perp-no-trade-kill-report   --signal-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/signal_rows.jsonl   --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json   --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json   --tournament-rows data/crypto_perp/real_market_no_cash/ticker_required/aggregate/tournament_rows_v2.json   --out data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest
```

## Decisions

- `KILL_NO_TRADE_LEADER`
- `KILL_AFTER_COST_NEGATIVE`
- `KILL_STRESS_NEGATIVE`
- `KILL_LOSS_CONCENTRATION`
- `REVISE_SOURCE_OR_SIGNAL`
- `COLLECT_MORE_DATA`
- `HOLD_FOR_LEADERBOARD`

`HOLD_FOR_LEADERBOARD` は Paper permission ではありません。次に candidate leaderboard と human review に渡すだけです。

## Boundary

The artifact always keeps:

```text
paper_permission_granted=false
permits_paper_order=false
permits_live_order=false
actual_cash_used=false
profit_proven=false
wallet_used=false
signing_used=false
exchange_write_used=false
live_order_submitted=false
```
