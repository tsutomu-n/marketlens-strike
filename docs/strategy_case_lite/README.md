<!--
作成日: 2026-06-19_01:02 JST
更新日: 2026-07-01_23:09 JST
-->

# Strategy Case Lite

## 結論

`strategy-case-lite-update` は、同じ strategy の stage decision、runtime observation、drift review、learning event、revision request、authoring update handoff、micro live plan、live observation、scale decision、next scale plan、追加の JSON artifact を読み、軽量な case timeline を作る first slice です。

これは registry の最終形ではありません。まず個人運用で artifact を探し回らないように、source path / hash / schema version / status / action / blocked reason を strategy 単位に束ねます。

paper / live の permission artifact ではありません。

## Command

```bash
uv run sis strategy-case-lite-update \
  --strategy-id <strategy-id> \
  --stage-decision data/strategy_stage_decisions/<id>/strategy_stage_decision.json \
  --runtime-observation data/runtime_observations/<strategy-id>/<session-id>/strategy_runtime_observation_manifest.json \
  --drift-review data/strategy_drift_reviews/<strategy-id>/<session-id>/paper_vs_backtest_drift_review.json \
  --micro-live-plan data/strategy_micro_live_plans/<strategy-id>/strategy_micro_live_plan.json \
  --live-observation data/strategy_live_observations/<strategy-id>/strategy_live_observation_manifest.json \
  --scale-decision data/strategy_scale_decisions/<strategy-id>/strategy_scale_decision.json \
  --next-scale-plan data/strategy_next_scale_plans/<strategy-id>/strategy_next_scale_plan.json \
  --artifact data/research/strategy_backtest_metrics.json \
  --out data/strategy_cases
```

入力 option は複数回指定できます。

- `--stage-decision`
- `--runtime-observation`
- `--drift-review`
- `--learning-event`
- `--revision-request`
- `--authoring-handoff`
- `--micro-live-plan`
- `--live-observation`
- `--scale-decision`
- `--next-scale-plan`
- `--artifact`

`--artifact` は追加の JSON artifact 用です。既知 schema は型付き artifact として記録し、未知 schema は `generic` として記録します。現時点で型付きになる追加 schema は次です。

- `strategy_input_contract_validation.v1`
- `strategy_authoring_backtest_result.v1`
- `strategy_backtest_pack.v1`
- `strategy_backtest_pack_validation.v1`
- `strategy_backtest_suite_result.v1`
- `strategy_backtest_comparison.v1`
- `strategy_review_manifest.v1`
- `strategy_input_contract_update_proposal.v1`
- `strategy_input_contract_update_review.v1`
- `strategy_ai_review_structured_findings.v1`

Input Feedback proposal / review を含めると、proposal の最初の recommendation と review の最初の required action を open action として拾います。`HOLD`、`REJECT`、`NEEDS_FIX` review は blocked reason に入り、`NEEDS_SOURCE_CONTRACT_CONTEXT` / `BLOCKED_BOUNDARY_VIOLATION` proposal も blocked reason に入ります。これは case の実行許可ではなく、manual review の未解決事項を一覧から見落とさないための表示です。

AI review structured findings を含めると、`finding_set_status` を status として拾い、先頭 finding の `recommended_next_action` を open action として拾います。これは human review の未確認事項を case に載せるだけで、AI recommendation の採用や paper / live permission ではありません。

## Artifact

出力:

```text
data/strategy_cases/<strategy-id>/
  strategy_case_lite.json
  strategy_case_lite.md
```

`strategy_case_lite.json` は次を持ちます。

- `source_artifacts`: source path、sha256、schema_version。
- `timeline`: artifact type、event time、status、action、blocked reasons。
- `summary.latest_status`
- `summary.open_actions`
- `summary.blocked_reasons`
- `summary.latest_source_hashes`

## 境界

- artifact を読むだけで、paper order は実行しない。
- live order、wallet、signing、exchange write は使わない。
- `latest_status` は case の現状表示であり、paper / live permission ではない。
- full registry、UI timeline、case merge policy は次 slice 以降で扱う。

## Verification

```bash
uv run pytest tests/strategy_case_lite -q
uv run sis strategy-case-lite-update --help
uv run python scripts/check_current_docs.py
```
