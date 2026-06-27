<!--
作成日: 2026-06-27_19:01 JST
更新日: 2026-06-27_19:01 JST
-->

# Crypto Perp Profit-Readiness Surface Inventory

## 既存 surface

| surface | current role | profit-readiness use |
|---|---|---|
| `crypto_perp_event.v1` | event snapshot and information cutoff | event id, cutoff, feature baseline, source refs |
| `crypto_perp_outcome.v1` | matured outcome and before-cost direction returns | before-cost proxy input only |
| `crypto_perp_tournament_rows_preview.v1` | matured outcome to 3action proxy rows | historical preview, not actual cash |
| `crypto_perp_tournament_report.v1` | same-event-set action comparison | actual-cash report when actual rows are supplied; otherwise carries proxy gaps |
| `crypto_perp_tournament_gate.v1` | local threshold gate | stop/continue classification, never live permission |
| `crypto_perp_truth_cycle_status.v1` | artifact chain status | operator next command, stop reasons, known gaps |
| `crypto_perp_live_measurement.v1` | mock tiny live measurement surface | not proof of real-network tiny live execution |
| `crypto_perp_cash_ledger.v1` | cash basis ledger | only source that can support `actual_cash_result_usd` when connected |

## 追加 surface

| surface | purpose | primary non-permission boundary |
|---|---|---|
| `crypto_perp_source_availability.v1` | eventごとの source 可用性と欠損をartifact化する | unavailable source is not zero-filled |
| `crypto_perp_replay_slice.v1` | event cutoff 以前の再生単位を記録する | future data is rejected |
| `crypto_perp_feature_pack.v1` | 最小feature packをaction決定から分離する | optional OFI/trade/depth features remain null when absent |
| `crypto_perp_edge_score.v1` | deterministic ruleで行動候補を比較する | ML/prediction claimではない |
| `crypto_perp_tournament_rows.v2` | fee/funding/slippage/operator cost込みのestimate rowsを作る | estimate fields are not actual cash |
| `crypto_perp_bias_guard.v1` | sample不足、lookahead、recursive warmup、concentrationを止める | `NOT_ESTIMABLE` is a valid result |
| `crypto_perp_tiny_live_shadow.v1` | tiny-live前の非発注shadow preflightを記録する | exchange write and live order are always false |

## 入口

- Current plan: [PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md](PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md)
- Vocabulary: [PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md)
- Runbook: [../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)
