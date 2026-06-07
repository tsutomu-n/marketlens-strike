<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 04 Acceptance

## 1. この計画全体の完成条件

Phase A/B完了時点で、次を満たす。

```text
1. docs/research/ndx/ にスコープ、Seed、Mechanism、Variable、Causal Role、Temporal、Core DAGの説明がある。
2. configs/research_layer_2_2/ndx/ に scope / seed_registry / mechanism_parts / variable_inventory / causal_roles / temporal_availability / core_dag / counter_dags がある。
3. Pydantic modelで各configを読み込める。
4. core_dag.yamlをvalidateできる。
5. forbidden edge linterが未来情報・outcome→treatmentを拒否する。
6. HYP-NDX-001がvalidate/lintを通る。
7. Counter-DAGが最低6つ登録されている。
8. Mermaid / JSON / Markdown report / data requirements を出力できる。
9. 外部APIを呼ばない。
10. Strategy Lab signal / paper / live へ接続しない。
```

## 2. 代表コマンド

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 3. 生成成果物

実行後、次のruntime artifactが生成される。

```text
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/counter_dags.md
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
```

これらは `data/` 配下なのでgit管理対象ではない。テストでは `tmp_path` へ出力する。

## 4. 必須テスト

```text
tests/research/test_hypothesis_scope.py
tests/research/test_seed_registry.py
tests/research/test_mechanism_parts.py
tests/research/test_variable_inventory.py
tests/research/test_causal_roles.py
tests/research/test_temporal_availability.py
tests/research/test_core_dag_contracts.py
tests/research/test_core_dag_validator.py
tests/research/test_core_dag_linter.py
tests/research/test_ndx_core_dag_config.py
tests/research/test_counter_dags.py
tests/research/test_core_dag_export.py
tests/research/test_data_requirements_export.py
tests/research/test_research_dag_commands.py
```

## 5. 必ず落とすケース

```text
- duplicate seed_id
- duplicate mechanism part id
- variable id重複
- unknown causal role
- temporal layer未定義
- edgeが未知nodeを参照
- self-loop
- duplicate edge
- outcome -> treatment_candidate
- t_after_close -> t_after_open
- forbidden_edgesに登録したedgeがedgesに存在
- counter_dagsなし
- data requirement proxyなし
```

## 6. 完成扱いにしないケース

以下は完了ではない。

```text
- docsだけ作ってvalidatorがない
- core_dag.yamlだけ作ってlinterがない
- counter DAGが任意扱い
- reportが出ない
- tests/researchがない
- research-dag-exportがStrategy Lab signalを作る
- paper/live関連のartifactが生成される
```

## 7. Stop Condition

以下のいずれかが発生したら、そのPRでは停止し、別PRへ切る。

```text
- 外部APIが必要になった
- API key / credentialが必要になった
- 新規依存が必要になった
- pyproject.toml / uv.lock変更が必要になった
- Strategy Lab Exportが必要になった
- feature panelやresidual builderを実装したくなった
- Trade[XYZ] readinessを変更したくなった
- paper/live orderに触れたくなった
```

## 8. Review Checklist

```text
[ ] 2.2以前のcontractがある
[ ] HYP-NDX-001はSeedからDAGまで追跡できる
[ ] linterは未来情報を拒否する
[ ] Counter-DAGは必須
[ ] data requirementsは出るが実データ取得しない
[ ] reportはDAGを真因果と主張しない
[ ] strategy_signals.parquetを作っていない
[ ] PaperIntentPreviewを作っていない
[ ] exchange_write_usedが出る経路に触っていない
[ ] ./scripts/checkが通る
```
