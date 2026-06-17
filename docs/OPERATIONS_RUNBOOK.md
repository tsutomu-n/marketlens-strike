<!--
作成日: 2026-06-04_16:48 JST
更新日: 2026-06-17_21:52 JST
-->

# Operations Runbook

この runbook は current repo を再開・再検証・再生成するための root index です。長い domain 手順は [runbooks/README.md](runbooks/README.md) から辿ります。`data/` は git 管理外なので、artifact は必要に応じて作り直します。

現在の開発主経路は backtest-first / venue-neutral です。Trade[XYZ] collection 手順は再利用可能な運用手順として残しますが、Trade[XYZ] quote coverage を現在の主経路 next action とは扱いません。

## Restart

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
uv run sis strategy-lifecycle-review --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

読む順番:

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md)
3. [CODE_STATUS.md](CODE_STATUS.md)
4. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
5. [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
6. [runbooks/README.md](runbooks/README.md)
7. `data/reports/current_state_index.md`
8. `data/reports/readiness_snapshot.md`
9. `data/reports/phase_gate_review.md`
10. `data/reports/operations_dashboard.md`

外部入力が来た場合は、先に [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md) の `External Input Restart Checklist` を読む。対象は Trade[XYZ] public user address、Bitget demo credentials、新しい通常 paper observation evidence です。ここでの再確認は read-only / observation であり、paper / live 実行許可ではありません。

## Domain Runbooks

| Runbook | 概要 |
|---|---|
| [runbooks/NDX_RESEARCH_RUNBOOK.md](runbooks/NDX_RESEARCH_RUNBOOK.md) | NDX Layer 2.2 review gate と Layer 2.3 / 2.4 local research gate の再生成手順 |
| [runbooks/TRADE_XYZ_RUNBOOK.md](runbooks/TRADE_XYZ_RUNBOOK.md) | Trade[XYZ] collection、historical archive、account fee、pure backtest の手順 |
| [runbooks/STRATEGY_RESEARCH_RUNBOOK.md](runbooks/STRATEGY_RESEARCH_RUNBOOK.md) | Strategy Research Lab、backtest-first baseline、Bitget demo local smoke、Alpaca smoke の手順 |
| [runbooks/PAPER_EXECUTION_RUNBOOK.md](runbooks/PAPER_EXECUTION_RUNBOOK.md) | Paper operations、read-only execution artifacts、legacy live evidence、daemon、micro-live boundary の手順 |

## Verification

通常の repo 確認:

```bash
uv run python scripts/check_current_docs.py
./scripts/check
```

read-only / paper-observation 状態の再確認:

```bash
uv run sis execution-read-only-surfaces
uv run sis execution-snapshot --venue trade_xyz
uv run sis execution-drift-overview
uv run sis phase-gate-review
uv run sis strategy-paper-observation-status --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

この再確認で `READ_ONLY_GO` が出ても、production live trading ready とは読まない。`phase-gate-review`、execution lineage、paper observation status を分けて読む。

## Stop Conditions

- `phase-gate-review` が `phase2_entry_allowed=false` の間は、運用上の昇格完了と扱わない。ただし legacy artifact blocker が出ている場合は current Trade[XYZ] path と legacy path を分けて読む。
- generated artifact が欠けている場合、推測で判断せず再生成する。
- `READ_ONLY_GO` を production live trading ready と読まない。fee mode unknown の再発、execution drift degraded、micro live public CLI 不在は別 gate として扱う。
- `execution_drift_classification_counts.LIVE_READINESS_BLOCKER > 0` の間は live trading ready と扱わない。
- micro live code path があることをもって live trading ready と解釈しない。
- Strategy Lab schema / candidate / paper preview があることをもって live-ready と解釈しない。
- Strategy Lab の JSON Schema は thin guard。詳細 validation は `src/sis/research/strategy_lab/` の Pydantic model に従う。
- migration docs と legacy live evidence docs を混同しない。
