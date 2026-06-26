<!--
作成日: 2026-06-26_23:16 JST
更新日: 2026-06-26_23:21 JST
-->

# Document Audit 2026-06-26 Code Truth Doc Triage

## 結論

2026-06-26_23:16 JST 時点の `main` / `a9faf8a` を基準に、コード、CLI、schema、tests、docs checker を正として docs を見直した。2026-06-26_23:21 JST に、最優先の archive 移動を実行済み。

今すぐ新機能開発を再開する障害になる docs 破損は見つからない。`uv run python scripts/check_current_docs.py` は current docs 161 件を通し、`uv run python scripts/check_cli_catalog.py` は Typer 登録の public CLI 208 件を通している。

ただし、docs の整理余地は残る。優先度順では、次の 4 点を扱うのがよい。

1. `docs/plans/pass_376_*.md` から `docs/plans/pass_409_*.md` までの 34 件は、既に `main` へ取り込まれた `refactor/backtest-primitives` 作業計画なので、`docs/archive/2026-06-26-refactor-backtest-primitives-plans/` へ移動済み。
2. `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` は過去 audit として有用だが、HEAD・当時の確認値・完了済み判断を含むため、今後はこの文書を最新版の docs triage 入口にする。
3. `docs/AGENT_ASSESSMENT_*_2026-06-20.md` は判断補助として有用だが、古い CLI/docs/pytest count を含む。本文内で当時値と明示されているため緊急修正は不要。ただし README / CURRENT_STATE から読まれるので、次回更新時に「現行値は必ず再実行」とさらに目立たせる余地がある。
4. `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` は 1 本に説明を集めすぎている。コードとの矛盾は今回見つけていないが、非技術者向け guide、技術 glossary、surface catalog に分け直す候補。

## 調査範囲

正本として確認したもの:

- `git status --short --branch --untracked-files=all`
- `git log -1 --oneline --decorate`
- `uv run sis --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `scripts/check_current_docs.py`
- `scripts/check_cli_catalog.py`
- `README.md`
- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md`
- `docs/final-summary.md`
- `plan/README.md`
- `src/`, `tests/`, `schemas/`, `configs/`, `.github/workflows/ci.yml` の存在と routing

調査コマンドの結果:

```text
git status --short --branch --untracked-files=all
=> ## main...origin/main

git log -1 --oneline --decorate
=> a9faf8a (HEAD -> main, origin/main, origin/HEAD) docs: update final summary after merge

uv run python scripts/check_current_docs.py
=> checked 161 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok

uv run python scripts/check_cli_catalog.py
=> checked 208 public CLI commands against Typer registration

git ls-files docs | wc -l
=> 356
```

tracked docs の粗い分布。これは 2026-06-26_23:21 JST の archive 移動後の値:

```text
docs/archive: 228 files
docs/plans: 0 files
docs/(root): 25 files
docs/strategy_research_lab: 23 files
docs/algo: 20 files
docs/research: 18 files
docs/backtest: 9 files
docs/runbooks: 6 files
```

## 判定基準

| 分類 | 意味 |
|---|---|
| 更新できる | 内容は概ね正しいが、HEAD、件数、説明の重複、導線、強調を直すと読みやすくなる。 |
| 古い内容がある | 過去の branch、commit、pass count、CLI count、artifact snapshot、作業中状態を含む。historical と明記されていれば緊急度は下げる。 |
| 作り直したほうがいい | 1 文書に複数 audience / current proof / historical detail が混ざり、局所更新より再分割が安全。 |
| 削除・アーカイブしてもよい | 現行導線ではなく、履歴としては残せるが current docs root に置く必要が薄い。 |

## 更新できるドキュメント

| 対象 | 状態 | 根拠 | 推奨 |
|---|---|---|---|
| `docs/final-summary.md` | 更新できる | merge 完了後の summary として有用。`Unrun Checks` に同じ 2 行が重複している。`2756 passed` は merge summary の証拠値として妥当だが、current proof ではない。 | 次回触る時に重複を削り、「これは merge 時点の証拠値」と明示する。 |
| `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` | 更新できる | 2026-06-23 時点の整理として有用だが、HEAD が `f40241c`、当時の軽量確認値、作り直し済み判断が混在する。 | この文書を直接更新し続けるより、今回の `docs/DOCUMENT_AUDIT_2026-06-26_CODE_TRUTH_DOC_TRIAGE.md` を最新版入口にする。 |
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | 更新できる | 古い `1340 passed`、`189/205 public CLI commands`、`151 current docs` を持つが、当時値と明記している。 | 判断補助として残す。次回更新時は「投資判断・現行 proof に使わない」を冒頭にもう一段強く置く。 |
| `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` | 更新できる | `205 public CLI commands`、`148 current docs` は現行 208 / 160 と違うが、当時値と明記している。 | 判断補助として残す。現行値を固定追記せず、再実行 command への誘導を強くする。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | 維持更新 | `scripts/check_cli_catalog.py` が public CLI 208 件を通している。 | CLI 追加・削除時だけ更新。現時点で緊急修正なし。 |
| `docs/CURRENT_STATE.md` | 維持更新 | 固定 pass count を置かず、source-of-truth と current docs / archive の優先順を明示している。 | 新しい product axis や外部入力導線が増えた時だけ更新。 |
| `README.md` | 維持更新 | Read First / Judgment Notes / Historical References が分離されている。 | 今回の新 audit doc を Read First へ入れるかは任意。docs audit を日常入口に増やしすぎると逆に読みにくい。 |

