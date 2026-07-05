<!--
作成日: 2026-07-05_10:24 JST
更新日: 2026-07-05_10:24 JST
-->

# Crush Doc Residual Risk Plan 2026-07-05

## 目的

前回の docs cleanup で残した residual risk を消す。対象は、長い `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` と `docs/final-summary.md` が current proof / history /用語 / surface reference を混ぜて読まれるリスク。

## 方針

- 旧本文は削除せず `docs/archive/2026-07-05-residual-risk-doc-split/` に保存する。
- current path には短い入口だけを残す。
- app current state は overview、glossary、surface reference に分割する。
- final summary は最新状態の入口に戻し、古い addendum ledger は archive に回す。
- README、CURRENT_STATE、capability doc、user guide、docs checker、archive README、triage doc を同じ pass で更新する。

## 対象ファイル

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/APP_CURRENT_STATE_OVERVIEW_2026-07-05.md`
- `docs/APP_TERMS_GLOSSARY_2026-07-05.md`
- `docs/CURRENT_ARTIFACT_SURFACE_REFERENCE_2026-07-05.md`
- `docs/final-summary.md`
- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/DOCUMENT_AUDIT_2026-07-05_CODE_TRUTH_DOC_TRIAGE.md`
- `docs/DOCS_LINT_POLICY_2026-05-30.md`
- `docs/archive/README.md`
- `scripts/check_current_docs.py`

## 検証

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `./scripts/check`

## 完了条件

- read-first current docs が旧 1086 行 detailed guide や旧 2812 行 final-summary ledger を直接入口にしない。
- archive README に移動先が残る。
- current-doc checker が新しい分割 docs を検査する。
- docs checker と full gate が通る。
