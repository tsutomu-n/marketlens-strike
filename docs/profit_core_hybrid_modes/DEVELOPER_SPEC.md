<!--
作成日: 2026-06-29_22:07 JST
更新日: 2026-06-29_22:07 JST
-->

# Developer Spec

## 結論

実装方針は **同じ Core を 2 mode で動かす** こと。

```text
verification_throughput = default
risk_taker_sprint       = isolated attack mode
```

mode は gate を飛ばすためではなく、探索幅、candidate cap、threshold policy、report label、昇格条件を切り替えるために使う。

## Core / Core補助 / Add-on

| 分類 | 含めるもの | 判断 |
|---|---|---|
| Core | Edge Candidate Factory、Multiplicity / Search Accounting、Candidate-to-Backtest Bridge、Backtest Kill Gate、Thin Virtual Execution Gate、Risk-Taker Review、Actual Cash Report Gate | 利益追求の主導線 |
| Core補助 | Strategy Authoring minimal path、C9 bridge、candidate-scoped backtest pack、manual AI packet / import | Core の検証 throughput を上げる時だけ使う |
| Add-on | NDX / QQQ standalone、Trade[XYZ]、generic Strategy Lab、optional backtest frameworks、Workbench Viewer full UI、full ops/audit/remediation、broad AI narrative support | 今回の主導線から外す |

C9 bridge は重要だが、C9 固有名を Core 本体へ固定しない。Core 本体は `Candidate-to-Backtest Bridge`。C9 はその v0 実装候補。

## Mode Contract

| field | `verification_throughput` | `risk_taker_sprint` |
|---|---|---|
| intent | 再現性と検証 throughput を上げる | 小口・高リスク向けに探索幅を広げる |
| candidate cap | 250-1000 目安 | 5000-50000 目安 |
| generator | classical + limited grammar | classical + grammar + limited random / light GA |
| ML | off | ranking / no-trade filter まで |
| thresholds | conservative, family-specific | looser discovery threshold, strict promotion threshold |
| sealed holdout | required | required |
| success-only report | prohibited | prohibited |
| actual cash direct promotion | prohibited | prohibited |
| output label | `CORE_VALIDATION` | `SPECULATIVE_SPRINT` |

`risk_taker_sprint` は本命集計に混ぜない。sprint candidate は再検証なしに actual cash へ進めない。

## Artifact Draft

### `candidate_protocol_manifest.v1`

必須 field:

```text
schema_version
protocol_id
mode
created_at
target_market
target_venue_family
families
parameter_spaces
objective
exclusion_rules
sealed_holdout_definition
family_event_count_policy
source_requirements
venue_execution_constraints
llm_policy
permits_actual_cash=false
permits_live_order=false
```

役割は、候補生成前に探索空間と禁止事項を固定すること。あとから良い結果を見て探索条件を変える p-hacking を抑える。

### `trial_multiplicity_account.v1`

必須 field:

```text
schema_version
account_id
mode
candidate_count_total
candidate_count_shortlisted
family_count
family_trial_count
parameter_grid_hashes
effective_trial_count
correlation_cluster_count
validation_peek_count
rerank_count
sealed_test_used_for_selection=false
success_only_reporting=false
raw_p_value_count
fdr_status
pbo_status
dsr_status
white_reality_check_status
not_estimable_reasons
```

`PBO`、`DSR`、`White Reality Check` は入力がないなら `NOT_ESTIMABLE` を正式結果にする。空欄や success 表示で埋めない。

### `backtest_kill_gate.v1`

出力 state:

```text
KILL
INCONCLUSIVE_DATA
RESEARCH_ONLY
SHORTLIST_FOR_VIRTUAL
```

主な判定軸:

```text
event_count
closed_trade_count
after_cost_edge_over_no_trade
stress_edge_over_no_trade
largest_loss_usd
profit_concentration
regime_stability
source_gap_count
unexecutable_reason_count
selection_adjustment_status
```

この gate は攻める許可ではない。大量に殺す装置。

### `virtual_execution_gate.v1`

初期版は local/mock lifecycle でよい。外部 venue API は後続。

必須 false:

```text
actual_cash=false
cash_metric_basis=virtual_exchange
production_exchange_write_used=false
live_order_submitted=false
permits_live_order=false
```

見たいもの:

```text
order accepted
partial fill handled
cancel handled
reject reason captured
position reconciled
reduce-only close works
fee/funding-like fields captured
duplicate order prevented
flat reconciliation pass
```

## Bridge Status Vocabulary

`BRIDGED` だけでは弱い。少なくとも次へ分ける。

```text
BRIDGED_TECHNICAL_ONLY
BLOCKED_UNSUPPORTED_FAMILY
BLOCKED_MISSING_SOURCE
BLOCKED_BACKTEST_PACK
BLOCKED_ECONOMIC_GATE
BLOCKED_MULTIPLICITY_ACCOUNT
```

`BRIDGED_TECHNICAL_ONLY` は候補別 spec / suite / pack が生成できたという意味に限定する。alpha、profit、paper、live の proof ではない。

## Mode Promotion Rule

```text
risk_taker_sprint
  -> KILL | RESEARCH_ONLY | SHORTLIST_FOR_VIRTUAL
  -> virtual_execution_gate
  -> risk_taker_review
  -> re-register under verification_throughput
  -> actual_cash_report_gate
```

攻撃モード候補は、本命 mode に再登録してからでなければ actual cash へ進めない。

## LLM Boundary

LLM は `ADVERSARIAL_FINDING` を作るだけ。

許可:

- missing artifact 検出。
- 矛盾検出。
- overclaim 検出。
- `NO_TRADE` 比較漏れ検出。
- operator burden 指摘。

禁止:

- PnL 計算。
- official metric 決定。
- actual_cash 判定。
- gate override。
- paper / live / tiny-live 許可。
- 良い戦略の選定。

machine-checkable な欠落だけを hard blocker にする。LLM の「怪しい」は human review input であり、自動 KILL ではない。

## Must Not Break

- `actual_cash` と proxy / estimate / virtual を混ぜない。
- `NO_TRADE` を失敗扱いしない。
- `BRIDGED_TECHNICAL_ONLY` を合格扱いしない。
- `risk_taker_sprint` を本命成績に混ぜない。
- validation を見て直した候補を同じ sealed holdout で再評価しない。
- external venue docs を legal clearance と読まない。
- Workbench / viewer / AI narrative を Core の代わりにしない。
