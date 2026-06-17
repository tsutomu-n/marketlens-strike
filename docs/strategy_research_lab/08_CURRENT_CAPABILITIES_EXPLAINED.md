<!--
作成日: 2026-06-17_23:01 JST
更新日: 2026-06-17_23:01 JST
-->

# Strategy Research Lab で今できること Markdown 正本

この文書は [08_CURRENT_CAPABILITIES_EXPLAINED.html](08_CURRENT_CAPABILITIES_EXPLAINED.html) の文章正本です。

HTML は見た目つきの別表示です。内容を更新する時は、この Markdown を先に直し、HTML はこの文書と矛盾しないように更新します。実装コード、生成済み artifact、paper / live の許可はこの文書では変わりません。

短い入口は [08_CURRENT_CAPABILITIES.md](08_CURRENT_CAPABILITIES.md)、コマンド別の詳細は [08_CURRENT_CAPABILITIES_DETAILS.md](08_CURRENT_CAPABILITIES_DETAILS.md)、作れる戦略タイプの棚卸しは [13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md](13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md) を読んでください。

## 結論

Strategy Research Lab は、売買アイデアをいきなり注文に変える場所ではありません。

今できることは、作戦案を signal にし、試行記録に残し、paper-only の候補と仮注文案まで進めることです。paper-only とは「本物のお金を使わない紙上運用」という意味です。

まだできないことは、実資金注文、wallet signing、exchange write、live-ready 判定、収益性の証明です。

安全な読み方:

- できる: 研究用の signal、trial、candidate、promotion decision、paper-only preview を作る。
- できる: YAML で宣言型の売買ルールを書き、fixed-horizon backtest と paper-only preview まで進める。
- できない: Strategy Lab artifact だけで本番取引できると判断する。

## 一目で見る現在地

難しい言葉を抜くと、「売買アイデアを候補リストにして、紙上の仮注文案まで作れる」状態です。

ただし、勝てるかどうかの証明や実注文は別工程です。候補が出たことは、利益が出る証明でも、paper 実行許可でも、live 実行許可でもありません。

## 処理の流れ

1. 作戦を選ぶ: 登録済み generator または YAML/JSON の実験仕様を選ぶ。
2. signal を作る: 売買方向らしさ、強さ、理由を持つ行データを作る。
3. trial に記録する: 候補条件ごとの評価記録を残す。
4. candidate 化する: paper に進める候補を束ねる。
5. 人が判断する: hold / reject / promote を記録する。
6. 仮注文案を作る: paper-only preview を作る。
7. 再検証する: 最新 quote で paper runner が確認する。

途中で止まった場合も、どこまで進んだか、なぜ止まったかを artifact から確認できます。

## 具体的にできること

### 登録済みの作戦から売買シグナルを作る

あらかじめ登録された作戦を選び、売買方向、強さ、理由を持つデータを作れます。

```bash
uv run sis strategy-preview
uv run sis strategy-preview --generator-id sp500_trend_rates_vix
```

主な出力:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/reports/strategy_signals_preview.md`

### StrategyExperimentSpec から作戦を実行する

YAML/JSON の実験仕様を読み、登録済み generator を spec の lineage で実行できます。

```bash
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
```

`parameter_grid` は組み合わせ展開され、variant ごとに `parameter_hash` が付きます。未登録 generator や上限超過は fail closed で止まり、live order は出しません。

ここで fail closed とは、「危ないか不明なら安全側へ倒して止める」という意味です。

### 候補条件を変えて比較記録を作る

スコアがどの水準以上なら候補にするかを変えて、複数の試行記録を残せます。

```bash
uv run sis evaluate-strategy-lab --rank-thresholds 0.2,0.8
```

主な出力:

- `data/research/trial_ledger.jsonl`
- `data/reports/strategy_trial_report.md`

これは比較記録であり、収益性の証明ではありません。

### 複数のシグナルを paper 候補にする

最新の 1 件だけでなく、条件を通ったシグナルを複数まとめて候補化できます。

```bash
uv run sis evaluate-strategy-lab --candidate-limit 0
uv run sis build-paper-candidate-pack
```

主な出力:

- `data/research/paper_candidate_pack.json`
- `data/reports/paper_candidate_pack.md`

### 時期ごとのシグナル数を記録する

日別・週別・月別などで、どのくらいシグナルが出たかを記録できます。

```bash
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit trading_day
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit week
uv run sis evaluate-strategy-lab --split-method walk_forward --era-unit month
```

これは era 別 signal count metrics です。PnL 計算や live-ready 証明ではありません。

### paper-only の仮注文案まで進める

人間の判断ファイルを経由して、paper runner に渡す仮注文案を作れます。

```bash
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

