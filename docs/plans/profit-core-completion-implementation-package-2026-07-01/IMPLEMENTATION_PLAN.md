<!--
作成日: 2026-07-01_21:05 JST
更新日: 2026-07-01_21:05 JST
-->

# Profit Core Completion Implementation Plan

## 目的

`profit-core-long-horizon-goal-checkpoints-2026-06-30.md` の最終像を、実装順、対象ファイル、検証、完了条件まで固定する。

Final shape:

```text
protocol-bound candidate generation
-> multiplicity/accounting
-> candidate-to-backtest bridge
-> backtest kill gate
-> local/mock virtual execution gate
-> evidence packet + adversarial review
-> human risk review isolation
-> explicit approval and tiny actual-cash measurement record
-> actual cash report gate
-> feedback and threshold calibration
```

## 制約

- Code, tests, schemas, config, lockfiles, CI, CLI help が正本。
- 破壊的操作は禁止。
- 破壊的変更、大規模変更、依存変更、architecture 変更は専用 branch / worktree。
- external network、credential、exchange write、wallet、signing、live order、tiny-live execution はこの計画から実行しない。
- P10 external venue adapter は current docs / official docs / account condition の直前確認なしに venue 仕様を固定しない。
- P11 actual-cash measurement は既存 local evidence を記録する artifact path であり、order submit path ではない。
- P13 feedback calibration は proposal-only。既存 protocol / multiplicity account / threshold は mutate しない。

## 現在の実装状態

2026-07-01_21:05 JST 時点で、P1-P13 の主要 implementation surface は存在する。再実装ではなく completion audit として始める場合、まず `VERIFICATION_MATRIX.md` の `V0` を実行する。

## Checkpoint Plan

### P0: Current State Reconciliation

目的:

古い roadmap と current code truth の差分を消す。

対象ファイル:

- `docs/CURRENT_STATE.md`
- `docs/final-summary.md`
- `docs/profit_core_hybrid_modes/IMPLEMENTATION_CHECKPOINTS.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `./.ai_memory/HANDOFF.md`

実装手順:

1. `git status --short --branch --untracked-files=all` で開始状態を記録する。
2. `uv run sis --help`、`scripts/check_cli_catalog.py`、`scripts/check_current_docs.py` を実行する。
3. current docs が CP1-CP3 を「契約部品は実装済み、pipeline 接続は別 checkpoint」と説明しているか確認する。
4. 古い pass count は固定せず、再実行 command を記録する。

完了条件:

- current docs が docs-only / implemented / historical を混ぜない。
- CLI catalog と current-doc checker が通る。

### P1-P3: Pipeline Attachment, Bridge Vocabulary, Backtest Kill Gate

目的:

既存 `strategy_idea_candidates` output を Profit Core lineage に接続し、C9 bridge を technical-only に分解し、candidate-scoped backtest kill gate を接続する。

対象ファイル:

- `src/sis/strategy_idea_candidates/profit_core.py`
- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `src/sis/edge_candidates/protocol.py`
- `src/sis/edge_candidates/multiplicity.py`
- `src/sis/edge_candidates/backtest_kill_gate.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `tests/strategy_idea_candidates/test_profit_core_attachment.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`
- `tests/edge_candidates/test_protocol_manifest.py`
- `tests/edge_candidates/test_multiplicity_account.py`
- `tests/edge_candidates/test_backtest_kill_gate.py`
- `schemas/candidate_protocol_manifest.v1.schema.json`
- `schemas/trial_multiplicity_account.v1.schema.json`
- `schemas/backtest_kill_gate.v1.schema.json`

実装手順:

1. Add/verify `candidate_protocol_manifest.v1`, `trial_multiplicity_account.v1`, `backtest_kill_gate.v1`.
2. Implement/verify `strategy-idea-candidates-multiplicity-account-build`.
3. Make authoring bridge emit `BRIDGED_TECHNICAL_ONLY`, not `BRIDGED`.
4. Attach protocol/multiplicity refs and hashes to bridge manifest.
5. Build candidate-scoped `backtest_kill_gate.json` from local backtest pack outputs.
6. Preserve no-paper/no-live/no-actual-cash permission fields.

完了条件:

- Candidate id、candidate set hash、ledger hash、protocol hash、multiplicity account hash が追える。
- `raw_p_value_count=0` の BH/FDR は `NOT_ESTIMABLE`。
- `SHORTLIST_FOR_VIRTUAL` は permission ではなく次 gate への state。

