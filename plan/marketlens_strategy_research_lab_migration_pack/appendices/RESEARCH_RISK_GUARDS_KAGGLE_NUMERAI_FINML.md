# Research Risk Guards From Kaggle / Numerai / Financial ML

## Leakage Guard

```text
- feature_ts <= signal_ts
- quote_ts <= signal_ts
- label_horizon_minutesを明示
- purge_minutes / embargo_minutesを必須化
```

## Era Evaluation

```text
- era_unitを持つ
- per-era metricsを出す
- all-period metricだけで採用しない
```

## Rank / Tail

```text
- raw_scoreだけでなくrank_score / percentile_rank / tail_bucketを持つ
- candidate選定ではtop tailを意識する
```

## Unique Contribution / Exposure Hook

```text
- unique_contribution_score
- index_exposure_score
- exposure_refs
```

初期は完全実装しない。hookだけ入れる。

## Trial Count Guard

```text
- trial_countを隠さない
- parameter_space_hashを残す
- selected_for_next_stageを明示
- best resultだけを保存しない
```
