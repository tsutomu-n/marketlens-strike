<!--
作成日: 2026-06-13_16:12 JST
更新日: 2026-06-13_20:51 JST
-->

# OSS Backtest Framework Evaluation Plan

## 結論

`vectorbt` 以外にも使える OSS はある。採用候補は一枚岩ではなく、役割ごとに分ける。

現時点の推奨は次である。

| Tier | 候補 | 役割 | 判断 |
|---|---|---|---|
| Tier 1 | `vectorbt` | 高速 vectorized research / parameter sweep | license decision により明示承認まで未採用 |
| Tier 1 | `bt` | portfolio / allocation / rebalance 型の比較 | optional extra 採用済み |
| Tier 2 | `backtesting.py` | 小型 OHLC strategy prototype | license review 後の spike 候補 |
| Tier 2 | `zipline-reloaded` | event-driven equity / calendar / pipeline 系 | 重いが大型比較候補 |
| Tier 3 | `backtrader` | indicator-heavy / event-driven 比較 | GPL/live 機能分離が重く、別環境候補 |
| 補助 | `quantstats` | return / drawdown / tear sheet | engine ではなく report 補助候補 |
| 補助 | `empyrical-reloaded` | risk / performance metrics | engine ではなく metrics 補助候補 |
| 補助 | `pyfolio-reloaded` | portfolio analysis report | report 補助候補 |
| 保留 | `QSTrader` | schedule/event-driven equities | repo maturity / Python 3.13 / install spike 後 |

標準 engine は引き続き `strategy_authoring_native` とする。外部OSSは、現行 `strategy-backtest-external-run` / `strategy-backtest-compare` / `strategy-backtest-pack` に接続する adapter として評価する。

## 現行 repo の制約

外部OSS評価で壊してはいけない境界:

- `paper_only=true`
- `live_order_submitted=false`
- `permits_live_order=false`
- `wallet_used=false`
- `exchange_write_used=false`
- `strategy_authoring_native` を標準 engine として維持
- `pyproject.toml` / `uv.lock` の変更は採用判断後だけ
- external result は source path / source hash / framework version / runner mode を残す

## 候補分類

### 1. Core backtest engine 候補

#### vectorbt

用途:

- 大量 parameter sweep
- vectorized signal research
- pandas / NumPy / Numba 系の高速探索

現状:

- `strategy-backtest-external-run` で `vectorbt.Portfolio.from_signals` の一時 smoke 済み。
- 実行処理は `src/sis/backtest/vectorbt_adapter.py` に分離済みで、external result と comparison result に `framework_version` と `runner_mode` を残す。
- PyPI の `vectorbt 1.0.0` は Python `>=3.10`、Python 3.13 classifier を持つ。
- 公式 license は `Apache 2.0 with Commons Clause` で、通常 Apache-2.0 単体ではない。
- [VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md](VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md) により、legal / owner approval なしでは repo optional extra にしない。

判断:

- 技術的には optional adapter 候補だが、現時点では採用しない。
- `vectorbt[full]` / `vectorbt[rust]` は初回採用に含めない。

参照:

- https://pypi.org/project/vectorbt/
- https://vectorbt.dev/
- https://vectorbt.dev/terms/license/

#### bt

用途:

- portfolio construction
- allocation / rebalance rule
- reusable algo blocks
- Strategy Authoring bundle / risk parity / target weight 系との比較

現状:

- PyPI / docs は、quantitative trading strategies の flexible backtesting framework と説明している。
- 現行 repo の portfolio allocation / bundle comparison と役割が近い。
- `strategy-backtest-portfolio-compare` は `bt` が import できる環境では `bt.run()` を呼び、`strategy_backtest_portfolio_comparison.v1` に `framework_version`, `runner_mode`, `portfolio_return`, `max_drawdown`, `turnover`, `rebalance_count` を記録できる。
- `uv run --with bt sis strategy-backtest-portfolio-compare` の一時 smoke は `bt=1.2.0` で通過済み。

判断:

- `bt==1.2.0` は optional extra 採用済み。
- 最初は engine 置換ではなく、portfolio allocation comparison adapter として見る。

参照:

- https://pypi.org/project/bt/
- https://pmorissette.github.io/bt/

#### backtesting.py

用途:

- 小型 OHLC strategy prototype
- strategy class での簡潔な比較
- 単純な indicator / entry / exit ルール検証

現状:

- PyPI は Python `>=3.9` と AGPLv3+ classifier を示す。
- docs は historical data 上で trading strategy viability を見る framework と説明している。

判断:

- 技術的には軽い候補だが、AGPLv3+ のため repo dependency 追加は license review 後。
- 別環境 adapter または sample-only が無難。