守る境界:

- `paper_only=true`
- `live_conversion_allowed=false`
- wallet / signing / exchange write は使わない。

### YAML で戦略を書いて backtest する

`strategy_authoring_spec.v1` YAML で entry、hold、close、reduce、add、rebalance、long、short、損切、利確、部分利確、trailing stop、position sizing、portfolio exposure、execution quality gate、event window、derived features などを書けます。

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
```

外部 API なしで baseline を通す場合:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

主な出力:

- `data/research/strategy_authoring_run.json`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/research/strategy_authoring_bundle_result.json`
- `data/reports/strategy_authoring_explain.md`
- `data/reports/strategy_backtest_report.md`
- `data/reports/strategy_authoring_bundle_report.md`

これも paper-only の研究用 artifact です。live order、wallet、exchange write は許可しません。

## 専門用語の言い換え

| 用語 | 一般的な言い換え | この repo での意味 |
|---|---|---|
| generator | シグナルを作る作戦部品 | 登録済みの戦略ロジック。例: `qqq_trend_rates_vix`。 |
| signal | 売買の気配、候補の元 | 方向、強さ、理由を持つ行データ。まだ注文ではない。 |
| artifact | 処理結果として残るファイル | `strategy_signals.parquet` や `trial_ledger.jsonl` など。 |
| TrialRecord | 試した条件の記録 | どの signal artifact を、どの条件で候補化したかを残す履歴。 |
| rank threshold | 候補にする最低点 | `rank_score` がこの値以上の signal を候補として扱う。 |
| candidate | paper に進める売買候補 | 注文ではない。paper intent preview の材料。 |
| paper-only | 実資金を使わない紙上運用 | wallet、署名、exchange write を使わない観測モード。 |
| PromotionDecision | 人間の判断メモ | candidate pack を hold / reject / promote する判断 artifact。 |
| authoring YAML | ユーザーが書く作戦ファイル | `strategy_authoring_spec.v1`。条件、損切、利確、sizing などを書く。 |
| authoring bundle | 複数作戦の比較束 | `strategy_authoring_bundle.v1`。複数 YAML を allocation weight 付きで paper 比較する。 |
| hold signal | 今は入らない記録 | `side=none` の研究 artifact。注文にも backtest trade にもしない。 |
| PaperIntentPreview | paper runner に渡す仮注文案 | paper-only の意図。live order へ変換してはいけない。 |
| walk-forward | 時期を分けて検証する考え方 | Strategy Lab 評価では era count metrics、authoring backtest では era 別 aggregate metrics を記録する。 |

## できないこと

できないことを明確にします。

- 任意 Python plugin や任意式 eval を実行する。
- 外部モデル学習や live optimizer をこの CLI で直接走らせる。
- Strategy Lab artifact だけで profitability / paper-ready / live-ready を判断する。
- 実資金注文、wallet signing、exchange write を行う。
- NDX / QQQ research gate の通過を Trade[XYZ] や Bitget production live の許可として読む。

このページの安全な読み方:

「戦略の候補を作って観測に進める準備はできた」。

危険な読み方:

「このまま実注文できる」「利益が出ると証明された」。

## 関連資料

- [08_CURRENT_CAPABILITIES.md](08_CURRENT_CAPABILITIES.md): 短い current capabilities 入口。
- [08_CURRENT_CAPABILITIES_DETAILS.md](08_CURRENT_CAPABILITIES_DETAILS.md): コマンド別の詳細、artifact、実行例。
- [08_CURRENT_CAPABILITIES_EXPLAINED.html](08_CURRENT_CAPABILITIES_EXPLAINED.html): この文書の見た目つき HTML 版。
- [13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md](13_STRATEGY_ARCHETYPE_COVERAGE_MATRIX.md): 作れる戦略タイプと証拠 test。
- [09_STRATEGY_AUTHOR_GUIDE.md](09_STRATEGY_AUTHOR_GUIDE.md): YAML で作戦を書く実務 guide。
- [05_OPERATOR_RUNBOOK.md](05_OPERATOR_RUNBOOK.md): operator 向けの実行手順。
