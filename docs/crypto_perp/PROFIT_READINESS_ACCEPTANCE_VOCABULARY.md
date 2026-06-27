<!--
作成日: 2026-06-27_19:01 JST
更新日: 2026-06-28_07:07 JST
-->

# Crypto Perp Profit-Readiness Acceptance Vocabulary

## 評価値

| term | use when | do not use when |
|---|---|---|
| `actual_cash_result_usd` | 実fill・実fee・実funding・cash ledger または live measurement artifact に接続している | outcome preview、replay、simulation、operator estimateだけの場合 |
| `before_cost_proxy_usd` | matured outcome の return を notional に掛けただけの比較値 | fee/funding/slippage/operator cost込みの値として読む場合 |
| `cost_adjusted_cash_estimate_usd` | fee/funding/slippage/operator time を明示的に控除した local estimate | 実現損益やfuture profit proofとして読む場合 |
| `stress_cash_estimate_usd` | cost-adjusted estimate に追加摩擦を入れた保守値 | live permission、注文許可、利益保証として読む場合 |
| `evidence_level` | row が `before_cost_proxy` / `cost_adjusted_estimate` / `actual_cash` のどれかを明示する | primary metric の代替として曖昧に使う場合 |
| `cash_metric_basis` | tournament row / report の cash 数値が `actual_cash`、`before_cost_proxy`、`cost_adjusted_estimate`、`mixed` のどれかを示す | `actual_cash_result_usd` という field 名だけで実cashと判断する場合 |

## action

| action | meaning |
|---|---|
| `REVERSAL_SHORT` | event後の反落short候補。固定方針ではない。 |
| `CONTINUATION_LONG` | event後の継続long候補。固定方針ではない。 |
| `NO_TRADE` | 見送り。失敗ではなく、同じevent setで比較する正式action。 |
| `UNKNOWN` | source不足、推定不能、または判定しない状態。trade actionではない。 |

## source / guard

| term | meaning |
|---|---|
| `known_gaps` | 欠損sourceや制約を下流へ伝播させる一覧。0埋めの代替ではない。 |
| `source_availability` | eventごとに何が計算可能かを source refs と row counts で示す artifact。 |
| `pbo_status=NOT_ESTIMABLE` | event数やfoldが不足して PBO を推定しない正式結果。 |
| `bias_guard_status=BLOCKED` | lookahead、recursive warmup、sample不足、stress lossなどで次段階へ進めない状態。 |
| `tiny_live_shadow` | 実発注しない preflight artifact。`exchange_write_used=false`、`live_order_submitted=false`、`permits_live_order=false` が必須。 |

## preview rows guard

`crypto_perp_tournament_rows_preview.v1` は display / dogfood 用の before-cost proxy です。`actual_cash_result_usd` report の入力ではありません。

- `crypto-perp-tournament-report --rows tournament_rows_preview.json` は `PREVIEW_ROWS_NOT_ACTUAL_CASH` で失敗する。
- `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` を持つ rows は actual cash evidence として扱わない。
- `cash_metric_basis != actual_cash` の rows は `crypto-perp-tournament-report` の CLI input として拒否する。
- `crypto_perp_tournament_report.v1` は `primary_metric_display_name`、`cash_metric_basis`、`actual_cash`、`leader_cash_metric_value_usd` を出し、`leader_actual_cash_result_usd` は actual cash basis の時だけ値を持つ。
- outcome 由来の estimate / cost-aware 比較は `crypto-perp-tournament-rows-v2` を使い、actual cash が無い row の `actual_cash_result_usd` は `null` と読む。
