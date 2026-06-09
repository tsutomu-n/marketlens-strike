<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 12_TEST_PLAN

## テスト方針

fixture-first。外部API、credentials、networkを使わない。

## 追加テスト

```text
tests/research/test_ndx_start_conditions.py
  - APPROVE_2_3以外は2.3開始不可
  - freeze manifestなしは不可
  - second_review_required=trueは不可

tests/research/test_ndx_source_resolution.py
  - required/optional/deferred分類
  - optional sourceをrequired扱いしない
  - QQQがETF proxyとして記録される

tests/research/test_ndx_fixture_loader.py
  - required columns missing fail
  - duplicate date fail
  - valid fixture pass

tests/research/test_ndx_feature_panel.py
  - qqq_gap計算
  - qqq_open_to_close_return計算
  - factor列生成
  - manifest生成

tests/research/test_ndx_feature_leakage.py
  - source_ts_max > feature_ts fail
  - outcome列をmodel inputに入れるとfail
  - same-day close由来inputをfail

tests/research/test_ndx_residual_model.py
  - rolling modelが未来を見ない
  - min_window未満は予測しない
  - factor_columnsにoutcomeがあるとfail

tests/research/test_ndx_residual_artifact.py
  - residual parquet / manifest生成
  - dag_artifact_hash / model_config_hash保持

tests/research/test_ndx_diagnostics.py
  - diagnostics report生成
  - missing rate / sample count出力

tests/research/test_ndx_refutation.py
  - enabled/deferred counter-DAG categories出力
  - deferred sourceはdeferredとして報告

tests/research/test_ndx_commands.py
  - CLI valid input exit 0
  - invalid input exit 2
```

## 最小検証

```bash
uv run pytest -q tests/research/test_ndx_start_conditions.py
uv run pytest -q tests/research/test_ndx_source_resolution.py
uv run pytest -q tests/research/test_ndx_feature_panel.py
uv run pytest -q tests/research/test_ndx_feature_leakage.py
uv run pytest -q tests/research/test_ndx_residual_model.py
```

## 最終検証

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 禁止

```text
- testsでyfinance/FRED/Alpacaなどのlive fetchを呼ばない
- testsで環境変数credentialsを要求しない
- flaky time-dependent testsを作らない
```
