<!--
作成日: 2026-06-15_20:13 JST
更新日: 2026-06-15_20:31 JST
-->

# OSS Backtest Capability Expansion Implementation Plan

## 結論

この計画の決定事項は、外部 OSS を標準 backtest engine に置き換えないことである。

標準 engine は引き続き `strategy_authoring_native` とし、外部 OSS は次の3種類に分ける。

1. 既存 optional extras として実行するもの:
   `vectorbt`, `bt`, `empyrical-reloaded`, `quantstats`
2. dependency 追加なしで reference-only / metadata / contract を整えるもの:
   `HftBacktest`, `qstrader`, `skfolio`, `Riskfolio-Lib`, `PyBroker`, `Freqtrade`, `NautilusTrader`, `Qlib`, `FinRL`
3. 現時点では採用しないもの:
   GPL / AGPL / build failure / live surface が重い framework

この計画で最初に完了させるべき実装は、既存4 optional extras を `strategy-backtest-framework-run` / `strategy-backtest-pack` / `strategy-backtest-artifact-summary` で再現可能に扱うことと、lookahead 検査を強化することである。

`HftBacktest` は前回計画からの修正追加である。L2/L3、queue position、latency、tick replay の不足を補う候補としては強い。ただし、この repo には標準 backtest pack で使える L2/L3/tick data contract がないため、採用ではなく reference-only metadata と data readiness probe から始める。

`PyBroker` と `Riskfolio-Lib` は追加調査で補完した。`PyBroker` は ML / walk-forward / bootstrap workflow の参考候補、`Riskfolio-Lib` は portfolio optimization 参考候補である。ただし、どちらも標準 backtest engine にしない。`PyBroker` は package / license / data-source surface が重く、`Riskfolio-Lib` は backtest engine ではなく optimizer であるため、dependency 追加前の reference-only 分類に留める。

## 目的

- 現行 backtest system に、実務で意味のある外部検算・portfolio 比較・report・leakage 検査を追加する。
- 現行 artifact chain の `paper_only`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を壊さない。
- コーダーがこの文書だけで、何をどの順に実装し、どのファイルを触り、どのテストで完了判定するか分かる状態にする。
- 大型OSSの宣伝文句ではなく、現 repo の Python 3.13、uv lock、schema、CLI、生成 artifact、license risk に合わせて採用判断する。

## 制約

- 標準 engine は `strategy_authoring_native` のままにする。
- `strategy-backtest-pack` の完成線は `complete_without_locked_external_dependency` のままにする。
- `vectorbt`, `bt`, `metrics`, `reports` 以外の dependency は、この計画の必須タスクでは追加しない。
- `HftBacktest`, `qstrader`, `skfolio`, `Riskfolio-Lib`, `PyBroker`, `Freqtrade`, `NautilusTrader`, `Qlib`, `FinRL` は、最初は dependency 追加なしの reference-only / smoke / contract に閉じる。
- live order、wallet、signing、exchange write、broker credential、external API write は実装しない。
- replay-style simulation から market impact を主張しない。
- L2/L3/tick data が存在しない状態で、HFT realism を実装済み扱いしない。
- backtest pass だけで alpha、paper pass、live readiness を主張しない。
- GPL / AGPL 系 package は license review なしに `pyproject.toml` / `uv.lock` に入れない。
- `vectorbt` は owner approval 済みの base optional extra 範囲だけ使う。`vectorbt[full]`, `vectorbt[rust]`, `vectorbt[all]` はこの計画では採用しない。
- 生成 artifact は source path / source hash / dependency source / runner mode / safety boundary を残す。

## 現在確認済みの事実

