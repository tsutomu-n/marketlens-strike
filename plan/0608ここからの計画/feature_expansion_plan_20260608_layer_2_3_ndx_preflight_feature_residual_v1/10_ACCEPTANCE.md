<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 10_ACCEPTANCE

## 実装完了条件

### コマンド

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx

uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx

uv run sis research-ndx-feature-panel \
  --root configs/research_layer_2_2/ndx \
  --input-root tests/fixtures/ndx \
  --out data/research/ndx

uv run sis research-ndx-residual \
  --feature-panel data/research/ndx/ndx_feature_panel.parquet \
  --out data/research/ndx

uv run sis research-ndx-diagnostics \
  --residuals data/research/ndx/open_gap_residuals.parquet \
  --out data/reports

uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

### 生成物

```text
data/research/ndx/data_source_resolution.json
data/reports/ndx_data_source_resolution_report.md

data/research/ndx/ndx_feature_panel.parquet
data/research/ndx/ndx_feature_manifest.json
data/reports/ndx_feature_panel_report.md

data/research/ndx/open_gap_residuals.parquet
data/research/ndx/open_gap_residual_manifest.json
data/reports/ndx_open_gap_residual_report.md

data/research/ndx/neutralized_residuals.parquet
data/reports/ndx_neutralization_report.md
data/reports/ndx_counter_dag_refutation_report.md
```

### 成功条件

```text
- 外部APIなしでfixture modeが通る
- credentials不要
- dependency追加なし
- feature leakage checkがpass
- residual modelが未来を見ない
- all outputs include dag_id and dag_artifact_hash
- Strategy Lab exportをしない
- paper/live/order pathに触らない
```

### 失敗条件

```text
- same-day closeがmodel inputに入る
- source_ts_max > feature_ts が許可される
- missing required sourceが黙って通る
- optional/deferred sourceをrequired扱いする
- open_gap_residualからlong/short sideを出す
- strategy_signals.parquetを生成する
```
