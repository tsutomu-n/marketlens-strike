<!--
作成日: 2026-06-07_20:09 JST
更新日: 2026-06-07_20:09 JST
-->

# Layer 2.2 Implementation Record

## 結論

Layer 2.2 DAG Compiler foundation は `HYP-NDX-001` の local-only 研究 artifact 基盤として実装済みである。

完成扱い:
- NDX / QQQ の research scope、seed、mechanism parts、variable inventory、causal roles、temporal availability を YAML と Pydantic contract で読める。
- `HYP-NDX-001` core DAG を validate / lint できる。
- forbidden edge、future-to-signal、outcome-to-treatment を拒否できる。
- counter DAG refs と counter DAG registry を必須 artifact として検証できる。
- JSON / Mermaid / counter DAG Markdown / data requirements / Markdown report を生成できる。

## 実装範囲

追加した主な領域:
- `configs/research_layer_2_2/ndx/`
- `docs/research/ndx/`
- `schemas/research_*.schema.json`
- `schemas/core_dag.v1.schema.json`
- `schemas/counter_dag.v1.schema.json`
- `src/sis/research/hypothesis/`
- `src/sis/research/dag/`
- `tests/research/`

変更した主な領域:
- `src/sis/commands/research.py`
- `scripts/check_current_docs.py`
- `tests/test_docs_current_truth.py`

## CLI

利用できる CLI:

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
```

`research-dag-validate` は core DAG 単体ではなく、同じ directory にある次の companion config も必須として検証する。

- `variable_inventory.yaml`
- `causal_roles.yaml`
- `temporal_availability.yaml`
- `counter_dags.yaml`

## 追加監査で修正した点

初回実装後の追加監査で、core DAG YAML だけが通る余地があることを検出した。Layer 2.2 は前段 contract 込みで成立するため、次を fail 条件にした。

- companion config 欠落
- DAG node が variable inventory にない
- DAG node が causal roles にない
- DAG node role と causal role assignment の不一致
- causal role が variable role candidates にない
- DAG node が temporal availability にない
- temporal availability と variable temporal class の不一致
- `counter_dag_refs` 欠落
- YAML duplicate key

## 明示的にやっていないこと

今回の実装では次を行っていない。

- external API call
- Bitget network call
- Trade[XYZ] readiness 変更
- backtest engine 変更
- Strategy Lab export
- `strategy_signals.parquet` 生成
- PaperIntentPreview 生成
- paper/live order
- wallet / signing / exchange write

## 検証記録

確認済み:

```text
HEAD: ff42f5356097924e3c6e420ff2c1c5bc04465f58
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
  status=pass
  dag_id=HYP-NDX-001
  node_count=9
  edge_count=8
  warning_count=0

uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
  status=pass
  core_dag_json=data/research/ndx/core_dag.json
  core_dag_mermaid=data/research/ndx/core_dag.mmd
  counter_dags_report=data/research/ndx/counter_dags.md
  data_requirements=data/research/ndx/data_requirements.yaml
  report=data/reports/ndx_core_dag_report.md

uv run pytest -q tests/research
  30 passed

uv run python scripts/check_current_docs.py
  checked 96 current docs: metadata, links, EOF, and legacy roots ok

./scripts/check
  875 passed
```

Generated artifacts under `data/` are runtime outputs and are gitignored.

## 次の候補

次に進むなら別計画として扱う。

- Phase C: feature panel / residual builder
- data requirement から実データ provider 方針の確定
- Strategy Lab export contract
- 実データ取得の利用規約、rate limit、保存方針

T5b Bitget credentialed read-only smoke と T6 demo order lifecycle は、この Layer 2.2 実装とは別タスクであり、credentials と明示許可がない限り進めない。
