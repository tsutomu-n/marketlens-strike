<!--
作成日: 2026-06-19_02:16 JST
更新日: 2026-06-22_18:55 JST
-->

# Strategy Workbench Viewer

## 結論

Strategy Workbench Viewer は、Strategy Operations Workbench の JSON / Markdown artifact を読むための static HTML viewer です。

これは正本ではありません。正本は各 artifact、schema、CLI、test です。viewer は artifact を探しやすくするだけで、paper 実行、live 実行、scale-up、wallet、signing、exchange write を許可しません。

Crypto Perp の `crypto_perp_tournament_report.v1`、`crypto_perp_tournament_gate.v1`、`crypto_perp_truth_cycle_status.v1` も通常の JSON artifact として読めます。viewer は `tournament_status`、`gate_status`、`cycle_status`、`human_summary`、`approval_boundary`、`leader_action`、`primary_metric`、`event_count`、`proxy_gap_count`、`failed_condition_count`、`stop_reason_count`、`first_stop_reason`、`missing_artifact_path_count`、`first_next_step`、`first_next_step_network_allowed=false`、`first_stage_blocker`、`first_stage_blocker_expected_cli_option`、`leader_actual_cash_result_usd` などのcompact summaryを表示対象にします。

`strategy_case_index.v1` は、case count、strategy count、latest status、latest case path、first open action、first blocked reason、source hash を compact summary として表示できます。

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
- Crypto Perp tournament / gate / truth-cycle status の leader_action / primary_metric / event_count / proxy_gap_count / stop_reason_count / first_stop_reason / first_next_step / first_stage_blocker / human_summary などのcompact summary
- Strategy Case Index の case_count / strategy_count / latest_status / latest_case_path / first_open_action / first_blocked_reason / case_index_source_hash などのcompact summary
- boundary violation count
- HTML report path / hash
- fixed false permission flags

## 境界

- static HTML を生成するだけ。
- artifact を編集しない。
- paper / live execution permission ではない。
- `first_next_step_network_allowed`、`first_next_step_exchange_write_allowed`、`first_next_step_live_order_allowed` は false の時だけ summary に出す。true は許可ではなく malformed source artifact として扱う。
- `READY_FOR_HUMAN_TINY_LIVE_REVIEW` は warning badge と `approval_boundary` で表示する。これは承認待ちであり、live execution permission ではない。
- `first_stage_blocker` は先に読むべき欠損 stage の索引であり、次 stage や tiny live へ進む許可ではない。
- `strategy_case_index.v1` は read-only case index として表示するだけで、source case artifact、DB registry、paper/live permission を作らない。
- hidden mutable state を持たない。
- `data/` runtime artifact の内容を docs に固定しない。

## 検証

```bash
uv run pytest tests/strategy_workbench_viewer -q
uv run sis strategy-workbench-viewer-build --help
uv run python scripts/check_current_docs.py
```
