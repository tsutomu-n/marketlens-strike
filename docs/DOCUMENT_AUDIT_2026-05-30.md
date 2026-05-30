# Documentation Audit 2026-05-30

コード、tests、CLI help、schema、現行 docs を正として、tracked docs を再分類した結果です。

## 結論

今の docs は、現行正本、strategy research 詳細仕様、historical snapshot、legacy/archive が混在しています。現行判断では次を正本に寄せます。

1. `README.md`
2. `docs/CURRENT_STATE.md`
3. `docs/CODE_STATUS.md`
4. `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
5. `docs/strategy_research_lab/`
6. `docs/OPERATIONS_RUNBOOK.md`
7. `docs/ARCHITECTURE_AND_PHASES.md`
8. `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md`
9. `docs/algo/strategy_factory/`
10. scoped current references:
    - `docs/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md`
    - `docs/XNYS_MARKET_CALENDAR.md`
    - `plan/README.md`

`docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` は有用ですが、2026-05-28 の focused historical audit として読み、current verification の入口にはしません。

`docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/04_ARTIFACT_EXAMPLES.md`, `05_WORKED_EXAMPLE_TREND_PULLBACK.md`, `09_CHECKLISTS_AND_TEMPLATES.md` は旧 `signals.csv` / decision log 前提が残っていたため、現行 Strategy Lab artifact chain に全面更新済みです。

## Code Truth

現行 CLI surface:

```text
strategy-preview
evaluate-strategy-lab
build-paper-candidate-pack
promotion-decision
build-paper-intent-preview
paper-from-intents
bot-preview
collect-trade-xyz-quotes
phase-gate-review
validate-artifacts
diagnose-quotes
```

現行 code surface:

```text
src/sis/research/strategy_lab/
src/sis/research_protocol/
src/sis/commands/research.py
src/sis/commands/paper.py
src/sis/paper/runner.py
src/sis/venues/trade_xyz/
src/sis/real_market/
src/sis/tracking/
src/sis/execution/
```

現行 Strategy Lab boundary:

- `data/research/strategy_signals.parquet` が canonical signal artifact。
- `data/research/signals.csv` は legacy export。
- `TradeCandidate` は order ではない。
- `PaperIntentPreview` は paper-only preview。
- `paper-from-intents` は latest quote と PaperBroker で再検証する。
- JSON Schema は thin guard。runtime validation は Pydantic model。

## 更新した docs

| Path | 変更内容 |
|---|---|
| `README.md` | Current docs read order に本 audit と Strategy Lab 入口を追加 |
| `docs/CURRENT_STATE.md` | restart read order と Strategy Lab の現行 boundary を更新 |
| `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md` | 予定だった Strategy Lab docs と appendix 更新を実施済みに変更 |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/04_ARTIFACT_EXAMPLES.md` | 旧 Signal CSV / Decision Log 例を Strategy Lab schema別 artifact例へ全面更新 |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/05_WORKED_EXAMPLE_TREND_PULLBACK.md` | Trend Pullback例を `StrategyExperimentSpec -> PaperIntentPreview -> paper-from-intents` flow へ全面更新 |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/09_CHECKLISTS_AND_TEMPLATES.md` | checklistを StrategyExperimentSpec / EvaluationPlan / TrialLedger / Candidate / Promotion / PaperIntentPreview 前提へ全面更新 |
| `docs/archive/2026-05-30-doc-audit/` | superseded docs 6本を archive move |
| `plan/archive/20260526_211746_trade_xyz_quote_collector_cli_plan.md` | consumed plan を archive move |
| `docs/DOCS_LINT_POLICY_2026-05-30.md` | current docs だけを strict lint する方針を追加 |
| `scripts/check_current_docs.py` | current docs の link / EOF / legacy root path check を追加し、`docs/algo` 直下の現行 strategy prep docs、live-readiness plan、XNYS calendar、plan index を対象化 |
| `docs/algo/SOURCE_NOTES_INDEX.md` | strict check 対応のため、括弧入り local link を URL encoding で安全化 |
| `docs/algo/EXPERIMENT_SCORECARD.md`, `docs/algo/STRATEGY_PREP_WORKFLOW.md` | strict check 対応のため、EOF 余分空行を修正 |
| `docs/DOCUMENT_AUDIT_2026-05-30.md` | 本監査を新規作成 |

## 更新できる docs

