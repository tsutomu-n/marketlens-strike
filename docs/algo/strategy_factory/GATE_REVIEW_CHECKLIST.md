# Gate Review Checklist

候補を次の状態へ進める前のレビュー表です。`FACTORY_WORKFLOW.md` のgateを、実際に判定できる粒度へ分解します。

## idea -> specified

進めてよい条件:

- one sentence hypothesisがある。
- archetypeが1つに決まっている。
- triggerが条件式または明確な文章で書ける。
- invalidationがある。
- baselineがある。
- signalとorderが混ざっていない。

止める条件:

- `SPEC_NO_INVALIDATION`
- `SPEC_NO_BASELINE`
- `SPEC_TRIGGER_AMBIGUOUS`
- `SPEC_SIGNAL_ORDER_MIXED`

## specified -> data-ready

進めてよい条件:

- required inputsが列名またはデータ項目で書けている。
- historical dataまたは安全なpaper collectionで取れる。
- `observed_at` または利用可能時刻を記録できる。
- 欠損率、遅延、timezoneの扱いが決まっている。

止める条件:

- `DATA_NOT_AVAILABLE`
- `DATA_LIVE_ONLY`
- `DATA_OBSERVED_AT_MISSING`
- `DATA_MISSINGNESS_HIGH`

## data-ready -> backtest-ready

進めてよい条件:

- feature time <= decision timeを検査できる。
- cost/slippage前提がある。
- no-trade conditionsがある。
- reject rulesが先に書かれている。
- baselineの実装または計算方法が決まっている。

止める条件:

- `BACKTEST_LEAKAGE_RISK`
- `SPEC_NO_BASELINE`
- `RISK_NO_STOP_CONDITION`

## backtest-ready -> backtested

進めてよい条件:

- baseline comparisonがある。
- cost/slippage込みで結果を見る。
- trade countが十分。
- average adverse excursionを見る。
- parameter neighborhoodを見る。
- skipしたsignalを記録する。

止める条件:

- `BACKTEST_COST_FRAGILE`
- `BACKTEST_TRADE_COUNT_LOW`
- `BACKTEST_PARAMETER_POINT_ONLY`
- `BACKTEST_WALK_FORWARD_FAIL`

## backtested -> paper-observing

進めてよい条件:

- backtest結果がin-sampleだけではない。
- paperで観測する価格参照が決まっている。
- expected fillとobserved fillの差を記録できる。
- risk guardとmanual stopが文書化済み。
- live executionなしで観測できる。

止める条件:

- `PAPER_PRICE_REF_UNCLEAR`
- `RISK_LIVE_REQUIRED_TOO_EARLY`
- `RISK_EXPOSURE_UNBOUNDED`

## paper-observing -> continue

進めてよい条件:

- paper/backtest gapが説明できる。
- fill gap、skip理由、stale dataが記録されている。
- risk guardが想定通り働く。
- next implementation sliceが小さい。

止める条件:

- `PAPER_FILL_GAP_UNEXPLAINED`
- `PAPER_SKIP_NOT_LOGGED`
- `PAPER_TOO_SHORT`

## Batch Review Output

```md
# Gate Review: <batch-id>

- reviewed_at:
- candidates_reviewed:
- promoted:
- rejected:
- archived_duplicates:
- top_reject_codes:
- next_batch_limit:
```
