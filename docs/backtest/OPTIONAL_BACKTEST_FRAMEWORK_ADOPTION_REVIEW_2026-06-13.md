<!--
作成日: 2026-06-13_20:36 JST
更新日: 2026-06-14_17:55 JST
-->

# Optional Backtest Framework Adoption Review

## 結論

`vectorbt` は 2026-06-14_11:00 JST の owner 承認により、高速 signal runner / parameter sweep 用の optional extra として採用済みである。通常 dependency には入れず、`uv sync --dev --extra vectorbt --locked` または `uv run --extra vectorbt ...` で使う。

`bt` は portfolio allocation / rebalance comparison 用の optional extra として採用済みである。通常 dependency には入れず、`uv sync --dev --extra bt --locked` または `uv run --extra bt ...` で使う。

`empyrical-reloaded` と `quantstats` は [METRICS_REPORT_OPTIONAL_EXTRAS_DECISION_2026-06-13.md](METRICS_REPORT_OPTIONAL_EXTRAS_DECISION_2026-06-13.md) により、別々の optional extra として採用済みである。`backtesting.py`, `zipline-reloaded`, `zipline-refresh`, `backtrader`, `pyfolio-reloaded`, `alphalens-reloaded`, `qstrader` は現時点では `pyproject.toml` / `uv.lock` に追加しない。

正式 optional extra の第一候補は、用途で分ける。

| 用途 | 第一候補 | 判断 |
|---|---|---|
| 高速 signal runner / parameter sweep | `vectorbt` | optional extra 採用済み。Commons Clause 付き license は owner 承認済みとして扱い、base extra のみ lock する。 |
| portfolio allocation / rebalance comparison | `bt` | optional extra 採用済み。MIT、Python 3.13 wheel、現行 adapter surface との役割一致がある。 |
| metrics normalization | `empyrical-reloaded` | `metrics` optional extra 採用済み。base package のみ採用し、`datareader` / `yfinance` extra は含めない。 |
| report / tear sheet | `quantstats` | `reports` optional extra 採用済み。base package のみ採用し、`plotly` extra は含めない。 |

`backtesting.py`, `zipline-reloaded`, `zipline-refresh`, `backtrader`, `pyfolio-reloaded`, `alphalens-reloaded`, `qstrader` は次の理由で今回は採用しない。

- `backtesting.py`: lightweight OHLCV backtest runner として技術的には補完候補だが、AGPLv3+ のため repo dependency 化前に license review が必須。
- `zipline-reloaded`: 大型 event-driven runner 候補だが、2026-06-14_17:41 JST の local spike でも `bcolz-zipline==1.13.0` build が `Python.h` 不足で失敗した。
- `zipline-refresh`: `zipline-reloaded` とは別の新しい Zipline fork として確認したが、2026-06-14_17:41 JST の local spike では `zipline-refresh==4.0.0` build が `Python.h` 不足で失敗した。
- `backtrader`: GPLv3+ と live trading surface の分離確認が重い。
- `pyfolio-reloaded`: report 補助候補だが、現行では `empyrical-reloaded` と `quantstats` が先。
- `alphalens-reloaded`: alpha factor analysis 候補であり、backtest engine ではない。Strategy Lab の factor research を拡張する場合に再評価する。
- `qstrader`: MIT / schedule-driven long-short equities and ETF backtest engine として技術的には補完候補。Python 3.13 import smoke は通ったが、PyPI classifier は Python 3.12 までで、runner boundary と入力データ設計の確認が先。

## 確認した正本

Local repo:

- `pyproject.toml`: Python `>=3.13,<3.14`、`vectorbt==1.0.0` を `[project.optional-dependencies].vectorbt`、`bt==1.2.0` を `bt`、`empyrical-reloaded==0.5.12` を `metrics`、`quantstats==0.0.81` を `reports` に固定。通常 dependency / dev dependency ではない。
- `uv.lock`: `vectorbt==1.0.0`, `bt==1.2.0`, `empyrical-reloaded==0.5.12`, `quantstats==0.0.81` と transitive dependency を optional extra として lock。
- `src/sis/backtest/frameworks.py`: 9件の候補を metadata candidate として列挙。
- `src/sis/backtest/framework_smoke.py`: `vectorbt`, `bt`, `quantstats`, `empyrical-reloaded` を一時 import smoke 対象にする。
- `src/sis/backtest/adapter_selection.py`: `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` を adapter design 対象にし、他候補を deferred にする。
- `data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json`: locked env では4候補すべて `not_installed`、`dependency_added=false`。
- `data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json`: selected 4件、deferred 5件、全件 `dependency_added=false`, `permits_live_order=false`。
- `data/research/backtest_external/strategy_backtest_external_result.json`: optional extra env では `vectorbt` が `dependency_source=optional_extra_available` として実行される。
- `docs/backtest/VECTORBT_ADOPTION_PLAN_2026-06-13.md`: `vectorbt` は optional adapter として正式採用済み。
- `docs/backtest/OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md`: 役割別候補分類の既存計画。

