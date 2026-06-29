<!--
作成日: 2026-06-29_21:02 JST
更新日: 2026-06-29_21:02 JST
-->

# Profit Core Scope Docs 実装計画

## チェックポイントID

CP1 profit core scope docs

## 目的

Profit Core を「実際のお金に近い証拠、費用と悪条件への耐性、続けるか止めるか待つかの判断」に限定し、Strategy Lab、NDX、Trade[XYZ]、Workbench、AI Review、audit/remediation を Core に接続する時だけ Add-on として扱う文書を追加する。

## 現状

- `docs/CURRENT_STATE.md` は current entrypoint として、主要 surface と readiness 境界を短く案内している。
- README の `Judgment Notes` は正本ではない利益目線の判断メモへ案内している。
- `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` は「儲かった気になる前に止める」判断補助として存在する。
- Crypto Perp の profit-readiness docs は `actual_cash_result_usd` と proxy / estimate の境界、`NO_TRADE` の扱い、live permission ではないことを既に定義している。

## 制約

- 実装、schema、CLI、CI、runtime artifact は変更しない。
- 既存の practical decision note は置き換えない。
- 既存 docs は肥大化させず、README と `docs/CURRENT_STATE.md` は導線追加に留める。
- `actual_cash` を estimate/proxy と混同しない。
- `PASS`、`READY_FOR_HUMAN_REVIEW`、`READ_ONLY_GO`、viewer 完成、docs 量、CLI 数、artifact 数を利益進捗として扱わない。

## 対象ファイル

- `docs/PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md`
- `docs/PROFIT_CORE_SCOPE_USER_GUIDE_2026-06-29.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## 実装方針

- developer doc は Core / Add-on / Anti-KPI / new-surface rule を実装者向けに固定する。
- user guide は専門用語を減らし、利益証明ではなく損を避ける判断道具として説明する。
- README は `Judgment Notes` に 2 本を足す。
- `docs/CURRENT_STATE.md` は結論と「現在できること」に導線を足す。
- existing practical decision note は supporting context として参照する。

## 実装手順

1. `.ai-work` に今回の checkpoint と境界を記録する。
2. developer doc を追加する。
3. user guide を追加する。
4. README と `docs/CURRENT_STATE.md` に短い導線を追加し、timestamp を更新する。
5. `docs/final-summary.md` に latest addendum を追加する。
6. current-doc checker、whitespace check、軽量 rg 確認を実行する。
7. `.ai-work` に検証結果を記録する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `git diff --check`
- `rg -n "PROFIT_CORE_SCOPE|actual cash|Core|Add-on|NO_TRADE" README.md docs/CURRENT_STATE.md docs/PROFIT_CORE_SCOPE_*`

## 完了条件

- 新規 2 docs が hidden metadata header 付きで追加される。
- Core の定義、KPI、Anti-KPI、Add-on ルール、new-surface rule が明記される。
- user guide が「儲かった気になる前に止める道具」として説明する。
- README と `docs/CURRENT_STATE.md` から 2 docs に到達できる。
- `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` が置き換えられず参照される。
- 検証コマンドが通る。

## 失敗条件

- proxy / estimate を actual cash proof と読める表現にする。
- Add-on surface を利益証明または readiness proof と読める表現にする。
- 既存 docs を長く肥大化させる。
- code/schema/CLI/runtime artifact を変更する。

## 影響範囲

docs-only。現在の判断入口と利益目線の誤読防止導線が増える。

## ロールバック方針

新規 2 docs とこの plan doc を削除し、README、`docs/CURRENT_STATE.md`、`docs/final-summary.md` の追記と timestamp を戻す。code/schema/CLI/runtime data は変更しない。

## 代替案

- `AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` に追記する案: 既存 note がさらに長くなり、scope-control と practical memo が混ざるため採用しない。
- README に長く書く案: current entrypoint が肥大化するため採用しない。

## 未解決事項

なし。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-scope-docs-20260629-2102`

## 移行手順

なし。

## 実装前 Critique

- 用語衝突: `actual_cash` は estimate / proxy と分ける。developer doc では field 名を使ってよいが、user guide では自然言語中心にする。
- 責任境界: Strategy Lab、NDX、Trade[XYZ]、Workbench、AI Review、audit/remediation は Core の判断を速く、強く、棄却しやすくする時だけ Add-on。
- 仕様リスク: 新規 docs が「利益化ロードマップ」に見えると危険。keep/kill/wait と NO_TRADE を中心に置く。
- テストで見るべき破壊: current-doc links / headers / EOF、whitespace、導線語句。
- readiness: ready.
