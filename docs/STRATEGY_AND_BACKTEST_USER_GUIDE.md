<!--
作成日: 2026-06-18_05:03 JST
更新日: 2026-06-18_05:03 JST
-->

# Strategy And Backtest User Guide

## 結論

この文書は、人間が「戦略を作る、少し編集する、backtest する、結果を読む、次に何を確認するか」を理解するための入口です。

この repo の backtest は、研究用の検証です。結果が良く見えても、それだけで paper 実行許可や live 取引許可にはなりません。

## 戦略とは何か

ここでの戦略とは、次のような売買ルールをファイルに書いたものです。

- どの銘柄を見るか。
- どんな条件で買うか、売るか、何もしないか。
- いつ手じまいするか。
- 損切り、利確、保有時間、取引コストをどう見るか。
- どれくらい悪い結果なら失敗扱いにするか。

この repo では、戦略は主に YAML で書きます。YAML は、人間が読める設定ファイルです。

最初に読む例:

- [strategy_research_lab/examples/trend_pullback_authoring_spec.yaml](strategy_research_lab/examples/trend_pullback_authoring_spec.yaml)
- [strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md](strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md)

## YAML のどこを変えると何が変わるか

| 変える場所 | 変わること | 注意 |
|---|---|---|
| 銘柄設定 | どの市場・銘柄で検証するか | 現行の正式 venue は限定されている |
| entry rule | どんな時に入るか | 条件を厳しくしすぎると取引数が減る |
| exit rule | どんな時に出るか | 損切り、利確、時間切れが結果を大きく変える |
| cost / slippage | 手数料や不利な約定をどれくらい見るか | 甘すぎると実運用に近づかない |
| pass thresholds | どの水準なら合格扱いにするか | 合格は研究上の合格であり、取引許可ではない |
| backtest horizon | どれくらい先まで持つ想定か | 短すぎるとノイズ、長すぎると別の前提が必要 |

## まず実行する手順

外部 API を使わず、local fixture で最短の backtest pack を作る手順です。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

この手順は wallet、signing、exchange write、live order を使いません。

## Backtest の出力を見る順番

### 1. まず summary を見る

```bash
uv run sis strategy-backtest-artifact-summary
```

ここで見ること:

- 必要な artifact が存在するか。
- pack validation が PASS / FAIL か。
- live order を許可していないか。
- benchmark、stress、no-lookahead、data availability がそろっているか。

### 2. 単体の結果を見る

主な artifact:

- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_backtest_report.md`

見る field:

- `trade_count`: 取引回数。少なすぎると判断しにくい。
- `total_return`: 検証期間の合計リターン。
- `max_drawdown`: 途中でどれくらい悪化したか。
- `backtest_passed`: YAML 内の合格条件を満たしたか。
- `executed_signal_summary`: 実際に評価された signal の要約。

### 3. 比較と弱点を見る

主な artifact:

- `data/research/backtest_compare/strategy_backtest_comparison.json`
- `data/research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json`
- `data/research/backtest_stress/strategy_backtest_stress.json`
- `data/research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json`

見る順番:

1. benchmark と比べて良いのか。
2. stress をかけても壊れにくいか。
3. walk-forward など複数手法で極端に弱くならないか。
4. no-lookahead 検査で未来情報を使っていないか。
5. data availability に大きな欠損がないか。

## 用語の読み方

| 用語 | 一般的な説明 | 良い読み方 | 危ない読み方 |
|---|---|---|---|
| return | どれくらい増減したか | 他の指標と一緒に見る | return だけで良い戦略と決める |
| drawdown | 途中でどれくらい負けたか | 損失の深さを見る | 小さいだけで安全と決める |
| trade_count | 何回検証できたか | 少ない時は結論を弱める | 1回の大勝ちを強い証拠にする |
| benchmark | 比較対象 | 何もしない場合や市場平均との差を見る | benchmark より少し良いだけで十分と決める |
| stress | 悪条件を足した検査 | 手数料や滑りに耐えるか見る | stress を通ったから実運用OKと読む |
| no-lookahead | 未来情報を使っていないかの検査 | future leakage の疑いを減らす | 完全に漏れなしと断定する |
| data availability | データが足りているか | gap や欠損を確認する | 欠損を無視して結果だけ見る |

## 結果タイプ

### 検証不足

例:

- `trade_count` が少なすぎる。
- 必要な artifact がない。
- data availability に大きな gap がある。
- no-lookahead の検査対象が小さすぎる。

次にやること:

- 対象期間や条件を見直す。
- 入力データを増やす。
- artifact を再生成する。

### 弱い

例:

- return はプラスだが drawdown が深い。
- stress をかけるとすぐ悪くなる。
- 特定の regime や時間帯だけでしか勝っていない。

次にやること:

- entry / exit rule を見直す。
- 損切り、利確、保有時間を見直す。
- position sizing や cost 前提を見直す。

### 要追加検証

例:

- 単発 backtest は良い。
- benchmark 比較や walk-forward では微妙。
- no-lookahead や data availability に不安が残る。

次にやること:

- `strategy-backtest-pack` を再実行する。
- stress、rolling stability、benchmark relative を読む。
- Strategy Review packet を作って人間が確認する。

### paper観察候補

例:

- backtest pack validation が通っている。
- benchmark、stress、no-lookahead、data availability に最低限の説明がある。
- Strategy Review で人間が文脈を確認している。
- paper observation status で次に必要な観察条件が分かっている。

重要:

`paper観察候補` は paper 実行許可ではありません。次の検証候補という意味です。

## Paper observation へ進む条件

まず次を満たす必要があります。

- backtest artifact がそろっている。
- pack validation が通っている。
- Strategy Review packet を人間が読める。
- `operator_review.yaml` が `live_allowed=false` と `paper_execution_allowed=false` を維持している。
- `strategy-paper-observation-status` が normal observation と smoke observation を分けている。
- `permits_live_order=false` と `live_conversion_allowed=false` を維持している。

paper observation へ進む場合も、すぐ live へ進むわけではありません。

## よくある誤読

| 表示 | 正しい意味 | 誤読してはいけない意味 |
|---|---|---|
| `PASS` | その検査に通った | 儲かる、paper実行してよい、live可能 |
| `READ_ONLY_GO` | read-only / paper gate の判断 | live trading ready |
| `PAPER_OBSERVATION_CANDIDATE` | 次の検証候補 | paper実行許可 |
| `backtest_passed=true` | YAML の閾値を満たした | alpha 証明 |
| `permits_live_order=false` | live order を許可しない | 状況次第で無視できる |

## HTML / グラフで見たい場合

現行 repo には、optional `quantstats` 経路で HTML report artifact を作る `strategy-backtest-report-extension` があります。

ただし、次のような統一 dashboard はまだ標準機能ではありません。

- 損益グラフ。
- 指定期間の取引一覧。
- entry / exit のチャート表示。
- benchmark と strategy の重ね合わせ。
- stress scenario の比較グラフ。

この機能を追加するなら、既存 backtest artifact を読むだけの HTML / JS renderer から始めるのが安全です。renderer は注文、wallet、signing、exchange write に接続しない形にします。

## もっと詳しく読む

- [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)
- [backtest/README.md](backtest/README.md)
- [backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md)
- [backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md](backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md)
- [strategy_research_lab/README.md](strategy_research_lab/README.md)
- [strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md](strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md)
- [strategy_review/README.md](strategy_review/README.md)
- [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
