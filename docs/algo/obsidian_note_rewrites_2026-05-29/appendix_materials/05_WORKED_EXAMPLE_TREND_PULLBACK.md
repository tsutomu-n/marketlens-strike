<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Worked Example: Trend Pullback

Trend Pullback を Strategy Research Lab の現行 artifact chain に沿って、仮説から paper-only preview まで通す例です。

この例は投資助言ではありません。目的は、戦略部品を `StrategyExperimentSpec`, `StrategySignalRecord`, `TrialRecord`, `TradeCandidate`, `PaperCandidatePack`, `PromotionDecision`, `PaperIntentPreview` に落とす粒度を示すことです。

## 1. Hypothesis

```text
長期トレンドが上向きで、短期的に押したあと再上昇する場面だけを拾うと、
単純な常時押し目買いより entry 直後の逆行と drawdown が下がる。
```

baseline:

- `close > sma20` の単純 long signal

candidate:

- trend regime
- pullback trigger
- source confidence gate
- venue quality gate
- event / session block

invalidation:

- trend regime 以外で頻繁に発火する。
- cost / slippage stress 後に baseline delta が消える。
- source confidence または venue quality が低い時間帯でしか成績が出ない。
- paper observation で `LATEST_QUOTE_MISSING` や `PAPER_BROKER_REVALIDATION_BLOCKED` が多すぎる。

## 2. SymbolBinding

```text
execution_venue=trade_xyz
execution_symbol=XYZ100
real_market_symbol=QQQ
asset_class=basket_index
currency=USD
```

理由:

- feature / tracking 側は `QQQ` を実市場 proxy として見る。
- paper intent / venue quote 側は `XYZ100` を見る。
- `XYZ100 -> QQQ` は code 上の proxy rule で検証される。

## 3. Required Inputs

| field | purpose |
|---|---|
| `close` | 価格 |
| `sma_20` | 押し目判定 |
| `sma_50` | 中期 trend 判定 |
| `sma_50_slope` | trend 方向 |
| `realized_vol_20` | panic / high vol 回避 |
| `source_confidence` | real market source quality |
| `venue_quality_score` | execution venue quality |
| `trade_allowed` | tracking / venue gate |
| `market_status` | open / closed 判定 |
| `is_event_blackout` | イベント回避 |

最低停止条件:

- feature の時刻が signal 時刻より未来なら reject。
- `source_confidence` が最低値未満なら block。
- `venue_quality_score` が最低値未満なら block。
- market closed なら paper intent に進めない。

## 4. StrategyExperimentSpec

```text
strategy_id=trend_pullback_xyz100_v0
strategy_family=momentum
strategy_version=v0
generator_id=qqq_trend_rates_vix
evaluation_plan_id=initial_walkforward_v1
run_profile_id=strategy_lab
parameter_grid:
  trend_window: [20, 50]
  min_source_confidence: [0.70, 0.80]
  max_spread_bps: [8.0]
forbidden_claims:
  profitability_claimed
  paper_ready_claimed
  tiny_live_ready_claimed
  live_ready_claimed
```

現行制約:

- `strategy-experiment-run --spec` は `StrategyExperimentSpec` YAML/JSON を読み込める。`parameter_grid` は safe cartesian sweep として展開され、built-in generator は `min_source_confidence`, `max_vix_level` / `vix_gate`, `min_research_return_1d`, `timeframe` を signal 条件または出力 timeframe として消費できる。任意式 eval や任意 Python plugin は実行しない。
- 現行 default generator は `qqq_trend_rates_vix`。
- この spec は「どう作るべきか」の契約例で、live order 定義ではない。

## 5. Signal Rule

```text
precondition:
  source_confidence >= min_source_confidence
  venue_quality_score >= 0.80
  market_status == open
  is_event_blackout == false

regime:
  close > sma_50
  sma_50_slope > 0
  realized_vol_20 <= vol_p90

long trigger:
  close > sma_50
  abs((close - sma_20) / sma_20) <= 0.01
  short_momentum_turns_up == true
```

StrategySignalRecord の例:

```text
strategy_id=trend_pullback_xyz100_v0
execution_symbol=XYZ100
real_market_symbol=QQQ
side=long
rank_score=0.90
tail_bucket=top
confidence=0.78
source_confidence=0.92
venue_quality_score=0.88
reason_codes=TREND_UP,PULLBACK_TO_SMA20,QUALITY_OK
block_reasons=[]
```

注意:

- `side=long` は signal direction。order action ではない。
- `rank_score` は candidate selection 用。quantity へ直結しない。

## 6. EvaluationPlan

