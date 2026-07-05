<!--
作成日: 2026-06-20_20:32 JST
更新日: 2026-07-05_10:24 JST
-->

# App Current State Detailed

## 結論

この path は互換用の入口です。旧版の長い本文は、利用者向け説明、用語説明、実装 surface、artifact reference が混ざっていたため archive しました。

現在の読み方は次の3つに分けます。

- 全体像: [APP_CURRENT_STATE_OVERVIEW_2026-07-05.md](APP_CURRENT_STATE_OVERVIEW_2026-07-05.md)
- 用語: [APP_TERMS_GLOSSARY_2026-07-05.md](APP_TERMS_GLOSSARY_2026-07-05.md)
- 実装 surface / artifact reference: [CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md](CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md)

旧 1086 行版は historical context として [archive/2026-07-05-residual-risk-doc-split/APP_CURRENT_STATE_DETAILED_2026-06-20_FULL.md](archive/2026-07-05-residual-risk-doc-split/APP_CURRENT_STATE_DETAILED_2026-06-20_FULL.md) にあります。旧版の固定 snapshot、branch、artifact 状態は current proof として使いません。

## 正本

現行判断では、次を優先します。

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`
2. CLI help: `uv run sis --help`
3. current docs: [CURRENT_STATE.md](CURRENT_STATE.md), [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md), [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md)
4. generated runtime artifacts under `data/`
5. archive docs only as history

## 確認

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```
