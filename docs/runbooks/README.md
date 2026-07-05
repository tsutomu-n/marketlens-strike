<!--
作成日: 2026-06-17_21:52 JST
更新日: 2026-07-05_12:35 JST
-->

# Domain Runbooks

`docs/OPERATIONS_RUNBOOK.md` は再開用の root index です。個別の再生成手順、長い command list、境界条件はこの directory の domain runbook に分けます。

通常時の現在方向は [../CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](../CURRENT_GOAL_AND_DIRECTION_2026-07-05.md) を読む。domain runbook は個別手順であり、全体の次方向や profit / live readiness の証明ではありません。

外部入力が来た場合は、先に [../NEXT_DIRECTION_CURRENT.md](../NEXT_DIRECTION_CURRENT.md) の `External Input Restart Checklist` を読む。対象は Trade[XYZ] public user address、Bitget demo credentials、新しい通常 paper observation evidence です。ここでの再確認は read-only / observation であり、paper / live 実行許可ではありません。

## Runbook Map

| Runbook | 役割 |
|---|---|
| [NDX_RESEARCH_RUNBOOK.md](NDX_RESEARCH_RUNBOOK.md) | NDX Layer 2.2 review gate と Layer 2.3 / 2.4 local research gate の再生成手順 |
| [TRADE_XYZ_RUNBOOK.md](TRADE_XYZ_RUNBOOK.md) | Trade[XYZ] collection、historical archive、account fee、pure backtest の手順 |
| [STRATEGY_RESEARCH_RUNBOOK.md](STRATEGY_RESEARCH_RUNBOOK.md) | Strategy Research Lab、backtest-first baseline、Bitget demo local smoke、Alpaca smoke の手順 |
| [PAPER_EXECUTION_RUNBOOK.md](PAPER_EXECUTION_RUNBOOK.md) | Paper operations、read-only execution artifacts、legacy live evidence、daemon、micro-live boundary の手順 |
| [CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) | Crypto Perp candidate event から decision / outcome / tournament report までの再生成手順 |

## Reading Rule

- 現在状態は code、tests、schemas、CLI help、runtime artifact を優先する。
- `data/` 配下は git 管理外なので、fresh checkout では必要に応じて再生成する。
- `READ_ONLY_GO`、collector connected、paper preview artifact を production live trading ready と読まない。
