<!--
作成日: 2026-07-02_00:00 JST
更新日: 2026-07-02_19:40 JST
-->

# Artifact Contracts: Profit Core Smart Priors

## 結論

新Coreは、候補生成の賢さを `signal_expression` だけに閉じ込めない。候補ごとに、cause prior、mechanism、required sources、execution feasibility、kill conditions、information gain、multiplicity account、virtual execution boundary をartifactとして保存する。

この文書は、新規schemaと必須fieldを定義する。コーダーはこの契約に従ってPydantic model、JSON Schema、writer、testsを実装する。

## 共通boundary

すべての新artifactに、既存repoの安全検出語彙を含むboundaryを持たせる。新語彙だけに寄せない。

```json
{
  "paper_execution_allowed": false,
  "live_allowed": false,
  "permits_live_order": false,
  "live_conversion_allowed": false,
  "wallet_used": false,
  "signing_used": false,
  "exchange_write_used": false,
  "production_exchange_write_allowed": false,
  "production_exchange_write_used": false,
  "live_order_submitted": false,
  "auto_promote": false
}
```

`wallet_allowed` / `signing_allowed` のような許可語彙を追加する場合でも、既存の `wallet_used` / `signing_used` / `exchange_write_used` / `permits_live_order` を省略しない。

Virtual系artifactだけは demo / testnet opt-in 時に `exchange_write_used=true` を持ってよい。ただし、必ず環境を分け、production writeやactual cashへ昇格しない。

```json
{
  "execution_environment": "fixture_or_demo_or_testnet",
  "exchange_write_used": true,
  "production_exchange_write_used": false,
  "actual_cash": false,
  "cash_metric_basis": "virtual_exchange",
  "permits_live_order": false
}
```

## Cause Prior Taxonomy

`SmartCandidateCard.cause_priors` は次のallowlistに限定する。

| cause_prior | 意味 | 主な観測対象 | 初期扱い |
|---|---|---|---|
| `FORCED_FLOW` | 誰かが清算、証拠金、stop、funding負担などで不利に動かされる | liquidation, stop cascade, funding pressure | Core |
| `INVENTORY_RISK_TRANSFER` | market maker、LP、裁定業者が在庫やriskを減らす | inventory skew, LP adverse selection, AMM LVR | Phase 2 |
| `SLOW_INFORMATION` | 情報が遅れて反映される | CEX-DEX lag, oracle lag, on-chain flow | Phase 2 |
| `CONSTRAINED_ARBITRAGE` | 裁定が制約で即時に消えない | basis, deposit/withdraw halt, borrow constraint | Core |
| `CROWDED_POSITIONING` | 参加者が同じ側に偏る | funding, OI, liquidation risk, long/short skew | Core |
| `BEHAVIORAL_ATTENTION` | 注意、感情、ナラティブ、retail flowが価格を歪める | sentiment, volume shock, social attention | Phase 3 |
| `ADVERSE_SELECTION` | 古い価格や薄い板が情報優位者に抜かれる | OFI, spread, book depth, quote age | Core filter / Phase 2 signal |
| `EXECUTION_FRICTION` | 手数料、funding、spread、lot、API、latencyで候補が死ぬ | fee, spread, min notional, rate limit | Core |
| `DATA_OBSERVABILITY` | source品質、available-at、timestampで検証不能になる | source hash, missing data, stale quote | Core |

## Observable Allowlist

観測対象は自由文字列にしない。v0は次に限定する。

```text
funding_rate
funding_window
liquidation_notional
liquidation_side
mark_price
index_price
mark_index_basis_bps
spot_perp_basis_bps
open_interest
open_interest_change
spread_bps
bid_price
ask_price
book_depth
order_flow_imbalance
aggressive_trade_imbalance
volume
turnover
realized_volatility
volatility_compression
session_time
weekday
quote_age
fee_rate
min_notional
tick_size
lot_size
source_quality
available_at
```

v0でon-chain、sentiment、options gamma、ETF flow、token unlockを入れたい場合は、allowlistに追加せず `future_observable_request` としてresearch-onlyに残す。

## Schema 1: `smart_candidate_prior_report.v1`

### 目的

Smart Prior Generatorの1runの全candidate cards、source refs、生成設定、score summaryを保存する。

### 必須field

