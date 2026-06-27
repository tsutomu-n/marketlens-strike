<!--
作成日: 2026-06-27_07:30 JST
更新日: 2026-06-28_06:38 JST
-->

# Current Docs And Structure Triage 2026-06-27

## 結論

この文書は `marketlens-strike` の現在のドキュメント配置とディレクトリ構造だけを扱う。過去の状態、過去の pass 数、過去の branch 状態、過去の artifact snapshot はここに置かない。

今の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、`.github/workflows/ci.yml`、`pyproject.toml`、`.python-version`、`uv.lock`、CLI help である。docs は入口、説明、runbook、判断補助であり、runtime 値や readiness の正本ではない。

現在の docs は機械検証上は壊れていない。2026-06-28_06:38 JST 時点で、`scripts/check_current_docs.py` は current docs 174 件を検査し、`scripts/check_cli_catalog.py` は public CLI 216 件を Typer 登録と照合している。

ただし、古い棚卸し文書、完了済み作業ブランチ名、当時の HEAD、当時の件数、runtime artifact snapshot は current proof ではない。2026-06-27 夜の branch cleanup 後、local/remote branch は `main` のみで、完了済み作業計画は `docs/archive/2026-06-27-merged-plans/` へ移動済み。

ただし、目的別 docs を全部読んでも「コード全体を漏れなく説明している」とは言い切らない。現行 docs は入口、operator guide、surface map としては使えるが、`src/sis/reports/`、`src/sis/commands/`、低層 helper、template、tools、sidecar、runtime data までを 1 つずつ説明する完全索引ではない。完全性が必要な作業では、この文書の read order の後に `rg`, `find`, CLI help、schema、tests を直接確認する。

## 完全性の現実評価

| 観点 | 現実的な評価 | 理由 |
|---|---|---|
| 今の全体像を掴む | 十分 | `README.md`, `CURRENT_STATE.md`, `IMPLEMENTED_SURFACES.md`, この文書で主要 surface と docs 導線は辿れる。 |
| 目的別に作業を始める | 概ね十分 | backtest、NDX、Strategy Lab、Strategy Review、Crypto Perp、venue boundary は目的別 docs がある。 |
| コード全体を漏れなく説明する | 不十分 | `src/sis/reports/` と `src/sis/commands/` だけで多数の Python files があり、docs はそれらの全関数・全 helper を列挙していない。 |
| safety/readiness の誤読防止 | 概ね十分 | `READ_ONLY_GO`, `PASS`, `READY_FOR_HUMAN_REVIEW` を paper/live permission と読ませない記述が複数 docs にある。 |
| runtime artifact の現在値 | 不十分、意図的 | `data/`, `logs/`, `.tmp/` は生成状態であり、docs に固定値を置かない方針。 |
| 古い文書の排除 | 概ね十分 | archive と plan/archive は current proof ではないと明記。ただし archive 本文の意味を誤読する余地は残る。 |
| ディレクトリ構造の完全な説明 | 改善済みだが完全ではない | 主要領域は表にあるが、低層 helper や sidecar/tools は必要時にコード確認が必要。 |

## 現在の実装構造

