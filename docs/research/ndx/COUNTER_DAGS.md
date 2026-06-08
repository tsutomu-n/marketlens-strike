<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-08_18:01 JST
-->

# Counter DAGs

Counter DAG は自説の別説明を保存するための必須 artifact である。Core DAG が lint を通っても、counter DAG がない場合はレビュー不足として扱う。

初期 counter DAG:
- `BroadMarketOnlyDAG`
- `RatesOnlyDAG`
- `SOXOnlyDAG`
- `MegaCapOnlyDAG`
- `VolRegimeOnlyDAG`
- `SelectionBiasDAG`
- `ETFTrackingNoiseDAG`
- `FuturesPriceDiscoveryDAG`
- `IndexRebalanceDAG`
- `MacroEventDAG`
- `CalendarEffectDAG`
- `DataSourceLagDAG`

正本 config は `configs/research_layer_2_2/ndx/counter_dags.yaml`。
