# Live Evidence Reports

このディレクトリは live evidence runner が生成する markdown / HTML report の置き場です。

ここにある既存 report は historical runtime output です。現行判断の入口としては、まず次を再生成して読んでください。

```bash
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

読む順番:

1. `data/reports/phase_gate_review.md`
2. `data/reports/readiness_snapshot.md`
3. `data/reports/current_state_index.md`
4. `docs/live_evidence_reports/live_evidence_report_<run_id>.md`

