<!--
作成日: 2026-05-30_11:09 JST
更新日: 2026-06-17_23:01 JST
-->

# Strategy Research Lab

このフォルダーは、Strategy Research Lab を使って売買に関わる戦略を安全に研究し、paper-only の仮注文意図まで落とすための実務仕様です。

正本はコードです。特に `src/sis/research/strategy_lab/`, `src/sis/research_protocol/`, `src/sis/commands/research.py`, `src/sis/commands/paper.py`, `src/sis/paper/runner.py` を優先します。このフォルダーは、そのコード契約を実装者・レビュー者が読める粒度に展開したものです。

## 読む順番

1. [01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md](01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md)
   - 売買戦略に関わる schema と model の意味、禁止解釈、validation を把握する。
2. [02_ARTIFACT_FLOW_AND_LINEAGE.md](02_ARTIFACT_FLOW_AND_LINEAGE.md)
   - `StrategyExperimentSpec` から `PaperIntentPreview` と paper execution までの artifact chain を把握する。
3. [03_SIGNAL_TO_TRADE_CANDIDATE_SPEC.md](03_SIGNAL_TO_TRADE_CANDIDATE_SPEC.md)
   - signal row を売買候補へ変換する時に、何を signal とし、何を order としないかを確認する。
4. [04_PAPER_PROMOTION_AND_INTENT_SPEC.md](04_PAPER_PROMOTION_AND_INTENT_SPEC.md)
   - `PaperCandidatePack`, `PromotionDecision`, `PaperIntentPreview`, `paper-from-intents` の境界を確認する。
5. [05_OPERATOR_RUNBOOK.md](05_OPERATOR_RUNBOOK.md)
   - 実際の CLI 手順、成果物、止まり方、再生成手順を確認する。
6. [06_GENERATOR_AND_EXPERIMENT_SPEC.md](06_GENERATOR_AND_EXPERIMENT_SPEC.md)
   - generator registry、現行 default generator、新規 generator を追加する時の仕様を確認する。
7. [07_VALIDATION_STOP_CONDITIONS_AND_TEST_MATRIX.md](07_VALIDATION_STOP_CONDITIONS_AND_TEST_MATRIX.md)
   - 受け入れ条件、停止条件、既存テストが守る契約を確認する。
8. [08_CURRENT_CAPABILITIES.md](08_CURRENT_CAPABILITIES.md)
   - 現時点で Strategy Research Lab ができること、まだできないこと、確認済み検証を短く確認する。
   - 詳細参照: [08_CURRENT_CAPABILITIES_DETAILS.md](08_CURRENT_CAPABILITIES_DETAILS.md)
   - 専門用語を減らした説明: [08_CURRENT_CAPABILITIES_EXPLAINED.md](08_CURRENT_CAPABILITIES_EXPLAINED.md)
   - 見た目つき HTML 版: [08_CURRENT_CAPABILITIES_EXPLAINED.html](08_CURRENT_CAPABILITIES_EXPLAINED.html)
9. [09_STRATEGY_AUTHOR_GUIDE.md](09_STRATEGY_AUTHOR_GUIDE.md)
   - ユーザーが YAML で売買ロジックを作り、validate / explain / signals / backtest / paper-preview へ進める手順を確認する。
10. [10_STRATEGY_AUTHORING_IMPLEMENTATION_SPEC.md](10_STRATEGY_AUTHORING_IMPLEMENTATION_SPEC.md)
   - `strategy_authoring_spec.v1`、`strategy_authoring_bundle.v1`、Rule DSL、Strategy Lab signal adapter、paper-only artifact の実装契約を確認する。
11. [11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md](11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md)
   - ユーザーが YAML で作れる売買ロジック、buy / sell signal、hold、損切、portfolio / execution 制約、未実装領域を一覧で確認する。
12. [12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md](12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md)
   - 今回までに追加・整理した Strategy Authoring 機能、execution quality gate、paper-only 境界、検証済み状態を確認する。
13. [13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md](13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md)
   - 生成しうる strategy archetype ごとに、対応状況、DSL surface、証拠 test、paper-only 境界を確認する。
