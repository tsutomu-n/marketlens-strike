<!--
作成日: 2026-05-30_11:55 JST
更新日: 2026-06-18_01:50 JST
-->

# Docs Lint Policy 2026-05-30

この文書は、repo 内の Markdown / HTML を「どこまで機械チェックするか」を固定するための方針です。

## 結論

`current docs` だけを厳格チェック対象にします。

Obsidian 原本コピー、古い rewrite、archive は、壊れているから即修正する対象ではありません。これらは source snapshot / historical evidence として扱い、通常 lint から外します。

## Strict Check 対象

`scripts/check_current_docs.py` が検査する対象:

```text
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/IMPLEMENTED_SURFACES.md
docs/MIGRATION_HISTORY.md
docs/NEXT_DIRECTION_CURRENT.md
docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md
docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
docs/DOCUMENT_AUDIT_2026-06-17_CODE_TRUTH_CHECKLIST.md
docs/DOCS_LINT_POLICY_2026-05-30.md
docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md
docs/OPERATIONS_RUNBOOK.md
docs/LONG_RUNNING_SCRIPT_OPERATION_RUNBOOK_2026-06-05.md
docs/ARCHITECTURE_AND_PHASES.md
docs/XNYS_MARKET_CALENDAR.md
docs/algo/README.md
docs/algo/ALGO_STRATEGY_SYSTEM_GUIDE.md
docs/algo/STRATEGY_PARTS_CATALOG.md
docs/algo/STRATEGY_BLUEPRINTS.md
docs/algo/STRATEGY_PREP_WORKFLOW.md
docs/algo/EXPERIMENT_SCORECARD.md
docs/algo/RESEARCH_VALIDATION_PLAYBOOK.md
docs/algo/SOURCE_NOTES_INDEX.md
docs/algo/strategy_factory/**
docs/algo/obsidian_note_rewrites_2026-05-29/**
docs/backtest/**
docs/research/ndx/**
docs/strategy_lifecycle/**
docs/strategy_review/**
docs/strategy_research_lab/**
docs/runbooks/**
docs/live_evidence_reports/README.md
docs/archive/README.md
docs/trade_xyz_bot_beginner_guide.md
docs/trade_xyz_bot_beginner_guide.html
plan/README.md
```

## 通常 lint から外すもの

```text
docs/archive/**
docs/algo/obsidian_note_copies/**
docs/algo/obsidian_note_rewrites_2026-05-28/**
plan/archive/**
```

例外: `docs/archive/README.md` は archive index として current docs 側から読むため、strict check 対象です。

## 検査内容

`scripts/check_current_docs.py` は次を確認します。

- 対象ファイルが存在する。
- UTF-8 で読める。
- Markdown current docs は `作成日` / `更新日` metadata header を持つ。
- final newline がある。
- EOF に余分な空行がない。
- Markdown local link と HTML `href` local link が存在する。
- HTML current docs は同名の Markdown source を持つ。
- current docs が旧 root path へリンクしていない。
- `README.md`、`docs/CURRENT_STATE.md`、domain runbook、capability guide など現在状態を説明する入口文書では、古い判定語、固定の current-doc 件数、固定の full-check pass 件数、古い CLI 件数、tracked docs へ写した runtime hash 表現、古い operations / evidence runtime snapshot、古い paper-observation runtime snapshot、古い PR12 execution / readiness artifact snapshot が混入していない。
- 全 current docs では、archive 済みの Trade[XYZ] quote coverage 固有 PID / 起動時刻、または `READ_ONLY_GO` を固定の完了確認として読む PR12 generated artifact gate 文言を current 手順として再掲しない。必要な場合は archive record へリンクするか、runtime command の再実行へ誘導する。
- tracked plan file は `plan/README.md`、`plan/archive/**`、`plan/0609ここからの計画/03_venue_read_only_capability_probe/**` だけに限定する。

この最後の検査は、現在状態の説明だけを対象にする。監査記録、実装記録、completion evidence のような historical docs は、当時の件数や判定語を含んでもよい。古い値を消すのではなく、「今の確認は command を再実行する」と読める形に分ける。

## 旧 root path

次の path は current docs から直接リンクしません。必要な場合は archive path を使います。

```text
docs/DOCUMENT_AUDIT_2026-05-26.md
docs/DOCUMENT_AUDIT_2026-05-27.md
docs/DOCUMENT_AUDIT_2026-05-28.md
docs/DOCUMENT_AUDIT_2026-05-30.md
docs/DOCUMENT_AUDIT_2026-05-31.md
docs/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md
docs/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md
docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md
docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md
docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md
docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md
docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md
docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md
plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md
```

この文書と `docs/archive/README.md` では、移動履歴の説明として旧 root path の plain text を許可します。ただしリンク先は archive path にします。

## 実行

```bash
uv run python scripts/check_current_docs.py
```

通常の確認では `scripts/check` からも実行されます。

## 運用ルール

- current docs を増やす場合は、`scripts/check_current_docs.py` の allowlist に追加する。
- source snapshot / archive を整形するだけの変更は、current docs 修正と同じ差分に混ぜない。
- root `plan/` 側へ tracked plan を増やす場合は、current unimplemented plan か archive かを決め、必要なら `PLAN_ROUTING_ALLOWED_PREFIXES` を同時に更新する。
- 広域 docs lint を作る場合も、まず current docs lint とは別コマンドにする。
- `docs/algo/README.md` が正本として案内する docs は、原則 strict check 対象に入れる。
