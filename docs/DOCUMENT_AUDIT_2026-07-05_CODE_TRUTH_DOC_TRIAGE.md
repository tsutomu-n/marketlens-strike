<!--
作成日: 2026-07-05_10:08 JST
更新日: 2026-07-05_10:24 JST
-->

# Document Audit 2026-07-05 Code Truth Doc Triage

## 結論

コードを正とすると、current docs の最大のズレは Crypto Perp の短期終着点です。

2026-07-04 の `Pre Actual Cash Decision Gate` と progress-to-90 pack は、当時の候補分類としては有用ですが、現在の短期終着点は `crypto-perp-backtest-candidate-pack` です。したがって、Pre Actual Cash を current entry として残す docs と dogfood snapshots は archive へ移し、current docs は Backtest Candidate Pack v1 を入口にします。

## 確認した正本

- `uv run sis --help`
- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `src/sis/crypto_perp/backtest_candidate_pack.py`
- `src/sis/crypto_perp/backtest_candidate_pack_models.py`
- `src/sis/crypto_perp/backtest_candidate_pack_reports.py`
- `schemas/crypto_perp_backtest_candidate_pack.v1.schema.json`
- `tests/crypto_perp/test_backtest_candidate_pack.py`
- `data/crypto_perp/backtest_candidate_pack/latest/decision.json`
- `scripts/check_current_docs.py`

## 更新できるドキュメント

| doc | 判定 | 処置 |
|---|---|---|
| `README.md` | current entry | read order から 07-04 progress pack を外し、Backtest Candidate Pack guide へ向ける |
| `docs/CURRENT_STATE.md` | current entry | short-term Crypto Perp endpoint を Backtest Candidate Pack v1 に更新 |
| `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` | current docs policy | archive 実行結果と分類を更新 |
| `docs/IMPLEMENTED_SURFACES.md` | current surface map | Backtest Candidate Pack の split modules を反映 |
| `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md` | Crypto Perp surface map | `crypto_perp_backtest_candidate_pack.v1` と new guide を追加 |
| `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md` | operator runbook | actual cash なしの short-term endpoint として Backtest Candidate Pack を追加 |
| `docs/archive/README.md` | archive ledger | 2026-07-05 archive move を追記 |
| `scripts/check_current_docs.py` | current-doc scope | archived 07-04 progress folder を current scope から外す |

## 古い内容があるドキュメント

| doc | stale reason | 処置 |
|---|---|---|
| `docs/READ_THIS_FIRST_PROGRESS_TO_90_2026-07-04/` | 1 event / `selected_action=UNKNOWN` / Pre Actual Cash endpoint を current として扱う snapshot | archive |
| `docs/FINAL_STATE_PROGRESS_ASSESSMENT_2026-07-04.md` | 上記 folder への compatibility pointer | archive |
| `docs/PROGRESS_TO_90_ROADMAP_2026-07-04.md` | 上記 folder への compatibility pointer | archive |
| `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md` | Backtest Candidate Pack v1 に短期終着点が進んだため superseded | archive |
| `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/` | `COLLECT_MORE_SOURCES` dogfood snapshot。current proof ではない | archive |
| `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/` | varied dogfood snapshot。current proof ではない | archive |
| `docs/plans/*.md` from 2026-07-04/05 | 完了済み implementation plan。branch 名や当時 artifact を含む | archive。2026-07-05 residual-risk split で cleanup plans も archive 済み |

## 作り直したほうがいいドキュメント / 対応状況

| doc | 理由 | 今回の処置 |
|---|---|---|
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 非技術者向け説明、技術 detail、surface map が混ざる | 対応済み。旧全文を archive し、互換入口 / overview / glossary / surface reference に分割 |
| `docs/final-summary.md` | addendum が増え、current proof と history ledger が混ざる | 対応済み。旧 ledger を archive し、最新状態の短い入口に差し替え |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | surface index と低層 helper catalog が混ざりやすい | 今回は維持。完全 catalog 化は別作業 |
| `docs/trade_xyz_bot_beginner_guide.md` / `.html` | repo default が venue-neutral なのに Trade[XYZ] guide が読まれやすい | 今回は維持。次回は venue-specific guide と beginner guide を分離 |

## 削除・アーカイブしてよいドキュメント

今回削除はしない。以下を `docs/archive/2026-07-05-docs-code-truth-cleanup/` へ移す。

- `docs/READ_THIS_FIRST_PROGRESS_TO_90_2026-07-04/`
- `docs/FINAL_STATE_PROGRESS_ASSESSMENT_2026-07-04.md`
- `docs/PROGRESS_TO_90_ROADMAP_2026-07-04.md`
- `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md`
- `docs/crypto_perp/pre_actual_cash_realdata_dogfood_2026_07_04/`
- `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/`
- `docs/plans/bitget-ticker-artifact-2026-07-04.md`
- `docs/plans/crypto-perp-backtest-candidate-pack-v1-2026-07-05.md`
- `docs/plans/g3-ticker-source-2026-07-04.md`
- `docs/plans/pre-actual-cash-existing-artifact-read-2026-07-04.md`
- `docs/plans/pre-actual-cash-realdata-dogfood-2026-07-04.md`
- `docs/plans/pre-actual-cash-varied-dogfood-2026-07-04.md`
- `docs/plans/ticker-coverage-metadata-2026-07-04.md`

## 現在の代替入口

- Crypto Perp Backtest Candidate Pack current guide: `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- Current state: `docs/CURRENT_STATE.md`
- Surface map: `docs/IMPLEMENTED_SURFACES.md`
- CLI catalog: `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- Actual command: `uv run sis crypto-perp-backtest-candidate-pack`

## 抜け・漏れ・誤謬リスク

- `scripts/check_current_docs.py` は metadata/link/semantic marker を見るが、archive 判定は自動化しない。
- `docs/archive/**` は historical context なので、本文内の古い path、branch、pass count、decision は現在値ではない。
- Backtest Candidate Pack の `BACKTEST_COLLECT_MORE_DATA` は利益証明ではない。PBO と rolling stability が sample insufficient なので、current local data は候補保留ではなく追加データ収集に分類される。
- `APP_CURRENT_STATE_DETAILED` と `final-summary` の旧長文は `docs/archive/2026-07-05-residual-risk-doc-split/` に退避済み。current path は短い入口として維持する。
