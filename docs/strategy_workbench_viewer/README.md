<!--
作成日: 2026-06-19_02:16 JST
更新日: 2026-06-21_19:43 JST
-->

# Strategy Workbench Viewer

## 結論

Strategy Workbench Viewer は、Strategy Operations Workbench の JSON / Markdown artifact を読むための static HTML viewer です。

これは正本ではありません。正本は各 artifact、schema、CLI、test です。viewer は artifact を探しやすくするだけで、paper 実行、live 実行、scale-up、wallet、signing、exchange write を許可しません。

Crypto Perp の `crypto_perp_tournament_report.v1`、`crypto_perp_tournament_gate.v1`、`crypto_perp_truth_cycle_status.v1` も通常の JSON artifact として読めます。viewer は `tournament_status`、`gate_status`、`cycle_status`、`human_summary`、`leader_action`、`primary_metric`、`event_count`、`proxy_gap_count`、`failed_condition_count`、`stop_reason_count`、`first_stop_reason`、`missing_artifact_path_count`、`leader_actual_cash_result_usd` などのcompact summaryを表示対象にします。

## CLI

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/strategy_cases/<strategy-id>/strategy_case_lite.json \
  --artifact data/reports/strategy_daily_brief/strategy_daily_brief.json \
  --out data/reports/strategy_workbench_viewer
```

`--artifact` を省略すると `--data-dir` 配下の `.json`、`.md`、`.txt` を scan します。

```bash
uv run sis strategy-workbench-viewer-build \
  --data-dir data \
  --out data/reports/strategy_workbench_viewer \
  --replace-existing
```

出力:

```text
data/reports/strategy_workbench_viewer/
  strategy_workbench_viewer.html
  strategy_workbench_viewer_manifest.json
```

## Manifest

`strategy_workbench_viewer_manifest.json` は `strategy_workbench_viewer.v1` です。

主な内容:

- source artifact path
- source artifact sha256
- schema_version
- status / decision_status / plan_status / ingest_status / tournament_status / gate_status / cycle_status などの抜粋
- Crypto Perp tournament / gate / truth-cycle status の leader_action / primary_metric / event_count / proxy_gap_count / stop_reason_count / first_stop_reason / human_summary などのcompact summary
- boundary violation count
- HTML report path / hash
- fixed false permission flags

## 境界

- static HTML を生成するだけ。
- artifact を編集しない。
- paper / live execution permission ではない。
- hidden mutable state を持たない。
- `data/` runtime artifact の内容を docs に固定しない。

## 検証

```bash
uv run pytest tests/strategy_workbench_viewer -q
uv run sis strategy-workbench-viewer-build --help
uv run python scripts/check_current_docs.py
```