```text
schema_version = smart_candidate_prior_report.v1
report_id
generated_at
producer
source_refs
generator_config
candidate_cards
candidate_count_total
candidate_count_accepted
candidate_count_rejected
rejection_summary
score_summary
boundary
known_gaps
```

### `generator_config`

必須field:

```text
profile
symbols
product_type
timeframe
families
candidate_cap
parameter_grid_hash
source_root
sealed_test_policy
network_attempted=false
credentials_used=false
production_exchange_write_used=false
```

### `SmartCandidateCard`

必須field:

```text
candidate_id
candidate_status = UNVERIFIED_CANDIDATE
candidate_decision = GENERATED | REJECTED
cause_priors
family
mechanism_card
observables
required_sources
source_requirement_status
execution_precheck
candidate_prior_score
parameter_set
action_set
entry_logic
exit_logic
kill_conditions
expected_information_gain
test_cost_estimate
operator_burden_estimate
candidate_cluster_id
similar_candidate_count
negative_control_refs
proof_status = not_alpha_or_profit_proof
rejection_reason
shortlist_reason
boundary
```

### `CandidateMechanismCard`

必須field:

```text
mechanism_id
mechanism_summary
who_is_forced_or_constrained
why_flow_may_be_unfavorable
expected_time_horizon
failure_modes
counter_hypothesis
```

例:

```json
{
  "mechanism_id": "forced_flow_liquidation_exhaustion",
  "mechanism_summary": "Large forced long liquidation may exhaust sell pressure and create short-horizon reversal.",
  "who_is_forced_or_constrained": "Leveraged long holders forced to liquidate.",
  "why_flow_may_be_unfavorable": "Forced sellers accept poor prices during thin liquidity.",
  "expected_time_horizon": "5m_to_60m",
  "failure_modes": ["cascade_continues", "spread_widens", "liquidity_does_not_recover"],
  "counter_hypothesis": "Continuation after liquidation dominates reversal."
}
```

### `CandidateExecutionPrecheck`

必須field:

```text
venue_id
product_type
symbol
min_notional_ok
tick_size_ok
lot_size_ok
max_spread_bps
observed_spread_bps
min_depth_usd
observed_depth_usd
fee_rate_available
funding_available
estimated_operator_time_minutes
estimated_capital_tied_up_minutes
unexecutable_reasons
execution_precheck_status = PASS | BLOCKED | NOT_ESTIMABLE
```

### `CandidatePriorScore`

必須field:

```text
mechanism_score
source_availability_score
execution_feasibility_score
testability_score
diversity_score
information_gain_score
operator_cost_penalty
unexecutable_penalty
overfit_surface_penalty
total_score
score_basis = prior_not_profit_proof
```

## Schema 2: `edge_candidate_search_ledger.v1`

### 目的

候補探索の行単位ledger。JSONLを主形式にする。1行1候補または1rejection。

### 必須field per row

```text
schema_version = edge_candidate_search_ledger.v1
run_id
candidate_id
row_kind = candidate | rejection | duplicate | cap_rejection | source_blocker
family
cause_priors
parameter_hash
parameter_set
candidate_cluster_id
similar_candidate_count
candidate_prior_score
candidate_decision
rejection_reason
source_requirement_status
execution_precheck_status
validation_peek_count_at_generation
sealed_test_used_for_selection=false
proof_status=not_alpha_or_profit_proof
```

### 禁止

- shortlistだけをledgerに出す。
- duplicateをsilent dropする。
- cap超過を保存しない。
- p-valueやreturnだけで `discovered` と書く。

## Schema 3: `trial_multiplicity_account.v1`

### 目的

候補生成の多重検定・探索回数・overfit surfaceを保存する。

### 必須field

```text
schema_version = trial_multiplicity_account.v1
account_id
created_at
producer
source_refs
candidate_run_id
candidate_count_total
candidate_count_shortlisted
candidate_count_rejected
family_count
family_trial_counts
parameter_grid_hashes
candidate_cluster_count
effective_trial_count_status
effective_trial_count
validation_peek_count
rerank_count
sealed_test_used_for_selection=false
success_only_reporting=false
adjustment_methods
known_gaps
boundary
```

### `adjustment_methods`

v0では次を明示する。