| Path | 理由 | 推奨更新 |
|---|---|---|
| `README.md` | 最短入口。現行 flow と検証値を掲載 | 2026-05-30 code/docs check へ更新済み |
| `docs/CURRENT_STATE.md` | restart 正本として有効 | code/docs verification と runtime artifact snapshot を分離済み |
| `docs/CODE_STATUS.md` | code surface と tests の実装状態を説明 | 2026-05-30 code/docs check へ更新済み。`StrategyExperimentSpec` 汎用 runner は詳細 Strategy Lab docs 側で制約として明記済み |
| `docs/OPERATIONS_RUNBOOK.md` | operator 手順は current CLI と一致 | `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md` への誘導を強める |
| `docs/ARCHITECTURE_AND_PHASES.md` | subsystem 境界は有効 | legacy paper bridge と Strategy Lab 正本の分離をさらに明文化可能 |
| `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md` | Strategy Lab 入口として有効 | Docs Audit section を「実施済み」に更新するとよい |
| `docs/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md` | live readiness blocker 分解の作業計画として有効 | current code/artifact で再検証してから使う。P2 read-only gate と live readiness を混同しない |
| `docs/XNYS_MARKET_CALENDAR.md` | real_market / tracking / micro_live の session 前提として有効 | `src/sis/market_calendar.py` と `configs/instrument_registry.seed.json` の symbol 対応と合わせて読む |
| `plan/README.md` | plan 全体の historical index として有効 | PR-00〜PR-08 は実装済みであり、current status は docs 側を先に読むことを維持 |
| `docs/trade_xyz_bot_beginner_guide.html` | 初心者向けとして有効 | Strategy Lab → paper intent preview の説明を追加できる |
| `docs/algo/EXPERIMENT_SCORECARD.md` | 戦略候補の比較テンプレートとして有効 | `TrialRecord`, `PromotionDecision`, `PaperIntentPreview` への対応欄を足すとさらに使いやすい |
| `docs/algo/strategy_factory/SIGNAL_CANDIDATE_TEMPLATE.md` | signal candidate intake として有効 | `Decision Log` を人間レビュー記録として明記し、Strategy Lab artifact と誤読しない注記を足せる |

## 古い内容がある docs

| Path | 古い内容 | 現在の扱い |
|---|---|---|
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-26.md` | PR12 前 snapshot | archived historical audit |
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-27.md` | 2026-05-27 values | archived historical audit |
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-28.md` | Strategy Lab 詳細 docs 追加前の audit | archived historical snapshot。current audit は本ファイル |
| `docs/archive/2026-05-30-doc-audit/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | P2 gate restore 前、fee unknown、pre-current facts | archived historical Trade[XYZ] audit |
| `docs/archive/2026-05-30-doc-audit/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md` | P2 実装前の failure state | archived historical design reference |
| `docs/archive/2026-05-30-doc-audit/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` | 実装済み計画と pre-snapshot | archived implemented-plan / historical |
| `plan/archive/20260526_211746_trade_xyz_quote_collector_cli_plan.md` | PR9a-PR12 消化済み計画と future候補が混在 | archived historical consumed plan |
| `plan/archive/PR-00_to_PR-08_implementation_plan.md` | PR-00〜PR-08 実装前/実装中の acceptance と micro live canary 計画 | archived historical migration contract。current code status は `docs/CODE_STATUS.md` を先に読む |
| `plan/archive/PR-00_python_313_migration_plan.md` | Python 3.13 migration の事前計画 | archived historical plan。Python 3.13 migration は現行 `scripts/check` と lockfile を正とする |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | full check `294 passed` と PR12 runtime snapshot | focused historical Trade[XYZ] audit。current code/docs verification は `378 passed` / current-docs lint を使う |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | full check `294 passed` を含む 2026-05-28 snapshot | failure-mode design reference として有効。current verification 値として引用しない |
| `docs/algo/obsidian_note_rewrites_2026-05-28/` | 薄い初版 rewrite bundle | old rewrite snapshot |

## 作り直したほうがいい docs