- `pyproject.toml` は `vectorbt==1.0.0`, `bt==1.2.0`, `empyrical-reloaded==0.5.12`, `quantstats==0.0.81` を optional extras として固定している。
- 通常 env では `vectorbt`, `bt`, `empyrical`, `quantstats`, `qstrader`, `hftbacktest`, `skfolio`, `pybroker`, `nautilus_trader`, `freqtrade`, `qlib`, `finrl` は未インストールだった。
- `uv run --extra vectorbt sis strategy-backtest-framework-run --framework vectorbt` は `engine_run=true`, `dependency_source=optional_extra_available` で完了した。
- `uv run --extra bt sis strategy-backtest-framework-run --framework bt` は `executed_count=1` で完了した。
- `uv run --extra metrics sis strategy-backtest-framework-run --framework empyrical-reloaded` は `engine_run=true`, `metric_status=completed` で完了した。
- `uv run --extra reports sis strategy-backtest-framework-run --framework quantstats` は `engine_run=true`, `report_status=completed` で完了した。
- `strategy-backtest-framework-run --framework` は repeat option であり、複数 framework を1 manifest にまとめられる。
- `src/sis/backtest/frameworks.py` は reference-only 候補として `nautilus_trader`, `freqtrade`, `qlib`, `finrl`, `skfolio` を持つが、`hftbacktest` はまだ持たない。
- `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md` と `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md` は、HftBacktest を現時点の non-goal / future scope として扱っている。
- `schemas/strategy_backtest_adapter_spike.v1.schema.json`, `schemas/strategy_backtest_adapter_selection.v1.schema.json`, `schemas/strategy_backtest_pack.v1.schema.json`, `schemas/strategy_backtest_comparison.v1.schema.json` は `additionalProperties=false` の surface を持つ。新 field や enum を足す場合は、schema、fixture、builder、reader、consumer test を同じタスクで更新する。
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md` は、`PyBroker` を `feature_validation_runner_candidate`、`Tardis` を data provider / integration 候補、`HftBacktest` を L2 / latency / queue realism の後段候補として整理済みである。

## 追加調査で確認した外部一次情報

- `HftBacktest` は PyPI metadata で `Requires-Python >=3.11`、Python 3.11 / 3.12 / 3.13 classifier、MIT classifier を持つ。公式説明は full order book / trade tick feed data、feed/order latency、queue position を中心にしている。現 repo では L2/L3/tick/latency 入力がないため、採用ではなく readiness probe から始める。
- `PyBroker` は公式 docs で NumPy / Numba backtesting、multi-instrument rules/models、Alpaca / Yahoo Finance / AKShare / custom data source、walkforward、randomized bootstrapping、parallelized computation を掲げる。package は `lib-pybroker`、import は `pybroker`。PyPI metadata は `Free for non-commercial use (Apache License 2.0 with Commons Clause)` である。外部 data source と model training surface を標準 backtest に混ぜないため、local DataFrame input contract に閉じる。
- `Riskfolio-Lib` は PyPI metadata で `Requires-Python >=3.10`、BSD 3-clause license、Python 3.10 / 3.11 / 3.12 / 3.13 / 3.14 classifier を持つ。CVXPY と Pandas に乗る portfolio optimization library であり、backtest engine ではない。
- `qstrader` は PyPI metadata で MIT classifier と Python 3.9 / 3.10 / 3.11 / 3.12 classifier を持つが、Python 3.13 classifier はない。schedule-driven equities / ETF framework として local input contract を先に定義する。
- `Tardis` は data provider / integration 候補であり、OSS backtest framework ではない。料金、ライセンス、取得条件を確認するまで標準入力にしない。
- `backtesting.py` は AGPL risk があるため、この計画では optional dependency にしない。

## ランキングと採用区分

| Rank | 区分 | 対象 | 決定 | 理由 |
|---:|---|---|---|---|
| 1 | 必須 | no-live / native-primary contract | 維持 | ここを崩すと既存 lifecycle / paper boundary が壊れる。 |
| 2 | 必須 | `vectorbt` | 既存 optional extra を太くする | signal runner / parameter sweep 検算に最も近い。既に lock 済み。 |
| 3 | 必須 | `bt` | 既存 optional extra を太くする | portfolio allocation / rebalance comparison の最短経路。既に lock 済み。 |
| 4 | 必須 | `empyrical-reloaded` | 既存 optional extra を太くする | metrics normalization の外部検算。既に lock 済み。 |
| 5 | 必須 | `quantstats` | 既存 optional extra を太くする | report / tear sheet の外部出力。既に lock 済み。 |
| 6 | 必須 | lookahead 検査 | repo 内実装を強化 | 高機能 engine より leakage 防止の方が先。Freqtrade は思想だけ参照。 |
| 7 | 推奨 | `HftBacktest` | reference-only + data readiness probe | L2/L3、latency、queue position の不足に最も刺さる。ただし data contract が先。 |
| 8 | 推奨 | `qstrader` | isolated runner contract | schedule-driven equities / ETF には合うが、Python 3.13 classifier 不足と input contract 未設計がある。 |
| 9 | 推奨 | `skfolio` | portfolio validation reference | backtest engine ではない。portfolio CV / stress-test artifact 候補。 |
| 10 | 推奨 | `Riskfolio-Lib` | portfolio optimization reference | Python 3.13 classifier と BSD signal は良いが、optimizer であり engine ではない。 |
| 11 | 推奨 | `PyBroker` | local input contract | walk-forward / bootstrap / ML風候補検証は有用。ただし Commons Clause / external data source / dependency load が重い。 |
| 12 | オプション | `NautilusTrader` | architecture reference | 強力だが統合が重い。標準 engine にしない。 |
| 13 | オプション | `LEAN` | external sandbox only | C# core / 別 platform 色が強く、Python 3.13 repo 内統合に向かない。 |
| 14 | オプション | `Qlib`, `FinRL` | research sandbox only | ML / DRL platform で、Strategy Lab と責務が重なる。 |
| 15 | オプション | `backtesting.py`, `backtrader`, Zipline 系 | 原則 defer | license / build / live surface / maintenance risk が大きい。 |
| 16 | オプション | `Tardis` | data vendor / integration candidate | backtest framework ではない。料金・ライセンス・取得条件の確認が先。 |

## 対象ファイル

必須タスクで変更する可能性が高いファイル:

- `src/sis/backtest/framework_run.py`
- `src/sis/backtest/pack.py`
- `src/sis/backtest/pack_runner.py`
- `src/sis/backtest/pack_contract.py`
- `src/sis/backtest/artifact_summary.py`
- `src/sis/backtest/artifact_summary_registry.py`
- `src/sis/backtest/compare.py`
- `src/sis/backtest/no_lookahead.py`
- `src/sis/backtest/frameworks.py`
- `src/sis/backtest/adapter_spike.py`
- `src/sis/backtest/adapter_selection.py`
- `src/sis/backtest/adapter_contract.py`
- `src/sis/commands/strategy_authoring.py`
- `schemas/strategy_backtest_framework_run.v1.schema.json`
- `schemas/strategy_backtest_pack.v1.schema.json`
- `schemas/strategy_backtest_comparison.v1.schema.json`
- `schemas/strategy_backtest_no_lookahead_diff.v1.schema.json`
- `schemas/strategy_backtest_adapter_spike.v1.schema.json`
- `schemas/strategy_backtest_adapter_selection.v1.schema.json`
- `tests/strategy_authoring/test_backtest_framework_run.py`
- `tests/strategy_authoring/test_cli_bundle.py`
- `tests/strategy_authoring/test_backtest_compare.py`
- `tests/strategy_authoring/test_backtest_no_lookahead.py`
- `tests/strategy_authoring/test_backtest_adapter_spike.py`
- `tests/strategy_authoring/test_backtest_adapter_selection.py`
- `tests/backtest/test_pack_contract.py`
- `tests/backtest/test_pack_runner.py`
- `tests/backtest/test_pack_validation_rules.py`
- `tests/backtest/test_artifact_summary_registry.py`
- `docs/backtest/README.md`
- `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`

必要になるまで変更しないファイル:

- `pyproject.toml`
- `uv.lock`

`pyproject.toml` / `uv.lock` は、既存4 extras 以外の package を正式 optional extra にすると決めた時だけ変更する。`HftBacktest`, `qstrader`, `skfolio`, `Riskfolio-Lib`, `PyBroker` の初期タスクでは変更しない。

## 実装タスク

### OBF0: Baseline と開始条件を固定する

goal:
現行 artifact と optional extra の実行状態を、変更前の基準として記録する。

target_files:

- 変更なし

out_of_scope:

- コード変更
- schema 変更
- dependency 追加

acceptance:

- `git status --short --branch --untracked-files=all` が開始時点で確認されている。
- 通常 env の `strategy-backtest-artifact-summary` が `pack_validation.decision=PASS` を返す。
- 通常 env の `strategy-backtest-framework-run --framework vectorbt` が `executed_count=0` になることを確認する。これは失敗ではなく、通常 env に optional extra がないことの確認である。
- `--extra vectorbt`, `--extra bt`, `--extra metrics`, `--extra reports` で個別 runner が `engine_run=true` になることを確認する。

verification:

```bash
git status --short --branch --untracked-files=all
uv run sis strategy-backtest-artifact-summary
uv run sis strategy-backtest-framework-run --framework vectorbt
uv run --extra vectorbt sis strategy-backtest-framework-run --framework vectorbt
uv run --extra bt sis strategy-backtest-framework-run --framework bt
uv run --extra metrics sis strategy-backtest-framework-run --framework empyrical-reloaded
uv run --extra reports sis strategy-backtest-framework-run --framework quantstats
```

destructive_level:
read-only except generated ignored artifacts under `data/`.

### OBF1: Optional Framework Run Matrix を安定化する

goal:
既存4 optional extras を、1 command で再現可能な matrix artifact として扱えるようにする。

target_files:

- `src/sis/backtest/framework_run.py`
- `schemas/strategy_backtest_framework_run.v1.schema.json`
- `tests/strategy_authoring/test_backtest_framework_run.py`
- `src/sis/commands/strategy_authoring.py`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`