| 領域 | 現在の場所 | 役割 |
|---|---|---|
| CLI root | `src/sis/cli.py` | `sis` Typer root app。public command surface の入口。 |
| CLI command wrappers | `src/sis/commands/` | CLI 引数、入出力、report command の薄い wrapper。 |
| Backtest | `src/sis/backtest/`, `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/` | strategy backtest、artifact pack、optional framework contracts、Trade[XYZ] pure backtest surface。 |
| Research / NDX | `src/sis/research/`, `src/sis/research/dag/`, `src/sis/research/ndx/`, `configs/research_layer_2_2/ndx`, `configs/research_layer_2_3/ndx`, `configs/research_layer_2_4/ndx` | NDX local research gates、DAG、feature/residual/paper-observation flow。 |
| Strategy Lab / Authoring | `src/sis/research/strategy_lab/`, `docs/strategy_research_lab/examples/` | Strategy Lab artifacts、YAML authoring、paper-only evaluation。 |
| Strategy operation loop | `src/sis/strategy_*` directories | input, feedback, stage, smoke, runtime observation, drift, learning, case lite/index, daily brief, AI review, model loop, micro-live plan, scale decision, viewer。 |
| Crypto Perp | `src/sis/crypto_perp/`, `src/sis/crypto_perp/bitget/`, `configs/crypto_perp/` | truth-cycle artifact chain、Bitget public/account/order-preview/tiny-live guarded surfaces。 |
| Venue / execution / paper | `src/sis/venues/`, `src/sis/execution/`, `src/sis/paper/` | Trade[XYZ] read-only surfaces、execution state、paper operation artifacts。 |
| Reports / operations | `src/sis/reports/`, `src/sis/ops/`, `src/sis/state/` | phase gate、operations dashboard/bundle/timeline、audit/remediation/readiness reports。 |
| Low-level domain helpers | `src/sis/core/`, `src/sis/bot/`, `src/sis/strategies/`, `src/sis/risk/`, `src/sis/tracking/`, `src/sis/validation/`, `src/sis/storage/` | 共通 model、bot preview、strategy helpers、risk/halt、tracking、validation、storage helper。目的別 docs では薄く、作業時はコードを直接読む。 |
| Market / protocol helpers | `src/sis/real_market/`, `src/sis/research_protocol/`, `src/sis/market_calendar.py` | real market providers、research protocol、market calendar。外部入力や calendar 関連作業では docs だけに依存しない。 |
| Schemas | `schemas/` | JSON artifact contracts。現在 143 files。 |
| Tests | `tests/` | domain 別 pytest。`tests/backtest/`, `tests/strategy_authoring/`, `tests/crypto_perp/`, `tests/strategy_*` が主要 slice。 |
| Templates | `templates/` | event calendar、evidence card、go/no-go report、research signals、venue cost matrix の templates。 |
| Tooling / spikes | `tools/`, `sidecars/`, `archive/legacy_sidecars`, `package.json`, `Justfile` | external validation、OSS spikes、legacy sidecars、Bun lockfile integrity、task shortcuts。Python/uv が主導線で、Node は main app entrypoint ではない。 |
| Runtime state | `data/`, `logs/`, `.tmp/` | generated/runtime state。fresh checkout の正本ではない。 |
| Docs | `docs/` | current docs、runbooks、guides、reference、archive。 |
| Plans | `plan/` | active/historical implementation contracts。current proof ではない。 |

## コード正本に対する docs のカバー範囲

| コード領域 | docs カバー | 実務上の扱い |
|---|---|---|
| `src/sis/backtest/` | 高 | `docs/backtest/README.md` と関連 docs がある。ただし helper 単位は tests/code を読む。 |
| `src/sis/research/`, `configs/research_layer_*` | 高 | `docs/research/ndx/README.md` と layer docs がある。artifact 現在値は再実行で確認。 |
| `src/sis/research/strategy_lab/` | 高 | `docs/strategy_research_lab/` がある。examples と schema を併読する。 |
| `src/sis/strategy_*` | 中 | 各 `docs/strategy_*/README.md` がある。細部は schema/tests を読む。 |
| `src/sis/crypto_perp/` | 中 | runbook と references はある。実ネットワークや tiny-live は docs だけで進めない。 |
| `src/sis/reports/` | 中から低 | operations/audit/remediation 系 docs はあるが、report helper 全体の完全索引ではない。 |
| `src/sis/commands/` | 中から低 | CLI catalog はあるが、command wrapper の内部詳細は docs にない。`uv run sis <command> --help` と code を確認する。 |
| `src/sis/core/`, `bot`, `risk`, `tracking`, `validation`, `storage`, `strategies` | 低 | 補助層としてコードに存在するが、目的別 docs では薄い。変更時は tests/code 優先。 |
| `src/sis/real_market/`, `research_protocol` | 低 | 関連 docs は断片的。外部 data/provider 作業時は code/config/tests を直接確認する。 |
| `templates/`, `tools/`, `sidecars/` | 低 | 補助資産。日常入口ではない。使う時に現物確認する。 |

## 現在の docs 配置

