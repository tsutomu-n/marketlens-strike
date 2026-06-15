<!--
作成日: 2026-06-15_19:17 JST
更新日: 2026-06-15_19:17 JST
-->

# Backtest Placeholder Output Sample

## 結論

これは、バックテストシステムを使ったときに「だいたいどんな出力が見えるか」を見るためのサンプルです。

ここにある数値、銘柄名、ID、hash、時刻、利益率はすべてプレースホルダーです。実際の backtest 結果でも、投資判断でも、成績の主張でもありません。

## 使ったことにするコマンド

例として、次のコマンドを実行した想定にします。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run sis strategy-backtest-acceptance
uv run sis strategy-lifecycle-review
```

## 1. 端末に出そうな表示例

実際の CLI は command によって表示量が違います。ここでは、ユーザーが見たいであろう要点だけをまとめた例にしています。

```text
$ uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv

strategy_backtest_pack=data/research/backtest_pack/strategy_backtest_pack.json
strategy_backtest_pack_report=data/reports/strategy_backtest_pack_report.md
paper_only=true
permits_live_order=false
wallet_used=false
exchange_write_used=false
standard_engine=strategy_authoring_native
suite_run_count=5
suite_method_count=5
```

```text
$ uv run sis strategy-backtest-pack-validate

strategy_backtest_pack_validation=data/research/backtest_pack/strategy_backtest_pack_validation.json
decision=PASS
check_count=198
passed_count=198
failed_count=0
paper_only=true
permits_live_order=false
wallet_used=false
exchange_write_used=false
```

```text
$ uv run sis strategy-backtest-acceptance

backtest_acceptance_decision=data/research/strategy_lifecycle/backtest_acceptance_decision.json
decision=PASS_BACKTEST_ACCEPTANCE
acceptance_id=sha256:PLACEHOLDER_ACCEPTANCE_ID
permits_live_order=false
```

```text
$ uv run sis strategy-lifecycle-review

