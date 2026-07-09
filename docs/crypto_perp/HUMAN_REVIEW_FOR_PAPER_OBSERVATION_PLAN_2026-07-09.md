<!--
作成日: 2026-07-09_19:01 JST
更新日: 2026-07-09_22:02 JST
-->

# Human Review Plan For Crypto Perp Paper Observation Candidate

## 結論

`NO_CASH_BACKTEST_HOLD` は Paper Observation permission ではありません。この計画は、real-market no-cash backtest artifact を人間レビューへ渡すための確認項目を固定します。

## Review Inputs

- ticker-required sample: `data/crypto_perp/real_market_no_cash/ticker_required`
- backtest candidate pack: `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest`
- no-cash gate: `data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest`
- NO_TRADE kill report: `data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest`
- candidate leaderboard: `data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest`
- human review packet: `data/crypto_perp/real_market_no_cash/human_review_packet/latest`

## Current Evidence

- gate decision: `NO_CASH_BACKTEST_HOLD`
- blocker count: `0`
- event / outcome count: `30 / 30`
- ticker / funding coverage: `30 / 30`
- critical missing count: `0`
- future signal source count: `0`
- unknown count: `0`
- executed simulated trades: `13`
- PBO status: `ESTIMATED`
- rolling stability status: `complete`
- backtest total result: positive
- stress total result: positive
- `NO_TRADE` comparison: backtest and stress both `beats_no_trade=true`

## Non-Goals

- Do not start Paper Observation from this artifact alone.
- Do not create paper orders.
- Do not create actual cash rows or a cash ledger.
- Do not use wallet, signing, exchange write, or live order paths.
- Do not claim profit proof, actual cash readiness, tiny-live readiness, live readiness, or production order readiness.

## Known Gaps

- books source is missing.
- trades source is missing.
- replay source is missing.
- evidence remains local simulation only.
- actual cash is not in scope.
- live readiness is not in scope.
- recomputed minimal artifacts are present.

## Human Review Questions

1. Are the known gaps acceptable for a Paper Observation planning discussion?
2. Is the `NO_TRADE` comparison sufficient to justify planning observation, not execution?
3. Does the NO_TRADE kill report keep the candidate alive after cost, stress, and concentration checks?
4. Does the candidate leaderboard rank the active candidate as `HOLD_FOR_HUMAN_REVIEW` rather than kill/revise/collect more data?
5. Does the human review packet keep `paper_permission_granted=false`, `permits_paper_order=false`, `actual_cash_used=false`, and `profit_proven=false`?
6. Are drawdown and loss concentration acceptable for a no-cash candidate?
7. Are cost assumptions acceptable as no-cash simulation assumptions?
8. Is any additional source coverage required before planning Paper Observation?

## Required Outcome

Human review may produce a follow-up plan for Paper Observation. It must not grant paper order permission directly from this document.