| Path | 推奨 | 理由 |
|---|---|---|
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-28.md` | 作り直し済み: `docs/DOCUMENT_AUDIT_2026-05-30.md` | 2026-05-30 の Strategy Lab docs と appendix 更新を含まない |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/04_ARTIFACT_EXAMPLES.md` | 作り直し済み | 旧 Signal CSV / Decision Log 中心だった |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/05_WORKED_EXAMPLE_TREND_PULLBACK.md` | 作り直し済み | 旧 paper review / signal CSV 前提だった |
| `docs/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/09_CHECKLISTS_AND_TEMPLATES.md` | 作り直し済み | Strategy Lab schema checklist になっていなかった |
| `docs/trade_xyz_bot_beginner_guide.html` | 部分再作成候補 | Strategy Lab / PaperIntentPreview の初心者向け説明が薄い |
| `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md` | 作り直すなら current Trade[XYZ] status audit と historical PR12 audit を分離 | 2026-05-28 runtime evidence と 2026-05-30 code/docs verification が混ざると current truth と誤読されやすい |
| `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md` | 作り直すなら `P2_BLOCKER` と `LIVE_READINESS_BLOCKER` の現行分類だけを短く再掲 | historical failure-mode evidence と current blocker handling を分けると operator が読みやすい |

## 削除・アーカイブしてよい docs

物理削除ではなく、archive move を推奨します。

| Path | 推奨 | 理由 |
|---|---|---|
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-26.md` | archived | current audit ではない |
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-27.md` | archived | current audit ではない |
| `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-28.md` | archived | 本ファイルに superseded |
| `docs/archive/2026-05-30-doc-audit/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md` | archived | 2026-05-28 audit に superseded |
| `docs/archive/2026-05-30-doc-audit/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md` | archived | 2026-05-28 map に superseded |
| `docs/archive/2026-05-30-doc-audit/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` | archived | implemented-planであり、次の実装計画ではない |
| `plan/archive/20260526_211746_trade_xyz_quote_collector_cli_plan.md` | archived | consumed plan |
| `plan/archive/PR-00_to_PR-08_implementation_plan.md` | archived | PR-00〜PR-08 は実装済み。historical migration contract として維持 |
| `plan/archive/PR-00_python_313_migration_plan.md` | archived | Python 3.13 migration は実装済み |
| `docs/algo/obsidian_note_rewrites_2026-05-28/` | archive | 2026-05-29 rewrite bundle に superseded |

削除しない:

- `plan/marketlens_strategy_research_lab_migration_pack/`
  - Strategy Lab の historical implementation contract として有用。
- `docs/archive/**`
  - current docs ではないが、過去判断の証跡。
- `docs/live_evidence_reports/README.md`
  - generated report 置き場の説明として有効。

## Current Read Rules

- code / tests / schemas を正本にする。
- `data/` artifact が無いだけで未実装と判断しない。必要なら CLI で再生成する。
- `READ_ONLY_GO` を live-ready と読まない。
- `bot-preview` を strategy engine と読まない。
- `PaperIntentPreview` を live order と読まない。
- `signals.csv` を Strategy Lab 正本にしない。
- historical plan から current command を拾わない。
- `Decision Log` という語があっても、それが人間レビュー記録なのか、旧 paper path の artifact 説明なのかを分ける。
- docs lint は `current docs` に限定する。source snapshot / archive の link や EOF は通常 lint の対象にしない。

## Docs Lint

Current docs の機械チェックは `docs/DOCS_LINT_POLICY_2026-05-30.md` と `scripts/check_current_docs.py` を正とする。

実行:

```bash
uv run python scripts/check_current_docs.py
```

検査対象は current read-first docs、`docs/algo` 直下の現行 strategy prep docs、Strategy Lab specs、strategy factory、archive index、live evidence README、beginner guide、live-readiness plan、XNYS calendar、plan index に限定する。`docs/archive/**`, `docs/algo/obsidian_note_copies/**`, `docs/algo/obsidian_note_rewrites_2026-05-28/**`, unchecked 2026-05-29 rewrite snapshots, `plan/archive/**` は通常 lint 対象外。

## 追加照査メモ

広域検索:

```text
rg -n "Signal CSV|Decision Log JSONL|Decision Log|ExecutionPlan|DecisionContext|data/research/signals\\.csv|OrderIntent|strategy_signals\\.parquet|PaperIntentPreview|TradeCandidate" docs -g '*.md'
```

確認結果:

- `docs/strategy_research_lab/**`, `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`, `docs/OPERATIONS_RUNBOOK.md` の該当語は、現行 boundary または legacy warning として使われている。
- `docs/algo/EXPERIMENT_SCORECARD.md` と `docs/algo/strategy_factory/SIGNAL_CANDIDATE_TEMPLATE.md` の `Decision Log` は、Strategy Lab artifact ではなく人間レビュー記録テンプレート。
- `docs/algo/obsidian_note_rewrites_2026-05-28/**` の `Decision Log` は old rewrite snapshot。現行入口にはしない。
- `docs/archive/**` の `signals.csv`, `ExecutionPlan`, `DecisionContext` は historical evidence。current docs とは分けて読む。

## Archive Move Result

2026-05-30 に archive move 済み。

移動先:

```text
docs/archive/2026-05-30-doc-audit/
  DOCUMENT_AUDIT_2026-05-26.md
  DOCUMENT_AUDIT_2026-05-27.md
  DOCUMENT_AUDIT_2026-05-28.md
  TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md
  FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md
  NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md
```

`plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md` は `plan/archive/20260526_211746_trade_xyz_quote_collector_cli_plan.md` へ移動済み。