External primary sources:

- PyPI `vectorbt`: latest `1.0.0`, released 2026-04-22, `Requires-Python >=3.10`, Python 3.13 classifier, machine-readable license metadata は空。
- vectorbt official license / GitHub license: `Apache 2.0 with Commons Clause`。GitHub API の repository license は `NOASSERTION` / `Other`。
- PyPI `bt`: latest `1.2.0`, `Requires-Python >=3.9`, MIT classifier, Python 3.13 classifier and CPython 3.13 wheels.
- PyPI `quantstats`: latest `0.0.81`, `Requires-Python >=3.10`, SPDX `Apache-2.0`, Python 3.13 classifier.
- PyPI `empyrical-reloaded`: latest `0.5.12`, `Requires-Python >=3.9`, Apache Software License, Python 3.13 classifier.
- PyPI `backtesting`: latest `0.6.5`, `Requires-Python >=3.9`, AGPLv3+.
- PyPI `zipline-reloaded`: latest `3.1.1`, `Requires-Python >=3.10`, SPDX `Apache-2.0`, Python 3.13 classifier.
- PyPI `zipline-refresh`: latest `4.0.0`, `Requires-Python >=3.10`, SPDX `Apache-2.0`, Python 3.13 classifier.
- PyPI `backtrader`: latest `1.9.78.123`, GPLv3+ classifier.
- PyPI `pyfolio-reloaded`: latest `0.9.9`, `Requires-Python >=3.9`, Apache Software License, Python 3.13 classifier.
- PyPI `alphalens-reloaded`: latest `0.4.6`, `Requires-Python >=3.10`, Apache Software License, Python 3.13 classifier.
- PyPI `qstrader`: latest `0.3.0`, released 2024-06-24, `Requires-Python >=3.9`, MIT classifier, Python classifier is 3.9-3.12.

2026-06-14_17:41 JST local temporary import smoke:

- `uv run --with backtesting python - ...`: `backtesting 0.6.5`, AGPL-3.0, `Requires-Python >=3.9`, import OK.
- `uv run --with backtrader python - ...`: `backtrader 1.9.78.123`, GPLv3+, `Requires-Python` metadataなし, import OK.
- `uv run --with qstrader python - ...`: `qstrader 0.3.0`, MIT classifier, `Requires-Python >=3.9`, import OK.
- `uv run --with pyfolio-reloaded python - ...`: `pyfolio-reloaded 0.9.9`, Apache Software License, `Requires-Python >=3.9`, import OK。`zipline.assets` 不在 warning は出る。
- `uv run --with alphalens-reloaded python - ...`: `alphalens-reloaded 0.4.6`, Apache Software License, `Requires-Python >=3.10`, import OK。
- `uv run --with zipline-reloaded python - ...`: `zipline-reloaded 3.1.1` が依存する `bcolz-zipline==1.13.0` の wheel build で `fatal error: Python.h: No such file or directory`。
- `uv run --with zipline-refresh python - ...`: `zipline-refresh==4.0.0` の wheel build で `fatal error: Python.h: No such file or directory`。

## 判断表

