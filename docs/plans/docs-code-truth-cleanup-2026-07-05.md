<!--
作成日: 2026-07-05_10:08 JST
更新日: 2026-07-05_10:08 JST
-->

# Docs Code Truth Cleanup Plan 2026-07-05

## チェックポイントID

DCT-20260705

## 目的

コード、CLI help、schema、tests、current artifact を正として、current docs と historical docs を分け直す。古い内容が current path に残っている場合は、修正ではなく archive へ移すか、現在の code truth に合う文書へ置き換える。

## 現状

- Branch: `ai/docs-code-truth-cleanup-20260705-1006`
- `uv run sis --help` は `crypto-perp-backtest-candidate-pack` を含む。
- `uv run python scripts/check_cli_catalog.py` は `234 public CLI commands` を確認した。
- `uv run python scripts/check_current_docs.py` は `181 current docs` を確認しているが、これは archive 判断を自動化しない。
- `docs/READ_THIS_FIRST_PROGRESS_TO_90_2026-07-04/` と `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md` は Pre Actual Cash を短期終着点として扱う旧入口で、現在の code truth は Backtest Candidate Pack v1 へ進んでいる。
- root `docs/plans/*.md` は完了済み implementation plans で、current proof ではない。
- `docs/crypto_perp/pre_actual_cash_*_dogfood_2026_07_04/` は tracked snapshot artifacts で、current docs path に残すと古い `COLLECT_MORE_SOURCES` / `UNKNOWN` 文脈を current と誤読しやすい。

## 制約

- 実装コードは変更しない。
- actual cash、tiny-live、live order、ML/LLM 判断は扱わない。
- archive docs は historical context として残し、削除しない。
- current docs には固定 pass count や古い branch/HEAD を正本として置かない。
- move 後は `scripts/check_current_docs.py` と link / route を通す。

## 対象ファイル

- 作成: `docs/DOCUMENT_AUDIT_2026-07-05_CODE_TRUTH_DOC_TRIAGE.md`
- 作成: `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- 更新: `README.md`
- 更新: `docs/CURRENT_STATE.md`
- 更新: `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- 更新: `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md`
- 更新: `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- 更新: `docs/IMPLEMENTED_SURFACES.md`
- 更新: `docs/archive/README.md`
- 更新: `scripts/check_current_docs.py`
- 移動: stale progress docs / pre-actual-cash gate / completed plans / dogfood snapshots to `docs/archive/2026-07-05-docs-code-truth-cleanup/`

## 実装方針

1. `Crypto Perp Backtest Candidate Pack v1` を current guide として作る。
2. 2026-07-04 progress-to-90 / pre-actual-cash gate / dogfood snapshot を historical archive へ移す。
3. 完了済み `docs/plans/*.md` を historical archive へ移す。
4. README、CURRENT_STATE、triage、surface inventory、runbook から stale paths を外し、新 current guide へ向ける。
5. checker の current dir allowlist から archived folder を外す。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- 必要なら `rg` で archived path の current references を再確認する。

## 完了条件

- current path から stale progress / dogfood snapshot / completed plans が外れている。
- current docs は Backtest Candidate Pack v1 を actual cash なしの現行短期終着点として案内する。
- archive README に移動先と理由が残る。
- docs checker が通る。

## 失敗条件

- current docs が archived file を current proof として指す。
- Backtest Candidate Pack を profit proof / paper permission / tiny-live readiness / live readiness と誤読させる。
- archive move でリンク切れや checker failure が残る。

## 影響範囲

docs と docs checker のみ。runtime artifact、schema、CLI 実装、tests は変更しない。

## ロールバック方針

archive move を `git mv` で逆向きに戻し、新規 current guide と audit doc を削除する。コード migration は不要。

## 代替案

- 古い progress docs を本文更新する: 07-04 時点の評価 snapshot と 07-05 の Backtest Candidate Pack を混ぜるため採用しない。
- dogfood snapshot を current path に残す: generated snapshot と current guidance が混ざるため採用しない。
- archive を削除する: historical evidence を失うため採用しない。

## 未解決事項

- `APP_CURRENT_STATE_DETAILED_2026-06-20.md` と `final-summary.md` は作り直し候補だが、この checkpoint では archive しない。
- current docs の完全索引化は対象外。低層 helper は引き続き code / tests / schemas を直接読む。

## 破壊的変更の有無

なし。tracked docs を archive へ移すが、削除しない。

## ブランチ名

`ai/docs-code-truth-cleanup-20260705-1006`

## 移行手順

なし。docs の読者は `README.md` と `docs/CURRENT_STATE.md` から新 current guide を読む。

## Critique 1

- archive 対象は「古い値を含む」だけでなく「current path にあると誤読しやすい」ものに限定する。
- current checker は green なので、checker 成功を理由に archive を止めない。
- Backtest Candidate Pack は current guide がないと plan/final-summary に埋もれるため、replacement doc を作る。

## Critique 2

- `docs/plans/` を全部 archive すると今回 plan も対象になり得るが、実行中の作業計画はこの checkpoint の completion record として残す。将来の cleanup で archive してよい。
- generated dogfood snapshot は削除せず archive に残す。runtime truth は `data/crypto_perp/backtest_candidate_pack/latest/decision.json` と CLI 再実行で確認する。
- 07-04 progress-to-90 docs は長期計画としての価値はあるが、short-term current entry として古い。archive へ移し、current docs からは Backtest Candidate Pack guide に置き換える。
