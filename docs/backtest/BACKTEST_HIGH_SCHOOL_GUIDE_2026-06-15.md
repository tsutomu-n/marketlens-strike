<!--
作成日: 2026-06-15_19:13 JST
更新日: 2026-06-18_01:22 JST
-->

# 高校生向け: バックテストシステムで今できること

## まず結論

このバックテストシステムは、投資やトレードの作戦を「過去のデータで試す」ための道具です。

たとえば、ある作戦について次を確認できます。

- 過去データでは、売買のサインが出たか
- そのサインで売買したら、結果はどう見えたか
- 1つの試し方だけでなく、複数の試し方でも大きく崩れないか
- データに抜けやズレがないか
- 未来の情報をうっかり使っていないか
- 結果を paper observation、つまり本物のお金を使わない観察段階へ進めてよいか

ただし、これは「本当に儲かる」と証明する道具ではありません。  
また、本物の注文を出す道具でもありません。

## バックテストとは

バックテストは、作戦を過去のデータに当てはめて試すことです。

たとえば、次のようなイメージです。

```text
作戦:
  価格が上がり始めたら買う
  一定時間たったら売る

過去データ:
  2026年1月の価格データ

バックテスト:
  その作戦を2026年1月のデータに当てはめる
  どこで買い、どこで売ったことになるかを見る
  損益や弱点を確認する
```

この repo のバックテストは、まず研究用です。  
本物の取引所へ注文を送るものではありません。

## このシステムで今できること

### 1. 作戦ファイルをチェックできる

作戦は YAML という設定ファイルで書きます。

この作戦ファイルが壊れていないか、必要な項目があるかを確認できます。

```bash
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
```

### 2. 作戦を過去データで試せる

作戦から売買サインを作り、過去データで試せます。

```bash
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
```

主な出力は次です。

- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/reports/strategy_backtest_report.md`

ざっくり言うと、サイン、数字の結果、人間向けレポートができます。

### 3. いろいろな試し方で確認できる

1回だけ試すと、たまたま良く見えることがあります。

そこで、このシステムでは複数の方法で試せます。

- 1つの期間で普通に試す
- 日付ごとに分けて試す
- 未来のデータを混ぜにくい形で分けて試す
- 結果を少しずつ並べ替えて、ブレを調べる

標準では 5 種類の試し方をまとめて実行できます。

```bash
uv run sis strategy-backtest-suite --suite docs/strategy_research_lab/examples/backtest_suite.yaml
```

### 4. 市場全体や基準データと比べられる

作戦だけを見ると、良いのか悪いのか分かりにくいことがあります。

そこで、別の基準データと比べられます。

```bash
uv run sis strategy-backtest-benchmark-relative \
  --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
