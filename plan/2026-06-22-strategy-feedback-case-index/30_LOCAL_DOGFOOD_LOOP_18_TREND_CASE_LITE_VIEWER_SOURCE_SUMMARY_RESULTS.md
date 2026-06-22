<!--
作成日: 2026-06-22_22:15 JST
更新日: 2026-06-22_22:18 JST
-->

# Local Dogfood Loop 18 Trend Case Lite Viewer Source Summary Results

## 結論

A: `trend_pullback_user_v1` の Local dogfood を継続した。

Loop 16-17 で backtest result / pack / suite / comparison の Viewer summary は改善したが、`strategy_case_lite.v1` 自体の Viewer summary は薄かった。Case Lite JSON には `artifact_count`、`timeline_count`、`source_artifacts` があるのに、Viewer 一覧では `latest_status` ほぼ単体でしか読めず、Case が何個の artifact を束ね、最初にどの source artifact から始まっているかを見落としやすかった。

修正後は、Case Lite の Viewer summary に artifact count、timeline count、first source artifact type / path / schema / hash が出る。

これは read-only な読みやすさ改善であり、Runtime Observation / Learning Event の生成、Input Feedback proposal の生成、paper / live 実行許可、profit claim ではない。

## 1. 計画

対象:

- lane: `Local dogfood`
- selection: `A`
- strategy_id: `trend_pullback_user_v1`
- primary viewer:
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json`
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`

完了条件:

- 現物の `strategy_case_lite.v1` にある count / source artifact 情報を確認する。
- Viewer compact summary に、Case Lite を一覧で読むための最小 key だけを追加する。
- focused RED / GREEN を残す。
- Trend Viewer を再生成し、現物 manifest に summary が出ることを確認する。
- docs を更新し、focused tests と docs check を通す。

やらないこと:

- Runtime Observation / Learning Event の捏造。
- Input Feedback proposal の無理な生成。
- source contract の自動更新。
- credential、network、paper order、live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

修正前の Trend Viewer 現物:

```text
strategy_case_lite.v1:
- status=READY_FOR_HUMAN_REVIEW
- summary.latest_status=READY_FOR_HUMAN_REVIEW
- summary.strategy_id=trend_pullback_user_v1
- summary.paper_execution_allowed=false
- summary.live_allowed=false
```

Case Lite JSON 側には次が存在していた。

```text
strategy_case_lite.v1:
- artifact_count=7
- timeline_count=7
- first source artifact type=strategy_input_contract_validation
- first source artifact path=data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json
- first source artifact schema=strategy_input_contract_validation.v1
- first source artifact hash=sha256:c56173f46090f5bc95ab53100f57434b73d7761416312bb6bc74205da54bed3e
```

判断:

- Case Lite は複数 artifact を束ねる artifact なので、count と first source は一覧 summary に出す価値がある。
- source artifact hash は traceability のための表示であり、artifact の内容を docs に固定するものではない。
- Case Lite の source artifact を Viewer が補正・再構築してはいけない。既存 JSON の値を compact summary として読むだけに止める。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - compact summary key に次を追加。
    - `artifact_count`
    - `timeline_count`
    - `first_source_artifact_type`
    - `first_source_artifact_path`
    - `first_source_artifact_schema_version`
    - `first_source_artifact_hash`
  - `strategy_case_lite.v1` の `source_artifacts` から first source artifact を抽出する処理を追加。

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - `test_strategy_workbench_viewer_uses_case_lite_latest_status_as_status_badge` に Case Lite count / first source artifact summary の期待値を追加。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Case Lite の compact summary に artifact count / timeline count / first source artifact summary が出ることを明記。

再生成した local artifact:

- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`
- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json`

再生成コマンド:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/research/strategy_backtest_metrics.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --artifact data/research/backtest_suite/strategy_backtest_suite_result.json \
  --artifact data/research/backtest_compare/strategy_backtest_comparison.json \
  --artifact data/strategy_reviews/dogfood-operator-current/review_manifest.json \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json \
  --out data/local_dogfood/2026-06-22-trend-pullback/viewer \
  --viewer-id trend-pullback-local-dogfood-viewer \
  --replace-existing
```

再生成結果:

```text
status=pass
artifact_count=9
boundary_violation_count=0
```

## 4. 修正後の現物確認

Viewer manifest:

```text
strategy_case_lite.v1:
- artifact_count=7
- timeline_count=7
- first_source_artifact_type=strategy_input_contract_validation
- first_source_artifact_path=data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json
- first_source_artifact_schema_version=strategy_input_contract_validation.v1
- first_source_artifact_hash=sha256:c56173f46090f5bc95ab53100f57434b73d7761416312bb6bc74205da54bed3e
- latest_status=READY_FOR_HUMAN_REVIEW
- live_allowed=false
- paper_execution_allowed=false
```

## 5. 検証

RED:

```text
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_uses_case_lite_latest_status_as_status_badge -q
-> failed: KeyError: 'artifact_count'
```

GREEN / focused verification:

```text
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_uses_case_lite_latest_status_as_status_badge -q
-> 1 passed

uv run ruff format --check src/sis/strategy_workbench_viewer/service.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py
-> 2 files already formatted

uv run ruff check src/sis/strategy_workbench_viewer/service.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py
-> All checks passed

uv run pytest tests/strategy_workbench_viewer -q
-> 14 passed
```

Full check:

```text
./scripts/check
-> 1528 passed in 69.21s
```

## 6. 残リスク

- A は読みやすさの改善が進んだが、Runtime Observation / Learning Event はまだない。
- したがって A から Input Feedback proposal を作る条件はまだ満たしていない。
- `READY_FOR_HUMAN_REVIEW` は human review 用の状態であり、paper / live 実行許可ではない。
- Case Lite の source artifact hash は traceability のための表示であり、artifact freshness や alpha 証明ではない。
