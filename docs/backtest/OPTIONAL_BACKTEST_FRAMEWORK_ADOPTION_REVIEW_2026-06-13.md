<!--
作成日: 2026-06-13_20:36 JST
更新日: 2026-06-13_20:36 JST
-->

# Optional Backtest Framework Adoption Review

## 結論

現時点では `pyproject.toml` / `uv.lock` に外部 backtest framework を追加しない。

正式 optional extra の第一候補は、用途で分ける。

| 用途 | 第一候補 | 判断 |
|---|---|---|
| 高速 signal runner / parameter sweep | `vectorbt` | 条件付き候補。Python 3.13 対応と一時 smoke はよいが、Commons Clause 付き license の review が終わるまで lock しない。 |
| portfolio allocation / rebalance comparison | `bt` | 最初に lock する optional extra として最も進めやすい候補。MIT、Python 3.13 wheel、現行 adapter surface との役割一致がある。 |
| metrics normalization | `empyrical-reloaded` | engine ではなく metrics extra 候補。Apache 系で比較的進めやすい。 |
| report / tear sheet | `quantstats` | engine ではなく report extra 候補。Apache-2.0 だが、HTML / plot dependency と artifact 再現性を先に確認する。 |

`backtesting.py`, `zipline-reloaded`, `backtrader`, `pyfolio-reloaded`, `qstrader` は次の理由で今回は採用しない。

- `backtesting.py`: AGPLv3+ のため repo dependency 化前に license review が必須。
- `zipline-reloaded`: 大型 event-driven runner 候補だが、過去 local spike で build smoke が安定していない。
- `backtrader`: GPLv3+ と live trading surface の分離確認が重い。
- `pyfolio-reloaded`: report 補助候補だが、現行では `empyrical-reloaded` と `quantstats` が先。
- `qstrader`: maturity / Python 3.13 smoke / runner boundary の確認が先。

## 確認した正本

Local repo:

- `pyproject.toml`: Python `>=3.13,<3.14`、現時点で外部 backtest framework は通常 dependency / dev dependency ではない。
- `src/sis/backtest/frameworks.py`: 9件の候補を metadata candidate として列挙。
- `src/sis/backtest/framework_smoke.py`: `vectorbt`, `bt`, `quantstats`, `empyrical-reloaded` を一時 import smoke 対象にする。
- `src/sis/backtest/adapter_selection.py`: `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats` を adapter design 対象にし、他候補を deferred にする。
- `data/research/backtest_framework_smoke/strategy_backtest_framework_smoke.json`: locked env では4候補すべて `not_installed`、`dependency_added=false`。
- `data/research/backtest_adapter_selection/strategy_backtest_adapter_selection.json`: selected 4件、deferred 5件、全件 `dependency_added=false`, `permits_live_order=false`。
- `data/research/backtest_external/strategy_backtest_external_result.json`: locked env では外部 engine は実行されず、各 framework は `skipped/not_installed_in_current_env`。
- `docs/backtest/VECTORBT_ADOPTION_PLAN_2026-06-13.md`: `vectorbt` は optional adapter 計画済みだが正式採用前 review が必要。
- `docs/backtest/OSS_BACKTEST_FRAMEWORK_EVALUATION_PLAN_2026-06-13.md`: 役割別候補分類の既存計画。

External primary sources:

- PyPI `vectorbt`: latest `1.0.0`, released 2026-04-22, `Requires-Python >=3.10`, Python 3.13 classifier, license text says `Apache 2.0 with Commons Clause`.
- PyPI `bt`: latest `1.2.0`, `Requires-Python >=3.9`, MIT classifier, Python 3.13 classifier and CPython 3.13 wheels.
- PyPI `quantstats`: latest `0.0.81`, `Requires-Python >=3.10`, SPDX `Apache-2.0`, Python 3.13 classifier.
- PyPI `empyrical-reloaded`: latest `0.5.12`, `Requires-Python >=3.9`, Apache Software License, Python 3.13 classifier.
- PyPI `backtesting`: latest `0.6.5`, `Requires-Python >=3.9`, AGPLv3+.
- PyPI `zipline-reloaded`: latest `3.1.1`, `Requires-Python >=3.10`, SPDX `Apache-2.0`, Python 3.13 classifier.
- PyPI `backtrader`: latest `1.9.78.123`, GPLv3+ classifier.
- PyPI `pyfolio-reloaded`: latest `0.9.9`, `Requires-Python >=3.9`, Apache Software License, Python 3.13 classifier.
- PyPI `qstrader`: latest `0.3.0`, `Requires-Python >=3.9`, MIT classifier.

## 判断表

