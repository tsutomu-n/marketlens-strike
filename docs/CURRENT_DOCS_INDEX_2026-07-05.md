<!--
作成日: 2026-07-05_11:55 JST
更新日: 2026-07-25_00:52 JST
-->

# Current Docs Index 2026-07-05

## 結論

現行判断では、このindexから読む。古いaudit、roadmap、dogfood log、completed plan、fixed pass-count snapshotはarchive / historyとして扱う。

Crypto Perp no-cash laneの現在値は、default fold_count 0によるguard BLOCKED、PBO未計算、position overlap未反映、独立market episode不足、selectorの単純基準未達により`BLOCKED_BY_BIAS_GUARD`である。現在の実装主計画はprofit evidence hardeningで、fail-closed計画とbias guard warning semantic計画は履歴である。

## Primary Current Docs

| 目的 | 読むもの |
|---|---|
| 現在地を短く読む | [CURRENT_STATE.md](CURRENT_STATE.md) |
| ここから目指す方向を読む | [CURRENT_GOAL_AND_DIRECTION_2026-07-05.md](CURRENT_GOAL_AND_DIRECTION_2026-07-05.md) |
| current docs の入口を選ぶ | この文書 |
| 実装済み surface を見る | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| CLI catalog を見る | [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) |
| code/status の誤読を避ける | [CODE_STATUS.md](CODE_STATUS.md) |
| 最新完了状態を読む | [final-summary.md](final-summary.md) |

## Domain Current Docs

| 領域 | 読むもの |
|---|---|
| Crypto Perp profit evidence hardening主計画 | [plans/CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md](plans/CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md) |
| Crypto Perp actual-cashなし短期終着点 / evidence grade | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) |
| Crypto Perp no-cash backtest gate | [crypto_perp/NO_CASH_BACKTEST_GATE_V1.md](crypto_perp/NO_CASH_BACKTEST_GATE_V1.md) |
| Crypto Perp real-market no-cash sample | [crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md](crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md) |
| Crypto Perp forward ticker coverage status | [crypto_perp/REAL_MARKET_TICKER_COVERAGE_STATUS_V1.md](crypto_perp/REAL_MARKET_TICKER_COVERAGE_STATUS_V1.md) |
| Crypto Perp human review plan / current blocked decision | [crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md](crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md) |
| Crypto Perp human review packet | [crypto_perp/HUMAN_REVIEW_PACKET_V1.md](crypto_perp/HUMAN_REVIEW_PACKET_V1.md) |
| Crypto Perp no-cash検証と停止理由の現在地 | [crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md](crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md) |
| Crypto Perp NO_TRADE kill report | [crypto_perp/NO_TRADE_KILL_REPORT_V1.md](crypto_perp/NO_TRADE_KILL_REPORT_V1.md) |
| Crypto Perp candidate leaderboard | [crypto_perp/CANDIDATE_LEADERBOARD_V1.md](crypto_perp/CANDIDATE_LEADERBOARD_V1.md) |
| Crypto Perp cost model assumptions | [../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml](../configs/cost_models/crypto_perp_bitget_usdt_futures.yaml) |
| Crypto Perp operator loop | [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) |
| Crypto Perp cash/proxy/estimate 用語境界 | [crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md) |
| Strategy Idea Candidate pipeline | [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md) |
| Strategy Idea 用語と C9 bridge 境界 | [strategy_idea_candidates/GOAL_AND_GLOSSARY.md](strategy_idea_candidates/GOAL_AND_GLOSSARY.md) |
| Backtest | [backtest/README.md](backtest/README.md) |
| Strategy Review | [strategy_review/README.md](strategy_review/README.md) |
| Strategy Lab / Authoring | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| NDX local research gates | [research/ndx/README.md](research/ndx/README.md) |
| Runbooks | [runbooks/README.md](runbooks/README.md) |
| Venue boundary | [venues/read_only_capability_probe.md](venues/read_only_capability_probe.md) |

## Current Discovery Plans

次は実装済みSurfaceではなく、独立Discovery SpikeのPlanである。これらをalpha、profit proof、Core integration permission、paper/live permissionとして読まない。

| 目的 | 読むもの |
|---|---|
| Alpha StrikeとResearch Foundryの非線形な運用原則 | [plans/ALPHA_STRIKE_RESEARCH_FOUNDRY_OPERATING_MODEL_2026-07-25.md](plans/ALPHA_STRIKE_RESEARCH_FOUNDRY_OPERATING_MODEL_2026-07-25.md) |
| 現Checkpointで実装するResearch Policy A/B Discovery Spike | [plans/RESEARCH_POLICY_AB_DISCOVERY_SPIKE_IMPLEMENTATION_2026-07-25.md](plans/RESEARCH_POLICY_AB_DISCOVERY_SPIKE_IMPLEMENTATION_2026-07-25.md) |
| Agent実装用の機械可読Task / Gate | [plans/RESEARCH_POLICY_AB_DISCOVERY_SPIKE_TASKS_2026-07-25.yaml](plans/RESEARCH_POLICY_AB_DISCOVERY_SPIKE_TASKS_2026-07-25.yaml) |

## Decision Support, Not Source Of Truth

| 目的 | 読むもの |
|---|---|
| お金を使わない段階の進捗 | [NO_CASH_GOAL_PROGRESS_2026-07-05.md](NO_CASH_GOAL_PROGRESS_2026-07-05.md) |
| 個人トレーダー目線の現実評価 | [AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md](AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md) |
| 利益目線の誤読防止 | [AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md](AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md) |
| Strategy idea 調査履歴 | [STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md) |
| Strategy idea 実装前 audit | [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md) |
| Strategy idea checkpoint | [STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md](STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md) |

## Historical / Archive

次の計画は現在の主計画ではなく、profit evidence hardeningへ至る実装履歴である。

- [Crypto Perp fail-closed decision chain plan](plans/CRYPTO_PERP_FAIL_CLOSED_DECISION_CHAIN_2026-07-11.md)
- [Crypto Perp bias guard warning semantics plan](plans/CRYPTO_PERP_BIAS_GUARD_WARNING_SEMANTICS_2026-07-11.md)
- [Crypto Perp no-cash third-party explainer plan](plans/CRYPTO_PERP_NO_CASH_THIRD_PARTY_EXPLAINER_2026-07-11.md)
- [Crypto Perp no-cash backtest goal implementation plan](crypto_perp/NO_CASH_BACKTEST_GOAL_IMPLEMENTATION_PLAN_2026-07-08.md)

その他のarchiveはcurrent proofではない。履歴を探す時だけ[archive/README.md](archive/README.md)と[../plan/README.md](../plan/README.md)から辿る。

## Current Verification

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
uv run sis --help
```

広く確認する時だけ:

```bash
./scripts/check
```
