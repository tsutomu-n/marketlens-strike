<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Coder Handoff Prompt

Use this prompt for the implementation pass.

```text
Read:

1. ./.ai_memory/HANDOFF.md
2. plan/0609ここからの計画/03_venue_read_only_capability_probe/README.md
3. plan/0609ここからの計画/03_venue_read_only_capability_probe/01_GOAL.md
4. plan/0609ここからの計画/03_venue_read_only_capability_probe/02_SCOPE_AND_BOUNDARIES.md
5. plan/0609ここからの計画/03_venue_read_only_capability_probe/03_CODE_TRUTH_AND_RISK_REVIEW.md
6. plan/0609ここからの計画/03_venue_read_only_capability_probe/04_TARGET_FILE_MAP.md
7. plan/0609ここからの計画/03_venue_read_only_capability_probe/05_ARTIFACT_CONTRACT.md
8. plan/0609ここからの計画/03_venue_read_only_capability_probe/06_IMPLEMENTATION_TASKS.md
9. plan/0609ここからの計画/03_venue_read_only_capability_probe/07_TEST_PLAN.md
10. plan/0609ここからの計画/03_venue_read_only_capability_probe/08_ACCEPTANCE.md
11. plan/0609ここからの計画/03_venue_read_only_capability_probe/09_STOP_CONDITIONS.md

Implement the plan exactly.

Current repo facts:

- VenueId remains trade_xyz / bitget_demo.
- bitget_futures and hyperliquid_perp are known in capability and suitability
  catalogs but disabled for schema, paper, network, and live.
- bitget_demo is execution-venue-schema enabled but not
  evaluation_plan.mls.v1 target enabled.
- evaluation_plan.mls.v1 target_venue remains trade_xyz.

Do:

- Add a fixture-first local read-only capability probe.
- Add JSON schema and tests.
- Add CLI command venue-read-only-probe.
- Add docs.
- Keep all default paths non-network, non-credentialed, and non-writing.

Do not:

- Widen VenueId.
- Widen Strategy Lab schemas.
- Call external APIs.
- Use credentials.
- Add dependencies.
- Enable paper/live execution.
- Submit, cancel, amend, or close orders.

Required final verification:

git diff -- schemas/strategy_signal.v1.schema.json schemas/trade_candidate.v1.schema.json schemas/paper_intent_preview.v1.schema.json schemas/evaluation_plan.mls.v1.schema.json src/sis/venues/ids.py
uv run pytest -q tests/test_venue_read_only_probe.py tests/test_venue_read_only_probe_cli.py tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py tests/test_bitget_demo_cli.py
uv run python scripts/check_current_docs.py
./scripts/check
```