```

これは「作戦が基準より良かったか、悪かったか」を見るためのものです。

### 5. 悪い条件でも大丈夫かを調べられる

現実の取引では、手数料、すべり、タイミングのズレなどがあります。

このシステムでは、条件を悪くしたときに結果がどうなるかを見られます。

```bash
uv run sis strategy-backtest-stress
uv run sis strategy-backtest-regime-split
uv run sis strategy-backtest-rolling-stability
```

これは「強さを証明する」というより、「弱点を探す」ための確認です。

### 6. データの抜けを確認できる

バックテストは、使ったデータが悪いと結果も信用できません。

このシステムでは、データの行数、期間、抜け、重複などを確認できます。

```bash
uv run sis strategy-backtest-data-availability
```

今の代表的な状態では、local data の確認は `pass` です。  
ただし、Bitget、Hyperliquid、Coinalyze のような将来候補データは、まだ実装対象外です。

### 7. 未来の情報を使っていないか確認できる

バックテストで一番危ない失敗の1つは、未来の情報をうっかり使うことです。

たとえば、今日の判断に明日の価格を使ってしまうと、結果はよく見えますが、現実には使えません。

このシステムでは、その危険を調べるための確認があります。

```bash
uv run sis strategy-backtest-no-lookahead-diff
```

### 8. 本物の注文ではなく、注文っぽい流れをシミュレーションできる

作戦が出したサインをもとに、paper-only の注文意図や fill event を作れます。

```bash
uv run sis strategy-backtest-execution-sim
```

これは本物の注文ではありません。  
取引所へ何かを書き込むこともありません。

## いちばん使いやすいまとめコマンド

細かい確認を1つずつ実行する代わりに、まとめて実行できます。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

この4つを実行すると、標準的なバックテストの材料と結果をまとめて作り、チェックし、要約できます。

## 今の代表的な状態

2026-06-15_19:13 JST 時点では、代表的な状態は次の通りです。

| 項目 | 状態 | かんたんな意味 |
|---|---|---|
| pack | 存在する | まとめ結果が作られている |
| pack validation | `PASS` | まとめ結果のチェックに通っている |
| validation failed count | `0` | チェック失敗がない |
| suite methods | `5` | 5種類の試し方を使っている |
| paper only | `true` | 研究・紙上取引用である |
| permits live order | `false` | 本物の注文は許可していない |
| wallet used | `false` | wallet は使っていない |
| exchange write used | `false` | 取引所への書き込みはしていない |
| backtest acceptance | `PASS_BACKTEST_ACCEPTANCE` | バックテスト段階は通過 |
| lifecycle decision | `CONTINUE_PAPER_OBSERVATION` | 次は paper observation を続ける |

## PASS と出たら何が分かるか

`PASS` と出ても、「この作戦は絶対に儲かる」という意味ではありません。

分かるのは、たとえば次のようなことです。

- 入力データや出力ファイルの形が合っている
- 必要な結果ファイルがある
- live order を出していない
- wallet を使っていない
- exchange write をしていない
- 標準のチェックに通っている

つまり、`PASS` は「次の確認へ進める」という意味です。  
「お金を入れて本番運用してよい」という意味ではありません。

## Paper observation とは

Paper observation は、本物のお金を使わずに、作戦の動きを観察する段階です。

バックテストは過去データでの確認です。  
Paper observation は、もっと運用に近い形で、しかし本物の注文は出さずに見る段階です。

今の状態は次のように読めます。

```text
バックテストは通った
-> paper observation に進む材料はある
-> でも paper observation の観察数がまだ足りない
-> だから CONTINUE_PAPER_OBSERVATION
```

つまり、今やるべきことは live trading ではありません。  
paper observation を続けることです。

## このシステムがしないこと

このバックテストシステムは、次のことをしません。

- 本物の注文を出す
- wallet を使う
- 署名をする
- 取引所へ書き込む
- 「絶対に儲かる」と判断する
- backtest だけで live readiness を出す
- market impact を証明する
- Bitget / Hyperliquid の direct schema を広げる
- Coinalyze collector を作る

この境界は重要です。  
バックテストは、あくまで研究と確認のための道具です。

## ファイルの見方

よく見るファイルは次です。

| ファイル | 何を見るか |
|---|---|
| `data/research/strategy_backtest_metrics.json` | 作戦を過去データで試した結果 |
| `data/research/backtest_pack/strategy_backtest_pack.json` | まとめ結果 |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | まとめ結果のチェック結果 |
| `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | バックテスト段階を通したか |
| `data/research/strategy_lifecycle/strategy_lifecycle_review.json` | 次に何をするべきか |

数字をざっと見たいだけなら、次を使います。

```bash
uv run sis strategy-backtest-artifact-summary
```

## どう読めばいいか

覚えるポイントは3つです。

1. バックテストは、過去データで作戦を試す道具。
2. `PASS` は、本番運用OKではなく、次の確認へ進めるという意味。
3. 今の次ステップは、live trading ではなく paper observation 継続。

## 次に読むもの

もう少し詳しく知りたい場合は、次を読みます。

1. `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md`
2. `docs/backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md`
3. `docs/strategy_lifecycle/README.md`
4. `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md`

## まとめ

このバックテストシステムは、作戦を過去データで試し、結果をまとめ、弱点を見つけ、paper observation へ進めるかを判断するための道具です。

今は、バックテスト側の確認は通っています。  
ただし、次は本番ではありません。  
次は paper observation を続ける段階です。
