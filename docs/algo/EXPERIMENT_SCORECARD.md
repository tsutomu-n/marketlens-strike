# Experiment Scorecard

戦略候補を同じ物差しで比較するためのテンプレートです。実装前、backtest後、paper観測後に更新します。

## Template

```md
# Experiment: <name>

## Status

- stage: idea | data-ready | backtest-ready | backtested | paper-observing | rejected
- owner:
- last updated:
- decision: pending | continue | reject | archive

## Hypothesis

<1文で書く。何を狙い、何と比べ、何が改善する想定か。>

## Market And Universe

- market:
- symbols/tokens:
- timeframe:
- session/active hours:
- exclusion rules:

## Data

| field | source | history available | live available | known risk |
| --- | --- | --- | --- | --- |
| | | | | |

## Parts

- Universe Selector:
- Data Collector:
- Feature Factory:
- Regime Detector:
- Signal Generator:
- Participation Filter:
- Token Safety Filter:
- Position Sizer:
- Exit Module:
- Risk Guard:
- Evaluation Harness:
- Monitoring Layer:

## Baseline

- baseline name:
- baseline logic:
- why this baseline is fair:

## Candidate Logic

- entry:
- filter:
- size:
- exit:
- stop:
- no-trade conditions:

## Cost And Slippage

- fee:
- spread/slippage:
- latency assumption:
- failed fill assumption:
- DEX/MEV/rate-limit assumption:

## Validation

- train period:
- test period:
- walk-forward setting:
- stress periods:
- Monte Carlo setting:
- minimum trade count:

## Metrics

| metric | baseline | candidate | required improvement | result |
| --- | ---: | ---: | ---: | --- |
| net return | | | | |
| profit factor | | | | |
| max drawdown | | | | |
| CVaR/tail loss | | | | |
| trade count | | | | |
| turnover | | | | |
| slippage sensitivity | | | | |
| parameter stability | | | | |

## Failure Modes

- 

## Rejection Rules

- 

## Source Notes

- 

## Decision Log

- YYYY-MM-DD: 
```

## Scoring Rubric

各項目を `0-3` で採点する。

| item | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| data availability | 取れない | liveのみ | historyあり一部欠損 | history/live両方安定 |
| testability | 検証不能 | 手動検証のみ | backtest可能 | walk-forward可能 |
| safety | secret/外部副作用あり | 注意が必要 | paperなら安全 | 観測のみで安全 |
| simplicity | 説明不能 | 複雑 | 部品で説明可 | baseline差分が小さい |
| expected edge | 根拠なし | 宣伝/主観 | 構造的仮説あり | baseline比較が明確 |
| reuse | 単発 | 一部再利用 | 複数戦略に使える | 基盤部品になる |

優先順位:

- `15-18`: 優先して準備する。
- `11-14`: 条件付きで準備する。
- `7-10`: source-onlyまたは保留。
- `0-6`: 捨てる。

## Initial Candidate Scores

| candidate | data | test | safety | simplicity | edge | reuse | total | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Trend + OrderBook Confirmation | 2 | 3 | 3 | 2 | 2 | 3 | 15 | prepare |
| Regime + RiskGuard Trend System | 3 | 3 | 3 | 2 | 2 | 3 | 16 | prepare |
| Pump.fun Event Watcher | 2 | 2 | 3 | 2 | 2 | 2 | 13 | observe-first |
| Solana Token Safety Gate | 2 | 2 | 3 | 3 | 2 | 3 | 15 | prepare |
| Feature Factory + Walk-Forward Gate | 3 | 3 | 3 | 2 | 2 | 3 | 16 | prepare |
| Research Assistant For Strategy Review | 3 | 2 | 2 | 3 | 1 | 2 | 13 | support-only |

## Interpretation

- `prepare`: データ定義とbaseline設計へ進める。
- `observe-first`: 売買せず、イベント収集とラベル付けを先に行う。
- `support-only`: 売買判断には使わず、レビューや要約だけに使う。
- `reject`: 実装しない。
