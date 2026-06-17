<!--
作成日: 2026-06-17_01:18 JST
更新日: 2026-06-17_21:52 JST
-->

# Code-Truth Documentation Checklist 2026-06-17

このチェックリストは 2026-06-17_01:18 JST 時点で、現在の作業ツリー込みのコード、CLI help、schemas、tests、current-doc checker を正として、docs / plan / 資料 を分類する。

## 結論

現行 docs は大きく壊れてはいない。current-doc checker は Strategy Review の専用 docs と `docs/NEXT_DIRECTION_CURRENT.md` も対象にしている。確認時は固定の checked count ではなく、`uv run python scripts/check_current_docs.py` を再実行する。

ただし、直近で `strategy-review-build` / `strategy-review-record`、外部入力時の read-only / observation 再確認手順、plain Japanese guide 導線、domain runbook 導線が強化されたため、top-level docs と実務 docs の導線は追加更新済み。2026-06-17_21:52 JST 時点で確認すべき点は次。

1. `README.md` と `docs/CURRENT_STATE.md` に `docs/strategy_review/README.md` / `OPERATOR_REVIEW_PACKET_RECIPE.md` への導線を足す。2026-06-17_01:26 JST に実施済み。
2. `docs/CODE_STATUS.md` は 2026-06-17_06:32 JST に thin index 化し、実装履歴を `docs/MIGRATION_HISTORY.md`、現行 surface を `docs/IMPLEMENTED_SURFACES.md` へ分割済み。
3. 分割後の新文書導線を `README.md`、`docs/CURRENT_STATE.md`、`docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`plan/README.md` へ 2026-06-17_06:45 JST に追加済み。
4. `strategy-review-record` / `operator_review.yaml` は実装済み。`plan/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` や `plan/ねくすと.md` の PR-OPERATOR-00 記述は historical として読み、現行の次手正本にしない。古い `APPROVE_FOR_PAPER` decision 名は使わない。
5. `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict 対象一覧が、現行 checker の `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`docs/strategy_lifecycle/**`、`docs/strategy_review/**` に追いついていなかったため、この監査で更新する。
6. 外部入力が来た時の再確認導線は `docs/NEXT_DIRECTION_CURRENT.md` の `External Input Restart Checklist` に集約済み。`README.md`、`docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/OPERATIONS_RUNBOOK.md`、`docs/strategy_lifecycle/README.md` から辿れる。
7. `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` は専門用語を減らして repo でできること / できないことを読む入口として追加済み。`README.md` の Read First でも上位に置く。
8. `docs/OPERATIONS_RUNBOOK.md` は root index に縮小済み。長い domain 手順は `docs/runbooks/` に分割し、current-doc checker 対象に追加済み。

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
- current-doc checker 対象件数は作業時点で変わる。確認時は `uv run python scripts/check_current_docs.py` と checker の allowlist を再確認する。
- `docs/strategy_review/README.md` と `docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md` は、現行 Strategy Review contract と概ね一致する。

## 更新できるドキュメント

現行コードと大きく矛盾しない。小さい追記・導線追加で維持できる。

| Document | 判定 | 理由 | 次の更新 |
|---|---|---|---|
| `docs/strategy_review/README.md` | 更新して維持 | `strategy-review-build` と `strategy-review-record` の現行 CLI、manifest、operator artifact、paper / live 境界を説明している | 今後 paper bridge を作る場合も、この文書では permission artifact と誤読させない |
| `docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md` | 更新して維持 | copy-paste 実行、読む順番、`operator_review.yaml` 保存 / stale check、paper / NDX gate 境界が明確 | 今後 paper bridge を作る場合も、別 plan と別 validation を要求する |
| `docs/strategy_review/DOGFOOD_REVIEW_2026-06-16.md` | 更新して維持 | dogfood 記録として有用。runtime artifact hash を固定していない | 新しい dogfood を足すなら別日付の record にする |
| `docs/backtest/README.md` | 更新して維持 | Strategy Review への導線を既に持つ | Backtest pack から Strategy Review へ進む最短手順を recipe 側へ寄せる |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 更新して維持 | public CLI catalog と capability summary としてまだ使える | Strategy Review を独立 section に近い形で強調し、operator recipe をリンク |
| `README.md` | 更新して維持 | repo entrypoint として正しい | 2026-06-17_01:26 JST に Read First と Main Flows へ Strategy Review docs を追加済み |
| `docs/CURRENT_STATE.md` | 更新して維持 | current state の入口として使える | 2026-06-17_01:26 JST に Strategy Review の現行 surface と「readiness proof ではない」境界を追加済み |
| `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` | 更新して維持 | 専門用語を減らし、repo でできること / できないことを説明する入口 | 外部入力時は `docs/NEXT_DIRECTION_CURRENT.md` の checklist を読む導線を維持 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 更新して維持 | 次方向と外部入力時の read-only / observation 再確認を分けている | `External Input Restart Checklist` を paper / live 許可と誤読させない |
| `docs/strategy_lifecycle/README.md` | 更新して維持 | paper observation status と normal / smoke threshold の読み分けを説明する | 新しい通常 paper evidence は新しい trading day を含む必要があることを維持 |
| `plan/README.md` | 更新して維持 | Strategy Review plan と next plan への導線を持つ | 実装済み plan と未実装 next をさらに明確に分ける |
| `plan/ねくすと.md` | historical として維持 | PR-OPERATOR-00 の実装計画として有用だが、現行コードでは `strategy-review-record` / `operator_review.yaml` は実装済み | 先頭で historical / implemented を明記し、現行次手には使わない |
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
| `docs/OPERATIONS_RUNBOOK.md` | Trade[XYZ]、NDX、Strategy Lifecycle、paper operations、long-running script が同居 | 2026-06-17_21:52 JST に root index + `docs/runbooks/**` へ分割済み |
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
5. [x] plain Japanese capability guide を追加し、`README.md` / `docs/CURRENT_STATE.md` / `docs/CODE_STATUS.md` から辿れるようにする。
6. [x] 外部入力時の read-only / observation 再確認を `docs/NEXT_DIRECTION_CURRENT.md` の checklist に集約し、`README.md` / `docs/CURRENT_STATE.md` / `docs/CODE_STATUS.md` / `docs/OPERATIONS_RUNBOOK.md` / `docs/strategy_lifecycle/README.md` から辿れるようにする。
7. [ ] 古い audit / plan を archive に寄せる。
8. [x] `docs/OPERATIONS_RUNBOOK.md` を domain runbook へ分割する。

## 残リスク

- この監査は docs 分類が目的で、archive 配下 295 件の本文正誤までは個別検査していない。
- `data/` 配下の runtime artifact freshness は正本にしていない。fresh checkout で再生成する前提。
- この監査は 2026-06-17 の複数回の更新を含む current docs audit であり、過去の時刻に実行した command 結果は固定 truth ではない。確認時は `uv run python scripts/check_current_docs.py` と `./scripts/check` を再実行する。
- 古い audit / plan archive は未完了。これは読みやすさの残作業であり、現行 paper / live permission ではない。
- runtime artifact freshness は `data/` の再生成状態に依存する。2026-06-17_21:39 JST の read-only 再確認では、Trade[XYZ] public user address、Bitget demo credentials、新しい trading day evidence が未入力のため、live / paper 実行許可には進んでいない。