### P4: Edge Candidate Factory V1

目的:

`verification_throughput` mode の protocol-bound candidate generation を作る。

対象ファイル:

- `src/sis/edge_candidates/factory.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_factory.py`
- `tests/strategy_idea_candidates/test_candidate_generator.py`
- `tests/strategy_idea_candidates/test_candidate_cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

実装手順:

1. Require protocol, strategy input contract, and validation artifact.
2. Generate all candidates, all rejections, all parameters, all family/source refs.
3. Add `unexecutable_reason_count` and `unexecutable_rate`.
4. Reject `risk_taker_sprint` in P4 factory.
5. Register `edge-candidate-factory-run`.

完了条件:

- protocol なしで run できない。
- best-only report が存在しない。
- no external network / no LLM / no live permission。

### P5: Virtual Execution Gate V1 Local/Mock

目的:

actual cash 前に local/mock order lifecycle と reconciliation を検査する。PnL 判定はしない。

対象ファイル:

- `schemas/virtual_execution_gate.v1.schema.json`
- `src/sis/edge_candidates/virtual_execution_gate.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_virtual_execution_gate.py`

実装手順:

1. Consume candidate set, factory summary, multiplicity account, backtest kill gate.
2. Model submit ack, partial fill, cancel, reject reason, duplicate prevention, flat reconciliation.
3. Mark unknown state and reconcile mismatch as blockers.
4. Emit false permission fields.
5. Register `edge-candidate-virtual-gate-run`.

完了条件:

- `actual_cash=false`, `cash_metric_basis=virtual_exchange`, `production_exchange_write_used=false`, `live_order_submitted=false`, `permits_live_order=false`.
- virtual PnL is not profit evidence.

### P6: Evidence Packet And Claim Diff

目的:

human-facing claim と machine-readable evidence を分け、overclaim を検出する。

対象ファイル:

- `schemas/profit_core_evidence_packet.v1.schema.json`
- `src/sis/edge_candidates/evidence_packet.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_evidence_packet.py`

実装手順:

1. Consume protocol, candidate set, bridge manifest, multiplicity account, backtest kill gate, virtual gate, optional claims.
2. Record source refs and sha256 for all input artifacts.
3. Detect unsupported claim, missing comparison, evidence basis mismatch, actual_cash overclaim.
4. Register `edge-candidate-evidence-packet-build`.

完了条件:

- human prose is never source of truth.
- claim findings include severity and machine-readable code.

### P7: LLM Adversarial Review

目的:

LLM を許可者ではなく adversarial reviewer に限定する。初期版は local/manual JSON record。

対象ファイル:

- `schemas/profit_core_adversarial_review.v1.schema.json`
- `src/sis/edge_candidates/adversarial_review.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_adversarial_review.py`

実装手順:

1. Consume P6 evidence packet.
2. Allow manual findings in constrained vocabulary.
3. Block LLM approval semantics.
4. Register `edge-candidate-adversarial-review-record`.

完了条件:

- `NO_ADDITIONAL_BLOCKER_FOUND` is not approval.
- No PnL, official metric, gate override, live/tiny-live permission from LLM.

### P8: Risk-Taker Sprint Isolation

目的:

attack mode を本命成績から隔離し、promotion debt を強制する。

対象ファイル:

- `schemas/profit_core_risk_taker_sprint_isolation.v1.schema.json`
- `src/sis/edge_candidates/risk_taker_sprint_isolation.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_risk_taker_sprint_isolation.py`

実装手順:

1. Consume risk_taker_sprint protocol, sprint candidate set, sprint ledger, sprint multiplicity account.
2. Require separate ledger, holdout, multiplicity account.
3. Record promotion debt into verification throughput.
4. Keep P4 factory conservative.
5. Register `edge-candidate-risk-taker-sprint-isolation-record`.

完了条件:

- sprint candidate cannot move directly to actual cash.
- sprint results do not enter default aggregate.

### P9: Actual Cash Readiness Packet

目的:

Tiny actual-cash measurement 前の human approval input を固定する。

対象ファイル:

- `schemas/profit_core_actual_cash_readiness_packet.v1.schema.json`
- `src/sis/edge_candidates/actual_cash_readiness.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_actual_cash_readiness.py`

実装手順:

1. Consume P6 evidence packet, P7 adversarial review, local readiness plan, optional P8 isolation.
2. Record max notional, max daily loss, isolated margin, withdrawal disabled, IP restriction, flat reconciliation, kill switch, stop condition.
3. Keep `approval_input_only`.
4. Register `edge-candidate-actual-cash-readiness-packet-build`.

完了条件:

- packet is not execution permission.
- no external service write.

### P10: External Virtual Venue Adapter

目的:

Local/mock gate 後、明示 opt-in の external demo/testnet/read-only adapter evidence を記録する。

対象ファイル:

- `schemas/profit_core_external_venue_adapter_run.v1.schema.json`
- `src/sis/edge_candidates/external_venue_adapter.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_external_venue_adapter.py`

実装手順:

1. Implement one venue at a time.
2. Require current docs / official docs / permission scope / rate limit / terms / jurisdiction verification before real external integration.
3. Initial implementation may be local record of adapter run evidence; network remains opt-in.
4. Register `edge-candidate-external-venue-adapter-record`.

完了条件:

- demo/testnet result is not actual cash.
- network / credential / write boundary is explicit.

### P11: Tiny Actual-Cash Measurement Record

目的:

Human approved, already-produced tiny actual-cash evidence を candidate lineage に接続して記録する。

対象ファイル:

- `schemas/profit_core_tiny_actual_cash_measurement.v1.schema.json`
- `src/sis/edge_candidates/tiny_actual_cash_measurement.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_tiny_actual_cash_measurement.py`

実装手順:

1. Consume readiness, external venue adapter evidence, human approval, order intent, submitted order evidence, fills, fee/funding evidence, cash ledger, actual-cash rows, flat reconciliation, stop-condition evidence.
2. Verify candidate id, event ids, venue, measured action, ledger totals, fee/funding totals, row hashes.
3. Require `NO_TRADE` comparison over same event set.
4. Register `edge-candidate-tiny-actual-cash-measurement-record`.

完了条件:

- No paper/demo/testnet/estimate rows can become actual_cash.
- No order submit occurs in this command.

### P12: Actual Cash Report Gate

目的:

P11 sample を集計し、conservative `promote` / `wait` / `kill` を出す。

対象ファイル:

- `schemas/profit_core_actual_cash_report_gate.v1.schema.json`
- `src/sis/edge_candidates/actual_cash_report_gate.py`
- `src/sis/edge_candidates/actual_cash_report_gate_models.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_actual_cash_report_gate.py`

実装手順:

1. Consume P11 measurement.
2. Re-read and hash-verify actual-cash rows, readiness packet, evidence packet.
3. Carry source refs for measurement, readiness, evidence, rows, protocol, multiplicity, backtest kill gate, virtual gate.
4. Compute `actual_cash_edge_over_NO_TRADE` from P11 rows only.
5. Report sample size, event diversity, profit concentration, largest loss, operator burden, reconcile mismatch.
6. Register `edge-candidate-actual-cash-report-gate`.

完了条件:

- `promote` requires positive actual-cash edge, sufficient events, acceptable concentration/loss/operator burden, valid reconciliation, lineage refs.
- `wait` and `kill` are first-class.

### P13: Feedback And Threshold Calibration

目的:

Failed candidates, actual execution failures, and P12 blockers を次 cycle の proposal に変換する。

対象ファイル:

- `schemas/profit_core_feedback_threshold_calibration.v1.schema.json`
- `src/sis/edge_candidates/feedback_calibration.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_feedback_calibration.py`

実装手順:

1. Consume current protocol, multiplicity account, P12 report gate, local feedback log.
2. Require failure sources; block success-only feedback.
3. Require next protocol id and next multiplicity account id for proposed updates.
4. Block holdout-peek same-family/version reuse.
5. Require validation peek count advance for threshold/family/holdout feedback.
6. Emit proposal-only artifact.
7. Register `edge-candidate-feedback-calibration-build`.

完了条件:

- `auto_applied=false`, `protocol_mutated=false`, `multiplicity_account_mutated=false`, `thresholds_applied=false`.
- No live / actual-cash permission.

## Final Completion Procedure

1. Run focused tests in `VERIFICATION_MATRIX.md`.
2. Run `uv run python scripts/check_cli_catalog.py`.
3. Run `uv run python scripts/check_current_docs.py`.
4. Run `git diff --check`.
5. Run `./scripts/check`.
6. Update `docs/final-summary.md`.
7. Update `./.ai_memory/HANDOFF.md`.
8. If user explicitly asks or goal permits, commit and push; otherwise stop with branch and verification report.
