<!--
作成日: 2026-07-04_19:37 JST
更新日: 2026-07-04_19:37 JST
-->

# Pre Actual Cash Writer Helper Plan

## チェックポイントID

PAC-WRITER-20260704

## 目的

`build_pre_actual_cash_evidence_pack()` が返す summary / decision / markdown を、public CLI を追加せず internal helper から指定出力先へ書けるようにする。

## 現状

`src/sis/crypto_perp/pre_actual_cash.py` は pack payload を返すが、source code 上の writer helper がない。`.tmp/pre_actual_cash_pack_current/` には生成済み artifact があるが、dogfood 用 API としては弱い。

## 制約

- public CLI は追加しない。
- actual cash source、cash ledger、actual cash rows、actual-cash gate、tiny-live、live order、exchange write、ML/LLM 売買判断は扱わない。
- 既存 builder の返り値と decision schema は壊さない。

## 対象ファイル

- `src/sis/crypto_perp/pre_actual_cash.py`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md`
- `docs/final-summary.md`

## 実装方針

既存 builder を単一の計算源として使い、`write_pre_actual_cash_evidence_pack()` を薄い writer にする。JSON / text の書き込みは既存 `sis.crypto_perp.io` helper に寄せる。

## 実装手順

1. summary artifact 名を定数化する。
2. internal writer helper を追加する。
3. 1 event / 1 outcome smoke test を writer 経由にし、11 artifact、schema validation、reason codes、markdown、non-goal flags を確認する。
4. docs の説明を writer ありに合わせる。
5. focused pytest、ruff、current docs check を実行する。

## テスト方針

- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q`
- `uv run ruff check src/sis/crypto_perp/pre_actual_cash.py tests/crypto_perp/test_profit_readiness_local_automation.py`
- `uv run python scripts/check_current_docs.py`

## 完了条件

- expected artifact 11個を書ける。
- `decision.json` が `crypto_perp_pre_actual_cash_decision.v1` schema に適合する。
- 1 event / 1 outcome は `COLLECT_MORE_SOURCES` になり、sample不足、source不足、UNKNOWN edge、NO_TRADE leader、bias guard不足を reason に残す。
- `decision.md` に event/outcome count、source gaps、selected action、leader action、bias guard status、non-goal flags が出る。

## 失敗条件

- public CLI が増える。
- actual cash / tiny-live / live trading readiness を主張する。
- builder と writer の計算結果が別ロジックになる。

## 影響範囲

Crypto Perp の pre-actual-cash internal builder と focused test のみ。

## ロールバック方針

この helper とテスト・docs 変更を revert する。生成 artifact は runtime output なので削除不要。

## 代替案

既存 builder の戻り値だけを dogfood API とする案もあるが、expected artifacts が明示されているため writer を追加する方が実務上明確。

## 未解決事項

なし。

## 破壊的変更の有無

なし。additive helper のみ。

## ブランチ名

`ai/pre-actual-cash-writer-audit-20260704-1937`

## 移行手順

なし。
