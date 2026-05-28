# Algo Strategy Docs

このディレクトリは、`/home/tn/Docs/algo/obsidian-vault` から拾ったトレード/Bot関連ノートを、戦略設計に使える形へ再構成した現行版の正本です。

## 読む順番

1. [ALGO_STRATEGY_SYSTEM_GUIDE.md](ALGO_STRATEGY_SYSTEM_GUIDE.md)
   - 全体像、設計思想、優先する仮説、避けるべき誤りを掴む。
2. [STRATEGY_PARTS_CATALOG.md](STRATEGY_PARTS_CATALOG.md)
   - 汎用戦略を作るための部品を、入力、出力、失敗モード、検証指標まで分解して見る。
3. [STRATEGY_BLUEPRINTS.md](STRATEGY_BLUEPRINTS.md)
   - 部品を組み合わせた実験候補を見る。
4. [RESEARCH_VALIDATION_PLAYBOOK.md](RESEARCH_VALIDATION_PLAYBOOK.md)
   - バックテスト、walk-forward、Monte Carlo、リーク検査、捨て条件を確認する。
5. [SOURCE_NOTES_INDEX.md](SOURCE_NOTES_INDEX.md)
   - どのObsidianノートに由来するか、どのノートを除外したかを確認する。

## 正本と参照元

- 現行正本: このディレクトリ直下の `ALGO_*`, `STRATEGY_*`, `RESEARCH_*`, `SOURCE_*` docs。
- 一次参照: [obsidian_note_copies/](obsidian_note_copies/) にある実ノートコピー。
- 旧docs: [../archive/2026-05-28-algo-doc-refresh/](../archive/2026-05-28-algo-doc-refresh/) に退避済み。

旧 `OBSIDIAN_*` docs は調査ログとして残しますが、今後の戦略検討ではこの新docs群を正本にします。

## 重要な前提

- これは投資助言ではなく、研究、設計、検証のための作業資料です。
- YouTube、X、メモ由来の勝率や利益主張は検証済み事実として扱いません。
- APIキー、秘密鍵、2FA、recovery codeを含むノートはコピーしません。索引にも値は書きません。
- 実弾運用は範囲外です。まずは再現可能なデータ収集、paper signal、検証から始めます。

