<!--
作成日: 2026-06-26_18:43 JST
更新日: 2026-06-26_18:43 JST
-->

# Pass 386: Remediation Session Checkpoint Action Helper Extraction

## 目的

`src/sis/reports/remediation_session_checkpoint.py` から、action checkpoint の merge / feedback enrichment / next action 選択ロジックを独立モジュールへ切り出す。

この pass は、Remediation Session Checkpoint の report 生成本体を薄くし、action state の優先順位と feedback 判定を直接テストできるようにする。

## 対象

- `src/sis/reports/remediation_session_checkpoint.py`
- `src/sis/reports/remediation_session_checkpoint_actions.py`
- `tests/test_remediation_session_checkpoint_actions.py`

## 制約

- public CLI command 名・option は変えない。
- summary key 名、artifact key 名、Markdown report text・順序は変えない。
- schema、auth、DB、CI、dependency、paper/live safety boundary は変えない。
- 既存 private helper 名は `remediation_session_checkpoint.py` から引き続き参照できるよう alias を残す。
- Pass 377-385 の未コミット変更は保持し、上書きしない。

## 実装方針

1. RED: `tests/test_remediation_session_checkpoint_actions.py` を追加し、まだ存在しない `sis.reports.remediation_session_checkpoint_actions` の import で失敗させる。
2. GREEN: action source parsing、priority key、feedback priority、action merge、next action 選択、checkpoint summary status を新モジュールへ移す。
3. `remediation_session_checkpoint.py` は新 helper を呼ぶだけにし、report text assembly と file write は元ファイルに残す。
4. feedback summary JSON 読み込み、navigation、Markdown 出力、summary key は変更しない。

## 検証

- `CI=true timeout 120 uv run pytest -q tests/test_remediation_session_checkpoint_actions.py`
- `CI=true timeout 120 uv run pytest -q tests/test_remediation_session_checkpoint_actions.py tests/test_remediation_session_checkpoint_navigation.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'remediation_session_checkpoint'`
- `CI=true timeout 120 uv run pytest -q tests/test_monitoring_comparison.py -k 'remediation_session_checkpoint or build_remediation_session_checkpoint'`
- `uv run ruff format src/sis/reports/remediation_session_checkpoint.py src/sis/reports/remediation_session_checkpoint_actions.py tests/test_remediation_session_checkpoint_actions.py`
- `uv run ruff check src/sis/reports/remediation_session_checkpoint.py src/sis/reports/remediation_session_checkpoint_actions.py tests/test_remediation_session_checkpoint_actions.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help`
- `git diff --check`
- `./scripts/check`

## リスクと対策

- next action selection order regression: direct tests assert retry beats pending, failed feedback beats lower-priority command when status ties.
- action merge key regression: direct tests assert pass/retry evidence status, notes, evidence paths, observed signals, command records, and latest summaries.
- report output regression: CLI smoke and monitoring comparison slices keep the public command/report behavior covered.

## ロールバック

この pass の追加ファイルと `remediation_session_checkpoint.py` の helper alias/import 変更だけを戻せばよい。生成物、依存関係、外部状態は変更しない。