## 古い内容があるドキュメント

| 対象 | 古い内容 | 誤読リスク | 推奨 |
|---|---|---|---|
| `docs/archive/2026-06-26-refactor-backtest-primitives-plans/pass_376_operations_audit_pack_navigation.md` から `docs/archive/2026-06-26-refactor-backtest-primitives-plans/pass_409_execution_venue_diagnostics_markdown.md` | `refactor/backtest-primitives` branch 前提、実装前 pass plan、当時の対象ファイル、当時の検証計画。 | current docs としては誤読しやすかったが、archive 移動済みなので現行導線からは外れた。 | 追加対応なし。 |
| `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` | `f40241c` HEAD、2026-06-23 の軽量確認値、当時の整理完了状態。 | 最新 audit として読むと HEAD と経緯が古い。 | historical audit として残し、この文書を最新版にする。 |
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | `1340 passed`、`189 public CLI commands`、`205 public CLI commands`、`151 current docs`。 | 結論だけ拾うと現行能力値と誤読される。 | 本文内の「現行 proof ではない」を維持。現時点では削除しない。 |
| `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` | `205 public CLI commands`、`148 current docs`。 | 実用判断の補助文書なので、古い数値が一人歩きしやすい。 | 再実行 command を正として扱う。固定値更新は不要。 |
| `docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md` | `101 current docs`、`936 passed` などの historical snapshot。 | Layer 2.2 record として読む限り問題ないが、現行全体の検証値として使うと古い。 | historical implementation record のまま維持。current status は `docs/research/ndx/README.md` と CLI を見る。 |
| `docs/MIGRATION_HISTORY.md` | PR-04 から PR12 までの historical migration record。 | current readiness として読むと古い。 | 履歴として残す。現行判断に使わない。 |

## 作り直したほうがいいドキュメント

| 対象 | 判断 | 理由 | 作り直し方 |
|---|---|---|---|
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 作り直し候補 | 現状説明、利用者向け説明、schema/artifact detail、専門用語が 1 本に集まっている。内容の破損は見つけていないが、読者別に分けたほうが安全。 | `APP_CURRENT_STATE_OVERVIEW`、`TECHNICAL_SURFACE_GLOSSARY`、`ARTIFACT_AND_SCHEMA_REFERENCE` のように分ける。 |
| `docs/trade_xyz_bot_beginner_guide.md` と `.html` | 将来の作り直し候補 | Trade[XYZ] は実装済み historical/read-only venue context だが、repo の default product axis ではない。初心者向け guide としては useful だが、現在の主軸からは重い。 | Trade[XYZ] 固有 guide と、venue-neutral beginner guide を分ける。HTML は Markdown source から派生扱いを明確にする。 |
| `docs/OPERATIONS_RUNBOOK.md` と `docs/runbooks/*.md` | 部分再編候補 | operations、paper、NDX、strategy research、Trade[XYZ]、Crypto Perp が分散している。破損ではないが入口判断に迷いやすい。 | `docs/runbooks/README.md` を operator route table として強化し、個別 runbook は今のまま維持する。 |
| `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md` | 作り直し候補 | detail と guide と capability catalog が重なる。現時点では current-doc checker 対象で機械検証は通る。 | Strategy Authoring の実行 guide と capability reference を分割する。 |

## 削除・アーカイブしてもよいドキュメント

