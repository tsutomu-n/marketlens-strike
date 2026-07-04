<!--
作成日: 2026-07-04_14:20 JST
更新日: 2026-07-04_14:20 JST
-->

# Pre Actual Cash Decision Gate

## 結論

actual cash を当分扱わない間のゴールは、利益証明ではなく、候補シグナルを
`KILL` / `REVISE_EVENT_DEFINITION` / `COLLECT_MORE_SOURCES` / `HOLD_FOR_FUTURE_ACTUAL_CASH`
に分類できる evidence line を作ること。

この gate は、実損益・口座履歴・約定履歴・cash ledger を使わない。したがって、ここを通っても
`READY_FOR_LIVE`、`READY_FOR_ACTUAL_CASH`、`PROFIT_PROVEN` とは読まない。

## Scope

扱うもの:

- public market event
- matured outcome
- source availability
- replay slice
- feature pack
- edge score
- tournament rows v2
- bias guard
- profit-readiness inventory / plan / run-local
- pre actual cash decision artifact

扱わないもの:

- actual cash ledger
- actual cash rows
- actual-cash report gate
- wallet / signing / exchange write
- live order
- tiny-live execution
- production live trading
- LLM/ML による売買判断

## 目標状態

最低到達点:

- 複数 event / outcome を同一 pipeline で処理できる。
- `event_id x source_type` の source availability matrix を出せる。
- missing source を 0 埋めせず、known gap として保持できる。
- `NO_TRADE` を含む同一 event set の比較を読める。
- `edge_score.selected_action` と `tournament_rows_v2.leader_action` を必ず確認する。
- bias guard が sample不足で止まる場合、その不足が decision に明示される。
- estimate / paper / actual cash を混同しない。
- 最終判断を4択に落とす。

actual cashなしでの現実的な完成度は 70-75% を上限目安にする。90% は actual cash、または
それに近い実約定 evidence なしでは狙わない。

## Inputs

### Required

- event records
- outcome records
- source availability artifacts
- feature pack artifacts
- edge score artifacts
- tournament rows v2 artifacts
- bias guard artifacts
- profit-readiness run manifest

### Recommended source types

- bars
- funding
- ticker
- trades
- book
- replay
- outcome

最初は public 5m candles only でもよい。ただし、その場合は `public_candle_only=true` 相当の制約を
known gap として残す。

## Output

推奨出力先:

```text
data/crypto_perp/pre_actual_cash_evidence_pack/latest/
```

推奨成果物:

```text
events_summary.json
outcomes_summary.json
source_availability_matrix.json
known_gaps_by_source.json
feature_pack_summary.json
edge_score_summary.json
tournament_rows_v2_summary.json
bias_guard_summary.json
decision.json
decision.md
```

## Decision values

### KILL

候補を捨てる。

代表条件:

- 複数eventで `NO_TRADE` に勝てない。
- `leader_action=NO_TRADE` が一貫している。
- `selected_action=UNKNOWN` が多い。
- source gaps が致命的で、estimate としても読めない。
- outcome定義が不安定で、比較対象として使えない。

### REVISE_EVENT_DEFINITION

event定義を作り直す。

代表条件:

- eventが広すぎて regime が混ざっている。
- eventが狭すぎて sample が増えない。
- outcome horizon が実際の仮説と合っていない。
- event/outcome pairing はできるが、edgeやtournamentの解釈が不安定。

### COLLECT_MORE_SOURCES

追加sourceを集める。

代表条件:

- barsだけでは cost-adjusted estimate が読めない。
- funding / trades / book / ticker / replay の不足が主要blocker。
- source availability が `can_compute_depth=false` や `can_compute_cost_adjusted_estimate=false` のまま。
- bias guard が sample不足だけで止まる。

### HOLD_FOR_FUTURE_ACTUAL_CASH

actual cash実装まで保留する。

代表条件:

- estimate上は候補が残る。
- `leader_beats_no_trade=true` が複数eventで確認できる。
- source gap は説明可能。
- ただし actual cash がないため、利益証明としては使えない。

