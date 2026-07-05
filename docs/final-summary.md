<!--
作成日: 2026-06-27_11:32 JST
更新日: 2026-07-05_10:38 JST
-->

# Final Summary

## 結論

この文書は最新の完了状態だけを読む入口です。旧版の長い addendum ledger は [archive/2026-07-05-residual-risk-doc-split/final-summary-ledger-before-2026-07-05-split.md](archive/2026-07-05-residual-risk-doc-split/final-summary-ledger-before-2026-07-05-split.md) に移動しました。

旧 ledger の pass count、branch、artifact snapshot は historical record であり、current proof ではありません。現在値は `src/`, `tests/`, `schemas/`, CLI help, current artifact, checker を再確認します。

## Latest Completed Work

| 作業 | 現在の入口 | 状態 |
|---|---|---|
| Crypto Perp Backtest Candidate Pack v1 | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) | merged locally to `main` |
| Code-truth docs cleanup | [DOCUMENT_AUDIT_2026-07-05_CODE_TRUTH_DOC_TRIAGE.md](DOCUMENT_AUDIT_2026-07-05_CODE_TRUTH_DOC_TRIAGE.md) | merged locally to `main` |
| Residual docs risk split | this file, [APP_CURRENT_STATE_OVERVIEW_2026-07-05.md](APP_CURRENT_STATE_OVERVIEW_2026-07-05.md), [APP_TERMS_GLOSSARY_2026-07-05.md](APP_TERMS_GLOSSARY_2026-07-05.md), [CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md](CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md) | completed and verified |

## Current Proof

Use these instead of old final-summary addenda:

- repo current state: [CURRENT_STATE.md](CURRENT_STATE.md)
- app overview: [APP_CURRENT_STATE_OVERVIEW_2026-07-05.md](APP_CURRENT_STATE_OVERVIEW_2026-07-05.md)
- terms: [APP_TERMS_GLOSSARY_2026-07-05.md](APP_TERMS_GLOSSARY_2026-07-05.md)
- surface reference: [CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md](CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md)
- implemented surfaces: [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
- CLI catalog: [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md)
- archive ledger: [archive/README.md](archive/README.md)

## Verification Commands

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
./scripts/check
```

Latest verification for the residual docs risk split:

- `uv run python scripts/check_current_docs.py` -> checked 178 current docs.
- `uv run python scripts/check_cli_catalog.py` -> checked 234 public CLI commands.
- `git diff --check` -> passed.
- `./scripts/check` -> passed; 2886 pytest tests passed in 116.34s.

## Boundary

This split does not change runtime behavior, schemas, public CLI implementation, dependencies, secrets, external services, or generated runtime artifacts.