| 対象 | 判断 | 根拠 | 推奨 |
|---|---|---|---|
| `docs/archive/2026-06-26-refactor-backtest-primitives-plans/pass_376_*.md` から `pass_409_*.md` | アーカイブ済み | 34 件すべて refactor branch 上の pass plan。現在は `main` / `a9faf8a` へ統合済み。current-doc checker の current docs には含まれていない。 | 削除せず historical implementation plan として読む。 |
| `plan/0607ここからの計画2/*.zip`、`plan/0608ここからの計画/**/*.zip`、`plan/0621ここから01/*.zip` | 削除候補、または archive manifest 化候補 | `git ls-files plan` には出ない untracked ZIP。current checker の対象外。現行実装・検証の正本ではない。 | 中身を使う予定がなければ削除候補。残すなら `plan/archive/` に manifest 付きで移す。 |
| `docs/archive/**` | 追加削除は不要 | すでに historical context として隔離済み。current docs から正本扱いしない運用がある。 | 原則そのまま。さらに軽くしたい時だけ古い archive bundle を別保管へ移す。 |
| `plan/archive/**` | 追加削除は不要 | implementation history として隔離済み。`scripts/check_current_docs.py` の plan routing でも許可されている。 | 原則そのまま。現行計画として読まない。 |
| `docs/live_evidence_reports/README.md` 配下の generated report 想定 | 生成物は tracking しない | README も「generated report は source doc ではない」と明記している。 | generated report が復活したら current docs ではなく archive または data artifact として扱う。 |

## 現行のまま維持してよいドキュメント

| 対象 | 理由 |
|---|---|
| `AGENTS.md` | repo-local rules と source-of-truth 境界が現在の運用に合う。 |
| `README.md` | current docs、judgment notes、historical references の分離が機能している。 |
| `docs/CURRENT_STATE.md` | 現行入口として機能し、固定 pass count を置かない。 |
| `docs/CODE_STATUS.md` | `DONE`、`READ_ONLY_GO`、`PASS` の誤読防止が明確。 |
| `docs/IMPLEMENTED_SURFACES.md` | CLI / schema / tests / docs の surface map と安全境界が概ね現行コードと一致。 |
| `docs/NEXT_DIRECTION_CURRENT.md` | 外部入力時の再確認と old snapshot を current proof にしない境界がある。 |
| `docs/backtest/README.md` | backtest scope、verification command、no-live boundary がある。 |
| `docs/research/ndx/README.md` | NDX research gate の current entry と正本 path が明確。 |
| `docs/strategy_review/README.md` | Strategy Review が paper/live permission ではない境界を持つ。 |
| `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md` | tiny live / network / order permission の境界が明確。 |
| `docs/venues/read_only_capability_probe.md` | venue probe が fixture-first / no-network / no permission であることが明確。 |

## 実装するなら重要度順

1. `docs/plans/pass_376_*.md` から `pass_409_*.md` までを archive へ移す。2026-06-26_23:21 JST 実行済み。
   - 理由: 現在の branch / next action と誤読されやすく、34 件まとまって docs root に残っているため。
   - 検証: `uv run python scripts/check_current_docs.py`、`find docs/plans -maxdepth 1 -type f -name 'pass_*.md' | wc -l`、`find docs/archive/2026-06-26-refactor-backtest-primitives-plans -maxdepth 1 -type f -name 'pass_*.md' | wc -l`。
2. `docs/final-summary.md` の重複行だけ直す。
   - 理由: 内容は有用だが、小さな重複がある。
   - 検証: `uv run python scripts/check_current_docs.py`。
3. `docs/AGENT_ASSESSMENT_*` の冒頭に「現行 proof ではない」をさらに短く強調する。
   - 理由: 数値自体を更新し続けるより、再実行 command に寄せるほうが安全。
   - 検証: `uv run python scripts/check_current_docs.py`。
4. `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` を読者別に分割する。
   - 理由: 重要だが大きい。機能開発再開のブロッカーではない。
   - 検証: `uv run python scripts/check_current_docs.py` と links check。

## 抜け・漏れ・誤謬リスク

- archive 配下の本文正誤は全文再検証していない。archive は historical context として扱う前提。
- 外部サイトや取引所仕様の現在値は再調査していない。今回の基準は repo 内コード、CLI、schema、tests、docs checker。
- `data/` runtime artifact freshness は検証対象外。fresh checkout では artifact がない、または古い可能性がある。
- `uv run sis --help` は command surface 確認に使ったが、各 command の option-level help は全件再確認していない。
- `docs/archive/**` の削除までは推奨しない。容量や公開配布の都合が出た時だけ、別途 archive slimming として扱う。
- `plan/0607.../*.zip` などの untracked ZIP は current proof ではないが、中身を読んでいない。削除前には用途確認が必要。

## 今回の判断

現時点で main にマージ済みの新機能開発を再開するなら、docs 側で必須の修正はない。

読み間違いを減らす最優先の次手だった `docs/plans/pass_376..409` の archive 移動は完了した。残る改善は、`docs/final-summary.md` の重複行修正、`docs/AGENT_ASSESSMENT_*` の冒頭強調、`docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` の将来分割であり、新機能開発再開のブロッカーではない。
