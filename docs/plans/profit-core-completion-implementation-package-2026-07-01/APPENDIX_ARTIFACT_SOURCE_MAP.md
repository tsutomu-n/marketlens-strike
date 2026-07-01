<!--
作成日: 2026-07-01_21:05 JST
更新日: 2026-07-01_21:05 JST
-->

# Appendix: Artifact Source Map

## P1-P3 Foundation

| Artifact / Surface | Schema | Source | CLI | Tests |
|---|---|---|---|---|
| Protocol manifest | `schemas/candidate_protocol_manifest.v1.schema.json` | `src/sis/edge_candidates/protocol.py` | `edge-candidate-protocol-validate` | `tests/edge_candidates/test_protocol_manifest.py` |
| Multiplicity account | `schemas/trial_multiplicity_account.v1.schema.json` | `src/sis/edge_candidates/multiplicity.py`, `src/sis/strategy_idea_candidates/profit_core.py` | `strategy-idea-candidates-multiplicity-account-build` | `tests/edge_candidates/test_multiplicity_account.py`, `tests/strategy_idea_candidates/test_profit_core_attachment.py` |
| Backtest kill gate | `schemas/backtest_kill_gate.v1.schema.json` | `src/sis/edge_candidates/backtest_kill_gate.py`, `src/sis/strategy_idea_candidates/authoring_bridge.py` | no dedicated CLI required by long-horizon P3 | `tests/edge_candidates/test_backtest_kill_gate.py`, `tests/strategy_idea_candidates/test_authoring_bridge.py` |
| Authoring bridge lineage | existing bridge manifest model | `src/sis/strategy_idea_candidates/authoring_bridge.py` | `strategy-idea-candidates-authoring-bridge` | `tests/strategy_idea_candidates/test_authoring_bridge.py` |

## P4-P8 Evidence Core

| Artifact / Surface | Schema | Source | CLI | Tests |
|---|---|---|---|---|
| Edge candidate factory | existing candidate schemas | `src/sis/edge_candidates/factory.py` | `edge-candidate-factory-run` | `tests/edge_candidates/test_factory.py` |
| Virtual execution gate | `schemas/virtual_execution_gate.v1.schema.json` | `src/sis/edge_candidates/virtual_execution_gate.py` | `edge-candidate-virtual-gate-run` | `tests/edge_candidates/test_virtual_execution_gate.py` |
| Evidence packet | `schemas/profit_core_evidence_packet.v1.schema.json` | `src/sis/edge_candidates/evidence_packet.py` | `edge-candidate-evidence-packet-build` | `tests/edge_candidates/test_evidence_packet.py` |
| Adversarial review | `schemas/profit_core_adversarial_review.v1.schema.json` | `src/sis/edge_candidates/adversarial_review.py` | `edge-candidate-adversarial-review-record` | `tests/edge_candidates/test_adversarial_review.py` |
| Risk-taker sprint isolation | `schemas/profit_core_risk_taker_sprint_isolation.v1.schema.json` | `src/sis/edge_candidates/risk_taker_sprint_isolation.py` | `edge-candidate-risk-taker-sprint-isolation-record` | `tests/edge_candidates/test_risk_taker_sprint_isolation.py` |

## P9-P13 Actual-Cash Evidence Path

| Artifact / Surface | Schema | Source | CLI | Tests |
|---|---|---|---|---|
| Actual-cash readiness packet | `schemas/profit_core_actual_cash_readiness_packet.v1.schema.json` | `src/sis/edge_candidates/actual_cash_readiness.py` | `edge-candidate-actual-cash-readiness-packet-build` | `tests/edge_candidates/test_actual_cash_readiness.py` |
| External venue adapter record | `schemas/profit_core_external_venue_adapter_run.v1.schema.json` | `src/sis/edge_candidates/external_venue_adapter.py` | `edge-candidate-external-venue-adapter-record` | `tests/edge_candidates/test_external_venue_adapter.py` |
| Tiny actual-cash measurement | `schemas/profit_core_tiny_actual_cash_measurement.v1.schema.json` | `src/sis/edge_candidates/tiny_actual_cash_measurement.py` | `edge-candidate-tiny-actual-cash-measurement-record` | `tests/edge_candidates/test_tiny_actual_cash_measurement.py` |
| Actual-cash report gate | `schemas/profit_core_actual_cash_report_gate.v1.schema.json` | `src/sis/edge_candidates/actual_cash_report_gate.py`, `src/sis/edge_candidates/actual_cash_report_gate_models.py` | `edge-candidate-actual-cash-report-gate` | `tests/edge_candidates/test_actual_cash_report_gate.py` |
| Feedback calibration | `schemas/profit_core_feedback_threshold_calibration.v1.schema.json` | `src/sis/edge_candidates/feedback_calibration.py` | `edge-candidate-feedback-calibration-build` | `tests/edge_candidates/test_feedback_calibration.py` |

## Cross-Cutting Files

- `src/sis/edge_candidates/__init__.py`: schema version constants.
- `src/sis/commands/edge_candidates.py`: edge candidate command registration.
- `src/sis/cli.py`: root Typer registration.
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`: public CLI catalog snapshot.
- `docs/final-summary.md`: historical implementation ledger.
- `./.ai_memory/HANDOFF.md`: restart artifact only.

## Artifact Naming

Expected default output names:

- `trial_multiplicity_account.json`
- `backtest_kill_gate.json`
- `edge_candidate_factory_summary.json`
- `virtual_execution_gate.json`
- `profit_core_evidence_packet.json`
- `profit_core_adversarial_review.json`
- `profit_core_risk_taker_sprint_isolation.json`
- `profit_core_actual_cash_readiness_packet.json`
- `profit_core_external_venue_adapter_run.json`
- `profit_core_tiny_actual_cash_measurement.json`
- `profit_core_actual_cash_report_gate.json`
- `profit_core_feedback_threshold_calibration.json`

## Compatibility Notes

- Historical docs may still describe P1-P13 as future work. Current code/test/schema/CLI help wins.
- P3 has no dedicated public CLI in the long-horizon plan. Its completion evidence is schema/model/tests plus bridge/evidence/virtual gate integration.
- Existing Crypto Perp actual-cash surfaces are not the same as Profit Core P11/P12 artifacts unless they pass the Profit Core lineage and basis separation rules.
