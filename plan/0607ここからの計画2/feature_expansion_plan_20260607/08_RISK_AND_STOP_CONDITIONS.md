<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 08 Risk And Stop Conditions

## 主要リスク

### R1. YAML管理ツールだけになる

悪い状態:

```text
NDX専用の設定ファイル置き場が増えただけで、2.2の安全柵になっていない。
```

対策:

```text
- linter rule v2を必須にする。
- counter-DAG不足をfailにする。
- variable_inventory / causal_roles / temporal_availability とのcross validationを必須にする。
```

### R2. Strategy Labと重複する

悪い状態:

```text
2.2がsignal生成やtrial評価まで持ち始める。
```

対策:

```text
- 今回は strategy_signals.parquet を生成しない。
- StrategyExperimentSpec への接続も行わない。
- 2.2は前段artifactで止める。
```

### R3. Open Gap Residual計算へ早く進みすぎる

悪い状態:

```text
DAGが固まる前にfeature panel / rolling regression / backtestへ進む。
```

対策:

```text
- Phase Cとしてdeferredに明記する。
- generated artifactはDAG/reportだけにする。
```

### R4. NDX / QQQ / NQを混同する

悪い状態:

```text
NQ overnight moveをQQQ open gapと同じnodeにする。
NDX指数概念とQQQ ETF価格を同じsourceとして扱う。
```

対策:

```text
- scope.yaml と data_sources.yaml で責務を分離する。
- Core DAG nodeは concept、proxyは QQQ/NQ/NDX として分ける。
```

### R5. Temporal leakage

悪い状態:

```text
QQQ close / same-day close / post-open finalized data を open signal に使う。
```

対策:

```text
- temporal_availability.yaml を必須にする。
- t_after_close -> t_open_plus_buffer をfail。
- qqq_open_to_close_return を outcome に固定。
```

### R6. External APIへ進む

悪い状態:

```text
yfinance / FRED / Alpaca / Bitget / Trade[XYZ] を呼ぶ。
```

対策:

```text
- Phase A/Bではfetch実装禁止。
- data_source_contractはprovider名を書くのみ。
- テストはfixtureだけ。
```

## Stop conditions

以下が発生したら実装を止め、ユーザーに確認する。

```text
1. external API call が必要になった。
2. credentials が必要になった。
3. pyproject.toml / uv.lock 変更が必要になった。
4. paper/live order path に触る必要が出た。
5. Strategy Lab export を先に実装しないと進めないと判断した。
6. DB schema / deploy / CI 変更が必要になった。
7. NDX/QQQ/NQ のどれを正本にするかで実装判断が分岐した。
8. VXN / SOX / NQ のデータ取得元を決めないとコードが書けない状態になった。
9. CLI追加により root CLI 構造の大幅変更が必要になった。
10. existing Strategy Lab model を変更しないと実装できないと判断した。
```

## 止まった時にユーザーへ聞く質問

```text
- Phase A/Bのまま外部APIなしで進めるか、Phase Cへ進める判断をするか？
- VXNは初期必須proxyにするか、VIX代替で始めるか？
- SOXは直接取得前提にするか、SMH ETF proxyで始めるか？
- NQ futuresはPhase C以降まで完全にdeferしてよいか？
- CLIは今回入れるか、Python API + testsだけで一度止めるか？
```

## 絶対にしないこと

```text
- live order readiness と言う。
- backtest-ready と言う。
- paper-ready と言う。
- profitability claim を立てる。
- `data/research/signals.csv` を正本にする。
- PaperIntentPreview を生成する。
- wallet / signing / exchange write を触る。
```
