<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# Appendix D Risk Register

## 主要リスク

| ID | リスク | 発生条件 | 影響 | 対策 |
|---|---|---|---|---|
| R1 | 2.2単体実装 | Variable/role/time前提なしでDAGを書く | 空中戦になる | Scope→Seed→Inventory→Role→Temporalを先に実装 |
| R2 | 売買ロジック化 | open_gap_residualからsideを出す | backtest沼 | Phase A/Bではsignal生成禁止 |
| R3 | 外部API混入 | QQQ/SPYを取りたくなる | 再現性低下 | Data requirements exportまで |
| R4 | Strategy Lab直結 | strategy_signals.parquetを出す | paper/liveへ近づく | Phase Cへ延期 |
| R5 | DAG真因果主張 | reportが因果証明と書く | 誤解 | hypothesis artifactと明記 |
| R6 | Counter-DAG省略 | 自説だけ記録 | 反証不能 | counter DAGを必須 |
| R7 | Outcome leakage | O2Cを説明変数に混ぜる | 無効な研究 | temporal linter |
| R8 | Existing repo boundary破壊 | paper/execution/backtestを触る | 安全境界破壊 | 触ってよい範囲を限定 |
| R9 | NQ/options/gammaへ拡張 | データ不足 | 実装膨張 | 後続Phaseへ切る |
| R10 | stale docs | 古い検証値を書く | 誤読 | pass countを固定しない |