14. [14_COMPLETION_EVIDENCE_LEDGER.md](14_COMPLETION_EVIDENCE_LEDGER.md)
   - paper-only Strategy Authoring scope の completion evidence、schema、example、非対象領域、最終 gate を確認する。

入口監査仕様は [../STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md](../STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md) です。

## 一文での位置づけ

Strategy Research Lab は、戦略アイデアを直接 order に変える機構ではありません。戦略仮説を schema 化し、signal、trial、candidate、promotion decision を経由して、再検証必須の paper-only preview に変換する機構です。

## 現行 artifact chain

```text
strategy_authoring_spec.v1 YAML
  -> StrategySignalRecord rows
  -> data/research/strategy_signals.parquet
  -> fixed-horizon backtest metrics
  -> paper-only preview artifacts

StrategyExperimentSpec
  -> StrategySignalRecord rows
  -> data/research/strategy_signals.parquet
  -> data/research/strategy_signal_manifest.json
  -> EvaluationPlan
  -> TrialRecord rows
  -> data/research/trial_ledger.jsonl
  -> TradeCandidate rows inside PaperCandidatePack
  -> data/research/paper_candidate_pack.json
  -> PromotionDecision
  -> data/research/promotion_decision.json
  -> PaperIntentPreview list
  -> data/bot/paper_intent_preview.json
  -> paper-from-intents revalidation
  -> data/paper/orders.parquet
  -> data/paper/fills.parquet
  -> data/paper/positions.parquet
```

## 最重要の禁止事項

- `PaperIntentPreview` を live order として扱わない。
- `TradeCandidate` を paper order / live order として扱わない。
- `PaperCandidatePack` を profitability / paper-ready / tiny-live-ready / live-ready の証明として扱わない。
- `data/research/signals.csv` を Strategy Lab の正本にしない。これは legacy export です。
- JSON Schema だけで full validation 済みと判断しない。詳細 validation は Pydantic model が正本です。
- `READ_ONLY_GO` を live trading ready と読まない。

## 現行実装の制約

- `build_signals()` の default generator は `qqq_trend_rates_vix` です。
- registered generator として `sp500_trend_rates_vix` も選べます。
- `build_signals()` は no-signal でも empty schema 付き `strategy_signals.parquet` と `strategy_signal_manifest.json` を書きます。
- `evaluate-strategy-lab` は同一 `trial_id` を重複追記しません。default では最新 `ts_signal` の 1 signal を選び、`--candidate-limit 0` で threshold 通過 signal を複数選べます。
- `evaluate-strategy-lab --rank-thresholds 0.2,0.8` で paper-only の rank threshold sweep を記録できます。
- `--split-method walk_forward` / `--era-unit` は era 別 signal count metrics を記録します。PnL や live-ready 証明ではありません。
- `strategy-experiment-run --spec path/to/spec.yaml` は `StrategyExperimentSpec` YAML/JSON を読み、登録済み `generator_id` の build 関数を spec の `strategy_id` / `symbol_bindings` / manifest lineage で実行します。`parameter_grid` は cartesian 展開され、各 variant は `parameter_hash` と `parameter_grid:<hash>` reason code で区別されます。現行 built-in generator は `min_source_confidence`, `max_vix_level` / `vix_gate`, `min_research_return_1d`, `timeframe` を signal 条件または出力 timeframe として消費できます。未登録 generator や `--max-variants` 超過は fail closed で止まります。
- `strategy-author-*` CLI は `strategy_authoring_spec.v1` YAML を読み、宣言型 rule から Strategy Lab signal artifact と fixed-horizon backtest metrics を作れます。`strategy-author-bundle-run` は `strategy_authoring_bundle.v1` で複数 spec の paper portfolio 比較を作れます。notional-aware pair / hedge のコピー用 example は `docs/strategy_research_lab/examples/notional_pair_hedge_bundle.yaml` です。
- `promotion-decision --decision promote` は required evidence が揃わないと model validation で止まります。
- `paper-from-intents` は最新 quote と paper broker で再検証し、expired intent や quote missing を block します。
