<!--
作成日: 2026-05-31_17:20 JST
更新日: 2026-06-05_22:12 JST
-->

# Backtest Docs

この directory は、現行 repo の backtest surface をコード基準で分けて読む入口です。

## 結論

現行 repo には、用途が違う backtest surface が複数あります。

| Surface | Entry | Status | 用途 |
|---|---|---|---|
| Trade[XYZ] pure backtest v0.1 | `sis.backtest.engine.runner.run_backtest()` | 実装済み、CLI未公開 | Trade[XYZ] 単一銘柄 long-only の純粋BT |
| Strategy Authoring fixed-horizon backtest | `uv run sis strategy-author-run --through backtest` | 実装済み | YAML戦略のpaper-only研究評価 |
| Legacy backtest bridge | `uv run sis build-backtest` | 互換維持 | Strategy Lab / historical bridge系の簡易評価 |

最初に読むべき詳細は [TRADE_XYZ_PURE_BACKTEST_V0_1.md](TRADE_XYZ_PURE_BACKTEST_V0_1.md) です。
Trade[XYZ] を当面の注文口にせず、バックテスト優先へ切り替える計画は
[BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md](BACKTEST_FIRST_VENUE_NEUTRAL_PIVOT_PLAN_2026-06-05.md)
を見ます。

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

2026-06-05 docs/runtime check:

- `uv run python -V`: `Python 3.13.7`
- `uv run python scripts/check_current_docs.py`: checked 83 current docs
- latest recorded `./scripts/check`: 830 passed in 2026-06-04 quote coverage docs
