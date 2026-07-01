<!--
作成日: 2026-07-01_21:05 JST
更新日: 2026-07-01_21:05 JST
-->

# Profit Core Verification Matrix

## V0: Current Completion Audit

Use this when the code may already contain P1-P13.

```bash
uv run python - <<'PY'
from pathlib import Path

expected = [
    "schemas/candidate_protocol_manifest.v1.schema.json",
    "schemas/trial_multiplicity_account.v1.schema.json",
    "schemas/backtest_kill_gate.v1.schema.json",
    "schemas/virtual_execution_gate.v1.schema.json",
    "schemas/profit_core_evidence_packet.v1.schema.json",
    "schemas/profit_core_adversarial_review.v1.schema.json",
    "schemas/profit_core_risk_taker_sprint_isolation.v1.schema.json",
    "schemas/profit_core_actual_cash_readiness_packet.v1.schema.json",
    "schemas/profit_core_external_venue_adapter_run.v1.schema.json",
    "schemas/profit_core_tiny_actual_cash_measurement.v1.schema.json",
    "schemas/profit_core_actual_cash_report_gate.v1.schema.json",
    "schemas/profit_core_feedback_threshold_calibration.v1.schema.json",
    "src/sis/strategy_idea_candidates/profit_core.py",
    "src/sis/strategy_idea_candidates/authoring_bridge.py",
    "src/sis/edge_candidates/protocol.py",
    "src/sis/edge_candidates/multiplicity.py",
    "src/sis/edge_candidates/backtest_kill_gate.py",
    "src/sis/edge_candidates/factory.py",
    "src/sis/edge_candidates/virtual_execution_gate.py",
    "src/sis/edge_candidates/evidence_packet.py",
    "src/sis/edge_candidates/adversarial_review.py",
    "src/sis/edge_candidates/risk_taker_sprint_isolation.py",
    "src/sis/edge_candidates/actual_cash_readiness.py",
    "src/sis/edge_candidates/external_venue_adapter.py",
    "src/sis/edge_candidates/tiny_actual_cash_measurement.py",
    "src/sis/edge_candidates/actual_cash_report_gate.py",
    "src/sis/edge_candidates/feedback_calibration.py",
]

missing = [path for path in expected if not Path(path).exists()]
print(f"checked={len(expected)} missing={len(missing)}")
for path in missing:
    print(path)
raise SystemExit(1 if missing else 0)
PY
```

CLI surface check:

```bash
uv run sis --help | rg "strategy-idea-candidates-authoring-bridge|strategy-idea-candidates-multiplicity-account-build|edge-candidate-"
```

## Focused Tests By Slice

P1-P3:

```bash
uv run pytest tests/strategy_idea_candidates/test_profit_core_attachment.py tests/strategy_idea_candidates/test_authoring_bridge.py tests/edge_candidates/test_protocol_manifest.py tests/edge_candidates/test_multiplicity_account.py tests/edge_candidates/test_backtest_kill_gate.py -q
```

P4:

```bash
uv run pytest tests/edge_candidates/test_factory.py tests/strategy_idea_candidates/test_candidate_generator.py tests/strategy_idea_candidates/test_candidate_cli.py tests/edge_candidates/test_protocol_manifest.py -q
```

P5:

```bash
uv run pytest tests/edge_candidates/test_virtual_execution_gate.py tests/edge_candidates/test_factory.py tests/edge_candidates/test_backtest_kill_gate.py tests/edge_candidates/test_multiplicity_account.py -q
```

P6:

```bash
uv run pytest tests/edge_candidates/test_evidence_packet.py tests/edge_candidates/test_virtual_execution_gate.py tests/edge_candidates/test_factory.py tests/edge_candidates/test_backtest_kill_gate.py tests/edge_candidates/test_multiplicity_account.py -q
```

P7:

```bash
uv run pytest tests/edge_candidates/test_adversarial_review.py tests/edge_candidates/test_evidence_packet.py -q
```

P8:

```bash
uv run pytest tests/edge_candidates/test_risk_taker_sprint_isolation.py tests/edge_candidates/test_factory.py -q
```

P9:

```bash
uv run pytest tests/edge_candidates/test_actual_cash_readiness.py tests/edge_candidates/test_adversarial_review.py tests/edge_candidates/test_evidence_packet.py -q
```

P10:

```bash
uv run pytest tests/edge_candidates/test_external_venue_adapter.py tests/edge_candidates/test_virtual_execution_gate.py -q
```

P11:

```bash
uv run pytest tests/edge_candidates/test_tiny_actual_cash_measurement.py tests/edge_candidates/test_actual_cash_readiness.py tests/edge_candidates/test_external_venue_adapter.py tests/edge_candidates/test_evidence_packet.py -q
```

P12:

```bash
uv run pytest tests/edge_candidates/test_actual_cash_report_gate.py tests/edge_candidates/test_tiny_actual_cash_measurement.py tests/edge_candidates/test_actual_cash_readiness.py tests/edge_candidates/test_evidence_packet.py tests/edge_candidates/test_external_venue_adapter.py -q
```

P13:

```bash
uv run pytest tests/edge_candidates/test_feedback_calibration.py tests/edge_candidates/test_actual_cash_report_gate.py tests/edge_candidates/test_multiplicity_account.py tests/edge_candidates/test_protocol_manifest.py -q
```

## CLI Help Checks

```bash
uv run sis strategy-idea-candidates-authoring-bridge --help
uv run sis strategy-idea-candidates-multiplicity-account-build --help
uv run sis edge-candidate-protocol-validate --help
uv run sis edge-candidate-factory-run --help
uv run sis edge-candidate-virtual-gate-run --help
uv run sis edge-candidate-evidence-packet-build --help
uv run sis edge-candidate-adversarial-review-record --help
uv run sis edge-candidate-risk-taker-sprint-isolation-record --help
uv run sis edge-candidate-actual-cash-readiness-packet-build --help
uv run sis edge-candidate-external-venue-adapter-record --help
uv run sis edge-candidate-tiny-actual-cash-measurement-record --help
uv run sis edge-candidate-actual-cash-report-gate --help
uv run sis edge-candidate-feedback-calibration-build --help
```

## Final Repo Checks

```bash
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Verification Interpretation

- Passing focused tests proves local artifact behavior, not alpha/profit/live readiness.
- Passing `./scripts/check` proves repo checks at that commit, not actual market profitability.
- P10/P11 tests must not be reinterpreted as permission to use real credentials or submit orders.
