<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 11_TARGET_FILE_MAP

## Create

```text
configs/research_layer_2_3/ndx/
  source_resolution.yaml
  feature_panel.yaml
  residual_model.yaml
  diagnostics.yaml

schemas/
  ndx_data_source_resolution.v1.schema.json
  ndx_feature_manifest.v1.schema.json
  ndx_open_gap_residual_manifest.v1.schema.json
  ndx_diagnostics_manifest.v1.schema.json

src/sis/research/ndx/
  __init__.py
  contracts.py
  start_conditions.py
  source_resolution.py
  fixture_loader.py
  feature_panel.py
  feature_manifest.py
  leakage.py
  residual_model.py
  residual_artifact.py
  diagnostics.py
  neutralization.py
  refutation.py
  reports.py

tests/research/
  test_ndx_start_conditions.py
  test_ndx_source_resolution.py
  test_ndx_fixture_loader.py
  test_ndx_feature_panel.py
  test_ndx_feature_leakage.py
  test_ndx_residual_model.py
  test_ndx_residual_artifact.py
  test_ndx_diagnostics.py
  test_ndx_refutation.py
  test_ndx_commands.py

tests/fixtures/ndx/
  qqq_bars.csv
  spy_bars.csv
  smh_bars.csv
  vix_daily.csv
  dgs10_daily.csv
  mega_cap_basket_bars.csv

docs/research/ndx/
  10_LAYER_2_3_NDX_PREFLIGHT.md
```

## Edit

```text
src/sis/commands/research.py
scripts/check_current_docs.py
  docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md をcurrent docsへ入れる場合のみ
```

## No-touch

```text
src/sis/research/strategy_lab/
src/sis/research_protocol/
src/sis/backtest/
src/sis/paper/
src/sis/execution/
src/sis/venues/trade_xyz/
src/sis/bot/
src/sis/real_market/providers/
schemas/strategy_signal.v1.schema.json
schemas/paper_intent_preview.v1.schema.json
pyproject.toml
uv.lock
.github/workflows/ci.yml
```

## Runtime outputs

```text
data/research/ndx/
data/reports/
```

`data/` はgit管理外のruntime artifactとして扱う。