```text
benjamini_hochberg_fdr = NOT_ESTIMABLE | AVAILABLE
benjamini_yekutieli_fdr = NOT_ESTIMABLE | AVAILABLE
pbo = NOT_ESTIMABLE | AVAILABLE
white_reality_check = NOT_ESTIMABLE | AVAILABLE
deflated_sharpe_ratio = NOT_ESTIMABLE | AVAILABLE
```

`NOT_ESTIMABLE` は失敗ではない。必要入力が無いことを明示する正式結果です。

## Schema 4: `backtest_kill_gate.v1`

### 目的

候補をbacktestで殺す。攻める許可は出さない。

### status

```text
KILL
INCONCLUSIVE_DATA
RESEARCH_ONLY
SHORTLIST_FOR_VIRTUAL
```

### 必須field

```text
schema_version = backtest_kill_gate.v1
gate_id
created_at
producer
candidate_id
candidate_source_refs
bridge_refs
multiplicity_account_ref
backtest_refs
gate_status
recommended_action
metric_extraction_status
metric_source_refs
metric_not_estimable_reasons
conditions
metrics
known_gaps
boundary
```

### conditions

最低限。booleanだけでなく、各conditionは `PASS | FAIL | NOT_ESTIMABLE | NOT_APPLICABLE` を持つ。

```text
condition_id
condition_status
observed
required
source_ref
```

必須condition id:

```text
source_available
bridge_technical_ready
candidate_scoped_backtest_exists
no_trade_comparison_available
event_count_meets_family_threshold
closed_trade_count_meets_threshold
after_cost_edge_positive
stress_edge_positive
largest_loss_within_limit
profit_concentration_within_limit
multiplicity_account_available
sealed_test_not_used_for_selection
execution_precheck_passed
```

### metrics

```text
event_count
closed_trade_count
after_cost_edge_over_no_trade_usd
stress_edge_over_no_trade_usd
largest_loss_usd
profit_concentration
source_gap_count
unexecutable_reason_count
validation_peek_count
candidate_cluster_count
effective_trial_count
```

`metrics` の各値は、既存artifactから抽出できない場合に推定で埋めない。値を `null` にし、該当conditionを `NOT_ESTIMABLE` にする。

## Schema 5: `virtual_execution_gate.v1`

### 目的

actual cash前に、demo/testnet/fixtureでexecution lifecycleを検査する。

### status

```text
VIRTUAL_NOT_RUN
VIRTUAL_BLOCKED_SOURCE
VIRTUAL_BLOCKED_EXECUTION_PRECHECK
VIRTUAL_FAILED_ORDER_LIFECYCLE
VIRTUAL_FAILED_RECONCILIATION
VIRTUAL_PASSED_EXECUTION_LIFECYCLE
```

### 必須field

```text
schema_version = virtual_execution_gate.v1
gate_id
created_at
producer
candidate_id
execution_environment
venue_id
source_refs
order_lifecycle_summary
fill_ledger_summary
reconciliation_summary
gate_status
recommended_action
actual_cash=false
cash_metric_basis=virtual_exchange
exchange_write_used
production_exchange_write_used=false
permits_live_order=false
conditions
known_gaps
boundary
```

### conditions

```text
order_preview_ready
order_accepted_or_rejected_with_reason
client_oid_unique
partial_fill_handled
cancel_handled
reduce_only_close_checked
flat_reconciliation_passed
fee_like_fields_captured
funding_like_fields_captured
duplicate_order_prevented
production_exchange_write_not_used
```

### 注意

`virtual_execution_gate.v1` はprofit proofではない。PnLを保存する場合でも、`cash_metric_basis=virtual_exchange` とし、actual cashへの変換を禁止する。

## Schema 6: `edge_candidate_risk_actual_cash_handoff.v1`

### 目的

既存Risk-Taker Review / Actual Cash Report Gateへ進める時に、virtual/backtest evidenceをactual cash evidenceとして誤送信しない。

### status

```text
BLOCKED_NEEDS_ACTUAL_CASH_ROWS
READY_WITH_ACTUAL_CASH_ROWS
```

### 必須field

