<!--
作成日: 2026-07-09_20:05 JST
更新日: 2026-07-09_20:05 JST
-->

# Candidate Leaderboard V1

## 結論

`crypto-perp-candidate-leaderboard` は、no-cash HOLD 候補を human review 用に順位付けする local artifact です。現行 v1 は 1 active candidate を `rows[0]` に出し、将来の複数候補比較へ拡張できる形にしています。

これは Paper Observation permission、paper order permission、profit proof、actual cash readiness、live readiness ではありません。

## CLI

```bash
uv run sis crypto-perp-candidate-leaderboard   --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json   --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json   --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json   --kill-report data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json   --gate data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json   --signal-rows data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/signal_rows.jsonl   --out data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest
```

## Next Actions

- `KILL`
- `REVISE_SIGNAL`
- `COLLECT_MORE_DATA`
- `HOLD_FOR_HUMAN_REVIEW`

`HOLD_FOR_HUMAN_REVIEW` は Paper permission ではありません。人間レビューで Paper Observation 計画へ進めるかを判断するための入力です。

## Ranking Policy

- kill decision が kill の候補は上位にしない。
- source quality と edge は別軸で表示する。
- stress negative、弱い NO_TRADE delta、高い concentration、少ない executed trade count は penalty として扱う。
- books / trades / replay missing は known gap として残す。
