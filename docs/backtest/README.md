<!--
作成日: 2026-05-31_17:20 JST
更新日: 2026-06-11_21:34 JST
-->

# Backtest Docs

この directory は、現行 repo の backtest surface をコード基準で分けて読む入口です。

## 結論

現行 repo には、用途が違う backtest surface が複数あります。

| Surface | Entry | Status | 用途 |
|---|---|---|---|
| Trade[XYZ] pure backtest v0.1 | `sis.backtest.engine.runner.run_backtest()` | 実装済み、CLI未公開 | Trade[XYZ] 単一銘柄 long-only の純粋BT |
| Strategy Authoring fixed-horizon backtest | `uv run sis strategy-author-run --through backtest` | 実装済み、baseline seedあり | YAML戦略のpaper-only研究評価 |
| Legacy backtest bridge | `uv run sis build-backtest` | 互換維持 | Strategy Lab / historical bridge系の簡易評価 |

バックテストへ最短で入る入口は Strategy Authoring baseline です。
Trade[XYZ] を当面の注文口にせず、バックテスト優先へ切り替える計画は
[BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md](BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md)
を見ます。

## Backtest-First Baseline

外部 API や Trade[XYZ] 30日 quote coverage を待たず、まずこの local fixture で Strategy Authoring backtest を通します。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
```

主な出力:

- `data/research/strategy_authoring_baseline_feature_panel.parquet`
- `data/research/strategy_authoring_baseline_quotes.parquet`
- `data/research/strategy_authoring_baseline_venue_cost_matrix.csv`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/reports/strategy_backtest_report.md`
- `data/reports/strategy_backtest_acceptance_report.md`

これは Strategy Authoring の paper-only 研究評価です。`strategy-backtest-acceptance` は backtest artifact の pass/fail/boundary 判定を固定しますが、Trade[XYZ] `backtest_data_ready=true`、Bitget 接続、demo order submit、live readiness の証明ではありません。

## Trade[XYZ] Pure Backtest v0.1

正本コード:

- `src/sis/backtest/engine/`
- `src/sis/backtest/trade_xyz/`
- `tests/backtest/`

現在できること:

- Trade[XYZ]専用
- single-symbol
- long-only
- market-like taker fill
- next-row fill
- fixed notional sizing
- fee / slippage / nullable funding v0
- entry gate / exit gate
- data quality report
- metrics / report / artifact出力

現在できないこと:

- public CLI
- live order
- wallet / signing / exchange write
- short
- multi-symbol portfolio
- limit / stop / partial fill
- L2 order book replay
- MT5 / IC Markets / CFD

## Boundary

`uv run sis build-backtest` は既存 bridge 系の command です。Trade[XYZ] pure backtest v0.1 の入口ではありません。

`strategy-author-run --through backtest` は Strategy Authoring の fixed-horizon paper-only 評価です。Trade[XYZ] pure backtest v0.1 の会計・約定・artifact契約とは別物です。

## Verification

current verification は固定の pass count ではなく、作業時点で次を再実行して確認する:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run pytest -q tests/backtest
uv run python scripts/check_current_docs.py
```
