# Documentation Audit (2026-05-26)

コードを正本として、`README.md` と `docs/` を調査し、誤読しやすい箇所を修正した後の分類をまとめる。

## 更新できるドキュメント

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/XNYS_MARKET_CALENDAR.md`
- `docs/live_evidence_reports/README.md`

補足:

- `docs/CODE_STATUS.md` は `src/sis/reports/implementation_status.py` と一致する generated document に戻した。
- `uv run sis implementation-status --write` を再実行しても current truth から外れにくい状態に修正済み。

## 古い内容があるドキュメント

- `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`
- `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md`
- `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md`
- `docs/archive/README.md`

補足:

- 上の 3 本は現行の主軸実装ではなく、legacy `gtrade` / `ostium` collector 向け資料。
- 誤読を減らすため、タイトルを `Legacy ...` に変更した。

## 作り直したほうがいいドキュメント

- 現時点では必須なし

補足:

- 以前は `docs/CODE_STATUS.md` がこの分類だったが、生成元修正で解消した。

## 削除・アーカイブしてもよいドキュメント

- `docs/live_evidence_reports/live_evidence_followup_20260522_2308.md`
- `docs/live_evidence_reports/live_evidence_followup_run.md`
- `docs/live_evidence_reports/live_evidence_report_20260522_2308.html`
- `docs/live_evidence_reports/live_evidence_report_20260522_2308.md`
- `docs/live_evidence_reports/live_evidence_report_run.html`
- `docs/live_evidence_reports/live_evidence_report_run.md`

補足:

- いずれも historical runtime output であり、current requirement や current status の正本には向かない。
- この分類に基づき、現物は `docs/archive/2026-05-26-live-evidence-history/` へ移す。

## 修正内容

1. `src/sis/reports/implementation_status.py` を PR-00〜PR-08 ベースの generated report へ更新
2. `tests/test_implementation_status.py` を current output 基準へ更新
3. legacy collector docs 3 本のタイトルを `Legacy` 明記へ変更
4. `docs/live_evidence_reports/` は `README.md` のみ tracked にし、historical report は archive へ移す

## 残る注意点

- `README.md` や runbook に CLI 例を書く時は、`src/sis/cli.py` の public command surface と毎回照合すること
- `micro_live` はコードと tests にはあるが、標準 operator CLI に直接 expose していない