```text
split_method=purged_walk_forward
label_horizon_minutes=240
purge_minutes=240
embargo_minutes=60
era_unit=trading_day
require_tracking_gate=true
require_source_confidence=true
require_venue_quality=true
min_trade_count=30
cost_stress_multiplier=2.0
slippage_stress_multiplier=2.0
primary_metric=net_return_after_cost_stress
secondary_metrics=max_drawdown,trade_count,blocked_rate
```

採用前に見るもの:

- baseline delta
- cost stress 後の残存
- max drawdown
- trade count
- blocked reason distribution
- eraごとの偏り

## 7. TrialRecord

`evaluate-strategy-lab` 後に `data/research/trial_ledger.jsonl` に残す。

評価例:

```text
trial_id=trial-trend-pullback-001
parameter_hash=trend20_conf070
signal_count=48
candidate_count=12
paper_candidate_count=2
blocked_count=36
selected_for_next_stage=true
baseline_strategy_id=close_above_sma20_v0
baseline_delta_metrics:
  net_return_after_cost_stress=0.006
  max_drawdown=0.015
```

読み方:

- `selected_for_next_stage=true` は paper candidate に進める意味。
- `profitability_claimed=false` のまま。
- best trial だけでなく rejected trial も ledger に残す。

## 8. TradeCandidate

Candidate 化の例:

```text
candidate_id=candidate-trial-trend-pullback-001
signal_id=sig-trend-pullback-001
trial_id=trial-trend-pullback-001
execution_symbol=XYZ100
real_market_symbol=QQQ
side=long
status=candidate
rank_score=0.90
tail_bucket=top
confidence=0.78
entry_reason_codes=TRIAL_SELECTED,TOP_TAIL_BUCKET
block_reasons=[]
live_order_submitted=false
```

reject 例:

```text
status=blocked
side=none
block_reasons=LOW_SOURCE_CONFIDENCE,REGIME_NOT_TREND
```

## 9. PaperCandidatePack

pack の selection policy:

```text
selected_candidate_ids:
  candidate-trial-trend-pullback-001
rejected_candidate_ids:
  candidate-trial-trend-pullback-002
selection_policy:
  tail_bucket=top
  min_confidence=0.75
  requires_no_block_reasons=true
```

確認:

- selected / rejected IDs は candidates 内に存在する。
- top-level `blocked_candidate_ids` は使わない。
- `paper_ready_claimed=false`, `live_ready_claimed=false`。

## 10. PromotionDecision

まずは `hold` にする:

```bash
uv run sis promotion-decision --decision hold
```

paper observation へ進める場合:

```text
decision=promote
required_evidence=trial_ledger,paper_candidate_pack
observed_evidence=trial_ledger,paper_candidate_pack
approval_reasons=manual_review_passed
wallet_used=false
exchange_write_used=false
live_ready_claimed=false
```

注意:

- `promote` は paper observation への許可。
- live-ready ではない。
- evidence が揃わなければ validation で止まる。

## 11. PaperIntentPreview

生成 command:

```bash
uv run sis build-paper-intent-preview
```

preview の意味:

```text
action=enter
side=long
order_style=paper_taker
price_reference=mark
notional_usd=1000.0
quantity=1.0
requires_revalidation=true
paper_only=true
live_conversion_allowed=false
wallet_used=false
exchange_write_used=false
```

注意:

- `PaperIntentPreview` は live order ではない。
- `notional_usd` は現行 paper runner の sizing 正本ではない。
- `quantity` が無ければ現行 runner は `1.0` を使うため、size設計は別途必要。

## 12. paper-from-intents

実行:

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

再検証:

- intent expiry
- latest quote existence
- paper broker validation
- halt policy

block reason:

- `INTENT_EXPIRED`
- `LATEST_QUOTE_MISSING`
- `PAPER_BROKER_REVALIDATION_BLOCKED`

出力:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

## 13. Continue / Reject

continue:

- baseline delta が cost stress 後も残る。
- paper observation で expired / missing quote 以外の異常 block が少ない。
- `source_confidence` と `venue_quality_score` の依存が説明できる。
- parameter 近傍で壊れない。

reject:

- `range` で発火している。
- low source confidence の時間だけ成績がよい。
- venue quality が低い時間帯でしか成績が出ない。
- paper observation で `PAPER_BROKER_REVALIDATION_BLOCKED` が多すぎる。
- exit / holding horizon の仮定が曖昧。

## 14. 実行順

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

`hold` のままなら intent は空になり得ます。paper observation に進める時だけ、人間レビュー後に `promote` を使います。
