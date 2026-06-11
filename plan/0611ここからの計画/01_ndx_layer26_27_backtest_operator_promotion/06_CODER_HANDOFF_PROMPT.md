<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Coder handoff prompt

Implement NDX Layer 2.6 paper-observation gate and Layer 2.7 operator promotion to paper observation in `/home/tn/projects/marketlens-strike`.

Read first:

1. `./.ai_memory/HANDOFF.md`
2. `AGENTS.md`
3. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/README.md`
4. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/01_GOAL_AND_SCOPE.md`
5. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/02_CODE_TRUTH_AND_RISK_AUDIT.md`
6. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/03_ARTIFACT_CONTRACT.md`
7. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/04_IMPLEMENTATION_TASKS.md`
8. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/05_ACCEPTANCE_AND_VERIFICATION.md`
9. `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/07_STOP_CONDITIONS.md`

Implement with Red -> Green.

Start by adding failing tests:

- `tests/research/test_ndx_layer26_paper_observation_gate.py`
- `tests/research/test_ndx_layer27_operator_promotion.py`

Then add:

- `src/sis/research/ndx/paper_observation_gate.py`
- `src/sis/research/ndx/operator_promotion.py`
- `schemas/ndx_paper_observation_gate_decision.v1.schema.json`
- `schemas/ndx_operator_promotion_decision.v1.schema.json`
- `research-ndx-paper-observation-gate` command
- `research-ndx-operator-promotion` command
- evidence-aware NDX/QQQ paper-stage override
- local quote evidence and paper-run revalidation tests
- minimal active docs updates after tests pass

Do not:

- add live order, wallet, signing, or exchange write code;
- expose a public live or micro-live Strategy Lab command;
- widen `VenueId`;
- add dependencies;
- fetch external data during tests or default command runs;
- remove paper-only `PaperIntentPreview` guards;
- claim alpha, profitability, paper readiness, or live readiness;
- allow NDX/QQQ paper path without matching Layer 2.6 and Layer 2.7 artifacts.
- claim robust out-of-sample performance from the current fixture-only signal set.
- skip quote availability and `paper-from-intents` revalidation.

Required final verification:

```bash
uv run sis research-ndx-paper-observation-gate --help
uv run sis research-ndx-operator-promotion --help
uv run sis research-ndx-paper-observation-gate --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports --quotes-path data/normalized/quotes.parquet
uv run sis research-ndx-operator-promotion --data-dir data --artifact-dir data/research/ndx --decision promote_to_paper_observation --reviewer local_operator --approval-reason "paper_observation_gate_reviewed"
uv run pytest tests/research/test_ndx_layer26_paper_observation_gate.py tests/research/test_ndx_layer27_operator_promotion.py -q
uv run python scripts/check_current_docs.py
./scripts/check
```
