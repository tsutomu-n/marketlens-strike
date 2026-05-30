# Generator And Experiment Spec

この文書は、Strategy Research Lab の generator と experiment 定義をどう扱うかを固定します。

## 現行 generator registry

Code:

- `src/sis/research/strategy_lab/signal_registry.py`
- `src/sis/research/signal_builder.py`
- `src/sis/strategies/qqq_trend_rates_vix.py`
- `src/sis/strategies/sp500_trend_rates_vix.py`

現行 registered generator:

```text
default_generator_id=qqq_trend_rates_vix
registered_ids=[
  qqq_trend_rates_vix,
  sp500_trend_rates_vix,
]
```

registry behavior:

- generator ID は空文字禁止。
- 同じ generator ID の二重登録は禁止。
- 未登録 generator は `KeyError` で fail closed。
- `registered_ids()` は登録済み ID を sorted list で返す。
- registry は `SignalGeneratorDefinition` を正本にし、generator callable と `strategy_id`, `strategy_family`, `strategy_version`, `SymbolBinding` を同じ定義で管理する。

## 現行 build_signals

`build_signals(data_dir, generator_id=qqq_trend_rates_vix)` は以下を行います。

1. `data/research/feature_panel.parquet` を読む。
2. default generator registry で登録済み `generator_id` を実行する。
3. generator output を `StrategySignalRecord` rows へ変換する。
4. `validate_strategy_signal_frame()` で必須列と symbol binding を検証する。
5. `data/research/strategy_signals.parquet` を書く。
6. `data/research/strategy_signal_manifest.json` を書く。
7. `data/research/strategy_signals.jsonl` を書く。
8. legacy `data/research/signals.csv` を書く。

現行 generator definition:

| generator_id | strategy_id | execution_symbol | real_market_symbol | asset_class |
|---|---|---|---|---|
| `qqq_trend_rates_vix` | `equity_index_momentum_v0` | `XYZ100` | `QQQ` | `basket_index` |
| `sp500_trend_rates_vix` | `sp500_index_momentum_v0` | `SP500` | `SPY` | `index` |

CLI では `--generator-id` で登録済み generator を選べます。これは任意 spec runner ではなく、固定 profile の選択です。

## Generator output の最低仕様

Generator は Strategy Lab artifact へ変換できる signal frame を返す必要があります。現行 `build_signals()` は generator output を内部で StrategySignalRecord row へ包み直していますが、新規 generator は次の情報を出せる必要があります。

- `ts_signal`
- `canonical_symbol` or equivalent symbol source
- `side`
- `timeframe`
- `signal_strength` or score source
- `reason`
- `source_confidence`
- `venue_quality_score`

`source_confidence` と `venue_quality_score` は optional です。入力 feature に列が存在する場合は generator output へ pass-through し、存在しない場合は Strategy Lab artifact 側で null として扱います。

変換後に必要な Strategy Lab fields:

- `schema_version`
- `signal_id`
- `generated_at`
- `strategy_id`
- `strategy_family`
- `strategy_version`
- `ts_signal`
- `timeframe`
- `execution_venue`
- `execution_symbol`
- `real_market_symbol`
- `side`
- `confidence`
- `tail_bucket`

## New generator checklist

新規 generator を追加する時:

1. generator ID を決める。
2. `strategy_family` を決める。
3. `SymbolBinding` を決める。
4. 必要 feature column を列挙する。
5. no-signal 条件を決める。
6. `side` の決定ルールを明文化する。
7. score の範囲と意味を定義する。
8. `reason_codes` を固定する。
9. source confidence / venue quality が無い場合の扱いを決める。
10. `SignalGeneratorDefinition` として registry に登録する。
11. no-signal 時も empty schema と manifest lineage が残る test を追加する。
12. `validate_strategy_signal_frame()` を通る test を追加する。

## StrategyExperimentSpec に落とす時の粒度

よい粒度:

