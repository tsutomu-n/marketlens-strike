<!--
作成日: 2026-05-30_14:13 JST
更新日: 2026-06-17_23:01 JST
-->

# Current Capabilities

この文書は、Strategy Research Lab で現在できることを短く読むための入口です。細かいコマンド別の説明、artifact、検証コマンドは [08_CURRENT_CAPABILITIES_DETAILS.md](08_CURRENT_CAPABILITIES_DETAILS.md) を読んでください。

正本はコードです。特に `src/sis/commands/research.py`, `src/sis/research/strategy_lab/`, `src/sis/research_protocol/`, `src/sis/paper/runner.py`, `tests/test_strategy_lab_commands.py` を優先します。

より具体的な説明と専門用語の言い換えは [08_CURRENT_CAPABILITIES_EXPLAINED.md](08_CURRENT_CAPABILITIES_EXPLAINED.md) で読めます。見た目つき HTML 版は [08_CURRENT_CAPABILITIES_EXPLAINED.html](08_CURRENT_CAPABILITIES_EXPLAINED.html) です。Strategy authoring の対応戦略一覧は [13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md](13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md) を読んでください。

## 結論

Strategy Research Lab は、戦略アイデアをそのまま注文に変える機能ではありません。戦略仮説を signal、trial、candidate、promotion decision、paper-only preview へ段階的に変換し、各段階で検証・停止できるようにする研究用の流れです。

今できること:

- 登録済み generator または `StrategyExperimentSpec` YAML/JSON から signal artifact を作る。
- `strategy_authoring_spec.v1` YAML で宣言型の売買ルールを書き、signal、fixed-horizon backtest、paper-only preview まで進める。
- trial ledger、paper candidate pack、promotion decision、paper intent preview を作り、後続の paper runner で再検証する。
- authoring spec では、long / short / hold、explicit close / reduce / add / rebalance、multi-leg、portfolio / execution / temporal / event-window / risk throttle などを paper-only に評価する。

今できないこと:

- live order、wallet signing、exchange write。
- Strategy Lab artifact だけを根拠にした profitability / paper-ready / live-ready claim。
- broker 固有 queue priority や full order book replay を含む本格 venue microstructure replay。
- 任意 Python、任意 plugin、外部 model artifact の安全でない実行。

重要な境界:

- `PaperIntentPreview` は注文ではなく、paper runner で再検証するための仮の意図です。
- `TradeCandidate` は paper order / live order ではありません。
- `READ_ONLY_GO` や backtest pass は live trading permission ではありません。
- NDX/QQQ family は research/backtest artifact として保持できますが、現行 paper path では venue suitability gate により selected candidate、paper intent、raw `paper-from-intents` JSON、legacy `paper-step` order generation で止まります。

## 最短の使い方

外部 API なしで authoring baseline を作る:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

generator から candidate pack まで作る:

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
```

paper-only preview まで進める:

```bash
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

## 詳しく読む場所

| 読みたいこと | 読む文書 |
|---|---|
| 専門用語を減らした説明 | [08_CURRENT_CAPABILITIES_EXPLAINED.md](08_CURRENT_CAPABILITIES_EXPLAINED.md) |
| コマンド別のできること、artifact、実行例 | [08_CURRENT_CAPABILITIES_DETAILS.md](08_CURRENT_CAPABILITIES_DETAILS.md) |
| YAML で作れる戦略タイプと証拠 test | [13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md](13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md) |
| 売買ロジックの書き方 | [09_STRATEGY_AUTHOR_GUIDE.md](09_STRATEGY_AUTHOR_GUIDE.md) |
| authoring の current summary | [11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md](11_STRATEGY_AUTHORING_CURRENT_SUMMARY.md) |
| operator 向けの実行手順 | [05_OPERATOR_RUNBOOK.md](05_OPERATOR_RUNBOOK.md) |
| schema と model の契約 | [01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md](01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md) |
| artifact chain と lineage | [02_ARTIFACT_FLOW_AND_LINEAGE.md](02_ARTIFACT_FLOW_AND_LINEAGE.md) |
| Strategy Lab 全体の入口 | [README.md](README.md) |

## 検証

current verification は固定の pass count ではなく、作業時点で次を再実行して確認します。

```bash
uv run pytest tests/test_strategy_lab_commands.py -q
uv run pytest tests/strategy_authoring -q
uv run python scripts/check_current_docs.py
./scripts/check
git diff --check
```
