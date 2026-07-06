<!--
作成日: 2026-07-06_06:37 JST
更新日: 2026-07-06_06:37 JST
-->

# Backtest Candidate Evidence Grade Plan 2026-07-06

## チェックポイントID

CP1

## 目的

Crypto Perp backtest candidate pack の fee default を 0.04% に揃え、decision artifact に optional `evidence_grade_summary` を追加する。

## 現状

Ubuntu 側 `main` は clean。Windows の `U:` は SSHFS なので、実行と Git 操作は `/home/tn/projects/marketlens-strike` で行う。builder default と CLI default は local `main` ではまだ `0.0006`。

## 制約

既存 `crypto_perp_backtest_candidate_pack.v1` artifact を壊さないため、top-level schema required には追加しない。存在する場合の内部字段は schema と Pydantic model で検証する。actual cash、paper、tiny-live、live、wallet、signing、exchange write の permission は出さない。

## 対象ファイル

- `src/sis/crypto_perp/backtest_candidate_pack.py`
- `src/sis/crypto_perp/backtest_candidate_pack_models.py`
- `src/sis/crypto_perp/backtest_candidate_pack_reports.py`
- `src/sis/commands/crypto_perp_backtest_candidate_pack.py`
- `schemas/crypto_perp_backtest_candidate_pack.v1.schema.json`
- `tests/crypto_perp/test_backtest_candidate_pack.py`
- `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/final-summary.md`

## 実装方針

`strongest_evidence_level` は次の順で決める。

- critical source 不足または simulated trade 0: `incomplete_local_artifact`
- recomputed_minimal artifact がある: `recomputed_minimal_simulated_estimate`
- 既存 artifact のみ: `local_simulated_estimate`

## 実装手順

1. テストに `evidence_grade_summary` と fee default の期待を追加する。
2. decision model と schema に optional field を追加する。
3. builder で evidence grade summary を作り、decision artifact と markdown に入れる。
4. CLI default と docs の `0.0006` 例を `0.0004` に更新する。
5. current docs index と final summary の導線を更新する。

## テスト方針

`uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py` を最小確認にする。docs/schema/catalog は `uv run python scripts/check_current_docs.py` と `uv run python scripts/check_cli_catalog.py` で確認する。

## 完了条件

最小 Pytest、current docs checker、CLI catalog checker が通る。

## 失敗条件

既存 v1 artifact が `evidence_grade_summary` 欠落で validation 不能になる、または live/actual cash permission と誤読される出力になる。

## 影響範囲

Crypto Perp backtest candidate pack の decision artifact、CLI default、関連 docs のみ。

## ロールバック方針

このブランチの差分を revert する。schema required は変更しないため artifact migration は不要。

## 代替案

`evidence_grade_summary` を `summary` 内だけに入れる案もあるが、ユーザー指定どおり top-level optional field にする。

## 未解決事項

なし。

## 破壊的変更の有無

なし。新規 field は optional。

## ブランチ名

`ai/backtest-candidate-evidence-grade-20260706-0637`

## 移行手順

なし。