## Minimum sample targets

| 段階 | event数 | 目的 |
| --- | ---: | --- |
| Smoke | 1 | CLI chain の疎通確認 |
| Thin pack | 10 | event/outcome/source matrix が複数件で壊れないか確認 |
| Useful pre-gate | 30 | `NO_TRADE` 比較とbias guardの入口 |
| Stronger pre-gate | 100 | regime / source gap / action別比較の初期評価 |

1 event の結果をもって、候補の優劣を判断しない。

## Required checks

必ず読む値:

```text
inventory.event_count
inventory.outcome_count
run_manifest.status
run_manifest.known_gap_count
source_availability.can_compute_cost_adjusted_estimate
source_availability.can_compute_actual_cash
source_availability.can_compute_depth
feature_pack.optional_feature_count
feature_pack.sets_entry_action
edge_score.selected_action
edge_score.known_gap_count
tournament_rows_v2.event_count
tournament_rows_v2.row_count
tournament_rows_v2.leader_action
tournament_rows_v2.leader_beats_no_trade
bias_guard.guard_status
bias_guard.pbo_status
```

`source_availability.can_compute_actual_cash=false` は、このgateでは許容する。ただし、
actual cash gateへ進んだとは読まない。

## CLI chain

現行CLIは `crypto-perp` 親コマンドではなく、flat command として使う。

代表コマンド:

```bash
uv run sis crypto-perp-profit-readiness-inventory
uv run sis crypto-perp-profit-readiness-plan --inventory path/to/inventory.json
uv run sis crypto-perp-profit-readiness-run-local --plan path/to/plan.json
uv run sis crypto-perp-source-availability --event path/to/event.json
uv run sis crypto-perp-feature-pack --event path/to/event.json --source-availability path/to/source_availability.json
uv run sis crypto-perp-edge-score --feature-pack path/to/feature_pack.json --source-availability path/to/source_availability.json
uv run sis crypto-perp-tournament-rows-v2 --help
uv run sis crypto-perp-bias-guard --help
```

具体引数は `--help` を正本にする。この文書のコマンド例は運用入口であり、CLI仕様の正本ではない。

## Non-goals

やらないこと:

- blocked run を complete と読む。
- public candle outcome を profit evidence と読む。
- before-cost proxy を cash result と読む。
- estimate を actual cash と読む。
- 1 event を十分な sample と読む。
- `NO_TRADE` leader を失敗扱いして、無理にaction candidateを選ぶ。
- source gaps を0埋めする。
- viewer / status / dogfood artifact を利益evidenceと読む。

## Acceptance

このgateのv1完了条件:

- 10件以上のevent/outcomeでpackを作れる。
- source availability matrix が生成される。
- known gaps がsource type別に集計される。
- `NO_TRADE` を含むaction比較が出る。
- bias guardのsample不足が、decision reason に反映される。
- `decision.json` と `decision.md` が生成される。
- decision が4択のどれかに落ちる。

v2に進む条件:

- 30件以上のevent/outcomeがある。
- `selected_action=UNKNOWN` 以外の候補が出る。
- `leader_beats_no_trade=true` の候補が複数eventで出る。
- source gap が説明可能、または次に集めるsourceが明確。

## Practical next step

次にやること:

1. 既存の1 event / 1 outcomeを smoke baseline として固定する。
2. 同じ形式で10 event / 10 outcomeを追加する。
3. source availability matrix と known gaps summary を作る。
4. `edge_score.selected_action` と `tournament_rows_v2.leader_action` を複数eventで読む。
5. decisionを `KILL` / `REVISE_EVENT_DEFINITION` / `COLLECT_MORE_SOURCES` / `HOLD_FOR_FUTURE_ACTUAL_CASH` のどれかに落とす。

この文書の目的は、actual cashなしの期間に、作業を「良さそうな候補探し」へ流さず、候補を安全に棄却・保留・再定義するための境界を固定すること。
