<!--
作成日: 2026-06-13_21:01 JST
更新日: 2026-06-13_21:11 JST
-->

# Metrics / Reports Optional Extras Decision

## 結論

`empyrical-reloaded` と `quantstats` は別々の optional extra として採用する。

- `metrics`: `empyrical-reloaded==0.5.12`
- `reports`: `quantstats==0.0.81`

通常 dependency には入れない。標準 backtest pack completion は引き続き `strategy_authoring_native` と `complete_without_locked_external_dependency` を正とし、`metrics` / `reports` extra は optional comparison / reporting surface に限定する。

## 分ける理由

`empyrical-reloaded` と `quantstats` は用途が違う。

| Extra | Package | Role | Primary command |
|---|---|---|---|
| `metrics` | `empyrical-reloaded==0.5.12` | returns series から Sharpe / Sortino / drawdown / annualized metrics を正規化する | `strategy-backtest-metric-extension` |
| `reports` | `quantstats==0.0.81` | returns series から HTML report / metrics table を生成する | `strategy-backtest-report-extension` |

1つの `reports` extra にまとめると、数値 metric だけ必要な場面でも HTML / plotting 依存が入る。逆に `metrics` だけなら `quantstats` の plot / font / HTML 生成コストを避けられる。そのため、責務ごとに分ける。

## 採用する範囲

採用する:

- `empyrical-reloaded` base package
- `quantstats` base package
- artifact field `dependency_source`
  - `not_installed_in_current_env`
  - `temporary_uv_with`
  - `optional_extra_available`

採用しない:

- `empyrical-reloaded[yfinance]`
- `empyrical-reloaded[datareader]`
- `quantstats[plotly]`
- live order / wallet / signing / exchange write への接続
- `metrics` / `reports` extra を標準 pack completion の必須条件にすること

`empyrical-reloaded[datareader]` は upstream docs が Python `>=3.12` 非互換の注意を出しているため、初回採用には含めない。

## 確認した一次情報

`empyrical-reloaded 0.5.12`:

- PyPI release: `0.5.12`
- release date: 2025-06-01
- Requires-Python: `>=3.9`
- Python 3.13 classifier: あり
- license classifier: `OSI Approved :: Apache Software License`
- GitHub license: Apache-2.0
- base dependency includes `bottleneck`, `numpy`, `pandas`, `peewee`, `scipy`

`quantstats 0.0.81`:

- PyPI release: `0.0.81`
- release date: 2026-01-13
- Requires-Python: `>=3.10`
- Python 3.13 classifier: あり
- license expression: `Apache-2.0`
- GitHub license: Apache-2.0
- base dependency includes `matplotlib`, `numpy`, `pandas`, `python-dateutil`, `scipy`, `seaborn`, `tabulate`, `yfinance`

参照:

- https://pypi.org/project/empyrical-reloaded/
- https://github.com/stefan-jansen/empyrical-reloaded
- https://pypi.org/project/quantstats/
- https://github.com/ranaroussi/quantstats

## 実行方法

通常環境:

```bash
uv sync --dev --locked
uv run sis strategy-backtest-metric-extension
uv run sis strategy-backtest-report-extension
```

通常環境では extra package が未インストールなら `skipped/not_installed_in_current_env` を記録する。

metrics extra:

```bash
uv sync --dev --extra metrics --locked
uv run --extra metrics sis strategy-backtest-metric-extension
```

reports extra:

```bash
uv sync --dev --extra reports --locked
uv run --extra reports sis strategy-backtest-report-extension
```

両方を使う場合:

```bash
uv sync --dev --extra metrics --extra reports --locked
uv run --extra metrics --extra reports sis strategy-backtest-metric-extension
uv run --extra metrics --extra reports sis strategy-backtest-report-extension
```

## 検証結果

2026-06-13_21:11 JST 時点:

- `uv sync --dev --locked`: passed; `empyrical`, `quantstats`, `bt` は未インストール。
- `uv sync --dev --extra metrics --locked`: passed.
- `uv run --extra metrics sis strategy-backtest-metric-extension`: `framework_version=0.5.12`, `dependency_source=optional_extra_available`, `metric_status=completed`, `engine_run=true`, `return_count=7`.
- `uv sync --dev --extra reports --locked`: passed.
- `uv run --extra reports sis strategy-backtest-report-extension`: `framework_version=0.0.81`, `dependency_source=optional_extra_available`, `report_status=completed`, `engine_run=true`, `return_count=7`, HTML report generated.
- focused tests: `11 passed in 0.88s`.
- full gate `./scripts/check`: `1039 passed in 34.75s`.

`quantstats` HTML generation can emit font / numerical runtime warnings on small demo return series. Current behavior still writes the HTML report and records `report_status=completed`; if warning noise becomes an operator problem, handle it in a separate report-rendering polish scope.

## 抜け・漏れ・誤謬リスク

- This is an engineering adoption decision, not legal advice.
- `empyrical-reloaded` constrains `peewee<3.17.4`, so the single `uv.lock` resolution currently pins `peewee==3.17.3`. Full gate must remain the acceptance check for existing `yfinance` / market-data surfaces.
- `quantstats` brings plotting/report dependencies and can produce noisy font warnings. It remains an optional `reports` extra, not a standard runtime requirement.
- Transitive dependency license review is limited to package metadata signals in this scope. Re-check before production redistribution or hosted service packaging.