strategy_lifecycle_review=data/research/strategy_lifecycle/strategy_lifecycle_review.json
decision=CONTINUE_PAPER_OBSERVATION
decision_reasons=PAPER_OBSERVATION_INSUFFICIENT
next_actions=Continue paper observation until thresholds are met.
permits_live_order=false
```

## 2. 全体要約のサンプル

`strategy-backtest-artifact-summary` は、いろいろな artifact の大事な部分だけを JSON でまとめて見せます。

```json
{
  "summary_kind": "strategy_backtest_artifact_summary.v1",
  "created_at": "2026-06-15T10:17:00Z",
  "pack": {
    "exists": true,
    "path": "data/research/backtest_pack/strategy_backtest_pack.json",
    "schema_version": "strategy_backtest_pack.v1",
    "paper_only": true,
    "permits_live_order": false,
    "wallet_used": false,
    "exchange_write_used": false,
    "suite_method_count": 5,
    "suite_run_count": 5,
    "external_framework_policy": {
      "standard_engine": "strategy_authoring_native",
      "decision": "complete_without_locked_external_dependency",
      "locked_dependency_added": false,
      "external_adapters_required_for_completion": false
    }
  },
  "pack_validation": {
    "exists": true,
    "path": "data/research/backtest_pack/strategy_backtest_pack_validation.json",
    "schema_version": "strategy_backtest_pack_validation.v1",
    "decision": "PASS",
    "check_count": 198,
    "passed_count": 198,
    "failed_count": 0,
    "paper_only": true,
    "permits_live_order": false,
    "wallet_used": false,
    "exchange_write_used": false
  },
  "benchmark_relative": {
    "exists": true,
    "strategy_total_return": 0.0123,
    "benchmark_total_return": 0.0081,
    "active_total_return": 0.0042,
    "tracking_error": 0.0035,
    "information_ratio": 1.2,
    "missing_benchmark_count": 0
  },
  "stress": {
    "exists": true,
    "base_total_return": 0.0123,
    "worst_scenario_id": "severe",
    "worst_stressed_total_return": -0.0064,
    "scenario_count": 4
  },
  "regime_split": {
    "exists": true,
    "dimension_count": 5,
    "worst_dimension_id": "ts_hour",
    "worst_bucket_id": "ts_hour:10",
    "worst_bucket_total_return": -0.0018
  },
  "rolling_stability": {
    "exists": true,
    "window_count": 2,
    "worst_window_size": 3,
    "worst_window_total_return": -0.0022
  },
  "data_availability": {
    "exists": true,
    "status": "pass",
    "summary": {
      "enabled_artifact_count": 3,
      "total_gap_count": 0,
      "total_duplicate_count": 0,
      "future_candidate_count": 3,
      "external_api_called": false,
      "network_used": false,
      "schema_widening_required": false
    }
  },
  "no_lookahead_diff": {
    "exists": true,
    "status": "pass",
    "summary": {
      "check_count": 7,
      "failed_count": 0,
      "runtime_future_mutation_replay": true
    }
  },
  "execution_simulation": {
    "exists": true,
    "status": "pass",
    "summary": {
      "signals_considered": 7,
      "order_intent_count": 7,
      "fill_event_count": 7,
      "blocked_count": 0,
      "market_impact_claimed": false
    }
  }
}
```

## 3. Pack validation のサンプル

Pack validation は、まとめ結果が壊れていないか、必要な artifact があるか、本物の注文を出していないかを確認します。

```json
{
  "schema_version": "strategy_backtest_pack_validation.v1",
  "created_at": "2026-06-15T10:17:10Z",
  "pack_path": "data/research/backtest_pack/strategy_backtest_pack.json",
  "pack_hash": "sha256:PLACEHOLDER_PACK_HASH",
  "decision": "PASS",
  "paper_only": true,
  "live_order_submitted": false,
  "permits_live_order": false,
  "live_conversion_allowed": false,
  "wallet_used": false,
  "exchange_write_used": false,
  "summary": {
    "check_count": 198,
    "passed_count": 198,
    "failed_count": 0,
    "min_suite_method_count": 5,
    "locked_dependency_added": false,
    "external_framework_policy_decision": "complete_without_locked_external_dependency",
    "required_methods": [
      "single_window",
      "walk_forward:trading_day",
      "purged_walk_forward:trading_day",
      "purged_walk_forward:trading_day+return_bootstrap",
      "purged_walk_forward:trading_day+block_bootstrap"
    ]
  },
  "findings": [
    {
      "check_id": "boundary_paper_only",
      "message": "paper_only must be True",
      "passed": true
    },
    {
      "check_id": "boundary_permits_live_order",
      "message": "permits_live_order must be False",
      "passed": true
    },
    {
      "check_id": "required_artifact_benchmark_relative",
      "message": "benchmark-relative artifact must exist and hash must match",
      "passed": true
    }
  ]
}
```

この例で重要なのは、`decision=PASS` と `failed_count=0` です。  
ただし、これは「本番運用してよい」ではありません。

## 4. Backtest acceptance のサンプル

Backtest acceptance は、Strategy Lifecycle に渡すための判定です。

```json
{
  "schema_version": "strategy_backtest_acceptance_decision.v1",
  "acceptance_id": "sha256:PLACEHOLDER_ACCEPTANCE_ID",
  "created_at": "2026-06-15T10:17:20Z",
  "decision": "PASS_BACKTEST_ACCEPTANCE",
  "source_metrics_path": "data/research/strategy_backtest_metrics.json",
  "source_metrics_hash": "sha256:PLACEHOLDER_METRICS_HASH",
  "decision_reasons": [
    "BACKTEST_ACCEPTANCE_PASSED"
  ],
  "summary_checks": {
    "backtest_passed": true,
    "pass_min_trade_count": true,
    "pass_all_thresholds": true
  },
  "era_summary": {
    "eras_present": true,
    "era_count": 2,
    "era_pass_count": 2,
    "era_fail_count": 0,
    "era_signal_counts": [
      12,
      15
    ]
  },
  "boundary_flags": {},
  "permits_live_order": false,
  "live_conversion_allowed": false,
  "wallet_used": false,
  "venue_write_used": false,
  "exchange_write_used": false
}
```

この例では、バックテスト段階は通っています。  
しかし、paper observation や live readiness まで通ったわけではありません。

## 5. Strategy Lifecycle review のサンプル

Lifecycle review は、次に何をするべきかを出します。

```json
{
  "schema_version": "strategy_lifecycle_review.v1",
  "review_id": "sha256:PLACEHOLDER_LIFECYCLE_REVIEW_ID",
  "created_at": "2026-06-15T10:17:30Z",
  "decision": "CONTINUE_PAPER_OBSERVATION",
  "decision_reasons": [
    "PAPER_OBSERVATION_INSUFFICIENT"
  ],
  "next_actions": [
    "Continue paper observation until thresholds are met."
  ],
  "input_status": {
    "backtest_acceptance_present": true,
    "paper_review_present": true,
    "phase_gate_present": true
  },
  "blocker_counts": {
    "P2_BLOCKER": 0,
    "LIVE_READINESS_BLOCKER": 5
  },
  "boundary_flags": {},
  "permits_live_order": false,
  "live_conversion_allowed": false,
  "wallet_used": false,
  "venue_write_used": false,
  "exchange_write_used": false
}
```

この例での読み方は、次の通りです。

- バックテストは通っている。
- paper observation はまだ観察数が足りない。
- live readiness blocker が残っている。
- 本物の注文はまだ許可されていない。

## 6. 人間向けレポートのサンプル

JSON は機械向けです。人間向けには Markdown report が出る想定です。

```markdown
# Strategy Backtest Pack Report

