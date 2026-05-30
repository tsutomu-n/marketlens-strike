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

## Strategy Lab Artifact Mapping

この scorecard は人間用の比較メモです。実装・検証 artifact に進める時は、次の対応を明示する。

| scorecard section | Strategy Lab artifact | required mapping |
| --- | --- | --- |
| Baseline | `TrialRecord.baseline_strategy_id`, `TrialRecord.baseline_delta_metrics` | fair baseline と candidate 差分を残す |
| Candidate Logic | `StrategyExperimentSpec`, `StrategySignalRecord`, `TradeCandidate` | entry/filter/size/exit/stop を signal と candidate 化の条件へ分解する |
| Validation | `EvaluationPlan`, `TrialRecord` | train/test/stress/minimum trade count を評価計画と trial record に残す |
| Metrics | `TrialRecord.metrics`, `TrialRecord.baseline_delta_metrics` | raw result と baseline 差分を分ける |
| Failure Modes / Rejection Rules | `TrialRecord.rejection_reasons`, `TradeCandidate.block_reasons`, `PaperCandidatePack.rejected_candidate_ids` | なぜ止めたかを次の candidate 生成で再利用できる形にする |
| Decision Log | `PromotionDecision` | `promote`, `hold`, `reject` と evidence/reason を人間判断 artifact として残す |
| Paper observation entry | `PaperIntentPreview` | paper runner に渡す仮意図だけを生成する。live order ではない |

guard:

- `TrialRecord.selected_for_next_stage=true` は paper/live ready の証明ではない。
- `PromotionDecision.decision=promote` は paper observation への許可であり、live trading への許可ではない。
- `PaperIntentPreview` は `requires_revalidation=true`, `paper_only=true`, `live_conversion_allowed=false` の paper-only preview として扱う。
- `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed` は Strategy Lab artifact 上で true にしない。

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
