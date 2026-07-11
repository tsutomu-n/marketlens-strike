<!--
作成日: 2026-06-27_11:32 JST
更新日: 2026-07-11_11:41 JST
-->

# Final Summary

## 結論

この文書は最新の完了状態だけを読む入口です。旧版の長い addendum ledger や過去の pass count、branch、artifact snapshot は historical record です。

履歴を探す場合は [archive/README.md](archive/README.md) から辿ります。現在値は `src/`, `tests/`, `schemas/`, CLI help, current artifact, checker を再確認します。

## Latest Completed Work

| 作業 | 現在の入口 | 状態 |
|---|---|---|
| Current-only docs refresh | [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md), [CURRENT_DOCS_INDEX_2026-07-05.md](CURRENT_DOCS_INDEX_2026-07-05.md) | completed in local worktree |
| Current-direction routing second pass | [CODE_STATUS.md](CODE_STATUS.md), [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md), [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) | current direction split from external input checklist |
| Runbook and beginner-guide safety pass | [runbooks/README.md](runbooks/README.md), [trade_xyz_bot_beginner_guide.md](trade_xyz_bot_beginner_guide.md), [trade_xyz_bot_beginner_guide.html](trade_xyz_bot_beginner_guide.html) | current direction added and HTML safety bullets aligned with Markdown |
| Crypto Perp Backtest Candidate Pack v1 | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) | current no-actual-cash endpoint |
| Crypto Perp Backtest Candidate Pack evidence grade | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) | optional `evidence_grade_summary` and 0.04% default fee alignment |
| Crypto Perp cost model default unification | [../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml](../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml), [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) | normal project assumption wired for targeted local simulation surfaces |
| Crypto Perp no-cash backtest gate | [crypto_perp/NO_CASH_BACKTEST_GATE_V1.md](crypto_perp/NO_CASH_BACKTEST_GATE_V1.md) | local gate before human review for Paper Observation; no paper permission granted |
| Crypto Perp no-cash backtest sample dogfood | [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) | fixture-only sample generator for gate prerequisites; not real-market evidence |
| Crypto Perp real-market no-cash sample | [crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md](crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md) | public candle source event/outcome generator for no-cash gate; not paper permission |
| Crypto Perp real-market no-cash HOLD | [crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md](crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md) | ticker/funding-covered real-market no-cash gate reached `NO_CASH_BACKTEST_HOLD`; human review planning only, no paper permission |
| Crypto Perp no-cash review artifacts | [crypto_perp/NO_TRADE_KILL_REPORT_V1.md](crypto_perp/NO_TRADE_KILL_REPORT_V1.md), [crypto_perp/CANDIDATE_LEADERBOARD_V1.md](crypto_perp/CANDIDATE_LEADERBOARD_V1.md) | NO_TRADE/cost/stress/concentration kill report plus one-candidate leaderboard for human review; no paper permission |
| Crypto Perp human review packet | [crypto_perp/HUMAN_REVIEW_PACKET_V1.md](crypto_perp/HUMAN_REVIEW_PACKET_V1.md) | bundles no-cash HOLD, kill report, leaderboard, known gaps, and review questions for human review planning; no paper permission |
| Crypto Perp no-cash third-party explainer | [crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md](crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md) | current review finds bias guard `BLOCKED` is not consumed by the downstream HOLD gate; Paper Observation planning remains stopped pending fail-closed correction and regeneration |
| No-cash goal progress split | [NO_CASH_GOAL_PROGRESS_2026-07-05.md](NO_CASH_GOAL_PROGRESS_2026-07-05.md) | implementation/routing, evidence quality, and overall no-cash progress split |
| Residual docs risk split | [APP_CURRENT_STATE_OVERVIEW_2026-07-05.md](APP_CURRENT_STATE_OVERVIEW_2026-07-05.md), [APP_TERMS_GLOSSARY_2026-07-05.md](APP_TERMS_GLOSSARY_2026-07-05.md), [CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md](CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md) | current replacements remain active |

## Current Proof

Use these instead of old final-summary addenda:

- repo current state: [CURRENT_STATE.md](CURRENT_STATE.md)
- current goal and direction: [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md)
- no-cash goal progress: [NO_CASH_GOAL_PROGRESS_2026-07-05.md](NO_CASH_GOAL_PROGRESS_2026-07-05.md)
- docs index: [CURRENT_DOCS_INDEX_2026-07-05.md](CURRENT_DOCS_INDEX_2026-07-05.md)
- implemented surfaces: [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
- crypto perp cost model reference: [../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml](../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml)
- no-cash backtest gate: [crypto_perp/NO_CASH_BACKTEST_GATE_V1.md](crypto_perp/NO_CASH_BACKTEST_GATE_V1.md)
- no-cash backtest sample CLI: `uv run sis crypto-perp-no-cash-backtest-sample`
- real-market no-cash sample CLI: `uv run sis crypto-perp-real-market-no-cash-sample`
- human review plan for no-cash HOLD: [crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md](crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md)
- NO_TRADE kill report CLI: `uv run sis crypto-perp-no-trade-kill-report`
- candidate leaderboard CLI: `uv run sis crypto-perp-candidate-leaderboard`
- human review packet CLI: `uv run sis crypto-perp-human-review-packet`
- current no-cash human review explanation: [crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md](crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md)
- CLI catalog: [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md)
- archive ledger: [archive/README.md](archive/README.md)

## Verification Commands

Current-only docs refresh でこちらが確認済み:

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `uv run sis --help`
- `./scripts/check`

再確認する時の command:

```bash
uv run sis crypto-perp-no-cash-backtest-sample
uv run sis crypto-perp-backtest-candidate-pack
uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/no_cash_backtest_gate/latest
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
uv run sis --help
./scripts/check
```

Do not treat old command counts, test pass counts, branch names, or artifact snapshots in historical docs as current proof.

Current Crypto Perp no-cash HOLD proof for the active real-market run:

- `data/crypto_perp/real_market_no_cash/ticker_required/selection_manifest.json`
- `data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest/decision.json`
- `data/crypto_perp/real_market_no_cash/no_cash_backtest_gate/latest/no_cash_backtest_gate.json`
- `data/crypto_perp/real_market_no_cash/no_trade_kill_report/latest/no_trade_kill_report.json`
- `data/crypto_perp/real_market_no_cash/candidate_leaderboard/latest/candidate_leaderboard.json`
- `data/crypto_perp/real_market_no_cash/human_review_packet/latest/human_review_packet.json`

Observed current result:

```text
gate_decision=NO_CASH_BACKTEST_HOLD
blocker_count=0
event_count=30
outcome_count=30
ticker_available_count=30
funding_available_count=30
critical_missing_count=0
unknown_count=0
executed_trade_count=13
pbo_status=ESTIMATED
rolling_stability_status=complete
permits_paper_order=false
permits_live_order=false
actual_cash_used=false
profit_proven=false
```

## Boundary

The latest Crypto Perp cost-model work changes local simulation defaults for targeted estimate surfaces: normal project assumption is `fee_rate=0.0004`, `funding_rate=0.0001`, and `slippage_bps=2`; zero-cost tournament rows are rejected.

The no-cash backtest gate adds a local artifact before human review for Paper Observation. It does not grant paper order permission. The no-cash sample command only writes fixture-only local dogfood artifacts and must not be treated as real-market evidence. The real-market no-cash sample command uses public candle source data but still does not grant paper permission, prove profit, or use actual cash. These surfaces do not change dependencies, secrets, external services, wallet/signing paths, exchange writes, or live order submission. They do not claim profit proof, actual cash readiness, tiny-live readiness, or live readiness.