| Candidate | Repo role | Current package signal | 採用判断 | 次の実装単位 |
|---|---|---|---|---|
| `vectorbt` | `high_speed_signal_runner` | `1.0.0`, Python 3.13 classifier, Commons Clause | 条件付き。license review なしで lock しない。 | license decision memo の後、`[project.optional-dependencies].vectorbt` と `dependency_source=optional_extra` を追加。 |
| `bt` | `portfolio_allocation_rebalance` | `1.2.0`, MIT, Python 3.13 wheel | 最初の optional extra として最有力。 | `bt = ["bt==1.2.0"]` extra、`uv sync --dev --extra bt --locked`、portfolio comparison real smoke。 |
| `empyrical-reloaded` | `metrics_normalization` | `0.5.12`, Apache系, Python 3.13 classifier | metrics extra 候補。engine ではない。 | `metrics = ["empyrical-reloaded==0.5.12"]` か `reports` extra に含める。 |
| `quantstats` | `report_tearsheet` | `0.0.81`, Apache-2.0, Python 3.13 classifier | report extra 候補。engine ではない。 | HTML report artifact の再現性と optional plot deps を確認してから lock。 |
| `backtesting.py` | `simple_ohlc_candidate` | AGPLv3+ | 今回は不採用。 | license review 後に別 spike。 |
| `zipline-reloaded` | `large_event_driven_candidate` | Apache-2.0, Python 3.13 classifier | 今回は不採用。 | build smoke が安定してから別環境 runner 検討。 |
| `backtrader` | `event_driven_candidate` | GPLv3+ | 今回は不採用。 | license / no-live isolation review 後に別環境候補。 |
| `pyfolio-reloaded` | `report_only_candidate` | Apache系, Python 3.13 classifier | 今回は不採用。 | `empyrical-reloaded` / `quantstats` 後に再評価。 |
| `qstrader` | `schedule_event_driven_candidate` | MIT, Python >=3.9 | 今回は不採用。 | maturity と Python 3.13 smoke 後に再評価。 |

## 採用順

依存追加を実行する場合の最小順:

1. `bt` を optional extra として採用する。
2. `strategy-backtest-portfolio-compare` の real `bt` run を optional extra 環境で検証する。
3. `strategy_backtest_portfolio_comparison.v1` に `dependency_source=optional_extra` を追加するか、現行 `runner_mode=temporary_or_optional_import` で足りるかを決める。
4. `strategy-backtest-pack` / `strategy-backtest-pack-validate` で通常 env と `--extra bt` env の読み分けを文書化する。
5. `empyrical-reloaded` と `quantstats` は `reports` extra として一括にするか、`metrics` / `reports` に分けるかを決める。
6. `vectorbt` は license review が通った場合だけ `vectorbt` extra として追加する。

## 受入条件

`bt` optional extra 採用の受入条件:

- `pyproject.toml` に `[project.optional-dependencies]` を追加し、通常 dependency には入れない。
- `uv.lock` の差分が optional extra 採用に限定される。
- `uv sync --dev --locked` が通常 env で通る。
- `uv sync --dev --extra bt --locked` が optional env で通る。
- `uv run --extra bt sis strategy-backtest-portfolio-compare` が `engine_run=true` を artifact に記録する。
- `uv run sis strategy-backtest-pack` は通常 env で `complete_without_locked_external_dependency` を維持する。
- 全 artifact で `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。

`vectorbt` optional extra 採用の追加受入条件:

- Commons Clause を含む license review 結果を docs に残す。
- `vectorbt[full]`, `vectorbt[rust]`, `vectorbt[all]` は初回採用に含めない。
- `src/sis/backtest/vectorbt_adapter.py` の入出力を source hash 付き artifact に閉じ込める。
- `strategy_authoring_native` を標準 engine として維持する。

## Stop Conditions

次の場合は optional dependency 採用を止める。

- license review が未完了、または repo 利用形態に合わない。
- Python 3.13 / uv lock / CI 相当 sync が不安定。
- optional extra が通常 `uv sync --dev --locked` に影響する。
- external framework result が source path / source hash / runner mode / dependency source を記録できない。
- external framework artifact が live order、wallet、signing、exchange write と接続しそうになる。
- native backtest と optional framework result の差分を説明できず、比較 report が誤解を生む。

## 抜け・漏れ・誤謬リスク

- PyPI metadata は package author が提供する metadata を含む。license は法務判断ではなく、採用前 review の入力である。
- `vectorbt` は 1.0.0 で公開情報が新しく、既存 0.x 系と API / license / dependency profile が変わっている可能性がある。
- ここでは transitive dependency license を全件棚卸ししていない。lock 採用時に `uv tree` / wheel metadata の確認が必要。
- 現在の generated smoke artifact は locked env の `not_installed` 状態であり、過去の一時 `uv --with ...` smoke 結果とは分けて読む。
- package popularity や maintenance activity は定量評価していない。採用直前に GitHub releases / issue activity を再確認する。

## Sources

- https://pypi.org/project/vectorbt/
- https://github.com/polakowo/vectorbt/blob/main/LICENSE.md
- https://pypi.org/project/bt/
- https://pypi.org/project/quantstats/
- https://pypi.org/project/empyrical-reloaded/
- https://pypi.org/project/backtesting/
- https://pypi.org/project/zipline-reloaded/
- https://pypi.org/project/backtrader/
- https://pypi.org/project/pyfolio-reloaded/
- https://pypi.org/project/qstrader/