```text
schema_version = edge_candidate_risk_actual_cash_handoff.v1
handoff_id
created_at
producer
candidate_id
candidate_report_ref
search_ledger_ref
multiplicity_account_ref
backtest_kill_gate_ref
virtual_execution_gate_ref
risk_taker_review_input_status
actual_cash_report_gate_input_status
actual_cash_rows_required=true
actual_cash_rows_ref
virtual_or_backtest_used_as_actual_cash=false
known_gaps
boundary
```

### 禁止

- `virtual_execution_gate.v1` を actual cash rows として扱う。
- `backtest_kill_gate.v1` を actual cash rows として扱う。
- actual cash rowsが無いのに `crypto-perp-actual-cash-report-gate` をreadyにする。

## Schema 7: `llm_adversarial_evidence_review.v1`

### 目的

LLMを候補採用者ではなく、反対尋問者として使う。

### status

```text
NO_BLOCKING_FINDING
ADVERSARIAL_FINDING
MISSING_ARTIFACT
CONTRADICTION
OVERCLAIM_FLAG
HUMAN_REVIEW_REQUIRED
```

### 必須field

```text
schema_version = llm_adversarial_evidence_review.v1
review_id
created_at
producer
source_refs
packet_hash
review_status
findings
hard_blocker_count
soft_warning_count
llm_approval_ignored=true
paper_execution_allowed=false
live_allowed=false
actual_cash_decision_allowed=false
gate_override_allowed=false
boundary
```

### finding fields

```text
finding_id
finding_type
severity
source_ref
claim_text
problem
required_fix
machine_checkable
hard_blocker
```

### 禁止

- LLMが `PASS`、`APPROVE`、`PROMOTE`、`LIVE_READY` を出す。
- LLMがPnLやactual cashを計算する。
- LLMがmissing artifactを補完する。
- LLMがgate resultをoverrideする。

## stdout conventions

新CLIは最低限次をstdoutに出す。

```text
network_attempted=false
credentials_used=false
exchange_write_used=false
production_exchange_write_used=false
live_order_submitted=false
permits_live_order=false
status=<status>
artifact_path=<path>
known_gap_count=<int>
```

Virtual demo/testnetでexchange writeを使った場合は次にする。

```text
exchange_write_used=true
production_exchange_write_used=false
actual_cash=false
cash_metric_basis=virtual_exchange
```

## Artifact path conventions

v0の既定出力:

```text
data/edge_candidate_factory/<run_id>/smart_candidate_prior_report.json
data/edge_candidate_factory/<run_id>/smart_candidate_prior_report.md
data/edge_candidate_factory/<run_id>/edge_candidate_search_ledger.jsonl
data/edge_candidate_factory/<run_id>/trial_multiplicity_account.json
data/edge_candidate_factory/<run_id>/candidate_rejections.jsonl
data/edge_candidate_factory/<run_id>/backtest_kill_gate/<candidate_id>.json
data/edge_candidate_factory/<run_id>/virtual_execution_gate/<candidate_id>.json
data/edge_candidate_factory/<run_id>/risk_actual_cash_handoff/<candidate_id>.json
data/edge_candidate_factory/<run_id>/adversarial_review/
```

`data/` はgit-ignored runtime state。tracked test fixturesは `tests/fixtures/edge_candidate_factory/` に置く。

## Compatibility with existing repo

既存 `strategy_idea_candidates` との接続は次に限定する。

1. Edge Candidate Factory outputを直接 paper candidate にしない。
2. shortlistだけを `strategy_idea_candidate_set.v1` または `strategy_idea.v1` draftへexportできる。
3. C9 bridgeへ渡す場合は candidate set path/hash と ledger path/hash を失わない。
4. `crypto-perp-risk-taker-review` へ渡す前に、Virtual Execution Gate と Backtest Kill Gate のknown gapsをsource refsとして残す。
5. `crypto-perp-actual-cash-report-gate` へ渡す前に、既存 actual-cash rows builder のrows refを必須にする。

## Acceptance invariants

Python validationで必ず落とすもの:

- selected-only output。
- success-only reporting。
- sealed test used for selection。
- paper/live/wallet/signing/production exchange write permission true。
- virtual cash basisをactual cashへ昇格するfield。
- missing source refsなのに `SHORTLIST_FOR_VIRTUAL`。
- C9 bridge technical statusだけで economic pass を出すartifact。
- virtual/backtest artifactをactual cash rowsとして扱うartifact。
- LLM approval fieldをgate resultとして扱うartifact。