| Candidate | Repo role | Current package signal | 採用判断 | 次の実装単位 |
|---|---|---|---|---|
| `vectorbt` | `high_speed_signal_runner` | `1.0.0`, Python 3.13 classifier, official license is Apache 2.0 with Commons Clause | optional extra 採用済み。 | `uv run --extra vectorbt sis strategy-backtest-framework-run --framework vectorbt`。 |
| `bt` | `portfolio_allocation_rebalance` | `1.2.0`, MIT, Python 3.13 wheel | optional extra 採用済み。 | `uv sync --dev --extra bt --locked`、`uv run --extra bt sis strategy-backtest-portfolio-compare`、portfolio comparison real smoke。 |
| `empyrical-reloaded` | `metrics_normalization` | `0.5.12`, Apache系, Python 3.13 classifier | `metrics` optional extra 採用済み。engine ではない。 | `uv run --extra metrics sis strategy-backtest-metric-extension`。 |
| `quantstats` | `report_tearsheet` | `0.0.81`, Apache-2.0, Python 3.13 classifier | `reports` optional extra 採用済み。engine ではない。 | `uv run --extra reports sis strategy-backtest-report-extension`。 |
| `backtesting.py` | `simple_ohlc_candidate` | AGPLv3+ | 今回は不採用。 | license review 後に別 spike。 |
| `qstrader` | `schedule_event_driven_candidate` | MIT, Python >=3.9, local Python 3.13 import OK, PyPI classifier は 3.12 まで | 今回は不採用だが、残候補では最有力。 | local CSV / parquet input を使う isolated runner spike。 |
| `zipline-reloaded` | `large_event_driven_candidate` | Apache-2.0, Python 3.13 classifier, local build failed at `bcolz-zipline` | 今回は不採用。 | system Python headers / container / wheel availability を分けた別環境 spike。 |
| `zipline-refresh` | `large_event_driven_candidate` | Apache-2.0, Python 3.13 classifier, local build failed at package C extension | 今回は不採用。 | `zipline-reloaded` とは別候補として container smoke。 |
| `backtrader` | `event_driven_candidate` | GPLv3+ | 今回は不採用。 | license / no-live isolation review 後に別環境候補。 |
| `pyfolio-reloaded` | `report_only_candidate` | Apache系, Python 3.13 classifier | 今回は不採用。 | `empyrical-reloaded` / `quantstats` 後に再評価。 |
| `alphalens-reloaded` | `factor_analysis_candidate` | Apache系, Python 3.13 classifier, local Python 3.13 import OK | 今回は不採用。backtest engine ではない。 | factor research artifact を作る scope で再評価。 |

## 追加調査後の優先順位

追加採用候補だけを見ると、優先順位は次の通り。

1. `qstrader`: MIT で、local Python 3.13 import smoke も通った。現行の NDX / QQQ research に近い equity / ETF schedule-driven portfolio backtest を補完できる。2026-06-14_17:55 JST 時点では、明示 smoke で imported の場合だけ `strategy-backtest-adapter-selection` が selected `separate_runner_research` に昇格する。ただし PyPI classifier は Python 3.12 までなので、CI 相当の `uv lock` / test gate と、外部データ取得を使わない local input runner が必要。
2. `backtesting.py`: simple OHLCV runner としては最も軽く、native backtest と `vectorbt` の間の readable prototype surface を補完できる。ただし AGPLv3+ のため、正式採用は license approval なしに進めない。
3. `zipline-reloaded` / `zipline-refresh`: event-driven / calendar / pipeline 方面の補完力は大きいが、現環境ではどちらも build が通らない。repo optional extra ではなく、別 Python headers / container / mamba 系の隔離検証が先。
4. `backtrader`: event-driven の補完力はあるが GPLv3+ と live trading surface の分離が重い。現 repo の no-live 境界では `qstrader` より後。
5. `pyfolio-reloaded` / `alphalens-reloaded`: backtest engine ではない。`quantstats` / `empyrical-reloaded` の次に、reporting または factor research が不足した場合だけ検討する。

## 採用順

残りの依存追加を実行する場合の最小順:

1. `strategy-backtest-pack` / `strategy-backtest-pack-validate` で通常 env と `--extra bt` env の読み分けを維持する。
2. `empyrical-reloaded` と `quantstats` は `metrics` / `reports` に分けて採用済み。
3. `vectorbt` は [VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md](VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md) の通り、owner approval 済みとして `vectorbt` extra に追加済みである。

## 受入条件

`bt` optional extra 採用の受入条件と確認結果:

- `pyproject.toml` に `[project.optional-dependencies].bt = ["bt==1.2.0"]` を追加し、通常 dependency には入れない。
- `uv.lock` の差分は `bt` optional extra と transitive dependency である。
- `uv sync --dev --locked` は通常 env で通る。
- `uv sync --dev --extra bt --locked` は optional env で通る。
- `uv run --extra bt sis strategy-backtest-portfolio-compare` は `engine_run=true`, `framework_version=1.2.0`, `dependency_source=optional_extra_available` を artifact に記録する。
- 通常 env では `bt` が未インストールなら `run_status=skipped`, `dependency_source=not_installed_in_current_env` を維持する。
- 全 artifact で `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。

`metrics` / `reports` optional extra 採用の受入条件と確認結果:

- `pyproject.toml` に `[project.optional-dependencies].metrics = ["empyrical-reloaded==0.5.12"]` を追加し、通常 dependency には入れない。
- `pyproject.toml` に `[project.optional-dependencies].reports = ["quantstats==0.0.81"]` を追加し、通常 dependency には入れない。
- `uv.lock` の差分は `metrics` / `reports` optional extra と transitive dependency である。
- `uv sync --dev --locked` は通常 env で通り、`empyrical`, `quantstats`, `bt` は未インストールのまま。
- `uv sync --dev --extra metrics --locked` と `uv run --extra metrics sis strategy-backtest-metric-extension` は `framework_version=0.5.12`, `dependency_source=optional_extra_available`, `metric_status=completed`, `engine_run=true` を artifact に記録する。
- `uv sync --dev --extra reports --locked` と `uv run --extra reports sis strategy-backtest-report-extension` は `framework_version=0.0.81`, `dependency_source=optional_extra_available`, `report_status=completed`, `engine_run=true` を artifact に記録する。
- 通常 env では未インストールなら `dependency_source=not_installed_in_current_env` を維持する。
- 全 artifact で `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。

