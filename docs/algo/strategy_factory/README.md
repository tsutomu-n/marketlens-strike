<!--
作成日: 2026-05-29_22:07 JST
更新日: 2026-06-05_08:11 JST
-->

# Strategy Factory

戦略を安全に量産するための作業フォルダーです。目的は「戦略案を増やす」ことではなく、候補を同じ形式で受け付け、早く落とし、残すべきものだけを検証へ送ることです。

## 使う順番

1. `SIGNAL_CANDIDATE_TEMPLATE.md`
   - 1戦略1枚で候補を書く。
2. `ARCHETYPE_REQUIRED_INPUTS.md`
   - archetypeごとの必須入力列と最低検査を確認する。
3. `SIGNAL_REJECT_REASON_TAXONOMY.md`
   - 落とす理由を固定コードで記録する。
4. `STRATEGY_BACKLOG_TABLE.md`
   - 候補を台帳に載せ、状態と次のgateを管理する。
5. `GATE_REVIEW_CHECKLIST.md`
   - 次gateへ進める前の合格/停止条件を確認する。
6. `DUPLICATE_CONTROL.md`
   - 似た候補や亜種の増殖を止める。
7. `FACTORY_WORKFLOW.md`
   - 状態遷移とgateを確認する。
8. `EXAMPLE_FILLED_SIGNAL_CARDS.md`
   - 記入例を見る。
9. `FACTORY_QUALITY_AUDIT.md`
   - 抜け漏れ、誤謬リスク、残リスクを見る。
10. `../../strategy_research_lab/README.md`
   - 候補を実装済み Strategy Lab schema と artifact chain に落とす時の正本を見る。

読みやすい運用ガイドは [STRATEGY_FACTORY_OPERATOR_GUIDE.html](STRATEGY_FACTORY_OPERATOR_GUIDE.html) です。

## 状態の考え方

```text
idea
  -> specified
  -> data-ready
  -> backtest-ready
  -> backtested
  -> paper-observing
  -> continue | rejected | archived
```

各状態は、次のgateを満たさない限り進めません。
Strategy Lab への接続は状態名ではなく、`backtested -> paper-observing` へ進むための実装ルートとして扱います。

## Factory Rules

- 1候補は1枚のSignal Candidate Sheetで管理する。
- signalとorderを混ぜない。
- invalidationがない候補はbacktestへ進めない。
- baselineがない候補はbacktestへ進めない。
- reject理由は自由文だけでなく、taxonomy codeで残す。
- 似た候補はduplicate keyでまとめ、重複量産しない。
- 次gateへ進める時は `GATE_REVIEW_CHECKLIST.md` を使う。
- thresholdや期間だけが違う候補は新戦略にせずvariantとして扱う。
- Crypto/DeFi固有の候補は通常候補とは分け、特殊ケースとして扱う。

## Relation To Implemented Strategy Lab

Factory docs は候補設計の入口です。実装済み artifact chain へ進める時は、次の対応で落とし込みます。

| Factory concept | Implemented artifact |
|---|---|
| Signal Candidate Sheet | `StrategyExperimentSpec` |
| archetype / family | `strategy_family` |
| variant / parameter sweep | `strategy_version`, `parameter_grid`, `parameter_hash` |
| required inputs | `EvaluationPlan`, `DataSnapshotManifest`, `FeatureSnapshotManifest` |
| reject taxonomy | `rejection_reasons`, `block_reasons`, `reason_codes` |
| gate review | `PromotionDecision` |
| paper observing entry | `PaperIntentPreview` |

詳細な現行 schema と docs 監査は `../../STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`、実務仕様は `../../strategy_research_lab/README.md` 以下を読む。`PaperIntentPreview` は paper-only であり、live order や execution-side `OrderIntent` と混同しない。

## Relation To Existing Docs

- 設計思想: `../ALGO_STRATEGY_SYSTEM_GUIDE.md`
- 戦略部品: `../STRATEGY_PARTS_CATALOG.md`
- 検証手順: `../RESEARCH_VALIDATION_PLAYBOOK.md`
- 実装済み Strategy Lab 仕様: `../../STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
- Strategy Lab 詳細仕様: `../../strategy_research_lab/README.md`
- 原ノート再構成: `../obsidian_note_rewrites_2026-05-29/`
- signal設計付録: `../obsidian_note_rewrites_2026-05-29/appendix_materials/12_SIGNAL_DESIGN_PLAYBOOK.md`
