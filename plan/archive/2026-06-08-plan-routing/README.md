<!--
作成日: 2026-06-18_00:08 JST
更新日: 2026-06-18_00:08 JST
-->

# 2026-06-08 Plan Routing Archive

このディレクトリは、2026-06-07 から 2026-06-08 頃に作った historical plan pack と template を `plan/` の現行導線から外すための archive です。

ここにある文書は、過去の判断、計画形式、実装順序、受け入れ条件を確認するための資料です。現行の仕様、実装済み機能、paper / live 許可、外部入力時の手順を判断する正本ではありません。

現行状態を確認する場合は、先に次を読んでください。

- `docs/CURRENT_STATE.md`: repo 全体の現在地を読む入口。
- `docs/CODE_STATUS.md`: 実装済み surface と履歴文書への入口。
- `docs/NEXT_DIRECTION_CURRENT.md`: 次に進める条件と外部入力時の再確認手順。
- `plan/README.md`: 現在残している未実装 plan と historical plan の読み分け。

## Archived Groups

- `0607ここからの計画/`: NDX Layer 2.2 foundation の historical implementation plan。
- `0607ここからの計画2/feature_expansion_plan_20260607/`: NDX Layer 2.2 v2 の historical feature expansion plan。
- `0607ここからの計画2/feature_expansion_plan_20260607_layer_2_2_exit_gate_v3_minimal/`: NDX Layer 2.2 exit gate の historical feature expansion plan。
- `0607ここからの計画2/zip_intake_guide/`: feature expansion plan ZIP の historical intake guide と manifest template。
- `marketlens_strategy_research_lab_migration_pack/`: Strategy Research Lab migration の historical planning pack。
- `TRADE_XYZ_*.md`: Trade[XYZ] real-data / backtest 周辺の historical implementation plans。

## Boundary

- archive 内の古い pass count、artifact snapshot、phase gate value は現在値ではない。確認時は `./scripts/check` と対象 CLI を再実行する。
- root `plan/0607ここからの計画2/*.zip` と `plan/0608ここからの計画/**` は ignored historical source packages であり、新しい実装指示ではない。
- root `plan/0609ここからの計画/03_venue_read_only_capability_probe/` は、まだ root 側に残している current unimplemented plan。
