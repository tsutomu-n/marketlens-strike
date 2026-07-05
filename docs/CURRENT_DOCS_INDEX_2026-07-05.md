<!--
作成日: 2026-07-05_11:55 JST
更新日: 2026-07-05_13:13 JST
-->

# Current Docs Index 2026-07-05

## 結論

現行判断では、この index から読む。古い audit、roadmap、dogfood log、completed plan、fixed pass-count snapshot は archive / history として扱う。

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
| Crypto Perp actual-cashなし短期終着点 | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) |
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

Archive は current proof ではありません。履歴を探す時だけ [archive/README.md](archive/README.md) と [../plan/README.md](../plan/README.md) から辿ります。

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
