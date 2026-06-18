<!--
作成日: 2026-06-19_00:12 JST
更新日: 2026-06-19_00:33 JST
-->

# Strategy Learning

## 結論

Strategy Learning は、Drift Review から得た実践上の学びを `strategy_learning_event.v1` として台帳に残し、必要なら `strategy_revision_request.v1` を作り、人間の `strategy_revision_request_review.v1` を記録し、承認済み request だけを `strategy_authoring_update_handoff.v1` として Strategy Authoring の人間編集入力へ渡す first slice です。

これは Strategy Authoring YAML を直接編集しない。`auto_applied=false`、`direct_spec_edit_allowed=false`、`requires_human_review=true` を固定し、実践からの学びと実際の戦略改訂を分ける。

## Commands

Drift Review から learning event を作り、ledger に反映する。

```bash
uv run sis strategy-learning-ledger-update \
  --drift-review data/strategy_drift_reviews/<strategy-id>/<session-id>/paper_vs_backtest_drift_review.json \
  --out data/strategy_learning
```

出力:

```text
data/strategy_learning/<strategy-id>/
  learning_events/<learning-event-id>.json
  learning_ledger.jsonl
  learning_summary.md
```

Learning ledger から revision request を作る。

```bash
uv run sis strategy-revision-request-build \
  --strategy-id <strategy-id> \
  --learning-ledger data/strategy_learning/<strategy-id>/learning_ledger.jsonl \
  --out data/strategy_learning/<strategy-id>/revision_requests
```

出力:

```text
data/strategy_learning/<strategy-id>/revision_requests/
  <revision-request-id>.json
  <revision-request-id>.md
```

Revision request に人間判断を記録する。

```bash
uv run sis strategy-revision-request-review \
  --revision-request data/strategy_learning/<strategy-id>/revision_requests/<revision-request-id>.json \
  --decision APPROVE_FOR_AUTHORING_UPDATE \
  --reviewer operator-a \
  --rationale "authoring update の入力として使う"
```

出力:

```text
data/strategy_learning/<strategy-id>/revision_requests/
  <revision-request-id>_review.json
  <revision-request-id>_review.md
```

承認済み revision request を Strategy Authoring の人間編集入力にする。

```bash
uv run sis strategy-authoring-update-handoff \
  --revision-request data/strategy_learning/<strategy-id>/revision_requests/<revision-request-id>.json \
  --revision-review data/strategy_learning/<strategy-id>/revision_requests/<revision-request-id>_review.json \
  --authoring-spec configs/strategies/<strategy-id>.yaml \
  --out data/strategy_learning/<strategy-id>/authoring_update_handoffs
```

出力:

```text
data/strategy_learning/<strategy-id>/authoring_update_handoffs/
  <handoff-id>.json
  <handoff-id>.md
```

## Artifact

`strategy_learning_event.v1`:

- `learning_event_id`
- `strategy_id`
- `source_stage`
- `source_artifacts`
- `event_type`
- `finding`
- `impact`
- `recommended_action`
- `requires_human_review=true`
- `auto_applied=false`
- `direct_spec_edit_allowed=false`
- `paper_execution_allowed=false`
- `live_allowed=false`

`strategy_authoring_update_handoff.v1`:

- `handoff_id`
- `revision_request_id`
- `strategy_id`
- `handoff_status`
- `review_decision`
- `authoring_update_input_allowed`
- `source_artifacts`
- `requested_changes`
- `authoring_update_tasks`
- `authoring_spec_path`
- `authoring_spec_sha256`
- `authoring_spec_schema_version`
- `requires_human_authoring_update=true`
- `auto_applied=false`
- `direct_spec_edit_allowed=false`
- `paper_execution_allowed=false`
- `live_allowed=false`

`strategy_revision_request.v1`:

- `revision_request_id`
- `strategy_id`
- `request_status`
- `reason`
- `source_learning_event_ids`
- `source_artifacts`
- `requested_changes`
- `decision_needed=REVIEW_AND_AUTHORING_UPDATE`
- `requires_human_review=true`
- `auto_applied=false`
- `direct_spec_edit_allowed=false`
- `paper_execution_allowed=false`
- `live_allowed=false`

`strategy_revision_request_review.v1`:

- `revision_request_id`
- `strategy_id`
- `reviewer`
- `decision`
- `rationale`
- `required_actions`
- `source_revision_request`
- `authoring_update_input_allowed`
- `requires_human_authoring_update=true`
- `auto_applied=false`
- `direct_spec_edit_allowed=false`
- `paper_execution_allowed=false`
- `live_allowed=false`

## 境界

- Strategy Authoring YAML を直接編集しない。
- paper order を実行しない。
- live order を実行しない。
- wallet、signing、exchange write は使わない。
- revision request は人間レビュー前提の要求であり、採用済みの改訂ではない。
- `APPROVE_FOR_AUTHORING_UPDATE` は別工程の human authoring update の入力許可であり、YAML 自動編集ではない。
- `strategy-authoring-update-handoff` は Strategy Authoring YAML を読んで source hash と task list を出すだけで、YAML を編集しない。
- `NO_REVISION_REQUIRED` は live readiness ではない。

## Verification

```bash
uv run pytest tests/strategy_learning -q
uv run python scripts/check_current_docs.py
```
