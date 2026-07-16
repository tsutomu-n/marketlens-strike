<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA3部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A3 — ML Data Truth

## A3.1 ゴール定義

XGBoost/LightGBMを動かす前に、Point-in-time Feature、Future Path Primitive、Label View、Discovery Windowを、再現可能なDataset Artifactとして完成させる。

A3は予測モデルを作らない。MLが将来情報、古いSnapshot、Symbol跨ぎ、重複Labelを学習しないためのデータ真実性を確立する。

## A3.2 Entry Criteria

- A2が`IMPLEMENTATION_COMPLETE`。
- Candle/Funding SourceのManifestとHashを取得できる。
- Candle Timestamp Semanticsを公式仕様とFixtureで確認可能。
- Initial Horizonを満たす履歴期間があるか測定可能。

## A3.3 対象範囲

### 実装する

- Source Adapter
- Polars Lazy Feature Builder
- Candle Completion Policy
- Funding Backward As-of Join
- Feature Manifest
- Ex-ante Risk Scale
- Future Path Primitive
- Label View
- Same-bar Ambiguity
- Horizon Censoring
- Event Cluster
- Four-window Discovery Split
- Label Interval Purge
- Dataset Diagnostics
- Public CLI

### 実装しない

- Model Training
- Hyperparameter Search
- Tree Rule
- Fee/Slippage/PnL
- Mark/Index/OIのHistorical補間
- Sealed Test

## A3.4 対象ファイル

```text
src/sis/strategy_idea_seeds/ml/data/
  source_adapter.py
  timestamp_semantics.py
  feature_specs.py
  feature_builder.py
  funding_join.py
  risk_scale.py
  path_primitives.py
  label_views.py
  event_clusters.py
  discovery_windows.py
  diagnostics.py
  artifacts.py

schemas/
  strategy_idea_seed_feature_manifest.v1.schema.json
  strategy_idea_seed_path_manifest.v1.schema.json
  strategy_idea_seed_discovery_windows.v1.schema.json
  strategy_idea_seed_dataset_diagnostics.v1.schema.json

configs/strategy_idea_seeds/ml/
  feature_set_v1.yaml
  tail_path_views_v1.yaml
  discovery_windows_v1.yaml

tests/strategy_idea_seeds/ml/data/
```

## A3.5 Candle Timestamp Semantics

実装開始時に次を確認する。

1. API仕様上、Candle TimestampがOpen TimeかClose Timeか。
2. Existing Source FetcherがCurrent Bucketを除外しているロジック。
3. FixtureのTimestampがInterval境界に一致するか。

Open Timeの場合:

```text
bar_open_at = ts
bar_close_at = ts + timeframe
decision_at = bar_close_at
```

Featureは`decision_at`までに完了したBarだけを使う。

意味を確認できなければ`TIMESTAMP_SEMANTICS_UNKNOWN`でA3 Current Data Operationalを停止する。Fixtureでは明示契約を使う。

## A3.6 Initial Feature Set

### Price/Return

```text
log_return_5m
log_return_15m
log_return_1h
log_return_4h
log_return_1d
distance_from_high_1d
distance_from_low_1d
```

### Volatility/Range

```text
realized_volatility_1h
realized_volatility_4h
realized_volatility_1d
range_compression_1h_vs_1d
true_range_fraction
```

### Volume/Turnover

```text
base_volume_ratio_1h_vs_1d
quote_turnover_ratio_1h_vs_1d
quote_turnover_z_1d
```

### Funding

```text
funding_rate_bps
funding_change_bps
funding_sign_duration_events
funding_age_seconds
```

### Calendar

```text
hour_utc_sin
hour_utc_cos
weekday
```

Mark/Index/OI/Bid/AskはHistorical Sourceが確認されるまでFeature Setへ入れない。

## A3.7 Funding As-of Join

Polars `join_asof`を使う。

```text
left: completed candle rows
right: funding events
by: symbol
left_on: decision_at
right_on: available_at
strategy: backward
```

必須条件:

- 両FrameをSymbol/TimestampでSort。
- `available_at <= decision_at`。
- `funding_source_at`と`funding_age_seconds`を保存。
- `funding_max_age_minutes`をConfigで明示。
- Tolerance超過はnull。
- Missingを0へ置換しない。
- Exact Matchを許可するのは`available_at <= decision_at`が明示される場合だけ。

## A3.8 Ex-ante Risk Scale

Stopが未定義のためRを使わない。Path正規化用ScaleをDecision Time以前の情報から計算する。

初期方式:

```text
risk_scale_fraction =
  max(
    past_realized_volatility_scaled_to_horizon,
    configured_volatility_floor_fraction
  )
```

保存:

```text
risk_scale_id
risk_scale_fraction
risk_scale_inputs_start_at
risk_scale_inputs_end_at
```

Raw Excursion Fractionも必ず保存し、Scale定義変更で再利用できるようにする。

## A3.9 Future Path Primitive

各Decision Row/Horizonについて保存する。

```text
label_start_at
label_end_at
full_horizon_available

max_up_excursion_fraction
max_down_excursion_fraction
normalized_up_multiple
normalized_down_multiple

first_up_hit_at_by_threshold
first_down_hit_at_by_threshold
adverse_before_up_hit_by_threshold
adverse_before_down_hit_by_threshold

both_sides_hit
first_side
barrier_order_ambiguous
time_to_hit
```

Label Enumを直接正本にしない。Primitiveを正本とし、Label Viewは派生Artifactとする。

## A3.10 Same-bar Ambiguity

同一OHLC Bar内で上下Barrierを両方通過した場合:

