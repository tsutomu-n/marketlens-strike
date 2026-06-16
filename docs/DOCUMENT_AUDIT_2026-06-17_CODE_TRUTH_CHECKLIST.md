<!--
作成日: 2026-06-17_01:18 JST
更新日: 2026-06-17_06:45 JST
-->

# Code-Truth Documentation Checklist 2026-06-17

このチェックリストは 2026-06-17_01:18 JST 時点で、現在の作業ツリー込みのコード、CLI help、schemas、tests、current-doc checker を正として、docs / plan / 資料 を分類する。

## 結論

現行 docs は大きく壊れてはいない。`uv run python scripts/check_current_docs.py` は 131 current docs を pass しており、Strategy Review の専用 docs も current-doc checker 対象に入っている。

ただし、直近で `strategy-review-build` が強化されたため、top-level docs の導線が少し古い。先に直すべきは次の4点。

1. `README.md` と `docs/CURRENT_STATE.md` に `docs/strategy_review/README.md` / `OPERATOR_REVIEW_PACKET_RECIPE.md` への導線を足す。2026-06-17_01:26 JST に実施済み。
2. `docs/CODE_STATUS.md` は 2026-06-17_06:32 JST に thin index 化し、実装履歴を `docs/MIGRATION_HISTORY.md`、現行 surface を `docs/IMPLEMENTED_SURFACES.md` へ分割済み。
3. 分割後の新文書導線を `README.md`、`docs/CURRENT_STATE.md`、`docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`plan/README.md` へ 2026-06-17_06:45 JST に追加済み。
4. `plan/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` には `APPROVE_FOR_PAPER` が残る。実装後の次手では `plan/ねくすと.md` を優先し、この古い decision 名は使わない。
5. `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict 対象一覧が、現行 checker の `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`docs/strategy_lifecycle/**`、`docs/strategy_review/**` に追いついていなかったため、この監査で更新する。

## 照合した正本

確認コマンド:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run sis strategy-review-build --help
uv run python scripts/check_current_docs.py
uv run python - <<'PY'
from scripts.check_current_docs import _iter_current_docs, _repo_relative
for p in _iter_current_docs():
    print(_repo_relative(p))
PY
rg -n "strategy-review-build|Strategy Review|strategy_review" src/sis/cli.py src/sis/commands src/sis/strategy_review tests/strategy_review schemas/strategy_review_manifest.v1.schema.json -g '*.py' -g '*.json'
```

確認した事実:

- `uv run sis --help` は `strategy-review-build` を公開している。
- `uv run sis strategy-review-build --help` は `--authoring-spec` と `--lifecycle-review` を表示し、旧 `*-path` 名は表示しない。
- Strategy Review 実装は `src/sis/strategy_review/`、CLI registration は `src/sis/commands/strategy_review.py` と `src/sis/cli.py`。
- manifest schema は `schemas/strategy_review_manifest.v1.schema.json`。`producer.command` は `strategy-review-build`、`source_artifacts[].status` は `present | missing | invalid | blocked`。
- tests は `tests/strategy_review/` にあり、golden fixture は `tests/fixtures/strategy_review/` にある。
- current-doc checker 対象は 128 docs。非 archive の `docs/` Markdown / HTML は 124、非 archive の `plan/` Markdown / JSON は 65、archive 側 Markdown / HTML / JSON は 295。
- `docs/strategy_review/README.md` と `docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md` は、現行 Strategy Review contract と概ね一致する。

## 更新できるドキュメント

現行コードと大きく矛盾しない。小さい追記・導線追加で維持できる。

| Document | 判定 | 理由 | 次の更新 |
|---|---|---|---|
| `docs/strategy_review/README.md` | 更新して維持 | `strategy-review-build` の現行 CLI、manifest、optional artifact、atomic replace、section order を説明している | PR-OPERATOR-00 実装後に operator artifact への導線を追記 |
| `docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md` | 更新して維持 | copy-paste 実行、読む順番、paper / NDX gate 境界が明確 | operator review artifact ができたら command を追加 |
| `docs/strategy_review/DOGFOOD_REVIEW_2026-06-16.md` | 更新して維持 | dogfood 記録として有用。runtime artifact hash を固定していない | 新しい dogfood を足すなら別日付の record にする |
| `docs/backtest/README.md` | 更新して維持 | Strategy Review への導線を既に持つ | Backtest pack から Strategy Review へ進む最短手順を recipe 側へ寄せる |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 更新して維持 | public CLI catalog と capability summary としてまだ使える | Strategy Review を独立 section に近い形で強調し、operator recipe をリンク |
| `README.md` | 更新して維持 | repo entrypoint として正しい | 2026-06-17_01:26 JST に Read First と Main Flows へ Strategy Review docs を追加済み |
| `docs/CURRENT_STATE.md` | 更新して維持 | current state の入口として使える | 2026-06-17_01:26 JST に Strategy Review の現行 surface と「readiness proof ではない」境界を追加済み |
| `plan/README.md` | 更新して維持 | Strategy Review plan と next plan への導線を持つ | 実装済み plan と未実装 next をさらに明確に分ける |
| `plan/ねくすと.md` | 更新して維持 | 次手は `PR-OPERATOR-00` と明記済み | PR-OPERATOR-00 実装後に完了欄へ移す |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | 更新して維持 | current-doc checker の運用方針として必要 | この監査で strict 対象一覧を現行 checker に合わせる |

## 古い内容があるドキュメント

価値はあるが、そのまま current truth として読むと誤読する。

| Document | 古い内容 | コード上の現在値 | 推奨処置 |
|---|---|---|---|
| `docs/CODE_STATUS.md` | PR-00 から PR-08 と Post-PR08 が主軸で、Strategy Review が status 表に見えなかった | `strategy-review-build` は CLI / code / schema / tests / docs まで実装済み | 2026-06-17_06:32 JST に thin index 化し、`MIGRATION_HISTORY.md` と `IMPLEMENTED_SURFACES.md` へ分割済み |
| `docs/CURRENT_STATE.md` | Strategy Lifecycle / Backtest は厚いが、Strategy Review の独立導線がなかった | `docs/strategy_review/` と `strategy-review-build` が current surface | 2026-06-17_01:26 JST に追加済み |
| `README.md` | Main Flows に Strategy Review がなかった | `uv run sis strategy-review-build --help` が公開済み | 2026-06-17_01:26 JST に追加済み |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | `strategy-review-build` は Backtest section に埋もれている | Strategy Review は backtest artifact を読む別 surface | 独立小節化する |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | strict 対象一覧に `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`docs/strategy_lifecycle/**`、`docs/strategy_review/**` がない | `scripts/check_current_docs.py` はそれらを current docs として検査している | この監査で修正 |
| `plan/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` | 後半に `APPROVE_FOR_PAPER` bridge が残る | `plan/ねくすと.md` は `PAPER_OBSERVATION_CANDIDATE` 系の弱い命名へ修正済み | historical contract として読む。次手の正本にしない |
| `docs/DOCUMENT_AUDIT_2026-05-31.md` | `596 passed` / current docs `78` など当時の snapshot が多い | 現行検証は command 再実行が正本 | historical audit として扱う |
| `docs/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | `650 passed` / current docs `81` など当時の snapshot が多い | Backtest docs は 2026-06-15/16 で追加整理済み | archive 候補 |
| `docs/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` | Layer 2.3/2.4 当時の fixed snapshot が中心 | 現行 NDX docs は Layer 2.8 まで current-doc checker 対象 | archive 候補 |
| `docs/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md` | 2026-06-09 の pass count snapshot がある | current verification は command 再実行 | historical snapshot と明記して維持、または archive |
| `docs/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | live readiness blocker の古い分解 | 現行は Strategy Lifecycle / NDX paper observation / phase gate が増えている | archive 候補 |

## 作り直したほうがいいドキュメント

差分更新を続けるより、役割を分割した方が安全。

| Document | 作り直す理由 | 作り直し後の形 |
|---|---|---|
| `docs/CODE_STATUS.md` | migration PR、post-PR status、implemented surfaces、known gaps、verification snapshots が混在していた | 2026-06-17_06:32 JST に `IMPLEMENTED_SURFACES.md` と `MIGRATION_HISTORY.md` に分離済み |
| `docs/CURRENT_STATE.md` | current state、capability catalog、runtime snapshots、known gaps が長くなりすぎている | 入口 index に縮小し、詳細は domain docs へリンク |
| `docs/OPERATIONS_RUNBOOK.md` | Trade[XYZ]、NDX、Strategy Lifecycle、paper operations、long-running script が同居 | root operator index + domain runbook へ分割 |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | capability catalog と CLI catalog が一文書に大きく積まれている | capability overview と generated/checked CLI catalog を分離 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | capability 列挙が長大で、更新漏れリスクが高い | short guide + schema-driven matrix に分離 |
| `docs/trade_xyz_bot_beginner_guide.html` | HTML が read-first にあるが、Markdown 正本との同期が追いにくい | Markdown 正本を作り、HTML は companion か生成物にする |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html` | Markdown と HTML の二重保守になる | Markdown 正本から生成する運用に寄せる |

## 削除・アーカイブしてもよいドキュメント

削除より archive 推奨。過去判断の証跡として残し、current truth から外す。

| Document | 推奨 | 理由 |
|---|---|---|
| `docs/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | `docs/archive/` へ移動 | historical backtest update audit。現行 backtest は 2026-06-15/16 docs が正本 |
| `docs/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` | `docs/archive/` へ移動 | Layer 2.3/2.4 の古い snapshot |
| `docs/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | `docs/archive/` へ移動 | current blocker 正本ではない |
| `plan/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/` | `plan/archive/` へ移動 | Layer 2.5 は実装済み |
| `plan/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/` | `plan/archive/` へ移動 | Layer 2.6 / 2.7 は実装済み |
| `plan/0611ここからの計画/02_strategy_lifecycle_control_plane/` | `plan/archive/` へ移動 | Strategy Lifecycle control plane は実装済み |
| `plan/0611ここからの計画/03_paper_observation_cycle_completion/` | `plan/archive/` へ移動 | Paper observation cycle / review は実装済み |
| `plan/0616ここからの計画/01_strategy_review_builder/README.md` | 実装済み plan として archive 可能 | `strategy-review-build` は実装済み。次手は `plan/ねくすと.md` |
| `plan/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` | 実装済み contract として archive または historical 明記 | 旧 `APPROVE_FOR_PAPER` bridge が残るため、PR-OPERATOR-00 の正本にしない |
| `資料/` | active docs から外す | current-doc checker 対象外。研究素材としてのみ扱う |
| `docs/archive/**` と `plan/archive/**` | 維持 | current proof ではないが、過去判断の証跡として有用 |

## 先に直す順番

1. [x] この監査を current-doc checker 対象に入れる。
2. [x] `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict 対象一覧を現行 checker に合わせる。
3. [x] `README.md` と `docs/CURRENT_STATE.md` に Strategy Review への導線を足す。
4. [x] `docs/CODE_STATUS.md` を migration history と implemented surfaces に分割する。
5. [ ] 古い audit / plan を archive に寄せる。
6. [ ] `docs/OPERATIONS_RUNBOOK.md` を domain runbook へ分割する。

## 残リスク

- この監査は docs 分類が目的で、archive 配下 295 件の本文正誤までは個別検査していない。
- `data/` 配下の runtime artifact freshness は正本にしていない。fresh checkout で再生成する前提。
- 現在の作業ツリーには Strategy Review 実装差分が未コミットで含まれる。この監査は、その作業ツリー込みのコードを正としている。
- full gate は直前の Strategy Review 実装で `./scripts/check` pass 済みだが、この監査 doc 追加後は current-doc checker と `git diff --check` を再実行する。