| docs 領域 | 現在の役割 |
|---|---|
| `README.md` | repo 入口。主要 docs への read order。 |
| `docs/CURRENT_STATE.md` | 現在地の短い入口。 |
| `docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md` | 非技術者向け説明。 |
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 詳細説明。大きいため将来の分割候補。 |
| `docs/CODE_STATUS.md` | code/status の誤読防止。 |
| `docs/IMPLEMENTED_SURFACES.md` | 実装済み surface map。 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 次方向と外部入力時の再確認入口。 |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 技術向け capability index。 |
| `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md` | 平易な capability 説明。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | public CLI catalog。CLI 変更時に更新する。 |
| `docs/backtest/` | backtest guide/reference/non-goals/Trade[XYZ] pure backtest docs。 |
| `docs/research/ndx/` | NDX research gates の current docs。 |
| `docs/strategy_research_lab/` | Strategy Lab / Strategy Authoring docs と examples。 |
| `docs/strategy_*` | Strategy operation loop の各 artifact surface docs。 |
| `docs/runbooks/` | operator runbooks。 |
| `docs/venues/` | venue boundary docs。 |
| `docs/references/crypto_perp/` | Crypto Perp reference / adoption decisions。 |
| `docs/algo/` | strategy ideas / parts / factory docs。 |
| `docs/archive/` | historical docs。current proof として読まない。 |
| `docs/plans/` | 現在 tracked file なし。 |
| `plan/2026-06-22-strategy-feedback-case-index/` | 現在 allowlist された active plan package。 |
| `plan/archive/` | historical plans。current proof として読まない。 |

## 判定基準

この分類は code-truth docs triage のための作業用 checklist であり、文書の価値判断ではない。判定時は次を優先する。

| 分類 | 判定基準 | 確認元 |
|---|---|---|
| 更新できるドキュメント | 現行の入口、runbook、surface map、operator route、CLI/schema/test の説明として使われており、局所更新で code truth に追従できる。 | `scripts/check_current_docs.py` の current allowlist / current dir、`src/`, `tests/`, `schemas/`, CLI help。 |
| 古い内容があるドキュメント | 作成時点の branch、HEAD、pass count、artifact snapshot、判断メモ、履歴要約を含み、現行判断では再確認が必要。 | 文書本文、archive routing、runtime artifact 参照、`git status`、CLI/checker 再実行結果。 |
| 作り直したほうがいいドキュメント | 入口、利用者説明、技術詳細、operator 手順、capability catalog が混ざり、次の変更で局所修正より分割のほうが安全。 | 文書の役割重複、読者混在、`docs/IMPLEMENTED_SURFACES.md` と CLI catalog との重なり。 |
| 削除・アーカイブしてもよいドキュメント | superseded audit、完了済み plan、生成 report、current routing から外れた snapshot。即削除ではなく archive 維持を基本にする。 | `docs/archive/`, `plan/archive/`, `scripts/check_current_docs.py` の excluded prefixes / legacy root paths。 |

## 更新できるドキュメント

以下は現行 docs として維持し、コードや CLI が変わった時に同じ pass で更新する。

| 対象 | 今の扱い | 更新条件 |
|---|---|---|
| `README.md` | 入口として維持。 | read order、主要 surface、setup command が変わった時。 |
| `docs/CURRENT_STATE.md` | 現在地の短い入口として維持。 | product axis、外部入力、主要 surface が変わった時。 |
| `docs/CODE_STATUS.md` | safety/readiness の誤読防止として維持。 | readiness boundary や exposed operator path が変わった時。 |
| `docs/IMPLEMENTED_SURFACES.md` | 実装済み surface map として維持。 | CLI、schema、tests、domain surface が増減した時。 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 次方向の入口として維持。 | 次に進める作業や外部入力 checklist が変わった時。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | CLI catalog として維持。 | `scripts/check_cli_catalog.py` の照合結果が変わる CLI 追加/削除時。 |
| `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` | docs / directory 現在地として維持。 | ディレクトリ構造、read order、分類が変わった時。 |
| `docs/runbooks/README.md` | operator route table として維持。 | runbook が増減した時。 |
| `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md` | Crypto Perp Truth-Cycle の operator runbook として維持。 | Crypto Perp CLI、artifact schema、manual outcome / tiny-live boundary が変わった時。 |
| `docs/backtest/README.md` | backtest 入口として維持。 | backtest CLI、artifact schema、optional framework surface が変わった時。 |
| `docs/research/ndx/README.md` | NDX research 入口として維持。 | NDX layer/config/CLI が変わった時。 |
| `docs/strategy_research_lab/README.md` | Strategy Lab / Authoring 入口として維持。 | authoring schema、examples、CLI flow が変わった時。 |

## 古い内容があるドキュメント

以下は current proof ではない。過去値や判断補助を含む可能性があるため、現行判断では必ず code、CLI、schema、tests、current runtime artifact を先に見る。