```text
strategy_id=equity_index_momentum_v0
strategy_family=momentum
strategy_version=v0
generator_id=qqq_trend_rates_vix
parameter_grid={
  "max_vix_level": [18, 22],
  "min_research_return_1d": [0.00, 0.01],
  "min_source_confidence": [0.70, 0.80],
  "timeframe": ["1h", "4h"]
}
evaluation_plan_id=initial_walkforward
run_profile_id=strategy_lab
```

悪い粒度:

```text
strategy_id=make_money_bot
strategy_family=ai
strategy_version=latest
parameter_grid={}
```

悪い理由:

- family が検証可能な型ではない。
- parameter space が空で比較できない。
- evaluation plan が曖昧。
- no-signal / reject 条件が追えない。

## Parameter hash

`parameter_hash` は trial や signal の由来を追うためのキーです。

用途:

- 同じ strategy の variant を区別する。
- trial ledger と signal を接続する。
- paper candidate の選別理由を後で再現する。

注意:

- threshold だけが違う候補は新しい `strategy_id` にしない。
- family が同じで input と exit がほぼ同じなら variant として扱う。
- duplicate control は `docs/algo/strategy_factory/DUPLICATE_CONTROL.md` と接続する。

現行 `evaluate-strategy-lab` の `--rank-thresholds` は `TrialRecord.parameter_hash` と `trial_id` を threshold / `--candidate-limit` / `--split-method` / `--era-unit` ごとに分けます。default evaluation だけは既存 artifact 互換のため `generator-default-{run_id}` と `trial-{run_id}` を維持します。

## StrategyExperimentSpec runner

`strategy-experiment-run --spec path/to/spec.yaml` は `StrategyExperimentSpec` YAML/JSON を読み、登録済み `generator_id` の build 関数を使って Strategy Lab signal artifact を生成します。

```bash
uv run sis strategy-experiment-run --spec docs/strategy_research_lab/examples/experiment.yaml
```

この runner は spec の `strategy_id`, `strategy_family`, `strategy_version`, `symbol_bindings` を `strategy_signals.parquet` と `strategy_signal_manifest.json` の lineage として使います。`parameter_grid` は safe cartesian sweep として展開し、各 variant の signal に `parameter_hash` と `parameter_grid:<hash>` reason code を付けます。未登録 `generator_id`、空の grid value、`--max-variants` 超過は exit code 2 で止まります。

現行 built-in generator の `qqq_trend_rates_vix` と `sp500_trend_rates_vix` は、`parameter_grid` variant から次のキーを実際の signal 条件として読みます。

| key | effect |
|---|---|
| `min_source_confidence` | `source_confidence >= value` を満たす row だけを signal 化する。入力列が無い場合、threshold 指定時は通過しない。 |
| `max_vix_level` | `vix_level <= value` を満たす row だけを signal 化する。 |
| `vix_gate` | `max_vix_level` の alias。既存 spec 互換用。 |
| `min_research_return_1d` | `research_return_1d >= value` を満たす row だけを signal 化する。 |
| `timeframe` | output signal の `timeframe` を上書きする。空文字は invalid。 |

上記以外の key は built-in generator では条件に使われません。ただし `parameter_hash` と `parameter_grid:<hash>` reason code には反映されるため、custom generator が読む key の lineage は残せます。

## Current limitations

- `strategy-experiment-run` は registered generator を spec metadata と `parameter_grid` variant で実行する runner です。任意式 eval や任意 Python plugin は実行しません。
- 現行 evaluation は full walk-forward backtester ではなく、artifact chain を成立させる簡易 runner です。`--split-method` は metrics に記録されますが、PnL 計算や walk-forward 検証 engine はまだ実装していません。
- 現行 candidate selection は default で最新 `ts_signal` の 1 件、`--candidate-limit 0` で threshold 通過 signal 全件を `selected_signal_ids` として pack に渡す最小実装です。
- 現行 `promotion-decision` は human review artifact を生成するが、review UI ではない。
- 現行 `build-paper-intent-preview` は selected candidate を simple notional / quantity placeholder で preview 化する。

これらは未実装領域であり、docs で実装済みのように書かないでください。
