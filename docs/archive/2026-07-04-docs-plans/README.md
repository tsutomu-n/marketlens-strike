<!--
作成日: 2026-07-04_18:37 JST
更新日: 2026-07-04_18:37 JST
-->

# Archived Docs Plans 2026-07-04

## 結論

この folder は、2026-07-04 時点で root-level `docs/plans/` に残っていた implementation plan 群の archive です。

これらは current proof ではありません。現行判断では code、CLI help、schemas、tests、runtime artifacts、current docs を先に確認してください。

## 移動理由

- `docs/plans/` が current-docs checker 対象に残っていると、branch-time plan、過去 pass count、古い artifact snapshot を current proof と誤読しやすい。
- progress-to-90 の正本は `docs/READ_THIS_FIRST_PROGRESS_TO_90_2026-07-04/` へ寄せた。
- root progress pointer docs と current docs 入口から plan 本文を main reading path に置かない方針にした。

## 扱い

- 削除ではなく archive move。
- 実装履歴、判断背景、rollback 参考としてだけ読む。
- 再利用する場合は、現行 code / CLI / schema / tests で再確認してから新しい plan を作る。
