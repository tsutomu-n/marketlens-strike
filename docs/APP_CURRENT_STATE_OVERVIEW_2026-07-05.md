<!--
作成日: 2026-07-05_10:24 JST
更新日: 2026-07-05_10:24 JST
-->

# App Current State Overview 2026-07-05

## 結論

`marketlens-strike` は、Web画面で本番売買するアプリではなく、ターミナルから `uv run sis ...` で使う Python 3.13 の CLI / artifact-first workspace です。

主な価値は、戦略や Crypto Perp 候補を本番投入する前に、入力データ、時系列の安全性、backtest、human review、paper-only preview、read-only gate、local artifact を分けて確認することです。

## 現在の主軸

| 領域 | 現在できること | 読む入口 |
|---|---|---|
| Crypto Perp no-actual-cash | local artifact から timestamp-safe simulation pack を作り、4択 decision に分類する | [crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md](crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md) |
| Strategy Lab / Authoring | 戦略案、YAML、signal、backtest、paper-only preview をつなぐ | [strategy_research_lab/README.md](strategy_research_lab/README.md) |
| Backtest | 過去データと fixture で戦略を検査し、report を作る | [backtest/README.md](backtest/README.md) |
| Strategy Review | existing artifact から human review packet と判断記録を作る | [strategy_review/README.md](strategy_review/README.md) |
| NDX research gates | local/manual の Layer 2.2 以降の研究 gate を扱う | [research/ndx/README.md](research/ndx/README.md) |
| Trade[XYZ] / venue | read-only capability と historical venue-specific surface を扱う | [venues/read_only_capability_probe.md](venues/read_only_capability_probe.md) |
| Operations | status、audit、runbook、safety boundary を確認する | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) |

## できないこと

- production live trading
- wallet 操作
- signing
- exchange write
- live order permission の自動付与
- backtest だけによる利益証明
- `READ_ONLY_GO` や `READY_FOR_HUMAN_REVIEW` からの paper / live permission

## 最初に読む順番

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [APP_CURRENT_STATE_OVERVIEW_2026-07-05.md](APP_CURRENT_STATE_OVERVIEW_2026-07-05.md)
3. [APP_TERMS_GLOSSARY_2026-07-05.md](APP_TERMS_GLOSSARY_2026-07-05.md)
4. [CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md](CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md)
5. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
6. [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md)

## 境界

この文書は overview です。完全な code catalog ではありません。変更や検証を行う時は `src/`, `tests/`, `schemas/`, CLI help, current artifact を直接確認します。
