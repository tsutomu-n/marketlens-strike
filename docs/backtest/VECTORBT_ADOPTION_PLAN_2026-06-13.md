<!--
作成日: 2026-06-13_16:04 JST
更新日: 2026-06-14_11:00 JST
-->

# vectorbt Adoption Plan

## 結論

`vectorbt` は 2026-06-14_11:00 JST の owner 承認により正式採用済みである。現行 repo には `vectorbt==1.0.0` の optional extra と、選択式実行 surface がある。

採用判断の正本は [VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md](VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md) とする。`Strategy Authoring native` を標準 engine として残したまま、`vectorbt` を optional adapter として入れ、外部 engine 比較の高速化と parameter sweep 補助に限定する。

この計画では `VectorBot` という呼び名は使わず、Python package 名の `vectorbt` に統一する。

## 現在の状態

現行の実装済み surface:

- `strategy-backtest-external-run` は `vectorbt` が import できる環境では `vectorbt.Portfolio.from_signals` を呼べる。
- `vectorbt` 実行処理は `src/sis/backtest/vectorbt_adapter.py` に分離済みで、外部 result は `framework_version` と `runner_mode` を記録する。
- `uv run --extra vectorbt sis strategy-backtest-external-run` と `strategy-backtest-framework-run --framework vectorbt` で正式 optional extra smoke を行う。
- `strategy_backtest_pack.v1` は `external_framework_policy` で、標準 engine を `strategy_authoring_native`、完成線を `complete_without_locked_external_dependency` として固定している。
- `pyproject.toml` / `uv.lock` には `vectorbt==1.0.0` を optional extra として入れている。
- live order、wallet、signing、exchange write はどの external framework surface でも許可しない。

現在の外部情報:

- PyPI の `vectorbt 1.0.0` は 2026-04-22 release、`Requires-Python >=3.10`、Python 3.13 classifier を持つ。
- PyPI の説明では、pandas / NumPy / Numba を中心に、大量設定を高速に評価する backtesting / analysis library とされている。
- 公式 license page と GitHub license file は `Apache 2.0 with Commons Clause` を示す。これは通常の Apache-2.0 単体とは扱いが違うため、2026-06-14_11:00 JST の owner approval を採用根拠として記録する。
- PyPI metadata は `License=None`, `License-Expression=None` で、machine-readable license 判定だけでは採用可否を決められない。
- optional dependencies はより制限的な license を含む可能性があるため、初回採用では `vectorbt[full]` や `vectorbt[rust]` は使わない。

参照:

- https://pypi.org/project/vectorbt/
- https://vectorbt.dev/
- https://github.com/polakowo/vectorbt

## 採用方針

採用する場合も、`vectorbt` は標準 engine ではなく optional adapter とする。

採用後の標準構造:

- 標準 backtest: `strategy_authoring_native`
- optional vectorbt runner: `strategy-backtest-external-run`
- 比較正本: `strategy-backtest-compare`
- 標準検証: `strategy-backtest-pack` + `strategy-backtest-pack-validate`
- dependency boundary: `vectorbt` は optional extra

やらないこと:

- `vectorbt` を標準 engine に置き換えない。
- `strategy_authoring_spec.v1` の backtest contract をすぐ変更しない。
- `vectorbt[full]` / `vectorbt[rust]` を初回採用に含めない。
- live order、wallet、signing、exchange write に接続しない。
- `vectorbt` の結果だけで alpha / paper / live readiness を主張しない。

## Phase 0: 採用前 review

目的:

- dependency 追加前に、license / Python 3.13 / uv lock / artifact boundary の採用可否を決める。

確認すること:

1. `vectorbt` の license を repo 利用形態で許容できるか。
2. `vectorbt==1.0.0` を Python 3.13 で lock できるか。
3. `vectorbt` の transitive dependency が CI で解決できるか。
4. `vectorbt` runner が `strategy_backtest_external_result.v1` に収まるか。
5. `dependency_added=false` を維持している現行 artifact と、optional extra 採用後の artifact boundary をどう分けるか。

想定コマンド:

```bash
uv run --with vectorbt python - <<'PY'
from importlib.metadata import metadata, version
m = metadata("vectorbt")
print("version", version("vectorbt"))
print("requires_python", m.get("Requires-Python"))
print("license", m.get("License"))
print("classifiers", [v for k, v in m.items() if k == "Classifier" and "License" in v])
PY
uv run --with vectorbt sis strategy-backtest-external-run
uv run sis strategy-backtest-compare
```

完了条件:

- license review 結果を docs に残す。
- `vectorbt` を採用するか、temporary `uv --with` のままにするかを明記する。

2026-06-13_20:51 JST の結果:

- [VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md](VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md) を作成済み。
- `vectorbt` は採用しない。
- temporary `uv --with vectorbt` smoke と existing adapter surface に留める。
- `pyproject.toml` / `uv.lock` に `vectorbt` を追加しない。

