<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 06 Open Questions

## 結論

この計画は、コーダーが実装を開始できる粒度まで決めている。以下は未決だが、Phase A/Bの実装を止めるものではない。

## A. 実装開始前に未決でもよいもの

```text
- NQ futures data provider
- SOXを直接使うかSMH proxyにするか
- VXNを取るかVIX proxyにするか
- mega-cap basketの正確な構成比
- rolling regressionのwindow
- neutralization method
- Strategy Lab export形式
- 評価指標
```

これらは Phase C 以降。

## B. Phase A/Bで決めるもの

```text
- scope.yamlのincluded/excluded
- seed_registry.yamlの初期Seed
- mechanism_parts.yamlの初期部品
- variable_inventory.yamlの初期変数
- causal_roles.yamlのrole
- temporal_availability.yamlの時点分類
- core_dag.yamlのnode/edge/forbidden_edges
- counter_dags.yamlの反証DAG
```

## C. コーダーが質問せず進めてよい判断

```text
- YAML + Pydantic + JSON Schema + pytestで実装する
- external APIは呼ばない
- paper/liveは触らない
- Strategy Lab exportはまだ作らない
- CLIは research-dag-validate / research-dag-export の2つまでなら作ってよい
- generated dataはdata/research/ndx/へ出す
- testsではtmp_pathを使う
```

## D. コーダーが停止して確認するべき判断

```text
- pyproject.tomlを変更したくなった
- uv.lockを変更したくなった
- external APIが必要になった
- data/research/strategy_signals.parquetを作りたくなった
- paper/live artifactに接続したくなった
- Trade[XYZ] readinessを変更したくなった
- backtest engineを触りたくなった
```

## E. T5b / T6 の扱い

```text
T5b / T6 は今回進めない。
今回の範囲は local / docs / config / schema / tests / report に閉じる。
Bitget demo read-only networkやdemo order lifecycleは本計画外。
```

## F. 最終的な判断

```text
未決項目は残るが、Phase A/Bは実装可能。
この計画の目的は、すべての研究を終わらせることではなく、2.2を安全に始められる土台を完成させること。
```
