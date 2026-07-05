<!--
作成日: 2026-07-05_10:24 JST
更新日: 2026-07-05_13:26 JST
-->

# Current Artifact Surface Reference 2026-07-05

## 結論

この文書は、current overview から実装正本へ進むための短い参照表です。完全な内部 helper catalog ではありません。

## 実装 surface

| 目的 | current doc | code / schema / test の入口 |
|---|---|---|
| public CLI surface | [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) | `src/sis/cli.py`, `src/sis/commands/`, `uv run sis --help` |
| implemented surface map | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) | `src/sis/`, `tests/`, `schemas/` |
| No-cash goal progress | [NO_CASH_GOAL_PROGRESS_2026-07-05.md](NO_CASH_GOAL_PROGRESS_2026-07-05.md) | current artifacts under `data/crypto_perp/backtest_candidate_pack/latest/`, `data/strategy_idea_candidates/`, CLI help |
| Crypto Perp Backtest Candidate Pack | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) | `src/sis/crypto_perp/backtest_candidate_pack*.py`, `schemas/crypto_perp_backtest_candidate_pack.v1.schema.json`, `tests/crypto_perp/test_backtest_candidate_pack.py` |
| Crypto Perp runbook | [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) | `src/sis/commands/crypto_perp*.py`, `src/sis/crypto_perp/`, `tests/crypto_perp/` |
| Strategy Lab / Authoring | [strategy_research_lab/README.md](strategy_research_lab/README.md) | `src/sis/research/strategy_lab/`, `tests/strategy_authoring/`, `schemas/strategy_*.json` |
| Backtest | [backtest/README.md](backtest/README.md) | `src/sis/backtest/`, `tests/backtest/`, `tests/strategy_authoring/` |
| Strategy Review | [strategy_review/README.md](strategy_review/README.md) | `src/sis/strategy_review/`, `schemas/strategy_review_manifest.v1.schema.json` |
| NDX local gates | [research/ndx/README.md](research/ndx/README.md) | `configs/research_layer_2_2/ndx/`, `src/sis/research/`, `tests/` |
| Operations / safety | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) | `src/sis/commands/`, `src/sis/tracking/`, `src/sis/validation/`, `tests/` |

## runtime artifact

`data/`, `logs/`, `.tmp/` は runtime / generated state です。fresh checkout では存在しないことがあります。artifact の存在や数値を current proof にする場合は、該当 command を再実行するか、生成日時と入力を確認します。

## verification

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```