| 対象 | 今の扱い | 推奨 |
|---|---|---|
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | 判断補助。正本ではない。 | 残す。冒頭の非正本注意を強める余地あり。 |
| `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` | 判断補助。正本ではない。 | 残す。冒頭の非正本注意を強める余地あり。 |
| `docs/MIGRATION_HISTORY.md` | 実装履歴。正本ではない。 | 残す。current readiness へリンクしない。 |
| `docs/archive/2026-06-27-doc-routing/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` | 過去 audit。`f40241c` HEAD と 2026-06-23 時点の整理を含む。 | archive 済み。最新入口にはしない。 |
| `docs/archive/2026-06-27-doc-routing/DOCUMENT_AUDIT_2026-06-26_CODE_TRUTH_DOC_TRIAGE.md` | 過去 audit。`a9faf8a` HEAD、current docs 161 件、public CLI 208 件などの当時値を含む。 | archive 済み。最新入口にはしない。 |
| `docs/final-summary.md` | merge summary。 | 残す。current proof ではなく merge 時点の要約として読む。 |
| `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md` | run plan。`ai/crypto-perp-profit-readiness-20260627-1901` など作業当時の branch 前提を含む。 | 計画として残す。現在の branch 状態や artifact 状態は code/CLI/artifact inventory で確認する。 |
| `docs/archive/2026-06-27-merged-plans/*.md` | 完了済み作業の implementation plan。多くが削除済み branch 名を含む。 | archive 済み。current proof として読まない。 |
| `docs/archive/**` | historical context。 | current proof として読まない。 |
| `plan/archive/**` | historical implementation plan。 | current proof として読まない。 |
| `plan/2026-06-22-strategy-feedback-case-index/` | allowlist された plan package。 | current proof ではなく、必要時だけ implementation context として読む。 |

## 作り直したほうがいいドキュメント

以下は壊れているという意味ではない。今の構造では 1 本に役割が集まりやすく、次に触る時は分割や再構成のほうが局所更新より安全。

