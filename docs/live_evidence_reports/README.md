<!--
作成日: 2026-05-25_19:45 JST
更新日: 2026-06-05_08:11 JST
-->

# Live Evidence Reports

このディレクトリは live evidence runner が生成する markdown / HTML report の置き場です。
tracked docs としては、この `README.md` だけを残します。

runtime がここに再生成する report は local artifact として扱い、git の current docs には含めません。
historical runtime output は `docs/archive/2026-05-26-live-evidence-history/` へ移しています。

現行判断の入口としては、まず次を再生成して読んでください。

```bash
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

読む順番:

1. `data/reports/phase_gate_review.md`
2. `data/reports/readiness_snapshot.md`
3. `data/reports/current_state_index.md`
4. local/generated `docs/live_evidence_reports/live_evidence_report_<run_id>.md` if it exists

この directory にある generated report は source doc ではありません。tracked に戻す場合は、まず `docs/archive/` へ移すか、current docs から参照しない形にしてください。
