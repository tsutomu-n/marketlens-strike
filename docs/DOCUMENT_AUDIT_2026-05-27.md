# Documentation Audit (2026-05-27)

> Superseded: current audit is `docs/DOCUMENT_AUDIT_2026-05-28.md`. This file remains as the 2026-05-27 PR12 snapshot.

コード、設定、CLI surface、tracked / ignored files、生成 artifact を正として、docs の current / stale / generated / archive boundary を再監査した結果。

> Updated: `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` を追加した後の current audit。詳細な PR9a-PR12 実装棚卸しは同文書を読む。

## 結論

- active current docs は `README.md`, `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/ARCHITECTURE_AND_PHASES.md`, `docs/trade_xyz_bot_beginner_guide.html`, `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md`。
- `probe trade-xyz` は live `perpDexs` から `asset_id` を解決できる。解決不能時は `api_orderable=false` で fail-closed。
- `collect-trade-xyz-quotes` は duration / symbol filter / dry-run / summary / report 出力を持つ current public CLI。
- legacy `gtrade` / `ostium` read-only collector docs は historical docs として扱う。現行 checkout の public CLI 正本ではない。
- `data/reports/*`, `data/ops/*`, `docs/live_evidence_reports/live_evidence_*` は generated artifact。手編集ではなく再生成か archive で扱う。
- 2026-05-27 の Trade[XYZ] PR12 read-only smoke は `READ_ONLY_GO` まで確認済み。
- `bot-preview` は code/CLI と tests では実装済みだが、`data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` は runtime artifact であり、現 checkout に常に存在するとは限らない。

## 更新対象

- `README.md`: current verification count と Trade[XYZ] quote collection options。
- `docs/CURRENT_STATE.md`: `perpDexs` asset mapping、quote summary/report、strict validation、PR12 evidence。
- `docs/CODE_STATUS.md`: PR-03 / PR-04 evidence、PR9a-PR12 evidence、current verification。
- `docs/OPERATIONS_RUNBOOK.md`: `collect-trade-xyz-quotes --write-summary --write-report` を標準 Trade[XYZ] refresh path にする。
- `docs/ARCHITECTURE_AND_PHASES.md`: active tree ではなく archive zip に残る legacy gTrade/Ostium boundary。
- `docs/trade_xyz_bot_beginner_guide.html`: asset id 解決済みと本番発注未完了を分ける。
- `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md`: PR9a-PR12 の実装済み / 一部実装 / 未実装を code truth に合わせて更新する。
- `.ai_memory/HANDOFF.md`: restart 正本。bot-preview artifact は「前回実装で出力された」事実と「現 checkout に存在する」事実を分ける必要がある。

## 古い内容

- `docs/DOCUMENT_AUDIT_2026-05-26.md`: 2026-05-26 snapshot。現行 audit ではない。
- `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md`: initial CLI plan。PR12 後は consumed plan / historical note として扱う。
- `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md`, `docs/archive/legacy_read_only_collectors_2026-05-28/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`, `docs/archive/legacy_read_only_collectors_2026-05-28/READ_ONLY_COLLECTOR_RISK_REVIEW.md`: legacy command を参照する。current public CLI としては使わない。
- `data/reports/phase_gate_review.md`, `data/reports/readiness_snapshot.md`: generated snapshot。古ければ再生成する。
- `.ai_memory/HANDOFF.md`: handoff としては current restart 正本だが、artifact existence は再開時に `find data/bot data/reports ...` で再確認する。

## 作り直すなら

- `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md` は historical consumed plan として archive するか、PR9a-PR12 result note として作り直す。
- legacy read-only collector docs 3 本は、active docs に残すなら「archive restore 前提の runbook」として再構成する。
- generated reports は `uv run sis refresh-operations-artifacts` と `uv run sis phase-gate-review` で再生成する。
- `docs/DOCUMENT_AUDIT_2026-05-27.md` はこの文書自身を短い current docs index として残し、詳細棚卸しは `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` へ寄せる。
- `docs/trade_xyz_bot_beginner_guide.html` は人向け説明として有用だが、HTML 内の artifact 説明は「`uv run sis bot-preview` 実行時に生成」と書き分けると誤読が減る。

## 削除・アーカイブ候補

- `docs/live_evidence_reports/live_evidence_report_*.md`
- `docs/live_evidence_reports/live_evidence_report_*.html`
- `docs/live_evidence_reports/live_evidence_followup_*.md`
- `docs/DOCUMENT_AUDIT_2026-05-26.md`

上記の live evidence report は source docs ではない。残す場合は `docs/archive/2026-05-26-live-evidence-history/` に置く。`docs/DOCUMENT_AUDIT_2026-05-26.md` はすでに superseded banner があるため即削除不要だが、current docs を減らすなら `docs/archive/` に移す候補。

## Current Code Truth

- Python runtime: 3.13
- `pyproject.toml` requires-python: `>=3.13,<3.14`
- `ruff` target-version: `py313`
- `pyrefly` python-version: `3.13`
- current CLI includes `collect-trade-xyz-quotes`, `validate-artifacts`, `probe`
- `collect-trade-xyz-quotes --help` exposes: `--registry-path`, `--normalize/--no-normalize`, `--symbols`, `--max-symbols`, `--duration-minutes`, `--interval-seconds`, `--replace/--append`, `--dry-run`, `--write-summary`, `--write-report`, `--output-dir`
- `validate-artifacts --strict` checks Trade[XYZ] v2 quote fields and `trade_xyz_quote_collection_summary.json`
- latest PR12 smoke observed: 310 rows, 3673.995702 seconds, 5 symbols x 62 rows
- latest phase gate observed: `READ_ONLY_GO`, `next_actions=[]`
- latest standard gate observed: `./scripts/check` -> 280 passed
- latest targeted recheck observed for the implementation audit: `31 passed`
- current generated bot-preview output files may be absent until `uv run sis bot-preview` is run.

## Rule

コード、schema、tests、CLI help、generated artifact の順で正本を確認する。docs はその説明であり、古い docs と code truth が衝突したら code truth を優先する。