```text
barrier_order_ambiguous=true
first_side=UNKNOWN
```

禁止:

- Candle色から順序推定
- Target先行固定
- Stop先行固定
- 都合のよい順序選択

Lower-timeframe Sourceが明示的にある場合だけ別Resolverで解決する。Core v1初期では解決しない。

## A3.11 Label View

PrimitiveからConfigで次を作る。

```text
UP_CLEAN_CONTINUATION
UP_DIRTY_CONTINUATION
DOWN_CLEAN_CONTINUATION
DOWN_DIRTY_CONTINUATION
UP_DEEP_ADVERSE_REVERSAL
DOWN_DEEP_ADVERSE_REVERSAL
UP_DELAYED_BREAKOUT
DOWN_DELAYED_BREAKOUT
TWO_SIDED_EXPANSION
CENSORED_NO_HIT
BARRIER_ORDER_AMBIGUOUS
```

Long/Shortを対称に実装する。Threshold、Adverse Limit、Delayed境界はConfig Hashへ含める。

## A3.12 Event Cluster

隣接RowのHorizonが重複するため、Support Row数だけでは証拠を水増しする。

同一Symbol、Direction、Label FamilyでLabel Intervalが連結するRowをInterval GraphのConnected Componentとしてまとめる。

保存:

```text
event_cluster_id
row_count
interval_start
interval_end
symbol
direction
label_family
```

## A3.13 Discovery Window

```text
fit
early_stop
rule_development
rule_observation
```

Rules:

- 時系列順を維持。
- Random Shuffle禁止。
- `fit`のLabel Endが`early_stop`開始以降ならPurge。
- `early_stop`のLabel Endが`rule_development`開始以降ならPurge。
- `rule_development`のLabel Endが`rule_observation`開始以降ならPurge。
- Tail Thresholdは`fit`で決定。
- `rule_observation`をModel、Path選択、Distillationへ渡さない。
- Sealed TestはFoundryへ含めない。

Scikit-learnの`TimeSeriesSplit.gap`は参考にできるが、Rowごとの`label_end_at`を使うCustom Purgeを必須とする。

## A3.14 Dataset Diagnostics

Label/Horizon/Foldごとに出す。

```text
row_count
symbol_count
date_range
missing_feature_rate
positive_row_count
positive_event_count
censored_count
ambiguous_count
purged_count
funding_stale_count
```

Core Codeに普遍的な最小Positive数を埋め込まない。Production Configで明示し、未達時はA4対象から除外する。

## A3.15 Public CLI

```bash
uv run sis strategy-idea-seeds-ml-dataset-build   --source-root <path>   --feature-config <path>   --label-config <path>   --split-config <path>   --out <path>
```

## A3.16 詳細タスク

| ID | タスク |
|---|---|
| A3-01 | Candle Timestamp Semantics Probeを実装 |
| A3-02 | Lazy Source Adapterを実装 |
| A3-03 | Feature Spec/Unit/Availability Modelを実装 |
| A3-04 | Symbol単位Rolling Featureを実装 |
| A3-05 | Funding backward as-of joinを実装 |
| A3-06 | Feature Manifest/Diagnosticsを実装 |
| A3-07 | Ex-ante Risk Scaleを実装 |
| A3-08 | Future Path Primitiveを実装 |
| A3-09 | Same-bar Ambiguity/Censoringを実装 |
| A3-10 | Label Viewを実装 |
| A3-11 | Event Clusterを実装 |
| A3-12 | Four-window Split/Purgeを実装 |
| A3-13 | Artifact/CLIを実装 |
| A3-14 | Synthetic/Leakage/As-of Testを追加 |

## A3.17 Test方針

### Leakage

- 将来Candleを変更しても過去Featureが不変。
- ETH追加でBTC Featureが不変。
- Funding Eventを未来へ移すとJoinされない。
- Stale FundingがTolerance超過でnull。
- Current incomplete BarがFeatureへ入らない。

### Path

Synthetic Path:

```text
100 → 95 → 150
100 → 150 → 95
100 → 110 → 90
100 → 90 → 110
```

を別Primitive/Labelへ分類する。

### Split

- Label Interval重複RowをPurge。
- Rule ObservationがDevelopment Codeへ渡されない。
- ThresholdがFit以外から計算されない。
- Random Split Configを拒否。

## A3.18 完了条件

### `IMPLEMENTATION_COMPLETE`

- FixtureからFeature、Primitive、Label、Split、Diagnosticsが生成される。
- Leakage、As-of、Ambiguity、Censoring、Purge Testが成功する。
- A4を開始可能なLabel/Foldと不足Label/Foldを区別できる。
- Model依存なしでCore CIが通る。

### `CURRENT_DATA_OPERATIONAL`

- Local HistoryからPoint-in-time Datasetを作れる。
- Timestamp Semanticsを確認済み。
- History不足、Positive不足、Source不足をDiagnosticとして出せる。
- 不足を0埋めまたは推測で補わない。

## A3.19 停止・再設計条件

- Candle Timestamp Semanticsを確認できない。
- Feature PanelにFuture列が混ざる。
- Funding JoinでSource Time/Ageを失う。
- Same-bar順序を決め打ちする。
- Label Viewだけ保存しPrimitiveを失う。
- `rule_observation`がRule作成へ漏れる。
- 履歴不足をFixture成功で隠す。

## A3.20 Gate G3

```text
CONTINUE_A4
PAUSE_ML_DATA_INSUFFICIENT
REVISE_A3
```

ML LaneをPauseしてもTechnical/LLMは継続できる。
