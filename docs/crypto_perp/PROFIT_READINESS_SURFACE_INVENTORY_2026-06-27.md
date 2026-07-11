<!--
作成日: 2026-06-27_19:01 JST
更新日: 2026-07-11_18:35 JST
-->

# Crypto Perp Profit-Readiness Surface Inventory

## 現行判定チェーン

新規Human Review Packetは`input_contract_version=crypto_perp_human_review_packet_inputs.v2`を持ち、selection manifestからleaderboardまで固定12入力を個別schema、raw SHA、event/outcome pair、execution window、decision chain、nested boundaryで検査します。旧v1はinput contract fieldがない場合だけreader互換です。

現在はguard `BLOCKED`、PBO `NOT_ESTIMABLE`、candidate/gate REJECT、kill/leaderboard KILL、packet `BLOCKED_BY_BIAS_GUARD`です。名目14 trades / 10 winsでも、position overlap、5 episodes、single-position負、always-long未達により進めません。

## 既存 surface

| surface | current role | profit-readiness use |
|---|---|---|
| `crypto_perp_event.v1` | event snapshot and information cutoff | event id, cutoff, feature baseline, source refs |
| `crypto_perp_outcome.v1` | matured outcome and before-cost direction returns | before-cost proxy input only |
| `crypto_perp_tournament_rows_preview.v1` | matured outcome to 3action proxy rows with `cash_metric_basis=before_cost_proxy` | historical preview, not actual cash |
| `crypto_perp_tournament_report.v1` | same-event-set action comparison with explicit cash basis summary | actual-cash report when actual rows are supplied; non-actual or mixed basis is not profit proof |
| `crypto_perp_tournament_gate.v1` | local threshold gate | blocks `actual_cash=false` or `cash_metric_basis != actual_cash` as `NEEDS_ACTUAL_CASH`; never live permission |
| `crypto_perp_truth_cycle_status.v1` | artifact chain status | operator next command, stop reasons, known gaps |
| `crypto_perp_live_measurement.v1` | mock tiny live measurement surface | not proof of real-network tiny live execution |
| `crypto_perp_cash_ledger.v1` | cash basis ledger | only source that can support `actual_cash_result_usd` when connected |

## 追加 surface

| surface | purpose | primary non-permission boundary |
|---|---|---|
| `crypto-perp-event-record` | validated public candle CSVから `market_window_v1` eventを作る | market window is not detector trigger, alpha proof, actual cash, or live permission |
| `crypto_perp_profit_readiness_inventory.v1` | profit-readiness入力ディレクトリの既知/未知 artifact と不足を棚卸しする | inventory readiness is not profit proof |
| `crypto_perp_profit_readiness_plan.v1` | 1 event/outcome local run の次コマンドを記録する | runnable command is not actual cash readiness or live permission |
| `crypto_perp_source_availability.v1` | eventごとの source 可用性と欠損をartifact化する | unavailable source is not zero-filled |
| `crypto_perp_replay_slice.v1` | event cutoff 以前の再生単位を記録する | future data is rejected |
| `crypto_perp_feature_pack.v1` | 最小feature packをaction決定から分離する | optional OFI/trade/depth features remain null when absent |
| `crypto_perp_edge_score.v1` | deterministic ruleで行動候補を比較する | ML/prediction claimではない |
| `crypto_perp_tournament_rows.v2` | fee/funding/slippage/operator cost込みのestimate rowsを作る | estimate fields are not actual cash |
| `crypto_perp_bias_guard.v1` | exact event/action set、pack-local rows SHA、lookahead、recursive warmup、sample/PBO入力条件を検査する | `INPUT_THRESHOLD_MET`はPBO計算済みではない。進行には`COMPUTED_PASS`が必要 |
| `crypto_perp_profit_readiness_run.v1` | 1 event/outcome の local run manifest と known gaps を記録する | run manifest status is not profit proof or actual cash readiness |
| `crypto_perp_pre_actual_cash_decision.v1` | 複数event/outcomeのpre-actual-cash evidenceを4択decisionへ集約する | decision is not profit proof, actual cash readiness, or live permission |
| `crypto_perp_backtest_candidate_pack.v1` | `ts+5m`可用時刻、next-bar open、cost identity、pack-local rows/guard、profit robustnessを4択BACKTEST decisionへ集約する | position overlap未考慮、PBO未計算の正値はprofit proofではない |
| `crypto_perp_no_cash_backtest_gate.v1` | candidateとbias/PBO/rolling/source statusを独立再検査するpositive-whitelist gate | 未知status、PBO未計算、blocker残存時はHOLDしない |
| `crypto_perp_no_trade_kill_report.v1` | 必須gate入力を取り込み、NO_TRADE/cost/stress/集中評価へ停止理由を伝播する | gateがHOLD以外ならhuman-review HOLDへ進めない |
| `crypto_perp_candidate_leaderboard.v1` | gateとkill reportを再検査して候補の次actionを固定する | gate/killの矛盾をHOLDへ昇格しない |
| `crypto_perp_human_review_packet.v1` | strict v2 12入力のschema/lineage、boundary、candidate/gate/kill/leaderboard、bias/PBOをfail-closedで集約する | `BLOCKED_BY_BIAS_GUARD`も`BLOCKED_BY_PBO`もPaper Observation permissionではない |
| `crypto_perp_tiny_live_shadow.v1` | tiny-live前の非発注shadow preflightを記録する | exchange write and live order are always false |

## 入口

- Vocabulary: [PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md)
- Backtest Candidate Pack v1: [BACKTEST_CANDIDATE_PACK_V1.md](BACKTEST_CANDIDATE_PACK_V1.md)
- No-cash progress split: [../NO_CASH_GOAL_PROGRESS_2026-07-05.md](../NO_CASH_GOAL_PROGRESS_2026-07-05.md)
- Runbook: [../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)
- Historical pre-actual-cash gate and dogfood snapshots: [../archive/2026-07-05-docs-code-truth-cleanup/crypto_perp/](../archive/2026-07-05-docs-code-truth-cleanup/crypto_perp/)
- Historical plans: [../archive/2026-06-28-merged-plans/PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md](../archive/2026-06-28-merged-plans/PROFIT_READINESS_EVIDENCE_PLAN_2026-06-27.md), [../archive/2026-06-28-merged-plans/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md](../archive/2026-06-28-merged-plans/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md)