- pack_id: PLACEHOLDER_PACK
- created_at: 2026-06-15T10:17:00Z
- standard_engine: strategy_authoring_native
- paper_only: true
- permits_live_order: false
- wallet_used: false
- exchange_write_used: false

## Summary

| Item | Value |
|---|---:|
| Suite methods | 5 |
| Suite runs | 5 |
| Strategy total return | 1.23% |
| Benchmark total return | 0.81% |
| Active total return | 0.42% |
| Worst stress return | -0.64% |
| Data gap count | 0 |
| No-lookahead failed count | 0 |

## Interpretation

The pack passed structural validation and stayed paper-only.
This report does not claim alpha, paper pass, or live readiness.
Continue paper observation before any live-readiness planning.
```

## 7. 高校生向けに読むとこうなる

同じ内容を短く言うと、こうです。

```text
作戦を過去データで試した。
5種類の方法で試した。
ファイルの形や安全チェックは通った。
本物の注文は出していない。
wallet も使っていない。
取引所への書き込みもしていない。
結果は「次の確認に進める」状態。
でも「本番で使ってよい」ではない。
次は paper observation を続ける。
```

## 8. どこを見ればよいか

最初に見るなら、次の順番が分かりやすいです。

1. `strategy-backtest-artifact-summary` の `pack_validation.decision`
2. `pack_validation.failed_count`
3. `pack.paper_only`
4. `pack.permits_live_order`
5. `backtest_acceptance.decision`
6. `strategy_lifecycle_review.decision`
7. `strategy_lifecycle_review.next_actions`

## 9. 重要な注意

このサンプルは、見た目を理解するためのプレースホルダーです。

- 実際の利益率ではありません。
- 実際の hash ではありません。
- 実際の銘柄や取引判断ではありません。
- 投資助言ではありません。
- live trading の許可ではありません。

実際の確認では、repo が生成した `data/research/...` と `data/reports/...` の artifact を見ます。
