<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 05 Acceptance

## 完了条件総括

この機能拡張は、以下を満たした時点で完了扱いにする。

```text
1. Phase A/B の YAML contracts がすべて存在する。
2. HYP-NDX-001 Core DAG が validate / lint を通過する。
3. HYP-NDX-001 に最低8本の counter-DAG がある。
4. Core DAG report / Mermaid / JSON / data requirements が生成される。
5. 全テストが外部API・credentialsなしで通る。
6. paper/live/order/backtest/Strategy Lab export へ接続していない。
```

## 生成物

期待する生成物:

```text
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/counter_dags.md
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
```

これらは runtime/generated artifact なので git commit 対象とは限らない。必要に応じて `.gitignore` 方針に従う。

## CLI期待出力

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
```

期待:

```text
exit code: 0
contains:
  dag_id=HYP-NDX-001
  lint_errors=0
  counter_dag_count>=8
```

```bash
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
```

期待:

```text
exit code: 0
writes:
  data/research/ndx/core_dag.json
  data/research/ndx/core_dag.mmd
  data/research/ndx/counter_dags.md
  data/research/ndx/data_requirements.yaml
  data/reports/ndx_core_dag_report.md
```

## 必須テスト

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 合格しなければならないnegative tests

```text
1. unknown nodeへのedgeはfail。
2. self-loopはfail。
3. duplicate node idはfail。
4. duplicate edgeはfail。
5. unknown roleはfail。
6. outcome -> treatment_candidate edgeはfail。
7. t_after_close -> t_open_plus_buffer edgeはfail。
8. forbidden_edgesに登録されたedgeがedgesにある場合はfail。
9. core_dag nodeがvariable_inventoryに存在しない場合はfail。
10. causal_rolesとcore_dag roleが矛盾した場合はfail。
11. HYP-NDX-001のcounter-DAGが8本未満ならfail。
12. optional_provider_dependent sourceをrequired proxyにした場合はwarning以上。
```

## まだ未実装でよいもの

```text
- feature panel
- residual calculation
- neutralization
- strategy_signals.parquet
- evaluation trial
- backtest
- paper candidate
- PaperIntentPreview
- external API connectivity
```

## 人間レビュー条件

生成された `ndx_core_dag_report.md` で、以下を人間が確認する。

```text
- NDX / QQQ / NQ が混ざっていない。
- open_gap_residual は outcome を使っていない。
- SPX / rates / SOX/SMH / VIX/VXN / mega-cap / ETF noise / futures price discovery の反証経路がある。
- Index methodology部品が最低限登録されている。
- 2.3へ進む前にDAGとしてレビューできる。
```
