<!--
作成日: 2026-06-29_22:07 JST
更新日: 2026-06-29_22:07 JST
-->

# Profit Core Hybrid Modes Docs 実装計画

## チェックポイントID

CP1 profit core hybrid modes docs

## 目的

ここまでの議論を、専用フォルダー `docs/profit_core_hybrid_modes/` に開発者向けの実装判断資料としてまとめる。Verification-Throughput Core を本命、Risk-Taker Sprint を隔離された攻撃モードとして定義し、抜け漏れ、誤謬リスク、Better 案、実装順、境界条件を current repo に合わせて固定する。

## 現状

- `docs/EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md` は Discovery / Validation / Execution Evidence Core を docs-only scope-control として定義している。
- `docs/PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md` は Edge Candidate Factory を Core だが profit evidence ではないと定義している。
- `docs/strategy_idea_candidates/README.md` は candidate set、search ledger、selection-adjusted metrics、C9 v0 authoring bridge、Bitget public source refresh を実装済みとして説明している。ただし alpha evaluator、実測 Perp cost evaluator、paper/live permission は未実装。
- `docs/IMPLEMENTED_SURFACES.md` は actual cash / proxy / estimate / tiny-live shadow / risk-taker review の境界を current truth として説明している。
- 既存 worktree には今回と無関係な untracked `資料/romano_wolf_stepwise*.py` がある。触らない。

## 制約

- docs-only。実装、schema、CLI、依存関係、runtime artifact、外部 API 連携は変更しない。
- 攻撃モードは gate を緩めるモードではない。探索幅を広げるが、actual cash、NO_TRADE、search accounting、LLM negative-veto 境界は緩めない。
- `BRIDGED` は技術接続 status であり、経済的合格、alpha proof、paper/live permission ではない。
- external venue docs は制約情報として扱い、実行手順や取引許可として扱わない。
- ドキュメント timestamp は `2026-06-29_22:07 JST` を使う。

## 対象ファイル

- `docs/profit_core_hybrid_modes/README.md`
- `docs/profit_core_hybrid_modes/DEVELOPER_SPEC.md`
- `docs/profit_core_hybrid_modes/IMPLEMENTATION_CHECKPOINTS.md`
- `docs/profit_core_hybrid_modes/APPENDIX_RESEARCH_EVIDENCE.md`
- `docs/profit_core_hybrid_modes/APPENDIX_RISKS_AND_OMISSIONS.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/final-summary.md`
- `docs/plans/profit-core-hybrid-modes-docs-2026-06-29.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## 実装方針

- 専用フォルダーは docs-only の decision package とする。
- README は結論、採用案、読む順番、実装済みではない境界を短く置く。
- DEVELOPER_SPEC は mode enum、Core / Core補助 / Add-on、artifact draft、昇格ルール、禁止事項を固定する。
- IMPLEMENTATION_CHECKPOINTS は PR ではなく checkpoint 単位で、対象ファイル候補、完了条件、検証、止める条件を置く。
- APPENDIX_RESEARCH_EVIDENCE は repo-local evidence と外部 research / venue docs を分けて置く。
- APPENDIX_RISKS_AND_OMISSIONS は理想的 narrative に寄らない risk pass と Better 案を置く。
- README と `docs/CURRENT_STATE.md` から専用フォルダーへ導線を追加する。

## 実装手順

1. read-only で AGENTS、HANDOFF、current docs、CLI help、repo state を確認する。
2. この計画文書と `.ai-work` を更新する。
3. 専用フォルダー配下に 5 docs を追加する。
4. README と `docs/CURRENT_STATE.md` に短い導線を追加する。
5. `docs/final-summary.md` に addendum を追加する。
6. `uv run python scripts/check_current_docs.py`、`git diff --check`、focused `rg` を実行する。
7. `.ai-work` を検証結果で更新する。

## テスト方針

- `uv run python scripts/check_current_docs.py`
- `git diff --check`
- `rg -n "verification_throughput|risk_taker_sprint|candidate_protocol_manifest|trial_multiplicity_account|backtest_kill_gate|virtual_execution_gate|BRIDGED_TECHNICAL_ONLY|actual_cash|NO_TRADE|LLM" README.md docs/CURRENT_STATE.md docs/profit_core_hybrid_modes docs/final-summary.md`

## 完了条件

- 専用フォルダー `docs/profit_core_hybrid_modes/` が存在する。
- 開発者向け docs と付録が存在し、hidden metadata header を持つ。
- 本命 + 攻撃案の hybrid と明示的 mode switch が定義される。
- 攻撃モードが safety bypass ではなく isolated exploratory mode として説明される。
- 抜け漏れ、誤謬リスク、Better 案が付録に明記される。
- README と `docs/CURRENT_STATE.md` から到達できる。
- 検証コマンドが通る。

## 失敗条件

- 攻撃モードを actual cash / live permission へ直行できるように見せる。
- virtual PnL、paper、demo、testnet を actual cash と混同する。
- LLM review を approval engine と読める表現にする。
- C9 `BRIDGED` を経済的合格として書く。
- 外部 venue docs を実行許可や legal clearance と読める形で書く。

## 影響範囲

docs-only。current docs routing と decision package が増える。

## ロールバック方針

`docs/profit_core_hybrid_modes/` とこの plan doc を削除し、README、`docs/CURRENT_STATE.md`、`docs/final-summary.md`、`.ai-work` の追記を戻す。code/schema/CLI/runtime data は変更しない。

## 代替案

- 既存 `EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md` に追記する案: 長くなりすぎ、mode / implementation checkpoint / research appendix が混ざるため採用しない。
- `docs/REALISTIC_ROADMAP_CURRENT_2026-06-28.md` に追記する案: current roadmap 全体に影響し、今回の議論専用パッケージとして読みにくい。
- `plan/` に置く案: ユーザー要求は開発者向けドキュメントと付録であり、current docs から discoverable にする方が良い。

## 未解決事項

なし。実装時の venue 選択、実発注、認証、課金、外部送信は今回の scope 外。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-scope-docs-20260629-2102`

## 移行手順

なし。

## 実装前 Critique

- 「攻撃モード」という名前は誤読されやすい。本文では safety bypass ではなく isolated sprint と明記する。
- 本命 + 攻撃 hybrid は、Core を太らせすぎるリスクがある。実装 checkpoint は最初 3 つに削る。
- PBO / DSR / SPA / White を P0 に入れると重い。初期は required input が無い時の `NOT_ESTIMABLE` を正規の停止結果にする。
- external venue docs は current だが変わり得る。付録で「実行前再確認必須」と明記する。
- readiness: ready with assumptions.
