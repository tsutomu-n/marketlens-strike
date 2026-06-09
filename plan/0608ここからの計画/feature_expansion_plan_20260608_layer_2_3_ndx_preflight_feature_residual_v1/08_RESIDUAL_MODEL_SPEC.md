<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 08_RESIDUAL_MODEL_SPEC

## Residual Modelの目的

known factorsから `expected_qqq_gap` を推定し、実際の `qqq_gap` との差を `open_gap_residual` として保存する。

## 初期モデル

```text
rolling OLS
```

dependency追加は禁止。scikit-learn / statsmodelsは使わない。  
既存依存の範囲で実装する。必要なら小さな線形回帰helperを自前実装する。

## 入力

```text
feature_panel:
  data/research/ndx/ndx_feature_panel.parquet

target:
  qqq_gap

known_factors:
  spy_gap
  smh_gap
  vix_change
  dgs10_delta
  mega_cap_basket_gap
```

## 出力列

```text
date
actual_qqq_gap
expected_qqq_gap
open_gap_residual
qqq_open_to_close_return
model_window_start
model_window_end
model_training_row_count
factor_columns
model_config_hash
dag_id
dag_artifact_hash
feature_manifest_hash
```

## Rolling rule

```text
For each prediction date t:
  train on rows strictly before t
  require min_window rows
  fit OLS on known factors -> qqq_gap
  predict expected_qqq_gap for t
  residual = actual_qqq_gap - expected_qqq_gap
```

## 禁止

```text
- qqq_open_to_close_return をfactorに入れる
- qqq_close由来のsame-day値をfactorに入れる
- prediction date t をtraining windowへ含める
- future rowsをtrainingに使う
- hyperparameter searchを行う
- model結果でlong/shortを出す
```

## 最小config例

```yaml
schema_version: ndx_residual_model_config.v1
model_id: ndx_open_gap_residual_rolling_ols_v1
dag_id: HYP-NDX-001
target_column: qqq_gap
outcome_column: qqq_open_to_close_return
factor_columns:
  - spy_gap
  - smh_gap
  - vix_change
  - dgs10_delta
  - mega_cap_basket_gap
min_window: 60
prediction_mode: expanding_or_rolling
regularization: none
```
