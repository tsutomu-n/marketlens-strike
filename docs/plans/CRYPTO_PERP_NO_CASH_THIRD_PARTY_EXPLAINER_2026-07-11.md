<!--
作成日: 2026-07-11_11:40 JST
更新日: 2026-07-11_11:47 JST
-->

# Crypto Perp No-Cash Third-Party Explainer Plan

## チェックポイントID

`DOC-20260711-CRYPTO-PERP-NO-CASH-EXPLAINER`

## 目的

Repo の概要だけを知る第三者が、Crypto Perp no-cash 検証で何を行い、何が確認され、なぜ現時点で Paper Observation 計画へ進めないのかを、コード・artifact・テストに基づいて理解できる current doc を作る。

## 現状

- no-cash artifact は `NO_CASH_BACKTEST_HOLD` と `READY_FOR_HUMAN_REVIEW_PLANNING` を返している。
- 元の bias guard は `BLOCKED` を返している。
- no-cash gate は `pbo_status` を検査するが、`bias_guard_status` を判定に使っていない。
- 既存の人間レビュー文書は確認項目を示すが、上記の矛盾を反映していない。

## 制約

- コード、テスト、schema、config、CLI help、current artifact を正本とする。
- Paper Observation、paper order、actual cash、wallet、signing、exchange write、live order を許可しない。
- 利益証明やライブ準備完了を主張しない。
- 過去の固定 pass count を現在値として扱わない。
- 第三者が Repo 全体と今回の局所作業を混同しない構成にする。

## 対象ファイル

- `docs/crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## 実装方針

単一の詳細説明書を正本候補として作り、current docs index と final summary からリンクする。本文は Repo 概要、対象範囲、処理フロー、artifact 判定、定量評価、矛盾の原因、現時点の判断、修正後の再検証、誤読防止、未確認事項を分離する。

## 実装手順

1. 現行コード、artifact、人間レビュー文書、Git 状態を照合する。
2. 第三者向け説明書を作成する。
3. current docs index と final summary に入口を追加する。
4. current-doc checker、CLI catalog checker、Markdown link、diff を検証する。
5. 作業記録を更新する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- 対象リンクと文書 metadata の目視確認

コード挙動を変更しないため、Pytest の再実行は必須条件にしない。直前に関連 focused tests 36 件が通過している事実は、今回の文書作業と区別して記載する。

最終的には標準 `./scripts/check` も実行し、`2953 passed` を含む全段階が成功した。

## 完了条件

- 第三者が「Repo 全体」「今回の no-cash lane」「現在の停止理由」「許可されていない操作」「次の修正」を区別できる。
- bias guard `BLOCKED` と後段 HOLD の矛盾が明記される。
- 数値は current artifact から出典を追える。
- current docs index から到達できる。
- 文書検査と diff check が通る。

## Critique 反映

初稿計画を次の観点で補強した。

- 30 events を独立標本と誤認しないよう、日付、銘柄、regime、方向、観測 horizon の集中を分けて示す。
- aggregate stress の正値と bias guard 内の負値は異なる集計単位であり、矛盾ではなく後者を無視したゲート連携が矛盾だと説明する。
- bias guard の既存 artifact 再利用が event count だけで照合されるため、現 artifact の不一致を断定せず、潜在的 lineage リスクとして分離する。
- 実施済み検証、未実施検証、次のコード修正、Paper Observation の将来要件を混ぜない。
- runtime artifact が Git ignore 対象であることと、`source_refs[].sha256` が raw file digest ではなく Repo 固有の `stable_hash([file_text])` であることを再現性の注意として示す。

## 失敗条件

- `NO_CASH_BACKTEST_HOLD` を Paper Observation permission と誤読させる。
- aggregate stress 正値だけを示し、bias guard の負値を隠す。
- 30 events を独立した30市場局面として扱う。
- books / trades / replay 不足だけを停止理由とし、ゲート実装の矛盾を落とす。
- 将来の修正方針を、実施済み変更として記載する。

## 影響範囲

文書ルーティングと説明のみ。コード、schema、依存関係、runtime artifact、外部サービスには影響しない。

## ロールバック方針

新規説明書と index / final summary のリンク行を削除する。コードや artifact のロールバックは不要。

## 代替案

- 既存の人間レビュー計画だけを増補する案: 計画と現状説明が混ざるため不採用。
- `CURRENT_STATE.md` に全詳細を入れる案: Repo 全体の短い入口が肥大化するため不採用。
- chat だけで説明する案: 再開可能な durable artifact が残らないため不採用。

## 未解決事項

- bias guard を candidate pack と no-cash gate のどちらで停止させるかは、次の実装修正で決める。
- Paper Observation 計画の最低観測期間、独立市場局面数、方向別取引数は未定義。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/human-review-packet-20260709-2200`

既存の human review packet と同じ責任範囲であり、worktree が clean、upstream と一致しているため継続する。

## 移行手順

不要。
