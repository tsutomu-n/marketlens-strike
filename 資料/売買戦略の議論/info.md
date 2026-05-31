According to a document from 2026-05-31, 結論：**最終決定版の開発者向けドキュメントZIPを作成しました。**
対象は、`marketlens-strike` に追加する **Trade[XYZ]専用 Pure Backtest Engine v0.1** です。

[ZIPをダウンロード](sandbox:/mnt/data/trade_xyz_pure_backtest_engine_v0_1_docs.zip)

SHA-256:

```text
c7414edb29bdc27f9ffb4d880b0cf7f23f5f53f337394dc01d5d09f711f6ebc2
```

## 最終方針

今回の計画は、既存の `Strategy Lab` や `uv run sis build-backtest` を拡張する案ではなく、**既存bridgeを温存したまま、別責任境界でTrade[XYZ]専用の純粋バックテストエンジンを作る**方針にしました。既存の `build-backtest` はStrategy Lab / bridge系commandであり、新規pure engineではないため、互換性を壊さないことを先に固定する必要があります。

MVPは、`SP500`、`1h相当`、`long-only`、`20期間高値ブレイクentry`、`10期間安値割れexit`、`market-like taker fill`、`fee + spread/slippage + nullable funding` に絞っています。fixture-firstで始め、既存 `src/sis/backtest/bridge.py` は触らず、CLI公開はcontract安定後に回します。

## ZIPに含めたもの

```text
trade_xyz_pure_backtest_engine_v0_1_docs/
  README.md
  FILE_INDEX.txt

  docs/
    00_final_decision.md
    01_scope_constraints.md
    02_architecture.md
    03_schema_contracts.md
    04_execution_semantics.md
    05_cost_funding_slippage.md
    06_artifacts_metrics.md
    07_test_plan.md
    08_migration_and_compatibility.md
    09_stop_conditions_and_risk_register.md
    10_coder_handoff.md
    11_future_scope.md

  tasks/
    TASK_CHAIN.yaml
    PR-0_existing_surface_compatibility_lock.md
    PR-1_backtest_contracts.md
    PR-2_trade_xyz_market_data_schema.md
    PR-3_cost_slippage_nullable_funding.md
    PR-4_fill_model_no_lookahead.md
    PR-5_minimal_runner_portfolio.md
    PR-6_metrics_artifacts.md
    PR-7_sample_strategy_adapter.md
    PR-8_cli_exposure.md

  schemas/
    backtest_market_data_row.v1.schema.json
    backtest_order.v1.schema.json
    backtest_fill.v1.schema.json
    backtest_position.v1.schema.json
    backtest_trade.v1.schema.json
    backtest_run.v1.schema.json
    backtest_metrics.v1.schema.json
    backtest_artifact_manifest.v1.schema.json

  examples/
    breakout_sp500_1h_v0.yaml
    deterministic_fixture_policy.md
    sample_artifact_tree.txt

  appendices/
    A_source_basis.md
    B_field_mapping.md
    C_accounting_formulas.md
    D_no_lookahead_cases.md
    E_not_in_scope.md
```

## 実装計画の粒度

各PRタスクには、以下を明記しました。

```text
目的
対象ファイル
実装手順
必須テスト
完了条件
禁止事項 / Stop Conditions
```

PR順は以下です。これは追加資料のPR計画をベースに、コーダーがそのまま進められるように分解しています。

```text
PR-0  Existing surface compatibility lock
PR-1  Backtest contracts
PR-2  Trade[XYZ] market data schema
PR-3  Fee / slippage / nullable funding model
PR-4  Fill model and no-lookahead rules
PR-5  Minimal runner and portfolio accounting
PR-6  Metrics and artifact writers
PR-7  Sample strategy adapter: SP500 breakout fixture
PR-8  CLI exposure after contracts stabilize
```

## 特に固定した仕様

`exec_buy_price` / `exec_sell_price` はカラムとして存在するが、現snapshotではNull型なので、fill modelでは `exec_buy_price -> best_ask -> mid + spread推定`、`exec_sell_price -> best_bid -> mid - spread推定` の順にfallbackします。推定値はrowを書き換えず、fill record側に `fill_price_source` として残す仕様にしました。

また、`funding_rate` の単位と適用間隔は推測しません。`None` は `0` として扱い、metricsにはfunding impact列を残します。feeはrowの `taker_fee_bps` / `maker_fee_bps` を優先し、欠ける場合だけ `configs/fee_model.trade_xyz.yaml` をfallbackにします。古い `0.04%` 仮定はhardcode禁止です。

## テスト方針

unit testは `data/normalized/quotes.parquet` や `data/research/*` の常在を前提にしません。`tmp_path` とPolarsでdeterministic fixtureを作る方針を明記しました。runtime artifactは実行履歴に依存するため、unit testの正本にしない、という資料上の制約を反映しています。

最終acceptanceは以下です。

```bash
uv run pytest tests/backtest -q
uv run pytest tests/test_backtest_bridge.py tests/test_backtest_fixed_horizon.py -q
uv run ruff check .
uv run pyrefly check
./scripts/check
```

## Stop Conditions

以下に当たったら実装を止めて計画を更新するように明記しました。

```text
fee_mode=unknownのままentryできる
block_reasons非空またはis_tradable=falseでentryできる
funding_rateの単位を推測する
signal rowと同じrowでfillする
既存bridgeのpublic behaviorを壊す
unit testがruntime dataに依存する
bot-previewを注文候補生成Botにする
BacktestEngineがwallet/signing/exchange writeを要求する
MT5 / IC Markets / CFD仕様をTrade[XYZ] engineへ混ぜる
```

これらは追加資料側のStop Conditionsを反映しています。

## 出力artifact契約

MVP backtestの出力は以下に固定しました。

```text
backtest_run.json
orders.parquet
fills.parquet
trades.parquet
equity_curve.parquet
metrics.json
candidate_result.json
data_manifest.json
config_hash.txt
backtest_report.md
```

必須metadataとして、`no_live_order=true`、`wallet_used=false`、`exchange_write_used=false` を入れます。metricsには、`net_return_after_cost`、`max_drawdown`、`trade_count`、`cost_drag_bps`、`fee_impact`、`funding_impact`、`slippage_impact`、`blocked_reason_counts` などを含めます。

## 読む順番

```text
1. README.md
2. docs/00_final_decision.md
3. docs/01_scope_constraints.md
4. docs/02_architecture.md
5. docs/03_schema_contracts.md
6. docs/04_execution_semantics.md
7. docs/07_test_plan.md
8. tasks/TASK_CHAIN.yaml
9. tasks/PR-0_existing_surface_compatibility_lock.md
```

13:32:41.(05/31)
