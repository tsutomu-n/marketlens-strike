<!--
作成日: 2026-05-28_20:41 JST
更新日: 2026-06-23_22:39 JST
-->

# Algo Strategy Docs

このディレクトリは、`/home/tn/Docs/algo/obsidian-vault` から拾ったトレード/Bot関連ノートを、戦略設計に使える形へ再構成した現行版の正本です。

## 読む順番

1. [ALGO_STRATEGY_SYSTEM_GUIDE.md](ALGO_STRATEGY_SYSTEM_GUIDE.md)
   - 全体像、設計思想、優先する仮説、避けるべき誤りを掴む。
2. [STRATEGY_PARTS_CATALOG.md](STRATEGY_PARTS_CATALOG.md)
   - 汎用戦略を作るための部品を、入力、出力、失敗モード、検証指標まで分解して見る。
3. [STRATEGY_BLUEPRINTS.md](STRATEGY_BLUEPRINTS.md)
   - 部品を組み合わせた実験候補を見る。
4. [STRATEGY_PREP_WORKFLOW.md](STRATEGY_PREP_WORKFLOW.md)
   - 戦略実装前に、仮説、データ、baseline、捨て条件を揃える。
5. [EXPERIMENT_SCORECARD.md](EXPERIMENT_SCORECARD.md)
   - 候補戦略を同じ物差しで採点し、優先順位を決める。
6. [strategy_factory/](strategy_factory/)
   - 戦略候補を安全に量産するため、1戦略1枚の候補シート、reject taxonomy、backlog台帳、状態遷移gateで管理する。
   - 作戦パーツを候補選別へ使う運用ガイドの文章正本は [strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md](strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md)。見た目つきの別表示は [strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html](strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html)。
7. [../strategy_research_lab/](../strategy_research_lab/)
   - Strategy Lab の売買戦略 schema、artifact flow、paper-only preview、operator runbook を詳細に確認する。
8. [RESEARCH_VALIDATION_PLAYBOOK.md](RESEARCH_VALIDATION_PLAYBOOK.md)
   - バックテスト、walk-forward、Monte Carlo、リーク検査、捨て条件を確認する。
9. [SOURCE_NOTES_INDEX.md](SOURCE_NOTES_INDEX.md)
   - どのObsidianノートに由来するか、どのノートを除外したかを確認する。
10. Historical source rewrites
   - 原ノート24本の批判的リライトは historical research notes として [../archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/](../archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/) に移動済み。
   - 図表、部品カード、売買発生シグナル設計、artifact例、テンプレートは [../archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/](../archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/appendix_materials/) を見る。

## 正本と参照元

- 現行正本: このディレクトリ直下の `ALGO_*`, `STRATEGY_*`, `RESEARCH_*`, `SOURCE_*` docs と [strategy_factory/](strategy_factory/)。
- 実装済み Strategy Lab 正本: `src/sis/research/strategy_lab/` と [../strategy_research_lab/](../strategy_research_lab/)。
- Strategy Lab 現行能力: [../strategy_research_lab/08_CURRENT_CAPABILITIES.md](../strategy_research_lab/08_CURRENT_CAPABILITIES.md)。
- 一次参照: [../archive/2026-06-08-doc-routing/algo/obsidian_note_copies/](../archive/2026-06-08-doc-routing/algo/obsidian_note_copies/) にある実ノートコピー。
- 再構成参照: [../archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/](../archive/2026-06-23-doc-triage/algo/obsidian_note_rewrites_2026-05-29/) にある原ノートの批判的リライト。これは current implementation proof ではない。
- 旧再構成: [../archive/2026-06-08-doc-routing/algo/obsidian_note_rewrites_2026-05-28/](../archive/2026-06-08-doc-routing/algo/obsidian_note_rewrites_2026-05-28/) は薄い初版として残すが、通常は使わない。
- 旧docs: [../archive/2026-05-28-algo-doc-refresh/](../archive/2026-05-28-algo-doc-refresh/) に退避済み。

旧 `OBSIDIAN_*` docs は調査ログとして残しますが、今後の戦略検討ではこの新docs群を正本にします。

## 重要な前提

- これは投資助言ではなく、研究、設計、検証のための作業資料です。
- YouTube、X、メモ由来の勝率や利益主張は検証済み事実として扱いません。
- APIキー、秘密鍵、2FA、recovery codeを含むノートはコピーしません。索引にも値は書きません。
- 実弾運用は範囲外です。まずは再現可能なデータ収集、paper signal、検証から始めます。