out_of_scope:

- 新 dependency 追加
- `vectorbt[full]`, `vectorbt[rust]`, `vectorbt[all]`
- live / wallet / exchange write

acceptance:

- `strategy-backtest-framework-run` が次の repeat option を1回で受け取れる。
  - `--framework vectorbt`
  - `--framework bt`
  - `--framework empyrical-reloaded`
  - `--framework quantstats`
- manifest の `summary.framework_count=4`。
- extras 付き環境では `summary.executed_count=4`。
- 通常 env では4件すべて `skipped/not_installed_in_current_env` になり、exit 0 で artifact を残す。
- 各 run は `dependency_added=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を持つ。
- child artifact path が framework ごとに分かれ、後続 run で別 framework の child artifact を壊さない。
- CLI help に repeat option であることが表示される。

verification:

```bash
uv run pytest -q tests/strategy_authoring/test_backtest_framework_run.py
uv run sis strategy-backtest-framework-run --framework vectorbt --framework bt --framework empyrical-reloaded --framework quantstats
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-framework-run --framework vectorbt --framework bt --framework empyrical-reloaded --framework quantstats
jq '.summary, [.runs[] | {framework_id, run_status, dependency_source, boundary}]' data/research/backtest_framework_run/strategy_backtest_framework_run.json
```

destructive_level:
low. Generated `data/research/backtest_framework_run/*` and reports only.

### OBF2: Framework Run Matrix を pack / comparison / summary に取り込む

goal:
optional framework run の結果を、pack と artifact summary から一貫して読めるようにする。

target_files:

- `src/sis/backtest/pack.py`
- `src/sis/backtest/pack_runner.py`
- `src/sis/backtest/pack_contract.py`
- `src/sis/backtest/compare.py`
- `src/sis/backtest/artifact_summary.py`
- `src/sis/backtest/artifact_summary_registry.py`
- `schemas/strategy_backtest_pack.v1.schema.json`
- `schemas/strategy_backtest_comparison.v1.schema.json`
- `tests/backtest/test_pack_contract.py`
- `tests/backtest/test_pack_runner.py`
- `tests/backtest/test_pack_validation_rules.py`
- `tests/backtest/test_artifact_summary_registry.py`
- `tests/strategy_authoring/test_backtest_compare.py`
- `tests/strategy_authoring/test_cli_bundle.py`

out_of_scope:

- optional framework を pack 完了の必須条件にすること
- `pack_validation` を optional extra 未実行で fail させること
- native metrics を external result で上書きすること

acceptance:

- `strategy-backtest-pack` は通常 env では framework run matrix を `skipped` として取り込める。
- extras 環境では framework run matrix を `executed_count=4` として取り込める。
- `strategy_backtest_pack.v1` に `framework_run` artifact row を追加する場合、既存 pack consumer を壊さない optional field にする。
- `strategy_backtest_comparison.v1` に `framework_run` summary を追加する場合、既存 `external_results`, `portfolio_comparison`, `metric_extension`, `report_extension` は維持する。
- `additionalProperties=false` の schema に field を足す場合は、schema property、fixture、builder output、reader、comparison test を同じ task で更新する。
- `framework_run` は required field にしない。欠損時は `exists=false` と null summary で表現し、既存 artifact を読み続けられるようにする。
- `strategy-backtest-artifact-summary` は `framework_run.exists`, `framework_run.summary.executed_count`, `framework_run.runs[*].dependency_source`, `framework_run.runs[*].boundary` を返す。
- `pack_validation` は framework run が欠損しても fail しない。ただし存在する場合は source hash と no-live boundary を検査する。

verification:

```bash
uv run pytest -q tests/backtest/test_pack_contract.py tests/backtest/test_pack_runner.py tests/backtest/test_pack_validation_rules.py tests/backtest/test_artifact_summary_registry.py
uv run pytest -q tests/strategy_authoring/test_backtest_compare.py tests/strategy_authoring/test_cli_bundle.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-pack-validate
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-artifact-summary
```

destructive_level:
low. Runtime artifacts under ignored `data/`; schema changes are additive only.

### OBF3: Lookahead / leakage 検査を実務レベルに近づける

goal:
外部 engine を増やす前に、feature leakage と signal replay の検査を強化する。

target_files:

- `src/sis/backtest/no_lookahead.py`
- `schemas/strategy_backtest_no_lookahead_diff.v1.schema.json`
- `tests/strategy_authoring/test_backtest_no_lookahead.py`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`

out_of_scope:

- Freqtrade 本体の dependency 追加
- arbitrary Python strategy static analysis
- ML training pipeline の leakage 検査

acceptance:

- no-lookahead artifact に `checked_signal_count`, `verified_signal_count`, `unverified_signal_count`, `false_negative_risk` を追加する。
- signal が少ない場合、`status=pass` だけでなく `coverage_status=insufficient_signal_coverage` を記録する。
- future mutation replay が not applicable の場合、理由を machine-readable に残す。
- cutoff 以前の signal / executed rows が変わった場合は fail closed になる。
- 既存小規模 fixture は壊さず、coverage warning として扱う。

verification:

```bash
uv run pytest -q tests/strategy_authoring/test_backtest_no_lookahead.py
uv run sis strategy-backtest-no-lookahead-diff
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
```

destructive_level:
low. Generated no-lookahead artifacts only.

### OBF4: HftBacktest を reference-only 候補に追加する

goal:
L2/L3、queue position、latency、tick replay の将来候補として `HftBacktest` を metadata に載せる。ただし dependency 追加も engine 実行もしない。

target_files:

- `src/sis/backtest/frameworks.py`
- `src/sis/backtest/adapter_spike.py`
- `schemas/strategy_backtest_adapter_spike.v1.schema.json`
- `tests/strategy_authoring/test_backtest_adapter_spike.py`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`
- `docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md`
- `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md`

out_of_scope:

- `hftbacktest` dependency 追加
- L2/L3 data collector
- Rust live bot
- market impact claim

acceptance:

- `strategy-backtest-adapter-spike` の candidates に `hftbacktest` が `candidate_kind=reference_only` として出る。
- reference-only candidate count のテスト期待値は、現行5件から `hftbacktest` 追加後の6件へ更新する。
- `engine_run=false`, `dependency_added=false`, `permits_live_order=false`, `wallet_used=false` を維持する。
- `adapter_role` は `reference_only_microstructure_replay` のように、L2/L3 / latency / queue に限定する。
- `adoption_note` または `risk_notes` に、Python 3.13 classifier / MIT classifier は良い signal だが、L2/L3/tick data、feed latency、order latency、queue model input が必要であることを残す。
- docs は `HftBacktest` を「採用済み」ではなく「data contract が揃った後の reference-only 候補」と表現する。

verification:

```bash
uv run pytest -q tests/strategy_authoring/test_backtest_adapter_spike.py
uv run sis strategy-backtest-adapter-spike
jq '[.candidates[] | select(.framework_id=="hftbacktest")]' data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json
uv run python scripts/check_current_docs.py
```

destructive_level:
low. Code metadata and docs only.

### OBF5: HftBacktest data readiness probe を作る

goal:
`HftBacktest` を使う前に、現 repo の data artifacts が L2/L3/tick replay に足りるかを判定する。

target_files:

- `src/sis/backtest/microstructure_readiness.py`
- `src/sis/commands/strategy_authoring.py`
- `schemas/strategy_backtest_microstructure_readiness.v1.schema.json`
- `tests/backtest/test_microstructure_readiness.py`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`

out_of_scope:

- `hftbacktest` import
- L2/L3 replay execution
- tick data download
- venue collector implementation

acceptance:

- 新 command は、現行 quotes / signals / data availability artifact を読み、L2/L3/tick replay に必要な項目を `available`, `missing`, `not_applicable` に分類する。
- 現行 baseline data では `decision=NOT_READY_FOR_HFT_REPLAY` になる。
- `missing_requirements` に少なくとも order book depth / trade ticks / order latency / feed latency / queue model input の欠損が出る。
- `market_impact_supported=false` を明示する。market replay readiness と market impact は別物として扱う。
- output は source path / source hash / schema version / no-live boundary を持つ。
- `decision=READY_FOR_HFT_REPLAY_SPIKE` になるのは、必要 field がすべて揃った fixture を test で用意した場合だけ。
- normal `strategy-backtest-pack-validate` は microstructure readiness が `NOT_READY_FOR_HFT_REPLAY` でも fail しない。これは high-frequency replay の未準備であって、通常 pack の破損ではない。

verification:

```bash
uv run pytest -q tests/backtest/test_microstructure_readiness.py
uv run sis strategy-backtest-microstructure-readiness
uv run python scripts/check_current_docs.py
```

destructive_level:
low. New read-only artifact only.

### OBF6: qstrader isolated runner contract を作る

goal:
`qstrader` を dependency に入れる前に、Strategy Authoring output から qstrader に渡す local input contract を定義する。

target_files:

- `src/sis/backtest/qstrader_contract.py`
- `src/sis/commands/strategy_authoring.py`
- `schemas/strategy_backtest_qstrader_contract.v1.schema.json`
- `tests/backtest/test_qstrader_contract.py`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`

out_of_scope:

- `qstrader` dependency 追加
- qstrader engine execution
- external Yahoo download

acceptance:

- contract artifact は `universe`, `alpha_model_input`, `risk_model_input`, `data_handler_input`, `rebalance_cadence`, `fee_model`, `source_signals_hash`, `source_quotes_hash` を持つ。
- 現行 artifact から作れない項目は `missing` として列挙し、runner 実行可能と誤読させない。
- `qstrader` の Python 3.13 classifier 不足を `risk_notes` に残す。
- dependency_added / engine_run / permits_live_order / wallet_used / exchange_write_used はすべて false。

verification:

```bash
uv run pytest -q tests/backtest/test_qstrader_contract.py
uv run sis strategy-backtest-qstrader-contract
uv run python scripts/check_current_docs.py
```

destructive_level:
low. New read-only artifact only.

### OBF7: portfolio validation contract を作る

goal:
`skfolio` と `Riskfolio-Lib` を backtest engine と誤認せず、portfolio validation / cross-validation / stress-test / optimization の候補として contract 化する。

target_files:

- `src/sis/backtest/portfolio_validation_contract.py`
- `src/sis/commands/strategy_authoring.py`
- `schemas/strategy_backtest_portfolio_validation_contract.v1.schema.json`
- `tests/backtest/test_portfolio_validation_contract.py`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`

out_of_scope:

- `skfolio` dependency 追加
- `riskfolio-lib` dependency 追加
- optimizer 実行
- Strategy Authoring allocation rule の置換

acceptance:

- contract artifact は returns matrix、asset labels、benchmark labels、rebalance frequency、CV split input、constraints input の可用性を分類する。
- 現行 baseline が単一または少数 signal で portfolio CV に不足する場合、`decision=NOT_READY_FOR_PORTFOLIO_VALIDATION_ENGINE` とする。
- `skfolio` と `Riskfolio-Lib` は `candidate_kind=portfolio_validation_reference` として扱い、`engine_run=false`, `dependency_added=false` を維持する。
- `Riskfolio-Lib` は optimizer / allocation candidate であり、native signal backtest engine ではないことを docs と artifact に残す。

verification:

```bash
uv run pytest -q tests/backtest/test_portfolio_validation_contract.py
uv run sis strategy-backtest-portfolio-validation-contract
uv run python scripts/check_current_docs.py
```

destructive_level:
low. New read-only artifact only.

### OBF8: PyBroker reference contract を作る

goal:
`PyBroker` を標準 engine にせず、local DataFrame input 専用の walk-forward / bootstrap / feature validation contract として扱う。

target_files:

- `src/sis/backtest/pybroker_contract.py`
- `src/sis/commands/strategy_authoring.py`
- `schemas/strategy_backtest_pybroker_contract.v1.schema.json`
- `tests/backtest/test_pybroker_contract.py`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`

out_of_scope:

- `lib-pybroker` dependency 追加
- PyBroker engine execution
- Alpaca / Yahoo Finance / AKShare / other external data fetch
- model training 実行
- PyBroker bootstrap 結果による alpha / paper / live readiness claim

acceptance:

- contract artifact は local DataFrame input、feature availability timestamp、walk-forward split、bootstrap settings、model input、source hash の可用性を分類する。
- `external_data_source_allowed=false`, `dependency_added=false`, `engine_run=false`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を持つ。
- feature に `available_at` 相当の point-in-time provenance がない場合は fail closed で、`decision=NOT_READY_FOR_PYBROKER_REFERENCE_RUN` とする。
- `PyBroker` の package 名 `lib-pybroker`、import 名 `pybroker`、Commons Clause / non-commercial classifier risk、外部 data source risk を docs と artifact に残す。
- local DataFrame input contract が作れる fixture だけ `decision=READY_FOR_PYBROKER_CONTRACT_SPIKE` になる。

verification:

```bash
uv run pytest -q tests/backtest/test_pybroker_contract.py
uv run sis strategy-backtest-pybroker-contract
uv run python scripts/check_current_docs.py
```

destructive_level:
low. New read-only artifact only.

### OBF9: Operator docs と current docs を更新する

goal:
実装後に operator が、通常 env、optional extras env、reference-only候補、non-goals を誤読しないようにする。

target_files:

- `docs/backtest/README.md`
- `docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`
- `docs/backtest/BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md`
- `docs/backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md`

out_of_scope:

- historical archive docs の全面更新
- marketing-style overview

acceptance:

- README からこの計画へリンクされている。
- docs は `採用済み optional extra`, `reference-only`, `future scope`, `non-goal` を分けている。
- `HftBacktest` は採用済みではなく、microstructure data readiness 後の候補として書かれている。
- `PyBroker` は local input / feature validation reference、`Riskfolio-Lib` は portfolio optimization reference、`Tardis` は data provider / integration candidate として分けている。
- `pack validation PASS` が alpha / paper pass / live readiness ではないことを明記する。
- すべての編集 docs に Tokyo time metadata がある。

verification:

```bash
uv run python scripts/check_current_docs.py
```

destructive_level:
docs-only.

### OBF10: Final Gate

goal:
全タスク後に、通常 env と optional extras env の両方で backtest chain が壊れていないことを確認する。

target_files:

- 変更なし

out_of_scope:

- live / wallet / exchange write
- external API fetch

acceptance:

- 通常 env で pack validation が PASS。
- optional extras env で framework run matrix が `executed_count=4`。
- reference-only artifacts は engine_run=false / dependency_added=false を維持。
- current docs check が通る。
- focused tests と full gate が通る。

verification:

```bash
uv run pytest -q tests/backtest tests/strategy_authoring
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-framework-run --framework vectorbt --framework bt --framework empyrical-reloaded --framework quantstats
uv run python scripts/check_current_docs.py
./scripts/check
```

destructive_level:
low. Generated ignored artifacts and normal verification only.

## 実装順

1. OBF0
2. OBF1
3. OBF2
4. OBF3
5. OBF4
6. OBF5
7. OBF6
8. OBF7
9. OBF8
10. OBF9
11. OBF10

OBF1 から OBF3 が必須完了範囲である。OBF4 から OBF8 は推奨範囲で、dependency 追加なしの設計・readiness・contract までを完了線にする。OBF10 はどの範囲で止めても最後に実行する。

## 完了条件

この計画全体の完了条件:

- 既存4 optional extras の framework run matrix が通常 env と extras env の両方で説明可能になっている。
- pack / comparison / artifact summary が optional framework run matrix を読める。
- no-lookahead artifact が signal coverage と false-negative risk を明示している。
- `HftBacktest` が reference-only 候補として artifact に出るが、dependency 追加や engine 実行はしていない。
- HFT replay readiness が、現行 baseline data では不足と判定される。
- `qstrader`, `skfolio`, `Riskfolio-Lib`, `PyBroker` は、dependency 追加前の contract artifact まで進み、engine 実行可能と誤読されない。
- docs が `採用済み`, `reference-only`, `future scope`, `non-goal` を分けている。
- `uv run pytest -q tests/backtest tests/strategy_authoring` と `uv run python scripts/check_current_docs.py` が通る。
- 可能なら `./scripts/check` が通る。

## 抜け・漏れ・誤謬リスク

- `HftBacktest` は package metadata 上は有望だが、現 repo に L2/L3/tick data がなければ実用価値は出ない。OBF5 で readiness を先に判定する。
- `qstrader` は MIT で schedule-driven equities / ETF に合うが、Python 3.13 classifier がない。local import smoke 成功だけで採用判断しない。
- `skfolio` は backtest engine ではない。portfolio optimizer / validation としてのみ扱う。
- `Riskfolio-Lib` は BSD signal と Python 3.13 classifier が良いが、CVXPY / Pandas に乗る portfolio optimization library であり、signal execution engine ではない。dependency 化する場合も solver / transitive dependency / CI load を別途確認する。
- `PyBroker` は walk-forward / bootstrap が魅力的だが、Commons Clause / non-commercial classifier と Alpaca / Yahoo Finance / AKShare などの data source surface がある。local input only と source hash を強制しない限り、この repo の no-external-fetch 境界を壊しやすい。
- `Tardis` は historical market data / integration 候補であって、backtest framework ではない。data vendor を OSS runner と同じ採用表に混ぜない。
- `NautilusTrader` は高機能だが、現 repo の Strategy Authoring YAML からの変換設計が大きすぎる。reference architecture 以上に進めない。
- `Qlib` / `FinRL` は研究 platform であり、現 repo の Strategy Lab と責務が重なる。標準 backtest enhancement として扱わない。
- `vectorbt` は Commons Clause 付きである。base optional extra 以外に広げる場合は再承認が必要。
- optional extras env で作った artifact は、通常 env の pack run で上書きされる可能性がある。OBF2 で pack / summary の読み方を明確にする。
- generated artifact の PASS を、alpha / paper pass / live readiness と誤読しない。

## Sources

External primary sources checked on 2026-06-15:

- `HftBacktest` PyPI: https://pypi.org/project/hftbacktest/
- `PyBroker` docs: https://www.pybroker.com/en/latest/
- `lib-pybroker` PyPI: https://pypi.org/project/lib-pybroker/
- `Riskfolio-Lib` PyPI: https://pypi.org/project/riskfolio-lib/
- `qstrader` PyPI: https://pypi.org/project/qstrader/

Repo sources checked:

- `pyproject.toml`
- `schemas/strategy_backtest_adapter_spike.v1.schema.json`
- `schemas/strategy_backtest_adapter_selection.v1.schema.json`
- `schemas/strategy_backtest_pack.v1.schema.json`
- `schemas/strategy_backtest_comparison.v1.schema.json`
- `docs/backtest/CURRENT_BACKTEST_PLAN_AND_FRAMEWORK_ROLES_2026-06-14.md`
