<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 07_FEATURE_PANEL_SPEC

## Feature Panelの目的

HYP-NDX-001のfeatureとoutcomeを同じ表にまとめる。ただし、モデルinputとoutcomeは明確に分ける。

## 出力

```text
data/research/ndx/ndx_feature_panel.parquet
data/research/ndx/ndx_feature_manifest.json
data/reports/ndx_feature_panel_report.md
```

## 必須列

```text
date
qqq_open
qqq_close
qqq_prev_close
qqq_gap
qqq_open_to_close_return
spy_gap
smh_gap
vix_level
vix_change
dgs10_delta
mega_cap_basket_gap
feature_ts
source_ts_max
source_tier
dag_id
dag_artifact_hash
```

## 列の意味

| Column | 意味 | model input? |
|---|---|---|
| qqq_gap | actual observed gap | target for expected gap model |
| qqq_open_to_close_return | same-day outcome | no |
| spy_gap | broad market factor | yes |
| smh_gap | semiconductor proxy | yes |
| vix_change | volatility change | yes |
| dgs10_delta | rates factor | yes |
| mega_cap_basket_gap | mega-cap factor | yes |
| feature_ts | featureが利用可能な時刻 | audit |
| source_ts_max | source最大時刻 | leakage check |
| dag_artifact_hash | 2.2 freezeとの紐付け | lineage |

## Leakage rules

```text
- qqq_open_to_close_return は outcome列。model inputには使わない
- qqq_close は qqq_open_to_close_return 計算にだけ使う
- same-day close 由来の値を expected_qqq_gap に使わない
- source_ts_max > feature_ts の行は fail または block
- missing source_tier は fail
```

## 欠損処理

```text
required source欠損:
  rowをdropし、manifestにdrop countを残す

optional/deferred source欠損:
  feature panel生成を止めない

date alignment欠損:
  left/right coverage reportを出す

market holiday / non-overlap:
  rowを作らず manifestに記録
```
