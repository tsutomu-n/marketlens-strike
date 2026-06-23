<!--
作成日: 2026-06-22_14:29 JST
更新日: 2026-06-23_22:44 JST
-->

# Document Audit 2026-06-22 Code Truth Triage

## 結論

コード、テスト、schema、config、CLI help を正にして current docs を再整理した。current docs の機械的な破損は、修正後の `uv run python scripts/check_current_docs.py` で見つからない。

ここにある件数や pass 数は、作業時点のスナップショットであり、current proof ではない。現行値は `uv run python scripts/check_current_docs.py`、`uv run python scripts/check_cli_catalog.py`、`./scripts/check` で取り直す。

1. `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md` と `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` は短い current overview / index へ作り直し済み。旧長文は `docs/archive/2026-06-23-doc-triage/` へ移動済み。
2. `docs/algo/obsidian_note_rewrites_2026-05-29/**` は current-doc checker 対象から外し、研究ノート再編物として `docs/archive/2026-06-23-doc-triage/algo/` へ移動済み。
3. current docs からは archive 先へリンクを張り替え済み。`scripts/check_current_docs.py` の current docs count は 160。
4. 旧 `.tmp/live_evidence_*` helper は archive 記録化済み。現行 tracked `.tmp` entry ではなく、operator entry でもない。

## 今回確認した正本

- `git status --short --branch`
- `git log -1 --oneline --decorate`
- `uv run sis --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `scripts/check_current_docs.py`
- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/strategy_daily_brief/README.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md`
- `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
- `docs/algo/README.md`

## 実行結果

```text
git status --short --branch
=> ## main...origin/main

git log -1 --oneline --decorate
=> f40241c (HEAD -> main, origin/main, origin/HEAD) Update restart contract verifier to add head oneline tracking and automated handoff body refresh with verification note support

uv run python scripts/check_current_docs.py
=> checked 160 current docs: metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok

uv run python scripts/check_cli_catalog.py
=> checked 208 public CLI commands against Typer registration

uv run sis --help command count check
=> `scripts/check_cli_catalog.py` の Typer 登録照合を優先する