`vectorbt` optional extra 採用の受入条件と確認結果:

- Commons Clause を含む license review 結果を docs に残す。
- owner approval を decision record に残す。
- `pyproject.toml` に `[project.optional-dependencies].vectorbt = ["vectorbt==1.0.0"]` を追加し、通常 dependency には入れない。
- `uv.lock` の差分は `vectorbt` optional extra と transitive dependency である。
- `vectorbt[full]`, `vectorbt[rust]`, `vectorbt[all]` は初回採用に含めない。
- `src/sis/backtest/vectorbt_adapter.py` の入出力を source hash 付き artifact に閉じ込める。
- `strategy-backtest-external-run` / `strategy-backtest-framework-run --framework vectorbt` は `dependency_source=optional_extra_available`, `engine_run=true` を artifact に記録する。
- `strategy_authoring_native` を標準 engine として維持する。

## Stop Conditions

次の場合は optional dependency 採用を止める。

- Python 3.13 / uv lock / CI 相当 sync が不安定。
- optional extra が通常 `uv sync --dev --locked` の依存集合に混入する。
- external framework result が source path / source hash / runner mode / dependency source を記録できない。
- external framework artifact が live order、wallet、signing、exchange write と接続しそうになる。
- native backtest と optional framework result の差分を説明できず、比較 report が誤解を生む。

## 抜け・漏れ・誤謬リスク

- PyPI metadata は package author が提供する metadata を含む。license は法務判断ではなく、採用前 review の入力である。
- `vectorbt` は 1.0.0 で公開情報が新しく、既存 0.x 系と API / license / dependency profile が変わっている可能性がある。
- ここでは transitive dependency license を全件棚卸ししていない。lock 採用時に `uv tree` / wheel metadata の確認が必要。
- 現在の generated smoke artifact は locked env の `not_installed` 状態であり、過去の一時 `uv --with ...` smoke 結果とは分けて読む。
- package popularity や maintenance activity は定量評価していない。採用直前に GitHub releases / issue activity を再確認する。
- `qstrader` は PyPI の latest metadata と local import は良好だが、公式説明上の主対象は long-short equities / ETF であり、既存 Strategy Lab artifact との入出力変換は未設計。
- `zipline-refresh` は `zipline-reloaded` とは別 fork なので、Zipline 系を再評価する時は両方を同じ bucket に雑にまとめない。
- `alphalens-reloaded` は backtest ではなく alpha factor analysis であり、backtest framework として採用すると役割誤認になる。
- local build failure の `Python.h` は環境側の Python development headers 不足を含む可能性がある。package そのものの Python 3.13 非対応とは断定しない。
- `empyrical-reloaded` の base dependency により lockfile の `peewee` は `3.17.3` へ解決される。既存 market data surface への影響は full gate で確認する。
- `quantstats` HTML generation は小さい demo return series で font / numerical warning を出し得る。artifact は生成済みだが、warning 抑制は別 scope。

## Sources

- https://pypi.org/project/vectorbt/
- https://vectorbt.dev/terms/license/
- https://github.com/polakowo/vectorbt/blob/master/LICENSE.md
- https://pypi.org/project/bt/
- https://pypi.org/project/quantstats/
- https://pypi.org/project/empyrical-reloaded/
- https://github.com/ranaroussi/quantstats
- https://github.com/stefan-jansen/empyrical-reloaded
- https://pypi.org/project/backtesting/
- https://pypi.org/project/zipline-reloaded/
- https://pypi.org/project/zipline-refresh/
- https://pypi.org/project/backtrader/
- https://pypi.org/project/pyfolio-reloaded/
- https://pypi.org/project/alphalens-reloaded/
- https://pypi.org/project/qstrader/
