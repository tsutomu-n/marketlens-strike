<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 05_TASKS

## 実装単位

### T0: 2.2 Start Condition Guard

目的:
- 2.3 CLIが2.2未承認状態で動かないようにする。

作るもの:
```text
src/sis/research/ndx/start_conditions.py
tests/research/test_ndx_start_conditions.py
```

入力:
```text
configs/research_layer_2_2/ndx/
data/research/ndx/review/layer_2_2_exit_decision.json
data/research/ndx/review/layer_2_2_freeze_manifest.json
```

完了条件:
```text
APPROVE_2_3 + freeze manifestあり + second_review_required=false だけ pass。
それ以外は exit code 2 相当の controlled failure。
```

---

### T1: Data Source Resolution Contract

目的:
- DAG上のproxyを、required / optional / deferred sourceへ解決する。

作るもの:
```text
schemas/ndx_data_source_resolution.v1.schema.json
src/sis/research/ndx/contracts.py
src/sis/research/ndx/source_resolution.py
tests/research/test_ndx_source_resolution.py
```

出力:
```text
data/research/ndx/data_source_resolution.json
data/reports/ndx_data_source_resolution_report.md
```

完了条件:
```text
QQQ/SPY/SMH/VIX/DGS10/mega_cap_basket が required。
NQ/VXN/SOX/options/gamma が optional/deferred。
外部APIを呼ばない。
```

---

### T2: Fixture Data Contract

目的:
- 外部APIなしでfeature panelを作れるfixture入力契約を作る。

作るもの:
```text
tests/fixtures/ndx/qqq_bars.csv
tests/fixtures/ndx/spy_bars.csv
tests/fixtures/ndx/smh_bars.csv
tests/fixtures/ndx/vix_daily.csv
tests/fixtures/ndx/dgs10_daily.csv
tests/fixtures/ndx/mega_cap_basket_bars.csv
src/sis/research/ndx/fixture_loader.py
tests/research/test_ndx_fixture_loader.py
```

完了条件:
```text
fixtureからtyped rowsを読める。
missing required columnsを拒否。
date重複を拒否。
timestamp/source_tsを保持。
```

---

### T3: NDX Feature Panel Builder

目的:
- required proxyからfeature panelを生成する。

作るもの:
```text
schemas/ndx_feature_manifest.v1.schema.json
src/sis/research/ndx/feature_panel.py
src/sis/research/ndx/feature_manifest.py
tests/research/test_ndx_feature_panel.py
```

出力:
```text
data/research/ndx/ndx_feature_panel.parquet
data/research/ndx/ndx_feature_manifest.json
data/reports/ndx_feature_panel_report.md
```

完了条件:
```text
qqq_gap, qqq_open_to_close_return, spy_gap, smh_gap, vix_level, vix_change, dgs10_delta, mega_cap_basket_gap を生成。
dag_id / dag_artifact_hashを保持。
```

---

### T4: Feature Leakage Checks

目的:
- 2.3の時点利用可能性を守る。

作るもの:
```text
src/sis/research/ndx/leakage.py
tests/research/test_ndx_feature_leakage.py
```

検査:
```text
source_ts_max <= feature_ts
same-day closeをsignal-side featureに使っていない
outcome列はmodel input列に含まれない
t_after_close列からt_open_plus_buffer列を作らない
```

完了条件:
```text
不正fixtureがfailする。
正しいfixtureがpassする。
```

---

### T5: Rolling OLS Residual Builder

目的:
- known factorsから expected_qqq_gap を作り、open_gap_residualを出す。

作るもの:
```text
schemas/ndx_open_gap_residual_manifest.v1.schema.json
src/sis/research/ndx/residual_model.py
src/sis/research/ndx/residual_artifact.py
tests/research/test_ndx_residual_model.py
tests/research/test_ndx_residual_artifact.py
```

出力:
```text
data/research/ndx/open_gap_residuals.parquet
data/research/ndx/open_gap_residual_manifest.json
data/reports/ndx_open_gap_residual_report.md
```

完了条件:
```text
rolling windowが未来を見ない。
factor_columnsにoutcomeが含まれない。
model_window_start/model_window_endを記録。
model_config_hashを記録。
```

---

### T6: Residual Diagnostics / Neutralization Pre-report

目的:
- 残差が既知ファクターでほぼ説明されていないか診断する。

作るもの:
```text
src/sis/research/ndx/diagnostics.py
src/sis/research/ndx/neutralization.py
tests/research/test_ndx_diagnostics.py
```

出力:
```text
data/reports/ndx_neutralization_report.md
data/research/ndx/neutralized_residuals.parquet
```

完了条件:
```text
raw correlation, factor exposure, sample count, missing rate, sign stability を出す。
ただしStrategy Lab exportはしない。
```

---

### T7: Counter-DAG Refutation Skeleton

目的:
- 2.2のcounter_dagsを実データ診断の観点に変換する。

作るもの:
```text
src/sis/research/ndx/refutation.py
tests/research/test_ndx_refutation.py
```

出力:
```text
data/reports/ndx_counter_dag_refutation_report.md
```

完了条件:
```text
BroadMarketOnly / RatesOnly / SOXOnly(SMH) / MegaCapOnly / VolRegimeOnly / SelectionBias / DataSourceLag の診断項目を出す。
ETFTrackingNoise / FuturesPriceDiscovery / IndexRebalance / MacroEvent / CalendarEffect は deferred として明記。
```

---

### T8: CLI Wrappers

目的:
- operatorが2.3 artifactを再生成できるようにする。

編集:
```text
src/sis/commands/research.py
```

追加CLI:
```bash
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-feature-panel --root configs/research_layer_2_2/ndx --input-root tests/fixtures/ndx --out data/research/ndx
uv run sis research-ndx-residual --feature-panel data/research/ndx/ndx_feature_panel.parquet --out data/research/ndx
uv run sis research-ndx-diagnostics --residuals data/research/ndx/open_gap_residuals.parquet --out data/reports
```

完了条件:
```text
valid fixtureではexit code 0。
invalid inputではexit code 2。
外部APIを呼ばない。
```
