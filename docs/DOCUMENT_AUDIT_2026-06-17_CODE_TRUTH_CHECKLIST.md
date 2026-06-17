<!--
作成日: 2026-06-17_01:18 JST
更新日: 2026-06-18_02:27 JST
-->

# Code-Truth Documentation Checklist 2026-06-17

このチェックリストは 2026-06-17_01:18 JST 時点で、現在の作業ツリー込みのコード、CLI help、schemas、tests、current-doc checker を正として、docs / plan / 資料 を分類する。

## 結論

現行 docs は大きく壊れてはいない。current-doc checker は Strategy Review の専用 docs と `docs/NEXT_DIRECTION_CURRENT.md` も対象にしている。確認時は固定の checked count ではなく、`uv run python scripts/check_current_docs.py` を再実行する。

ただし、直近で `strategy-review-build` / `strategy-review-record`、外部入力時の read-only / observation 再確認手順、plain Japanese guide 導線、domain runbook 導線、古い audit / 実装済み plan / historical implementation-sequence snapshot の archive 導線、古い operations / evidence / paper-observation / PR12 artifact runtime snapshot の再混入 guard が強化されたため、top-level docs と実務 docs の導線は追加更新済み。2026-06-18_01:06 JST 時点で確認すべき点は次。

1. `README.md` と `docs/CURRENT_STATE.md` に `docs/strategy_review/README.md` / `OPERATOR_REVIEW_PACKET_RECIPE.md` への導線を足す。2026-06-17_01:26 JST に実施済み。
2. `docs/CODE_STATUS.md` は 2026-06-17_06:32 JST に thin index 化し、実装履歴を `docs/MIGRATION_HISTORY.md`、現行 surface を `docs/IMPLEMENTED_SURFACES.md` へ分割済み。
3. 分割後の新文書導線を `README.md`、`docs/CURRENT_STATE.md`、`docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`plan/README.md` へ 2026-06-17_06:45 JST に追加済み。
4. `strategy-review-record` / `operator_review.yaml` は実装済み。`plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` や `plan/archive/2026-06-17-plan-routing/ねくすと.md` の PR-OPERATOR-00 記述は historical として読み、現行の次手正本にしない。古い `APPROVE_FOR_PAPER` decision 名は使わない。
5. `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict 対象一覧が、現行 checker の `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`docs/strategy_lifecycle/**`、`docs/strategy_review/**` に追いついていなかったため、この監査で更新する。
6. 外部入力が来た時の再確認導線は `docs/NEXT_DIRECTION_CURRENT.md` の `External Input Restart Checklist` に集約済み。`README.md`、`docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/OPERATIONS_RUNBOOK.md`、`docs/strategy_lifecycle/README.md` から辿れる。
7. `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` は専門用語を減らして repo でできること / できないことを読む入口として追加済み。`README.md` の Read First でも上位に置く。
8. `docs/OPERATIONS_RUNBOOK.md` は root index に縮小済み。長い domain 手順は `docs/runbooks/` に分割し、current-doc checker 対象に追加済み。
9. 古い root audit / blocker docs は `docs/archive/2026-06-17-doc-routing/` へ移し、current-doc checker 対象から外した。
10. 実装済み plan / historical review plan は `plan/archive/2026-06-17-plan-routing/` へ移し、`plan/0609ここからの計画/03_venue_read_only_capability_probe/` だけを current unimplemented plan として root 側に残した。
11. `docs/CURRENT_STATE.md` は 2026-06-17_22:22 JST に 1ページ寄りの入口文書へ縮小し、詳細能力列挙は `docs/IMPLEMENTED_SURFACES.md`、`docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、domain docs へ逃がした。
12. `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` は 2026-06-17_22:30 JST に短い入口文書へ縮小し、詳細列挙は `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md` へ分離した。schema / strategy type matrix は `docs/strategy_research_lab/13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md` が担う。
13. `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` の public CLI catalog は 2026-06-17_22:40 JST に `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` へ分離し、`scripts/check_cli_catalog.py` で Typer registration と照合するようにした。`strategy-paper-observation-append` の catalog 漏れも補正済み。
14. `docs/trade_xyz_bot_beginner_guide.html` は 2026-06-17_22:53 JST に `docs/trade_xyz_bot_beginner_guide.md` を文章正本として追加し、README は Markdown 正本を先に読む導線へ変更した。
15. `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html` は 2026-06-17_23:01 JST に `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.md` を文章正本として追加し、HTML は見た目つき companion とした。
16. `docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md` は 2026-06-17_23:18 JST に Layer 2.2 historical implementation record として凍結し、Layer 2.3 以降の current status や現在の artifact hash は tracked docs へ写さず runtime artifact と再実行 command で確認する導線にした。
17. `docs/strategy_lifecycle/README.md`、`docs/research/ndx/README.md`、`docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md`、`docs/runbooks/PAPER_EXECUTION_RUNBOOK.md` は 2026-06-17_23:19 JST に NDX Layer 2.8 paper review と Strategy Lifecycle の handoff を相互リンクし、canonical review path、status command、live 非許可境界を明記した。
18. `scripts/check_current_docs.py` は 2026-06-17_23:29 JST に current status docs 専用の semantic drift guard を追加した。対象は README、current-state、capability guide、domain runbook など現在状態を説明する入口文書に限定し、監査記録や implementation record の古い snapshot 値は historical として許可する。
19. `docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html` は 2026-06-17_23:38 JST に `docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md` を文章正本として追加し、HTML は見た目つき companion とした。
20. `scripts/check_current_docs.py` は 2026-06-17_23:47 JST に HTML current docs の同名 Markdown source を必須化した。今後 human-facing HTML が増える場合も、文章正本なしでは current-doc gate を通らない。
21. `plan/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` は 2026-06-17_23:53 JST に `plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` へ移動した。本文は historical implementation plan として残し、現行次手は `docs/NEXT_DIRECTION_CURRENT.md` と `plan/README.md` から読む。
22. `plan/ねくすと.md` は 2026-06-18_00:01 JST に `plan/archive/2026-06-17-plan-routing/ねくすと.md` へ移動した。本文は Strategy Review operator artifact の historical implementation plan として残し、現行次手は `docs/NEXT_DIRECTION_CURRENT.md` と `plan/README.md` から読む。
23. `plan/0607ここからの計画2/README.md` と `plan/0607ここからの計画2/TEMPLATE_MANIFEST.json` は 2026-06-18_00:08 JST に `plan/archive/2026-06-08-plan-routing/0607ここからの計画2/zip_intake_guide/` へ移動した。feature expansion ZIP の historical intake guide / template として残し、現行次手は `docs/NEXT_DIRECTION_CURRENT.md` と `plan/README.md` から読む。
24. `scripts/check_current_docs.py` は 2026-06-18_00:15 JST に tracked plan routing guard を追加した。tracked plan file は `plan/README.md`、`plan/archive/**`、`plan/0609ここからの計画/03_venue_read_only_capability_probe/**` だけを許可し、root historical plan file の再混入を失敗させる。
25. 2026-05-31 の base audit は 2026-06-18_00:24 JST に `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31.md` へ移動した。2026-05-31 時点の audit snapshot として残し、current-doc checker 対象からは外す。
26. 2026-06-15 の code-truth checklist は 2026-06-18_00:31 JST に `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md` へ移動した。2026-06-17 checklist に superseded された historical audit として残し、current-doc checker 対象からは外す。
27. root にあった `NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md` は 2026-06-18_00:39 JST に `docs/archive/2026-06-17-doc-routing/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md` へ移動した。2026-06-17 時点の implementation-sequence snapshot として残し、現行次手は `docs/NEXT_DIRECTION_CURRENT.md` と `plan/README.md` から読む。
28. `README.md`、`docs/NEXT_DIRECTION_CURRENT.md`、`docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` は 2026-06-18_00:49 JST に、古い operations dashboard / evidence card / execution artifact の固定 snapshot 値を tracked docs へ写さず、再実行 command と読む field に寄せた。`scripts/check_current_docs.py` は同種の古い marker の再混入を current-status docs で失敗させる。
29. `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` は 2026-06-18_00:59 JST に、paper observation の session id / fills / trading days などの固定 runtime 値を tracked docs へ写さず、`strategy-paper-observation-status` と読む field に寄せた。`scripts/check_current_docs.py` は同種の古い marker の再混入を current-status docs で失敗させる。
30. `docs/NEXT_DIRECTION_CURRENT.md` と `docs/runbooks/PAPER_EXECUTION_RUNBOOK.md` は 2026-06-18_01:06 JST に、paper observation の不足量や PR12 artifact の固定 runtime 値を tracked docs へ写さず、再実行 command と読む field に寄せた。`scripts/check_current_docs.py` は同種の古い marker の再混入を current-status docs で失敗させる。
31. `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md`、`docs/archive/2026-06-17-doc-routing/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md`、`docs/archive/2026-06-17-doc-routing/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md` は、Trade[XYZ] quote coverage 収集を主目的にしていた時点の historical operational record として残す。2026-06-18_01:12 JST に current-doc checker 対象からは外した。
32. `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md` は、BP0 bridge audit 時点の fixed artifact values を含む historical evidence map として残す。2026-06-18_01:22 JST に current-doc checker 対象からは外し、現行の paper observation 状態は `docs/strategy_lifecycle/README.md` と `uv run sis strategy-paper-observation-status` で確認する導線に寄せた。
33. `docs/archive/backtest/BACKTEST_DOCS_CODE_TRUTH_AUDIT_2026-06-15.md` は、2026-06-15 時点の backtest docs 分類 audit として残す。fixed artifact values と当時の current-doc 件数を含むため、2026-06-18_01:29 JST に current-doc checker 対象から外した。
34. `docs/archive/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md` と `docs/archive/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md` は、2026-05-30/31 時点の Strategy Authoring progress / completion snapshot として残す。fixed pass counts と当時の current-doc 件数を含むため、2026-06-18_01:34 JST に current-doc checker 対象から外した。
35. `docs/LONG_RUNNING_SCRIPT_OPERATION_RUNBOOK_2026-06-05.md` と `docs/runbooks/TRADE_XYZ_RUNBOOK.md` は、2026-06-18_01:42 JST に archive 済み Trade[XYZ] quote coverage 固有 PID / 起動時刻を current 手順から外した。`scripts/check_current_docs.py` は同種の再混入を全 current docs で失敗させる。
36. `docs/archive/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md` は、backtest 責務分離の完了記録として残す。fixed pass / check 表現を含むため、2026-06-18_01:50 JST に current-doc checker 対象から外した。`docs/ARCHITECTURE_AND_PHASES.md` の `READ_ONLY_GO` 表現も runtime 再確認と live 非許可の説明へ寄せた。
37. `docs/backtest/BACKTEST_HIGH_SCHOOL_GUIDE_2026-06-15.md` は、2026-06-18_01:57 JST に dated runtime snapshot 表を外し、`strategy-backtest-artifact-summary` / `strategy-backtest-pack-validate` / `strategy-paper-observation-status` で今の値を読む説明へ寄せた。
38. `docs/archive/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md` は、外部 PyPI metadata と local import smoke の dated adoption review として残す。2026-06-18_02:04 JST に current-doc checker 対象から外し、現行の optional framework 境界は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md`、CLI help、`pyproject.toml`、`uv.lock` で確認する導線に寄せた。
39. `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md` は、2026-06-18_02:10 JST に dated runtime snapshot 表や固定 benchmark / stress / data availability 値を外し、`strategy-backtest-artifact-summary`、targeted `jq`、`strategy-paper-observation-status` で現在値を読む導線へ寄せた。
40. `docs/archive/backtest/OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md` は、実装済み OSS capability expansion plan と当時の外部調査・対象ファイル一覧を含む履歴資料として残す。2026-06-18_02:18 JST に current-doc checker 対象から外し、現行の backtest technical boundary は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md`、CLI help、`pyproject.toml`、`uv.lock` へ寄せた。
41. `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md` は、BP0 完了後に bridge adapter 不要と判定した historical bridge audit plan として残す。2026-06-18_02:27 JST に current-doc checker 対象から外し、現行の backtest-to-paper 導線は `docs/strategy_lifecycle/README.md` と `uv run sis strategy-paper-observation-status` へ寄せた。

## 照合した正本

確認コマンド:

```bash
git status --short --branch --untracked-files=all
uv run sis --help
uv run python scripts/check_cli_catalog.py
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
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 更新して維持 | capability overview としてまだ使える。public CLI catalog は分離済み | Strategy Review を独立 section に近い形で強調し、operator recipe をリンク |
| `README.md` | 更新して維持 | repo entrypoint として正しい | 2026-06-17_01:26 JST に Read First と Main Flows へ Strategy Review docs を追加済み |
| `docs/CURRENT_STATE.md` | 更新して維持 | current state の入口として使える | 2026-06-17_22:22 JST に 1ページ寄りの index へ短文化済み |
| `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` | 更新して維持 | 専門用語を減らし、repo でできること / できないことを説明する入口 | 外部入力時は `docs/NEXT_DIRECTION_CURRENT.md` の checklist を読む導線を維持 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 更新して維持 | 次方向と外部入力時の read-only / observation 再確認を分けている | `External Input Restart Checklist` を paper / live 許可と誤読させない |
| `docs/strategy_lifecycle/README.md` | 更新して維持 | paper observation status と normal / smoke threshold の読み分けを説明する | 新しい通常 paper evidence は新しい trading day を含む必要があることを維持 |
| `plan/README.md` | 更新して維持 | Strategy Review plan と next plan への導線を持つ | 2026-06-17_22:13 JST に実装済み plan と未実装 plan の root/archive 導線を整理済み |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | 更新して維持 | current-doc checker の運用方針として必要 | この監査で strict 対象一覧を現行 checker に合わせる |
| `plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` | historical として維持 | Strategy Review Builder 次期実装の計画として有用だが、現行コードでは operator record まで実装済み | root plan からは外し、archive record として読む |
| `plan/archive/2026-06-17-plan-routing/ねくすと.md` | historical として維持 | PR-OPERATOR-00 の実装計画として有用だが、現行コードでは `strategy-review-record` / `operator_review.yaml` は実装済み | root plan からは外し、archive record として読む |
| `plan/archive/2026-06-08-plan-routing/0607ここからの計画2/zip_intake_guide/README.md` | historical として維持 | feature expansion ZIP を受け取る時の形式として有用だが、現行実装計画ではない | root plan からは外し、archive template として読む |

## 古い内容があるドキュメント

価値はあるが、そのまま current truth として読むと誤読する。

| Document | 古い内容 | コード上の現在値 | 推奨処置 |
|---|---|---|---|
| `docs/CODE_STATUS.md` | PR-00 から PR-08 と Post-PR08 が主軸で、Strategy Review が status 表に見えなかった | `strategy-review-build` は CLI / code / schema / tests / docs まで実装済み | 2026-06-17_06:32 JST に thin index 化し、`MIGRATION_HISTORY.md` と `IMPLEMENTED_SURFACES.md` へ分割済み |
| `docs/CURRENT_STATE.md` | Strategy Lifecycle / Backtest は厚いが、Strategy Review の独立導線がなかった | `docs/strategy_review/` と `strategy-review-build` が current surface | 2026-06-17_01:26 JST に追加済み |
| `README.md` | Main Flows に Strategy Review がなかった | `uv run sis strategy-review-build --help` が公開済み | 2026-06-17_01:26 JST に追加済み |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | `strategy-review-build` は Backtest section に埋もれている | Strategy Review は backtest artifact を読む別 surface | 独立小節化する |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | strict 対象一覧に `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`、`docs/strategy_lifecycle/**`、`docs/strategy_review/**` がない | `scripts/check_current_docs.py` はそれらを current docs として検査している | この監査で修正 |
| `plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` | 後半に `APPROVE_FOR_PAPER` bridge が残る | `plan/archive/2026-06-17-plan-routing/ねくすと.md` は `PAPER_OBSERVATION_CANDIDATE` 系の弱い命名へ修正済み | historical contract として読む。次手の正本にしない |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31.md` | `596 passed` / current docs `78` など当時の snapshot が多い | 現行検証は command 再実行が正本 | archive 済み |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | `650 passed` / current docs `81` など当時の snapshot が多い | Backtest docs は 2026-06-15/16 で追加整理済み | archive 済み |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md` | `117 docs` / `119 docs` など当時の current-doc count と、後続更新で完了した TODO が残る | 現行分類はこの 2026-06-17 checklist と command 再実行が正本 | archive 済み |
| `docs/archive/2026-06-17-doc-routing/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md` | 2026-06-17 時点の implementation sequence、runtime snapshot、完了済み実装順が混在 | 現行次手は `docs/NEXT_DIRECTION_CURRENT.md`、active / archived plan routing は `plan/README.md` | archive 済み |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` | Layer 2.3/2.4 当時の fixed snapshot が中心 | 現行 NDX docs は Layer 2.8 まで current-doc checker 対象 | archive 済み |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md` | 2026-06-09 の pass count snapshot がある | current verification は command 再実行 | archive 済み |
| `docs/archive/2026-06-17-doc-routing/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | live readiness blocker の古い分解 | 現行は Strategy Lifecycle / NDX paper observation / phase gate が増えている | archive 済み |
| `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md` | PID、row count、phase gate、pass count など当時の snapshot が多い | 現行 Trade[XYZ] 手順は `docs/runbooks/TRADE_XYZ_RUNBOOK.md` と再実行 command が正本 | archive 済み |
| `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md` | 2026-06-04 の collector 判断記録 | 現行 next action ではない | archive 済み |
| `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md` | 旧 Trade[XYZ] quote coverage cycle 固有の自然終了条件 | 汎用の長時間 script 手順は `docs/LONG_RUNNING_SCRIPT_OPERATION_RUNBOOK_2026-06-05.md` | archive 済み |
| `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md` | BP0 bridge audit 時点の fixed artifact values を含む | 現行 paper observation 状態は Strategy Lifecycle status command で再確認する | archive 済み |
| `docs/archive/backtest/BACKTEST_DOCS_CODE_TRUTH_AUDIT_2026-06-15.md` | 2026-06-15 時点の artifact values と current-doc 件数を含む | 現行 backtest docs は `docs/backtest/README.md` から読む | archive 済み |
| `docs/archive/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md` | backtest 責務分離の実装完了時点の fixed pass / check 表現を含む | 現行 backtest 境界は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` と CLI help で確認する | archive 済み |
| `docs/archive/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md` | PyPI latest metadata、local smoke、候補順位など dated external/source review を含む | 現行 optional framework 境界は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md`、`pyproject.toml`、`uv.lock`、CLI help で確認する | archive 済み |
| `docs/archive/backtest/OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md` | 実装済み plan、外部調査、対象ファイル一覧、OBF task contract が同居している | 現行 backtest 技術境界は `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md` と CLI help が正本 | archive 済み |
| `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md` | BP0 完了後も plan 形式が残り、current read order に見えると追加 bridge 実装が必要だと誤読しやすい | 現行 paper observation 状態は `docs/strategy_lifecycle/README.md` と `strategy-paper-observation-status` が正本 | archive 済み |
| `docs/archive/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md` | 2026-05-30/31 時点の fixed pass counts と current-doc 件数を含む | 現行 Strategy Research Lab は `docs/strategy_research_lab/README.md` から読む | archive 済み |
| `docs/archive/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md` | completion-time fixed pass counts と current-doc 件数を含む | 現行 verification は current docs の command を再実行する | archive 済み |

## 作り直したほうがいいドキュメント

差分更新を続けるより、役割を分割した方が安全。

| Document | 作り直す理由 | 作り直し後の形 |
|---|---|---|
| `docs/CODE_STATUS.md` | migration PR、post-PR status、implemented surfaces、known gaps、verification snapshots が混在していた | 2026-06-17_06:32 JST に `IMPLEMENTED_SURFACES.md` と `MIGRATION_HISTORY.md` に分離済み |
| `docs/CURRENT_STATE.md` | current state、capability catalog、runtime snapshots、known gaps が長くなりすぎていた | 2026-06-17_22:22 JST に入口 index へ縮小し、詳細は domain docs へリンク済み |
| `docs/OPERATIONS_RUNBOOK.md` | Trade[XYZ]、NDX、Strategy Lifecycle、paper operations、long-running script が同居 | 2026-06-17_21:52 JST に root index + `docs/runbooks/**` へ分割済み |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | capability catalog と CLI catalog が一文書に大きく積まれていた | 2026-06-17_22:40 JST に CLI catalog を `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` へ分離し、`scripts/check_cli_catalog.py` で照合するようにした |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` | capability 列挙が長大で、更新漏れリスクが高かった | 2026-06-17_22:30 JST に short guide 化し、詳細列挙は `08_CURRENT_CAPABILITIES_DETAILS.md`、matrix は `13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md` へ分離済み |
| `docs/trade_xyz_bot_beginner_guide.html` | HTML が read-first にあるが、Markdown 正本との同期が追いにくかった | 2026-06-17_22:53 JST に `docs/trade_xyz_bot_beginner_guide.md` を文章正本として追加し、HTML は companion とした |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html` | Markdown と HTML の二重保守になる | 2026-06-17_23:01 JST に `08_CURRENT_CAPABILITIES_EXPLAINED.md` を文章正本として追加し、HTML は見た目つき companion とした |

## 削除・アーカイブしてもよいドキュメント

削除より archive 推奨。過去判断の証跡として残し、current truth から外す。

| Document | 推奨 | 理由 |
|---|---|---|
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31.md` | 移動済み | 2026-05-31 時点の historical audit。現行検証は command 再実行が正本 |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md` | 移動済み | historical backtest update audit。現行 backtest は 2026-06-15/16 docs が正本 |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md` | 移動済み | 2026-06-15 時点の code-truth checklist。2026-06-17 checklist に superseded |
| `docs/archive/2026-06-17-doc-routing/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md` | 移動済み | 2026-06-17 時点の implementation-sequence snapshot。現行次手は `docs/NEXT_DIRECTION_CURRENT.md` と `plan/README.md` |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md` | 移動済み | Layer 2.3/2.4 の古い snapshot |
| `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_QQQ_VENUE_SUITABILITY_REFRESH.md` | 移動済み | NDX/QQQ venue suitability の 2026-06-09 snapshot |
| `docs/archive/2026-06-17-doc-routing/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | 移動済み | current blocker 正本ではない |
| `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md` | 移動済み | Trade[XYZ] quote coverage 待ち時点の historical operational plan |
| `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md` | 移動済み | 2026-06-04 時点のユーザー判断記録 |
| `docs/archive/2026-06-17-doc-routing/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md` | 移動済み | 旧 Trade[XYZ] quote coverage cycle 固有の自然終了条件記録 |
| `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md` | 移動済み | BP0 bridge audit 時点の fixed artifact values を含む historical evidence map |
| `docs/archive/backtest/BACKTEST_DOCS_CODE_TRUTH_AUDIT_2026-06-15.md` | 移動済み | 2026-06-15 時点の backtest docs 分類 audit。fixed artifact values と current-doc 件数を含む |
| `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md` | 移動済み | BP0 bridge audit plan と adapter 不要判断を含む historical record |
| `docs/archive/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md` | 移動済み | 2026-05-30/31 時点の Strategy Authoring progress snapshot |
| `docs/archive/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md` | 移動済み | paper-only Strategy Authoring completion-time evidence snapshot |
| `plan/archive/2026-06-17-plan-routing/0609ここからの計画/01_ndx_qqq_venue_suitability_gate/` | 移動済み | NDX / QQQ venue suitability gate は実装済み |
| `plan/archive/2026-06-17-plan-routing/0609ここからの計画/02_bitget_hyperliquid_venue_design_gate/` | 移動済み | Bitget / Hyperliquid capability design gate は実装済み |
| `plan/archive/2026-06-17-plan-routing/0610ここからの計画/01_grok_architecture_adoption_review/` | 移動済み | external suggestion review として有用だが current implementation plan ではない |
| `plan/archive/2026-06-17-plan-routing/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/` | 移動済み | Layer 2.5 は実装済み |
| `plan/archive/2026-06-17-plan-routing/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/` | 移動済み | Layer 2.6 / 2.7 は実装済み |
| `plan/archive/2026-06-17-plan-routing/0611ここからの計画/02_strategy_lifecycle_control_plane/` | 移動済み | Strategy Lifecycle control plane は実装済み |
| `plan/archive/2026-06-17-plan-routing/0611ここからの計画/03_paper_observation_cycle_completion/` | 移動済み | Paper observation cycle / review は実装済み |
| `plan/archive/2026-06-17-plan-routing/0616ここからの計画/01_strategy_review_builder/README.md` | 移動済み | `strategy-review-build` は実装済み。次手は runtime artifact readback と外部入力待ち |
| `plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` | 移動済み | 旧 `APPROVE_FOR_PAPER` bridge が残るため、PR-OPERATOR-00 の正本にしない |
| `plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` | 移動済み | Strategy Review Builder の historical plan。現行未実装 next action として root に残さない |
| `plan/archive/2026-06-17-plan-routing/ねくすと.md` | 移動済み | Strategy Review operator artifact の historical plan。現行未実装 next action として root に残さない |
| `plan/archive/2026-06-08-plan-routing/0607ここからの計画2/zip_intake_guide/` | 移動済み | 2026-06-07 の feature expansion ZIP intake guide / template。現行未実装 next action として root に残さない |
| `資料/` | active docs から外す | current-doc checker 対象外。研究素材としてのみ扱う |
| `docs/archive/**` と `plan/archive/**` | 維持 | current proof ではないが、過去判断の証跡として有用 |

## 先に直す順番

1. [x] この監査を current-doc checker 対象に入れる。
2. [x] `docs/DOCS_LINT_POLICY_2026-05-30.md` の strict 対象一覧を現行 checker に合わせる。
3. [x] `README.md` と `docs/CURRENT_STATE.md` に Strategy Review への導線を足す。
4. [x] `docs/CODE_STATUS.md` を migration history と implemented surfaces に分割する。
5. [x] plain Japanese capability guide を追加し、`README.md` / `docs/CURRENT_STATE.md` / `docs/CODE_STATUS.md` から辿れるようにする。
6. [x] 外部入力時の read-only / observation 再確認を `docs/NEXT_DIRECTION_CURRENT.md` の checklist に集約し、`README.md` / `docs/CURRENT_STATE.md` / `docs/CODE_STATUS.md` / `docs/OPERATIONS_RUNBOOK.md` / `docs/strategy_lifecycle/README.md` から辿れるようにする。
7. [x] 古い plan を archive に寄せる。古い root audit / blocker docs は 2026-06-17_22:02 JST に、実装済み plan / historical review plan は 2026-06-17_22:13 JST に archive 済み。
8. [x] `docs/OPERATIONS_RUNBOOK.md` を domain runbook へ分割する。
9. [x] current status docs に古い固定件数や旧 NDX 判定語が再混入しないよう、`scripts/check_current_docs.py` に追加 guard を入れる。
10. [x] human-facing HTML のうち current-doc 対象で Markdown 正本がなかった `STRATEGY_FACTORY_OPERATOR_GUIDE.html` に、文章正本 `STRATEGY_FACTORY_OPERATOR_GUIDE.md` を追加する。
11. [x] HTML current docs が同名 Markdown source を持つことを `scripts/check_current_docs.py` 本体で検査する。
12. [x] historical implementation plan `plan/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md` を root plan から archive へ移す。
13. [x] historical implementation plan `plan/ねくすと.md` を root plan から archive へ移す。
14. [x] historical template `plan/0607ここからの計画2/README.md` / `TEMPLATE_MANIFEST.json` を root plan から archive へ移す。
15. [x] tracked historical plan file が root `plan/` に戻らないよう `scripts/check_current_docs.py` に plan routing guard を追加する。
16. [x] 2026-05-31 の historical audit を `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-05-31.md` へ移し、current-doc checker 対象から外す。
17. [x] 2026-06-15 の historical code-truth checklist を `docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md` へ移し、current-doc checker 対象から外す。
18. [x] root にあった `NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md` を `docs/archive/2026-06-17-doc-routing/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md` へ移し、current 次手の正本を `docs/NEXT_DIRECTION_CURRENT.md` と `plan/README.md` に寄せる。
19. [x] current status docs に古い operations / evidence / execution runtime snapshot の固定値が戻らないよう、`scripts/check_current_docs.py` に semantic drift marker を追加する。
20. [x] current status docs に古い paper-observation runtime snapshot の固定値が戻らないよう、`scripts/check_current_docs.py` に semantic drift marker を追加する。
21. [x] current status docs に古い PR12 execution / readiness artifact snapshot の固定値が戻らないよう、`scripts/check_current_docs.py` に semantic drift marker を追加する。
22. [x] Trade[XYZ] quote coverage 待ち時点の historical operational record を archive へ移し、current-doc checker 対象から外す。
23. [x] BP0 bridge audit 時点の fixed artifact values を含む backtest evidence map を archive へ移し、current-doc checker 対象から外す。
24. [x] 2026-06-15 時点の backtest docs 分類 audit を archive へ移し、current-doc checker 対象から外す。
25. [x] 2026-05-30/31 時点の Strategy Authoring progress / completion snapshot を archive へ移し、current-doc checker 対象から外す。
26. [x] archive 済み Trade[XYZ] quote coverage 固有 PID / 起動時刻を current runbook から外し、current-doc checker で再混入を止める。
27. [x] backtest 責務分離の完了記録を archive へ移し、`READ_ONLY_GO` を fixed completion proof と誤読させる current architecture 表現を外す。
28. [x] 高校生向け backtest guide から dated runtime snapshot 表を外し、現在値は backtest artifact/status command で読む導線へ寄せる。
29. [x] optional framework adoption review を archive へ移し、現行 optional framework 境界は technical reference、lockfile、CLI help で読む導線へ寄せる。
30. [x] backtest user guide から dated runtime snapshot 値を外し、現在値は artifact/status command と読む field に寄せる。
31. [x] OSS backtest capability expansion implementation plan を archive へ移し、現行 backtest technical boundary は technical reference、lockfile、CLI help に寄せる。
32. [x] backtest to paper observation bridge plan を archive へ移し、現行 paper observation status は Strategy Lifecycle README と status command に寄せる。

## 残リスク

- この監査は docs 分類が目的で、archive 配下の本文正誤までは個別検査していない。
- `data/` 配下の runtime artifact freshness は正本にしていない。fresh checkout で再生成する前提。
- この監査は 2026-06-17 の複数回の更新を含む current docs audit であり、過去の時刻に実行した command 結果は固定 truth ではない。確認時は `uv run python scripts/check_current_docs.py` と `./scripts/check` を再実行する。
- 実装済み plan archive は完了したが、archive 配下の本文内には移動前パスや当時の pass count が残る。これは historical 記録であり、現行 paper / live permission ではない。
- runtime artifact freshness は `data/` の再生成状態に依存する。2026-06-17_21:39 JST の read-only 再確認では、Trade[XYZ] public user address、Bitget demo credentials、新しい trading day evidence が未入力のため、live / paper 実行許可には進んでいない。
