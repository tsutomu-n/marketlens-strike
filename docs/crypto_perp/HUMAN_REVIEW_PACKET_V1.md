<!--
作成日: 2026-07-09_22:02 JST
更新日: 2026-07-09_22:02 JST
-->

# Crypto Perp Human Review Packet v1

## 結論

`crypto-perp-human-review-packet` は、`NO_CASH_BACKTEST_HOLD` 候補を Paper Observation 計画の人間レビューへ渡すための local artifact です。

この artifact は Paper Observation permission、paper order permission、profit proof、actual cash readiness、wallet / signing readiness、exchange write readiness、live readiness を出しません。

## Inputs

- ticker-required sample: `data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json`
- candidate decision: `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json`
- backtest result: `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json`
- stress result: `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json`
- no-cash gate: `data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json`
- NO_TRADE kill report: `data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json`
- candidate leaderboard: `data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest/candidate_leaderboard.json`

## Command

```bash
uv run sis crypto-perp-human-review-packet
```

明示する場合:

```bash
uv run sis crypto-perp-human-review-packet \
  --selection-manifest data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json \
  --decision data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json \
  --backtest data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/stress_result.json \
  --gate data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json \
  --kill-report data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json \
  --leaderboard data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest/candidate_leaderboard.json \
  --out data/crypto_perp/real_market_no_cash/human_review_packet/latest
```

## Decisions

- `READY_FOR_HUMAN_REVIEW_PLANNING`: gate / kill report / leaderboard が人間レビュー計画へ渡せる形で揃っている。
- `BLOCKED_BY_GATE`: no-cash gate が `NO_CASH_BACKTEST_HOLD` ではない。
- `BLOCKED_BY_KILL_REPORT`: NO_TRADE kill report が `HOLD_FOR_LEADERBOARD` ではない。
- `BLOCKED_BY_LEADERBOARD`: leaderboard top action が `HOLD_FOR_HUMAN_REVIEW` ではない。
- `BLOCKED_BY_BOUNDARY_VIOLATION`: 入力 artifact に paper / actual cash / live 系の true flag が混ざっている。

## Boundary

`READY_FOR_HUMAN_REVIEW_PLANNING` でも、次は人間レビューであり Paper Observation 開始ではありません。books / trades / replay missing、local simulation only、not actual cash、not live readiness は known gaps として残ります。
