<!--
作成日: 2026-06-17_22:13 JST
更新日: 2026-06-17_22:13 JST
-->

# 2026-06-17 Plan Routing Archive

このディレクトリは、実装済みまたは historical review 扱いになった plan を `plan/` の現行導線から外すための archive です。

ここにある plan は、過去の判断・実装順序・受け入れ条件を確認するための資料です。現行の仕様、実装済み機能、paper / live 許可、外部入力時の手順を判断する正本ではありません。

現行状態を確認する場合は、先に次を読んでください。

- `docs/CURRENT_STATE.md`: repo 全体の現在地を読む入口。
- `docs/CODE_STATUS.md`: 実装済み surface と履歴文書への入口。
- `docs/NEXT_DIRECTION_CURRENT.md`: 次に進める条件と外部入力時の再確認手順。
- `plan/README.md`: 現在残している未実装 plan と historical plan の読み分け。

## Archived Groups

- `0609ここからの計画/01_ndx_qqq_venue_suitability_gate/`: NDX / QQQ venue suitability gate の実装済み plan。
- `0609ここからの計画/02_bitget_hyperliquid_venue_design_gate/`: Bitget / Hyperliquid capability design gate の実装済み plan。
- `0610ここからの計画/01_grok_architecture_adoption_review/`: external suggestion review の historical docs-only plan。
- `0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/`: Layer 2.5 Strategy Lab export の実装済み plan。
- `0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/`: Layer 2.6 / 2.7 backtest operator promotion の実装済み plan。
- `0611ここからの計画/02_strategy_lifecycle_control_plane/`: Strategy Lifecycle control plane の実装済み plan。
- `0611ここからの計画/03_paper_observation_cycle_completion/`: paper observation cycle / review の実装済み plan。
- `0616ここからの計画/01_strategy_review_builder/`: Strategy Review Builder の実装済み plan。
- `STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md`: Strategy Review contract の historical record。

## Boundary

- `plan/0609ここからの計画/03_venue_read_only_capability_probe/` は未実装 plan として root `plan/` 側に残す。
- `plan/ねくすと.md` は Strategy Review operator artifact の historical implementation context として root `plan/` 側に残す。
- archive 内の古い pass count、artifact snapshot、phase gate value は現在値ではない。確認時は `./scripts/check` と対象 CLI を再実行する。