./scripts/check
=> 未再実行。この整理は docs / checker routing 中心。Python code 変更は `scripts/check_current_docs.py` の current-doc allowlist 変更のみ。
```

tracked current docs の粗い確認。これは当時の整理用カウントであり、現在の対象数は `scripts/check_current_docs.py` の出力を優先する:

```text
docs/plan tracked Markdown/HTML outside docs/archive and plan/archive: 未再計算
archive ではないが current-doc checker 対象外の Markdown/HTML: 0
```

## 更新できるドキュメント

| 対象 | 判断 | 根拠 | 推奨作業 |
|---|---|---|---|
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | 更新済み | 古い `189 public CLI commands` と `pytest 1340 passed` は当時値として明示済み。2026-06-23_10:30 JST の軽量確認は 208 commands / 186 current docs。 | 追加対応なし。 |
| `docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md` | 更新済み | command/doc count は当時の軽量確認値であり、現行 proof ではないと明示済み。 | 追加対応なし。 |
| `docs/DOCUMENT_AUDIT_2026-06-22_CODE_TRUTH_TRIAGE.md` | 更新済み | 旧本文には `docs/CURRENT_STATE.md` や `plan/README.md` を「更新」とする完了前の記述が残っていた。現 HEAD では既に historical implementation contract へ更新済み。 | この版で現時点の分類へ更新済み。 |
| `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md` | 作り直し済み | 旧 2064 行版は current proof と誤読しやすかった。 | root には短い target overview を残し、旧長文は archive へ移動済み。 |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 作り直し済み | 旧 1387 行版は capability overview、履歴、詳細説明が同居していた。 | root には短い capability index を残し、旧長文は archive へ移動済み。 |
| `docs/IMPLEMENTED_SURFACES.md` | 小更新候補 | 大筋はコードと一致。`crypto-perp-tiny-live-measurement` の mock/guarded surface と実ネットワーク未実行の境界は既にあるが、CLI surface 表にも一言足す余地がある。 | 必須ではない。次に Crypto Perp CLI を触る時だけ補強。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | 維持更新 | `scripts/check_cli_catalog.py` で 208 command と照合済み。 | CLI 追加・削除時だけ更新。 |

## 古い内容があるドキュメント

| 対象 | 古い内容 | 影響 | 推奨 |
|---|---|---|---|
| `docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md` | `189 public CLI commands`、`pytest 1340 passed`。 | README / CURRENT_STATE から判断補助として読まれるため、現行 proof と誤読されやすかった。 | 当時値として明記済み。 |
| `docs/archive/2026-06-22-doc-routing/DOGFOOD_REVIEW_2026-06-16.md` | 2026-06-16 時点の dogfood review snapshot。 | current strategy review の使い方として読むと古い。 | archive 済み。current 入口は `docs/strategy_review/README.md` と `OPERATOR_REVIEW_PACKET_RECIPE.md`。 |
| `docs/archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md` | implementation plan としての長い coder handoff。対象 surface は current 実装済み。 | current root に置くと「これから実装する計画」と誤読される。 | archive 済み。current 入口は `docs/strategy_inputs/README.md`。 |
| `docs/archive/2026-06-22-doc-routing/live_evidence_20260526_tmp_helpers/live_evidence_current_status_2026-05-26.md` | 2026-05-26 固定の live evidence status。 | 現行 operator entry と誤読される余地があった。 | archive 記録化済み。 |

## 作り直したほうがいいドキュメント

| 対象 | 判断 | 理由 | 作り直し方 |
|---|---|---|---|
| `docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md` | 作り直し済み | 2064 行の target definition は current root に置くには重く、current proof と誤読されやすい。 | root は短い target overview。旧版は `docs/archive/2026-06-23-doc-triage/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18_FULL.md`。 |
| `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md` | 作り直し済み | 1387 行版は capability overview と履歴差分が同居していた。 | root は短い capability index。旧版は `docs/archive/2026-06-23-doc-triage/REPO_CAPABILITIES_CURRENT_2026-06-16_FULL.md`。 |
| `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` | 将来の作り直し候補 | 1085 行。利用者向け detail と schema / artifact 辞書が同居している。内容は概ねコードと一致。 | すぐには不要。次回 UI /利用者導線整理時に user guide と technical glossary を分離する。 |
| `docs/algo/obsidian_note_rewrites_2026-05-29/**` | archive 分離済み | current-doc checker 対象だったが、実装正本というより研究ノート再編物。 | `docs/archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/` に移動済み。 |

## 削除・アーカイブしてもよいドキュメント / tracked file

| 対象 | 判断 | 理由 | 推奨先 |
|---|---|---|---|
| `docs/archive/2026-06-22-doc-routing/DOGFOOD_REVIEW_2026-06-16.md` | archive 済み | dogfood snapshot。current 操作手順は別 README にある。 | 追加対応なし。 |
| `docs/archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md` | archive 済み | implementation plan は完了後の current root に残す優先度が低い。 | 追加対応なし。 |
| `docs/archive/2026-06-22-doc-routing/live_evidence_20260526_tmp_helpers/` | archive 記録化済み | 日付固定の one-off helper。現行 runbook / scripts ではない。 | 追加対応なし。 |
| `docs/archive/2026-06-23-doc-triage/REPO_CAPABILITIES_CURRENT_2026-06-16_FULL.md` | archive 済み | 旧長文 capability catalog。current root では短い index へ置換済み。 | historical detail として読む。 |
| `docs/archive/2026-06-23-doc-triage/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18_FULL.md` | archive 済み | 旧長文 target definition。current root では短い overview へ置換済み。 | historical target detail として読む。 |
| `docs/archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/` | archive 済み | 原ノート批判的リライト。Strategy Lab の code truth ではない。 | research note history として読む。 |
| `docs/archive/**` | 触らない | historical context としてすでに分離済み。 | 削除は不要。current proof として読まない。 |
| `plan/archive/**` | 触らない | implementation history として分離済み。 | 削除は不要。current proof として読まない。 |

## 現行のまま維持してよいドキュメント

| 対象 | 理由 |
|---|---|
| `README.md` | Read First / Judgment Notes / Historical References の分離が現行意図と合う。 |
| `docs/CURRENT_STATE.md` | fixed pass count を持たず、実装済み Crypto Perp plan を historical contract として扱っている。 |
| `docs/NEXT_DIRECTION_CURRENT.md` | Crypto Perp Post-MVP practical loop と未実行 tiny live 境界が明確。 |
| `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md` | `READY_FOR_HUMAN_TINY_LIVE_REVIEW` を approval boundary として扱い、live permission として読ませない。 |
| `docs/strategy_daily_brief/README.md` | Crypto Perp gate / truth-cycle follow-up の reason が明示されている。 |
| `docs/strategy_workbench_viewer/README.md` | compact summary と false-only permission flags の境界が現行コードと合う。 |
| `docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md` | 非技術者向け入口として役割が明確。 |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | CLI catalog checker と対応している。 |

## 抜け・漏れ・誤謬リスク

- archive 配下の本文正誤は今回の対象外。archive は historical context として残す前提。2026-06-23 に移動した旧長文も同じ扱い。
- `data/` runtime artifact freshness は今回の正本にしていない。fresh checkout では再生成が必要。
- 外部サイトを参照する Crypto Perp reference docs は、今回 live web 再確認していない。コード上の参照・境界としてだけ確認した。
- `docs/AGENT_ASSESSMENT_*` は判断補助として有用だが、current proof にしない運用が必須。
- 実ネットワークの Crypto Perp tiny live measurement は未実行。別の明示承認、isolated margin、withdrawal disabled API key、IP restriction、max notional 25 USD、max open positions 1、reduce-only close、flat reconciliation がない限り扱わない。

## 次の実行順

1. `./scripts/check` を必要に応じて再実行する。今回の最小確認は `uv run python scripts/check_current_docs.py`。
2. 次の docs cleanup では `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md` を user guide / technical glossary に分割するか判断する。
3. CLI 追加・削除時は `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` と `scripts/check_cli_catalog.py` を同じ pass で更新する。
