<!--
作成日: 2026-06-27_19:01 JST
更新日: 2026-07-11_18:35 JST
-->

# Crypto Perp Profit-Readiness Acceptance Vocabulary

## 2026-07-11現行契約

現在は`fold_count=0`、`pbo_status=NOT_ESTIMABLE`、guard `BLOCKED`です。candidate/gateはREJECT、kill report/leaderboardはKILL、packetは`BLOCKED_BY_BIAS_GUARD`です。

`INPUT_THRESHOLD_MET`や`COMPUTED_PASS`というstatus文字列だけではPBO合格になりません。専用PBO計算artifactとlineageを検証するproducerがないため、現packetは`pbo_evidence_verified=false`です。

30 events / 14 trades / 10 winsの名目正値は仮説継続材料ですが、peak6、episodes5、single-position負、episode bootstrapが0を跨ぐためprofit proofまたはPaper permissionではありません。

## 評価値

| term | use when | do not use when |
|---|---|---|
| `cash_metric_value_usd` | tournament row / score の正の比較値。basis は `cash_metric_basis` で読む | field 名だけで actual cash と判断する場合 |
| `actual_cash_result_usd` | `cash_metric_basis=actual_cash` の時だけ値を持つ legacy alias。実fill・実fee・実funding・cash ledger または live measurement artifact に接続している | outcome preview、replay、simulation、operator estimateだけの場合。non-actual basis では `null` と読む |
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
| `pbo_status=NOT_ESTIMABLE` | event数やfoldが不足し、PBO入力条件も満たさない正式結果。後段へ進めない。 |
| `pbo_status=INPUT_THRESHOLD_MET` | event数/fold数の入力閾値を満たしただけ。PBOは未計算で、後段へ進めない。legacy `ESTIMATED`も計算済み扱いにしない。 |
| `pbo_status=COMPUTED_PASS` | 実際のPBO計算が合格した状態。後段進行を許せる唯一のPBO statusだが、現production builderは生成しない。 |
| `packet_decision=BLOCKED_BY_BIAS_GUARD` | guardがPASS以外なので、PBOより先にHuman Review Planningを停止した状態。 |
| `packet_decision=BLOCKED_BY_PBO` | guard通過後もPBO専用証跡が検証できず停止した状態。status文字列だけでは解除しない。 |
| `position_overlap_accounted=false` | 同時保有と資本拘束をaggregate損益に織り込んでいない。positive totalを収益性の証明に使わない。 |
| `INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET` | nominal event数ではなく、重複しないmarket episode数が最低条件未満。現在は5 < 10なのでCOLLECT。 |
| `SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION` | 選択器の損益が同一標本の最良static actionを下回る。現在はselector `+3.042366...`に対しalways-long `+5.816219...`。 |
| `bias_guard_status=BLOCKED` | lookahead、recursive warmup、sample不足、stress lossなどで次段階へ進めない状態。 |
| `tiny_live_shadow` | 実発注しない preflight artifact。`exchange_write_used=false`、`live_order_submitted=false`、`permits_live_order=false` が必須。 |

## preview rows guard

`crypto_perp_tournament_rows_preview.v1` は display / dogfood 用の before-cost proxy です。`cash_metric_value_usd` に proxy 値を持ち、`actual_cash_result_usd` は `null` です。actual cash report の入力ではありません。

- `crypto-perp-tournament-report --rows tournament_rows_preview.json` は `PREVIEW_ROWS_NOT_ACTUAL_CASH` で失敗する。
- `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` を持つ rows は actual cash evidence として扱わない。
- `cash_metric_basis != actual_cash` の rows は `crypto-perp-tournament-report` の CLI input として拒否する。
- `crypto_perp_tournament_report.v1` は `primary_metric_display_name`、`cash_metric_basis`、`actual_cash`、`leader_cash_metric_value_usd` を出し、`actual_cash_result_usd` / `leader_actual_cash_result_usd` は actual cash basis の時だけ値を持つ。
- outcome 由来の estimate / cost-aware 比較は `crypto-perp-tournament-rows-v2` を使い、actual cash が無い row の `actual_cash_result_usd` は `null` と読む。