| 対象 | 今の問題 | 作り直し方 |
|---|---|---|
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 利用者向け説明、技術用語、surface detail が 1 本に集まっている。 | current overview、technical glossary、artifact/schema reference に分ける。 |
| `docs/trade_xyz_bot_beginner_guide.md` と `docs/trade_xyz_bot_beginner_guide.html` | Trade[XYZ] 固有 guide と repo 全体の初心者入口が混ざりやすい。 | Trade[XYZ] 固有 guide と venue-neutral beginner guide を分ける。 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md` | capability detail と operator guide が重なりやすい。 | capability reference と execution guide に分ける。 |
| `docs/runbooks/README.md` | runbook 入口としてさらに強化できる。 | operator が目的別に辿れる route table へ整理する。 |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | capability index として使えるが、低層 helper や tools は薄い。 | 完全 catalog を目指すなら code directory / CLI / schema / tests の coverage matrix を別文書に分ける。 |
| `docs/IMPLEMENTED_SURFACES.md` | surface map として有用だが、全 helper の索引ではない。 | 「実装済み surface」と「内部 helper catalog」を分ける。 |

## 削除・アーカイブしてもよいドキュメント

現時点で即削除すべき tracked docs はない。削除より archive 維持を優先する。

| 対象 | 今の扱い | 推奨 |
|---|---|---|
| `docs/archive/2026-06-27-merged-plans/*.md` | 完了済み作業計画。 | archive 済み。削除しない。 |
| `docs/archive/2026-06-27-doc-routing/DOCUMENT_AUDIT_2026-06-26_CODE_TRUTH_DOC_TRIAGE.md` | この文書に superseded された audit。 | archive 済み。削除しない。 |
| `docs/archive/2026-06-27-doc-routing/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` | 2026-06-22/23 時点の audit。 | archive 済み。削除しない。 |
| `docs/archive/**` | archive 済み。 | 削除しない。公開配布や容量問題が出た時だけ別途 archive slimming。 |
| `plan/archive/**` | archive 済み。 | 削除しない。current proof として読まない。 |
| `docs/live_evidence_reports/` に生成される report | source doc ではない。 | tracked に戻す場合は archive か `data/` artifact 扱いにする。 |
| `plan/0607ここからの計画2/*.zip`, `plan/0608ここからの計画/**/*.zip`, `plan/0621ここから01/*.zip` | untracked ZIP。 | 中身確認なしに削除しない。使わないなら別途削除判断。 |

## 次に実行する cleanup 候補

この文書の更新では削除・移動はしない。実行する場合は別タスクとして、対象を 1 group ずつ確認してから進める。

| 優先 | 候補 | 実行条件 | 最小確認 |
|---|---|---|---|
| 1 | `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` の分割設計 | 次に利用者向け current-state docs を大きく更新する時。 | `docs/CURRENT_STATE.md`, `docs/IMPLEMENTED_SURFACES.md`, schema/tests/CLI help との差分確認。 |
| 2 | `docs/trade_xyz_bot_beginner_guide.*` の役割分離 | venue-neutral beginner guide と Trade[XYZ] 固有 guide を分ける必要が出た時。 | 現在の default scope が venue-neutral / backtest-first であることを AGENTS と current docs で再確認。 |
| 3 | `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` と `docs/IMPLEMENTED_SURFACES.md` の責務整理 | 新しい surface 追加で capability index と surface map の重複が増えた時。 | CLI catalog、schemas、tests、`src/sis/commands/` の spot check。 |
| 4 | archive slimming | 公開配布、容量、検索ノイズが問題になった時。 | archive README、git history、current-doc checker excluded prefixes を確認。削除ではなく別 archive package を優先。 |
| 5 | `docs/live_evidence_reports/` の generated report 扱い明確化 | tracked/generated の境界が再び曖昧になった時。 | `.gitignore`, docs checker allowlist、runtime artifact location を確認。 |

## 抜け・漏れ・誤謬リスク

- 以前の説明は、主要 product surface には強いが、`core`, `bot`, `real_market`, `research_protocol`, `risk`, `storage`, `tracking`, `validation`, `strategies` のような低層/補助領域を薄く扱っていた。
- `templates/`, `tools/`, `sidecars/`, root `package.json`, `Justfile`, legacy sidecar archive は、日常入口ではないが repo 構造として存在する。完全説明を求めるなら無視できない。
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` は詳しいが、現在のコード全体の完全索引ではない。読み物としての全体説明と、実装 catalog を混ぜると誤読しやすい。
- `docs/IMPLEMENTED_SURFACES.md` は実装済み surface の map として有用だが、`reports`/`commands` の helper 群を漏れなく説明する文書ではない。
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` は CLI surface の catalog であり、CLI が呼ぶ内部処理の完全説明ではない。
- archive docs は量が多く、本文正誤は current-doc checker の対象外。archive を読んで現行判断する運用は危険。
- docs checker が通ることは、全ドキュメントの意味内容が現在値に一致することを保証しない。特に HEAD、branch 名、pass count、artifact count、runtime artifact value は snapshot として扱う。
- CLI catalog が Typer 登録と一致することは、各 command wrapper の内部処理、artifact 内容、外部副作用の有無を説明し切ることを保証しない。
- 2026-06-27 の完了済み `docs/plans/` 10 件は、作業ブランチ削除後も内容上は implementation history として残っていたため、`docs/archive/2026-06-27-merged-plans/` へ移動済み。
- Crypto Perp の dogfood/status artifact や手入力 outcome を profit evidence と読むリスクは docs 側にも残る。profit-readiness 判断では `data/crypto_perp` の実 event/outcome/source availability を inventory で確認する。
- `docs/archive/**` と `plan/archive/**` は historical context であり、現在の status、readiness、実装有無の根拠として使わない。
- 低層 helper は意図的に薄くしか docs 化していない。該当領域を変更する時は、docs の網羅性を前提にせず `rg`, tests, schemas, CLI help から直接確認する。

## 今の推奨 read order

1. `README.md`
2. `docs/CURRENT_STATE.md`
3. `docs/CODE_STATUS.md`
4. `docs/IMPLEMENTED_SURFACES.md`
5. `docs/NEXT_DIRECTION_CURRENT.md`
6. `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
7. 作業領域別 docs:
   - Backtest: `docs/backtest/README.md`
   - NDX: `docs/research/ndx/README.md`
   - Strategy Lab: `docs/strategy_research_lab/README.md`
   - Strategy Review: `docs/strategy_review/README.md`
   - Crypto Perp: `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
   - Venue boundary: `docs/venues/read_only_capability_probe.md`

## 今の verification

現在の docs / CLI の最低確認:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```

広い確認:

```bash
./scripts/check
```

この文書には固定の pytest pass count、runtime hash、phase gate result、artifact snapshot を置かない。それらは作業時点で再実行して確認する。