## Phase 1: optional extra と lockfile

目的:

- `vectorbt` を標準依存ではなく optional extra として lock する。

想定変更:

- `pyproject.toml`
  - `[project.optional-dependencies]`
  - `vectorbt = ["vectorbt==1.0.0"]`
- `uv.lock`
  - optional extra 解決結果
- docs
  - `uv sync --dev --extra vectorbt` の導線

想定コマンド:

```bash
uv lock
uv sync --dev --extra vectorbt --locked
uv run --extra vectorbt python -c 'import vectorbt; print(vectorbt.__version__)'
```

受入条件:

- `uv sync --dev --locked` が通常環境で通る。
- `uv sync --dev --extra vectorbt --locked` が vectorbt 環境で通る。
- 通常環境の `strategy-backtest-pack` は `external_engine_run=false` のまま PASS する。
- vectorbt extra 環境の `strategy-backtest-external-run` は `engine_run=true` を出す。
- `pyproject.toml` と `uv.lock` の差分が `vectorbt` optional extra に限定されている。

## Phase 2: artifact boundary update

目的:

- optional extra 採用後も、標準packと外部engine結果を混同しない。

想定変更:

- `strategy_backtest_external_result.v1`
  - `framework_version`: pre-adoption surface で実装済み
  - `runner_mode`: pre-adoption surface で実装済み。現行値は `not_installed_in_current_env`, `temporary_or_optional_import`, `installed_without_runner`
  - `dependency_source`: optional extra 採用時に `temporary_uv_with` / `optional_extra` の区別として追加検討
- `strategy_backtest_pack.v1`
  - `external_framework_policy.decision`
    - `complete_with_optional_vectorbt_extra`
  - `locked_dependency_added=true`
  - `external_adapters_required_for_completion=false` は維持
- `strategy-backtest-pack-validate`
  - optional extra 採用後の policy を検査

受入条件:

- 通常pack validation と vectorbt extra validation が別々に読める。
- `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` が全artifactで維持される。
- schema tests が policy 変更を検査する。

## Phase 3: vectorbt runner hardening

目的:

- 現在の最小 `Portfolio.from_signals` 呼び出しを、比較に耐える runner にする。

想定変更:

- Polars/parquet から pandas/index への変換を明示関数に分離する。
- symbol / timestamp alignment の検査を追加する。
- long / short / exit signal の対応範囲を明示する。
- fees / slippage / cost drag の対応範囲を明示する。
- vectorbt result を `strategy_backtest_external_result.v1` の metrics に正規化する。

受入条件:

- vectorbt runner の unit test は fake vectorbt と optional real vectorbt smoke に分ける。
- real vectorbt smoke は optional marker または separate command にする。
- `strategy-backtest-compare` は native result と vectorbt result を同じ report で比較できる。

## Phase 4: docs and operator workflow

目的:

- 利用者が「標準BT」と「vectorbt optional comparison」を混同しないようにする。

更新対象:

- `docs/backtest/README.md`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
- `docs/strategy_research_lab/09_STRATEGY_AUTHOR_GUIDE.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`

想定コマンド:

```bash
uv run sis strategy-backtest-pack
uv run sis strategy-backtest-pack-validate
uv run --extra vectorbt sis strategy-backtest-external-run
uv run sis strategy-backtest-compare
```

## Stop Conditions

次の場合は採用を止める。

- license review で repo 利用形態に合わない。
- `uv sync --dev --extra vectorbt --locked` が CI 相当環境で安定しない。
- optional dependency が重すぎて通常開発の sync や CI を不安定にする。
- vectorbt result を source hash / no-live boundary 付き artifact に正規化できない。
- `strategy_authoring_native` と `vectorbt` の metric 差分が説明不能で、比較 report が誤解を生む。

## 実装済み順

1. license review 結果を追記する。
2. owner approval を decision record に残す。
3. `pyproject.toml` に `vectorbt` optional extra を追加する。
4. `uv.lock` を更新する。
5. `strategy-backtest-external-run` の artifact に optional extra 採用後の `dependency_source` を追加する。
6. `strategy-backtest-framework-run --framework vectorbt` で選択式 runner から実行する。
7. focused tests と `./scripts/check` を通す。

実装済みの前倒し項目:

- `strategy-backtest-external-run` の artifact に `framework_version` と `runner_mode` を追加した。
- `strategy-backtest-compare` は external result の `framework_version` と `runner_mode` を保持する。
- `vectorbt` runner logic を `src/sis/backtest/vectorbt_adapter.py` に分離した。

## 採用後も残す境界

`vectorbt` を採用しても、現行の完成線は置き換えない。`strategy_authoring_native` が標準 backtest engine であり、`vectorbt` は高速探索・比較・外部framework評価のための optional adapter である。