参照:

- https://pypi.org/project/backtesting/
- https://kernc.github.io/backtesting.py/

#### zipline-reloaded

用途:

- event-driven equity backtest
- calendar-aware pipeline
- equity research workflow

現状:

- PyPI は Python `>=3.10` と説明している。
- GitHub pyproject では Apache-2.0 と Python 3.13 classifier が確認できる。
- 以前の local smoke では `bcolz-zipline` build で失敗している。

判断:

- 大型候補。Python 3.13 / native build / transitive dependency の確認を先に行う。
- 採用する場合も optional extra ではなく、別環境 runner の方が安全な可能性が高い。

参照:

- https://pypi.org/project/zipline-reloaded/
- https://github.com/stefan-jansen/zipline-reloaded

#### backtrader

用途:

- event-driven strategy
- indicator-heavy strategy
- analyzer / broker model 比較

現状:

- 公式 docs は backtesting and trading framework と説明している。
- live trading 機能も含む。
- local metadata smoke では GPLv3+ 系が観測済み。

判断:

- repo dependency としては優先度を下げる。
- 採用するなら no-live isolation と license review が必須。

参照:

- https://www.backtrader.com/
- https://pypi.org/project/backtrader/

### 2. Metrics / report 補助候補

#### quantstats

用途:

- tear sheet
- return / drawdown / risk report
- HTML / plotly optional report

現状:

- PyPI は Apache-2.0 license expression、Python `>=3.10` と説明している。
- `strategy-backtest-report-extension` は `quantstats` が import できる環境では `quantstats.reports.html` と `quantstats.reports.metrics` を呼び、`strategy_backtest_report_extension.v1` に framework version、runner mode、HTML report path/hash、metrics table row count を記録できる。
- `uv run --with quantstats sis strategy-backtest-report-extension` の一時 smoke は `quantstats=0.0.81` で通過済み。

判断:

- engine ではなく report 補助として有力。
- `strategy-backtest-compare` / `strategy-backtest-pack` の report extension として実装済み。

参照:

- https://pypi.org/project/quantstats/

#### empyrical-reloaded

用途:

- common risk / performance metrics
- Sharpe / drawdown / factor-style metric 補助

現状:

- PyPI は Apache License、Python `>=3.9` と説明している。
- Zipline / Pyfolio 系の metrics 補助として使いやすい。

判断:

- engine ではなく metrics normalization 補助。
- native engine の metric consistency test に使える可能性がある。

参照:

- https://pypi.org/project/empyrical-reloaded/

#### pyfolio-reloaded

用途:

- portfolio performance / risk analysis report
- tear sheet generation

現状:

- PyPI は Apache License、Python `>=3.9` と説明している。

判断:

- engine ではなく report 補助。
- UI/report 改善 scope で評価する。

参照:

- https://pypi.org/project/pyfolio-reloaded/

### 3. 保留候補

#### QSTrader

用途:

- schedule-driven / event-driven equities
- long-short equity / ETF systematic strategy

現状:

- QSTrader は open-source modular schedule-driven backtesting framework と説明されている。
- GitHub では alpha state の記述がある。
- PyPI 系 package は複数あり、正本 package / fork / Python 3.13 対応の確認が必要。

判断:

- すぐ採用しない。
- `zipline-reloaded` と同じ大型 event-driven 枠で比較する。

参照:

- https://pypi.org/project/qstrader/
- https://github.com/quantstart/qstrader

## 評価マトリクス

| 観点 | vectorbt | bt | backtesting.py | zipline-reloaded | backtrader | quantstats / empyrical / pyfolio |
|---|---|---|---|---|---|---|
| 役割 | vectorized engine | portfolio engine | simple OHLC engine | event-driven engine | event-driven engine | metrics/report |
| 初回採用優先度 | 高 | 高 | 中 | 中 | 低 | 中 |
| license risk | 中 | 要確認 | 高 | 低〜中 | 高 | 低〜中 |
| Python 3.13 risk | 低〜中 | 要確認 | 低〜中 | 中〜高 | 中 | 低〜中 |
| live機能混入 risk | 低 | 低 | 低 | 中 | 高 | 低 |
| 現行artifact接続 | 中 | 中 | 中 | 低 | 低 | 高 |
| 推奨採用形 | optional adapter | optional adapter | external sample / adapter | separate runner | separate runner | optional report extra |

## 実装順

### Phase A: OSS inventory artifact

実装状況: 実装済み。`strategy-backtest-adapter-spike` は9候補を dependency-free artifact に出す。

目的:

- 現行 `strategy-backtest-adapter-spike` の候補を `vectorbt`, `bt`, `backtesting.py`, `zipline-reloaded`, `backtrader`, `quantstats`, `empyrical-reloaded`, `pyfolio-reloaded`, `qstrader` へ広げる。

完了条件:

- candidate ごとの role / license / Python support / local import status / adoption blocker を JSON artifact に出す。
- `dependency_added=false` を維持する。

### Phase B: Tier 1 import smoke

実装状況: 実装済み。`strategy-backtest-framework-smoke` で一時 import smoke を artifact 化する。

対象:

- `vectorbt`
- `bt`
- `quantstats`
- `empyrical-reloaded`

完了条件:

- `uv run --with ... python -c 'import ...'` が通るか記録する。
- version / license metadata / Requires-Python を artifact に残す。
- 採用候補を `optional_extra_candidate` / `separate_runner_candidate` / `report_only_candidate` に分類する。

実測:

```bash
uv run --with vectorbt --with bt --with quantstats --with empyrical-reloaded sis strategy-backtest-framework-smoke
```

2026-06-13_16:50 JST 時点で、`vectorbt=1.0.0`, `bt=1.2.0`, `quantstats=0.0.81`, `empyrical-reloaded=0.5.12` はすべて `import_status=imported` だった。`pyproject.toml` / `uv.lock` は変更していない。

### Phase C: adapter selection

実装状況: 実装済み。`strategy-backtest-adapter-selection` で Phase C の初期選定を artifact 化する。

推奨:

1. `vectorbt`: high-speed signal runner
2. `bt`: portfolio allocation / rebalance comparison
3. `quantstats` と `empyrical-reloaded`: report / metrics extension

実測選定:

- selected: `vectorbt` = `high_speed_signal_runner`
- selected: `bt` = `portfolio_allocation_rebalance`
- selected: `empyrical-reloaded` = `metrics_normalization`
- selected: `quantstats` = report / tearsheet extension
- deferred: `backtesting.py`, `zipline-reloaded`, `backtrader`, `pyfolio-reloaded`, `qstrader`

やらない:

- `backtesting.py` / `backtrader` を license review 前に lock しない。
- `zipline-reloaded` を build smoke 前に optional extra にしない。

### Phase D: optional extras

実装状況: optional dependency 採用前の adapter contract を実装済み。`strategy-backtest-adapter-contract` が `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` の input / output / provenance / acceptance contract を artifact 化する。`vectorbt` の `strategy_backtest_external_result.v1` adapter wrapper、`bt` の `strategy_backtest_portfolio_comparison.v1` adapter wrapper、`empyrical-reloaded` の `strategy_backtest_metric_extension.v1` adapter wrapper、`quantstats` の `strategy_backtest_report_extension.v1` adapter wrapper は実装済み。`pyproject.toml` / `uv.lock` は未変更。

候補:

```toml
[project.optional-dependencies]
backtest-vectorbt = ["vectorbt==1.0.0"]
backtest-portfolio = ["bt==<locked-version>"]
backtest-report = ["quantstats==<locked-version>", "empyrical-reloaded==<locked-version>"]
```

注意:

- version は smoke 後に固定する。
- `vectorbt[full]`, `vectorbt[rust]` は初回に入れない。
- AGPL / GPL 系は optional extra にも入れない判断を優先する。

### Phase E: validation / docs

更新対象:

- `strategy_backtest_adapter_spike.v1`
- `strategy_backtest_external_result.v1`
- `strategy_backtest_comparison.v1`
- `strategy_backtest_pack.v1`
- `strategy-backtest-pack-validate`
- `docs/backtest/README.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`

完了条件:

- 通常環境の `strategy-backtest-pack-validate` は PASS。
- optional extra 環境の external runner は framework version / dependency source / metrics を記録。
- no-live boundary は全artifactで維持。

## Stop Conditions

次の場合は採用しない。

- license が repo 利用形態に合わない。
- Python 3.13 / uv lock / CI が安定しない。
- transitive dependency が通常開発や CI を重くしすぎる。
- external engine の result を source hash 付き artifact に正規化できない。
- native engine と external engine の差分を説明できず、report が誤解を生む。

## 次の具体タスク

1. `src/sis/backtest/frameworks.py` の候補を広げる。
2. `strategy-backtest-adapter-spike` の schema と report を更新する。
3. `bt`, `quantstats`, `empyrical-reloaded`, `pyfolio-reloaded`, `qstrader` の temporary import smoke を実行する。
4. `strategy-backtest-compare` に report-only candidate と engine candidate の区分を出す。
5. optional extra 採用候補を `vectorbt`, `bt`, `quantstats/empyrical` に絞る。
