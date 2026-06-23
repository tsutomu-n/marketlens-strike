<!--
作成日: 2026-06-18_19:47 JST
更新日: 2026-06-23_22:39 JST
-->

# Target Strategy Operations Workbench

## 結論

`marketlens-strike` の target は、完全自動売買 bot ではなく、人間レビュー前提の戦略運用検証ワークベンチです。

旧 2064 行版は historical target definition として [archive/2026-06-23-doc-triage/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18_FULL.md](archive/2026-06-23-doc-triage/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18_FULL.md) に移動済みです。この短縮版は current proof ではなく、現行 docs と code へ迷わず辿るための入口です。

## Target Definition

MarketLens Strike は、戦略を思いつきや単発 backtest で運用に出さないために、次を local artifact と CLI で管理する。

1. 入力データ契約と戦略仮説を残す。
2. backtest、比較、stress、no-lookahead、data availability、pack validation で弱い候補を落とす。
3. Strategy Review と operator record で、人間が読んだ判断を source hash 付きで残す。
4. stage policy、paper smoke plan、runtime observation、drift review、learning event、revision request、case timeline、daily brief、static viewer で、次に見るべきことと止めるべき理由を可視化する。
5. 十分な証拠がある場合でも、micro live plan は計画 artifact までに止め、実 execution は別承認にする。

## 現行実装入口

| 目的 | 読むもの |
|---|---|
| 現在地 | [CURRENT_STATE.md](CURRENT_STATE.md) |
| 実装済み surface | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| Strategy Operations first slices | [strategy_inputs/README.md](strategy_inputs/README.md), [strategy_stage/README.md](strategy_stage/README.md), [strategy_runtime_observation/README.md](strategy_runtime_observation/README.md), [strategy_learning/README.md](strategy_learning/README.md), [strategy_case_lite/README.md](strategy_case_lite/README.md), [strategy_workbench_viewer/README.md](strategy_workbench_viewer/README.md) |
| Backtest / Strategy Review | [backtest/README.md](backtest/README.md), [strategy_review/README.md](strategy_review/README.md) |
| 実務的な次方向 | [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) |

## やらないこと

- 完全自動 live trading。
- backtest pass だけでの paper / live 移行。
- AI / ML / optimizer output の自動採用。
- human review なしの stage advance。
- wallet、signing、exchange write、live order の暗黙実行。
- `READY_FOR_HUMAN_*` を execution permission と読むこと。

## 検証

この文書に固定 pass count は置かない。作業時点で次を再実行する。

```bash
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```
