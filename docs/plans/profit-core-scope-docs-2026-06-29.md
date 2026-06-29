<!--
作成日: 2026-06-29_21:02 JST
更新日: 2026-06-29_21:44 JST
-->

# Edge Candidate Factory / Execution Evidence Core Docs 実装計画

## チェックポイントID

CP1 edge candidate factory core docs

## 目的

Profit Core を Discovery / Validation / Execution Evidence の 3 層に整理し、Edge Candidate Factory を Core に昇格する。ただし候補生成は利益証拠ではなく、未検証候補、探索履歴、棄却理由、metric summary を保存して、shortlist だけを次段へ渡す Discovery Core として固定する。

## 現状

- `docs/PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md` は Profit Core を actual cash evidence、cost-stress survival、kill / wait / run decision に限定している。
- `docs/PROFIT_CORE_SCOPE_USER_GUIDE_2026-06-29.md` は利用者向けに、合格表示や AI review は利益証明ではないと説明している。
- `docs/CURRENT_STATE.md` と README は Profit Core docs への導線を持つ。
- strategy idea candidate docs は存在するが、Edge Candidate Factory / Execution Evidence Core の scope-control としては独立していない。

## 制約

- docs-only。実装、schema、CLI、CI、runtime artifact、依存関係、外部 API 連携は変更しない。
- `actual_cash` を estimate、preview、paper、virtual、simulation、operator estimate と混同しない。
- Edge Candidate Factory は Core だが、profit evidence ではない。
- LLM review は Core に入れるが、permission engine、official metric calculator、order generator、strategy editor ではない。
- v0 取引対象は crypto perps。Nasdaq / QQQ / SPY / NY proxy、Nikkei proxy、gold / silver、US rates、VIX、DXY、USDJPY は cross-market context feature として扱い、外部市場の standalone trade path は Add-on に置く。

## 対象ファイル

- `docs/EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md`
- `docs/PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md`
- `docs/PROFIT_CORE_SCOPE_USER_GUIDE_2026-06-29.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/final-summary.md`
- `docs/plans/profit-core-scope-docs-2026-06-29.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## 実装方針

- 新規 `EDGE_CANDIDATE_FACTORY_CORE` doc に Discovery / Validation / Execution Evidence の定義、入力カテゴリ、artifact 案、4 種類のサンプル、候補生成 Phase A-D、cross-market context、kill gate、virtual gate、LLM adversarial review、禁止事項、v0 実装順、現 repo との接続を集約する。
- developer doc は 3 層 Core / Core 補助 / Add-on の分類へ改訂し、既存の actual cash / NO_TRADE / kill decision 境界は残す。
- user guide は候補をたくさん作ることと儲かった証拠を分け、LLM は許可者ではなく止める理由を探す検査役として説明する。
- README と `docs/CURRENT_STATE.md` は短い導線だけ追加する。
- `docs/final-summary.md` には今回の docs-only addendum を追記する。

## 実装手順

1. `.ai-work` に今回の checkpoint、ブランチ、開始状態を記録する。
2. 新規 Edge Candidate Factory doc を作る。
3. developer doc を 3 層 Core 定義へ改訂する。
4. user guide を候補生成 / 仮想約定 / 実損益の違いが分かる形へ改訂する。
5. README と `docs/CURRENT_STATE.md` に導線を追加し、timestamp を更新する。
6. `docs/final-summary.md` に addendum を追記する。
7. current-doc checker、whitespace check、軽量 rg 確認を実行する。
8. `.ai-work` に検証結果を記録する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `git diff --check`
- `rg -n "Edge Candidate Factory|Discovery Core|Validation Core|Execution Evidence Core|LLM Adversarial|actual cash|virtual|NO_TRADE|cross-market|candidate sample|event sample" README.md docs/CURRENT_STATE.md docs/PROFIT_CORE_SCOPE_* docs/EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md`

## 完了条件

- `docs/EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md` が hidden metadata header 付きで追加される。
- Profit Core が Discovery / Validation / Execution Evidence の 3 層として説明される。
- Edge Candidate Factory は candidate 生成・探索履歴保存・棄却理由保存・shortlist export の Core だが、利益証拠ではないと明記される。
- 4 種類のサンプルが区別され、actual cash sample が利益証拠として扱える最初の層だと明記される。
- LLM は adversarial reviewer に限定され、permission、official metric、actual_cash 判定、order 作成、strategy 自動編集を持たない。
- 外部市場は v0 の取引対象ではなく cross-market context feature として説明される。
- README と `docs/CURRENT_STATE.md` から新規 doc と Profit Core docs に到達できる。
- 検証コマンドが通る。

## 失敗条件

- candidate generation を profit evidence と読める表現にする。
- virtual / paper / demo の結果を actual cash と混同する。
- LLM を permission engine または official metric source と読める表現にする。
- 外部市場を v0 の取引対象として扱う。
- code/schema/CLI/runtime artifact を変更する。

## 影響範囲

docs-only。Profit Core の読み方、候補生成の位置づけ、Execution Evidence までの停止条件が明確になる。

## ロールバック方針

新規 `docs/EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md` を削除し、Profit Core docs、README、`docs/CURRENT_STATE.md`、`docs/final-summary.md`、この plan doc の追記と timestamp を戻す。code/schema/CLI/runtime data は変更しない。

## 代替案

- 既存 Profit Core docs だけに追記する案: Edge Candidate Factory の入力、phase、sample taxonomy が長くなりすぎるため採用しない。
- Strategy idea candidate docs に追記する案: Profit Core / Execution Evidence との境界が埋もれるため採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-scope-docs-20260629-2102`

## 移行手順

なし。

## 実装前 Critique

- Discovery Core を Core に入れると「候補生成が利益進捗」と誤読されやすい。本文では `candidate sample` と `actual cash sample` を明確に分ける。
- Validation Core と Execution Evidence Core の境界が曖昧だと paper/demo を利益証拠に見せてしまう。virtual forward は lifecycle evidence、actual cash は cash evidence と明記する。
- LLM review は Core に入れるが、最後の status も許可ではない。status vocabulary を block / revise / evidence request / human review / no additional blocker に限定する。
- README と `docs/CURRENT_STATE.md` は入口なので、長い説明を入れずリンク導線に止める。
- readiness: ready.
