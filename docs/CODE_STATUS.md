<!--
作成日: 2026-05-22_11:36 JST
更新日: 2026-06-17_10:50 JST
-->

# Code Status

この文書は code status の入口です。実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、CLI help です。

## 結論

`CODE_STATUS.md` は、migration 履歴と現行 implemented surface を混ぜないために薄い index にした。

- PR-00 から PR-12 までの移行・復旧履歴は [MIGRATION_HISTORY.md](MIGRATION_HISTORY.md) を読む。
- 現在コードで使える主要 surface と境界は [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) を読む。
- runtime artifact の鮮度や readiness は [CURRENT_STATE.md](CURRENT_STATE.md)、`uv run sis --help`、`uv run python scripts/check_current_docs.py`、`./scripts/check` で確認する。

## 現在の読み方

| 目的 | 読むもの |
|---|---|
| repo が何をできるか知る | [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md) |
| 実装済み surface を見る | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) |
| PR migration 履歴を見る | [MIGRATION_HISTORY.md](MIGRATION_HISTORY.md) |
| runtime artifact / readiness を見る | [CURRENT_STATE.md](CURRENT_STATE.md) |
| operator 手順を見る | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) |
| Strategy Review を使う | [strategy_review/README.md](strategy_review/README.md) |
| venue capability boundary を見る | [venues/read_only_capability_probe.md](venues/read_only_capability_probe.md) |

## Verification

固定の pass count はこの文書に置かない。作業時点で次を再実行する。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

## Boundaries

- `DONE` は live trading ready を意味しない。
- `READ_ONLY_GO` は read-only / paper gate の状態であり、wallet、signing、exchange write、production live trading を許可しない。
- Strategy Review の `READY_FOR_HUMAN_REVIEW` と backtest pack validation `PASS` は、alpha、paper readiness、live readiness の証明ではない。
- `data/` は runtime / generated state であり、fresh checkout では再生成する。
