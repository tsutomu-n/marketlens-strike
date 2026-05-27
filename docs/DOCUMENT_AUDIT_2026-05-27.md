# Documentation Audit (2026-05-27)

コード、設定、CLI surface、tracked / ignored files を正として、docs の current / stale / generated / archive boundary を再監査した結果。

## 結論

- active current docs は `README.md`, `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/ARCHITECTURE_AND_PHASES.md`, `docs/trade_xyz_bot_beginner_guide.html`。
- `probe trade-xyz` は live `perpDexs` から `asset_id` を解決できる。解決不能時は `api_orderable=false` で fail-closed。
- `collect-trade-xyz-quotes` は duration / symbol filter / dry-run / summary / report 出力を持つ current public CLI。
- legacy `gtrade` / `ostium` read-only collector docs は historical docs として扱う。現行 checkout の public CLI 正本ではない。
- `data/reports/*`, `data/ops/*`, `docs/live_evidence_reports/live_evidence_*` は generated artifact。手編集ではなく再生成か archive で扱う。
- 2026-05-27 の Trade[XYZ] PR12 read-only smoke は `READ_ONLY_GO` まで確認済み。

## 更新対象

- `README.md`: current verification count と Trade[XYZ] quote collection options。
- `docs/CURRENT_STATE.md`: `perpDexs` asset mapping、quote summary/report、strict validation、PR12 evidence。
- `docs/CODE_STATUS.md`: PR-03 / PR-04 evidence、PR9a-PR12 evidence、current verification。
- `docs/OPERATIONS_RUNBOOK.md`: `collect-trade-xyz-quotes --write-summary --write-report` を標準 Trade[XYZ] refresh path にする。
- `docs/ARCHITECTURE_AND_PHASES.md`: active tree ではなく archive zip に残る legacy gTrade/Ostium boundary。
- `docs/trade_xyz_bot_beginner_guide.html`: asset id 解決済みと本番発注未完了を分ける。

## 古い内容

- `docs/DOCUMENT_AUDIT_2026-05-26.md`: 2026-05-26 snapshot。現行 audit ではない。
- `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md`: initial CLI plan。PR12 後は consumed plan / historical note として扱う。
- `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md`, `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`, `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md`: legacy command を参照する。current public CLI としては使わない。
- `data/reports/phase_gate_review.md`, `data/reports/readiness_snapshot.md`: generated snapshot。古ければ再生成する。

## 作り直すなら

- `plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md` は historical consumed plan として archive するか、PR9a-PR12 result note として作り直す。
- legacy read-only collector docs 3 本は、active docs に残すなら「archive restore 前提の runbook」として再構成する。
- generated reports は `uv run sis refresh-operations-artifacts` と `uv run sis phase-gate-review` で再生成する。

## 削除・アーカイブ候補

- `docs/live_evidence_reports/live_evidence_report_*.md`
- `docs/live_evidence_reports/live_evidence_report_*.html`
- `docs/live_evidence_reports/live_evidence_followup_*.md`

上記は source docs ではない。残す場合は `docs/archive/2026-05-26-live-evidence-history/` に置く。

## Current Code Truth

- Python runtime: 3.13
- current CLI includes `collect-trade-xyz-quotes`, `validate-artifacts`, `probe`
- `collect-trade-xyz-quotes --help` exposes: `--registry-path`, `--normalize/--no-normalize`, `--symbols`, `--max-symbols`, `--duration-minutes`, `--interval-seconds`, `--replace/--append`, `--dry-run`, `--write-summary`, `--write-report`, `--output-dir`
- `validate-artifacts --strict` checks Trade[XYZ] v2 quote fields and `trade_xyz_quote_collection_summary.json`
- latest PR12 smoke observed: 310 rows, 3673.995702 seconds, 5 symbols x 62 rows
- latest phase gate observed: `READ_ONLY_GO`, `next_actions=[]`
- latest standard gate observed: `./scripts/check` -> 270 passed

## Rule

コード、schema、tests、CLI help、generated artifact の順で正本を確認する。docs はその説明であり、古い docs と code truth が衝突したら code truth を優先する。
