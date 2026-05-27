# Documentation Audit (2026-05-26)

> Superseded: current audit is `docs/DOCUMENT_AUDIT_2026-05-27.md`. This file is a 2026-05-26 snapshot from before the PR12 Trade[XYZ] read-only smoke and `READ_ONLY_GO` phase gate evidence.

コード、設定、CLI surface、tracked files を正として、tracked docs の current / stale / historical boundary を再監査した結果をまとめる。

## 結論

- active docs は `README.md`, `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/ARCHITECTURE_AND_PHASES.md`。
- `plan/` は active implementation instruction ではなく、PR-00 から PR-08 の historical migration contract として扱う。
- `data/reports/*.md` と `data/research/*.md` は生成 artifact なので手編集しない。必要なら CLI で再生成する。
- ignored/local `.tmp/*.md` は source docs として扱わない。
- `.tmp/live_evidence_current_status_2026-05-26.md` は local historical status snapshot であり、current status の正本ではない。

## 更新できるドキュメント

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/live_evidence_reports/README.md`

更新方針:

- verification count は実測値だけを書く。
- public CLI command は `uv run sis --help` で確認できるものだけを書く。
- `micro_live` と `Trade[XYZ]` quote collector は code/test surface と public CLI surface を分けて書く。
- `plan/archive/PR-00_to_PR-08_implementation_plan.md` は current implementation plan ではなく historical migration contract と明記する。

## 古い内容があるドキュメント

- `plan/README.md`
- `plan/archive/PR-00_python_313_migration_plan.md`
- `plan/archive/PR-00_to_PR-08_implementation_plan.md`
- `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md`
- `.tmp/live_evidence_current_status_2026-05-26.md`

補足:

- `plan/README.md` は PR-00 をこれから開始する前提で書かれていたため、historical planning index に更新する。
- PR-00 / PR-08 までの migration plan は実施済み contract として残す。
- `collect-trade-xyz-quotes` は public CLI 化済み。今後の次PR候補は、これを operations/readiness/phase gate に接続する cutover。
- `.tmp/live_evidence_current_status_2026-05-26.md` は当時の status snapshot として残す場合も、current truth ではないと明記する。

## 作り直したほうがいいドキュメント

- `docs/DOCUMENT_AUDIT_2026-05-26.md`
- `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md`

補足:

- この文書自体は、旧監査結果が stale になったため current audit として再作成した。
- quote collector CLI plan は、CLI 実装済み status と次の operations gate cutover plan へ直す。

## 削除・アーカイブしてもよいドキュメント

- `plan/archive/PR-00_python_313_migration_plan.md`
- `plan/archive/PR-00_to_PR-08_implementation_plan.md`
- `.tmp/live_evidence_current_status_2026-05-26.md`

判断:

- すぐ削除はしない。migration 経緯や live evidence 経緯の audit trail として価値があるため、削除より archive / historical banner を優先する。
- `docs/archive/**` は既に archive なので削除対象にしない。
- `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`, `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md`, `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md` は legacy operational evidence の補助資料として残す。

## Current Code Truth

- `.python-version`: `3.13`
- `pyproject.toml` requires-python: `>=3.13,<3.14`
- `scripts/check`: locked sync, Python version print, ruff, pyrefly, pytest
- `src/sis/cli.py`: root Typer app registration and `main()`
- `src/sis/commands/`: feature-specific command modules
- `src/sis/cli.py`: 348 lines
- 最大 command module: `src/sis/commands/runtime_context.py`, 627 lines
- 700 行超の Python command file は現時点で確認されていない
- `collect-trade-xyz-quotes` は現行 public CLI に存在する

## 残る注意点

- `data/reports/*.md` の内容が古い場合は、手編集せず `uv run sis refresh-operations-artifacts` などで再生成する。
- ignored/local `.tmp` の古い巨大ファイル調査メモは current docs に混ぜない。
- historical generated artifacts の Python 3.14 traceback や過去ログは audit trail として書き換えない。
- Bot 化前の主な残作業は、`collect-trade-xyz-quotes` の fresh artifact を Trade[XYZ] 主軸の operations/readiness/phase gate に接続すること。
