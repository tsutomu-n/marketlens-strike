<!--
作成日: 2026-06-14_21:49 JST
更新日: 2026-06-14_21:49 JST
-->

# Backtest Maintainability Responsibility Plan

## 目的

既存の backtest system の機能を増やさず、責務を分けて保守とカスタマイズをしやすくする。

この計画は、次を完了させるための実装契約である。

- `strategy-backtest-pack` の orchestration を CLI 関数から分離する。
- artifact I/O、source hash、paper-only boundary、Markdown report、pack artifact key、validation rule、summary extraction を共通部品へ寄せる。
- 既存 CLI、schema、artifact、pack validation の挙動を維持する。
- 将来、baseline、data availability、report、optional framework surface を追加するときに、既存の builder を直接コピーしなくてよい構造にする。

## 確認済みの現状

2026-06-14_21:49 JST 時点で確認した事実:

- `git status --short --branch --untracked-files=all` は `## main...origin/main`。
- `src/sis/backtest/` の Python ファイル合計は `14039` 行。
- `src/sis/backtest/compare.py` は `1367` 行、`src/sis/backtest/pack.py` は `370` 行、`src/sis/commands/strategy_authoring.py` の `strategy-backtest-pack` command は信号生成から pack validation までを直列実行している。
- backtest 系 schema は `schemas/backtest_data_availability_ledger.v1.schema.json` と `schemas/strategy_backtest*.schema.json` を合わせて `25` 本ある。
- `src/sis/backtest/*` の複数 module が `_sha256_file`, `_read_json`, `_write_report`, `json.dumps(...).write_text(...)`, paper-only boundary fields を個別に持っている。
- `tests/strategy_authoring/test_cli_bundle.py` は `strategy-backtest-pack` の end-to-end artifact 生成、pack validation、artifact summary を検査している。

この計画は上記の確認済み事実に基づく。外部 OSS の最新仕様、外部 API、未実装 venue、live execution は扱わない。

## 制約

- live order、wallet、signing、exchange write を追加しない。
- Bitget / Hyperliquid direct schema widening、Coinalyze collector、venue-specific execution model を追加しない。
- no-lookahead の signal / quote mutation 拡張、execution simulation の cancel race / modify 拡張、trial ledger の粒度拡張、buy-and-hold / funding carry 実計算追加はこの計画の対象外。
- `vectorbt`, `bt`, `metrics`, `reports` 以外の dependency を追加しない。
- `strategy-backtest-pack`, `strategy-backtest-pack-validate`, `strategy-backtest-artifact-summary` の CLI 名と既定 path を変えない。
- 既存 schema version を変更しない。必要な field 追加がある場合は optional field に限定し、既存 artifact consumer を壊さない。
- 生成 artifact の `paper_only=true`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。
- 1 task につき、挙動変更を最小にし、対応する focused test を先に更新または追加する。

## 責務分離の決定

| 責務 | 現在の代表箇所 | 分離後の置き場 |
|---|---|---|
| JSON 読み書き、sha256、artifact row | 各 builder の `_read_json`, `_sha256_file`, `_artifact_row` | `src/sis/backtest/artifact_io.py` |
| paper-only / no-live boundary field | 各 payload に個別記述 | `src/sis/backtest/boundary.py` |
| Markdown report 組み立て | 各 builder の `_write_report` | `src/sis/backtest/reporting.py` |
| pack artifact key と default path | `strategy_authoring.py`, `pack.py`, tests に分散 | `src/sis/backtest/pack_contract.py` |
| pack orchestration | `strategy_authoring.py` の `strategy_backtest_pack_cmd` | `src/sis/backtest/pack_runner.py` |
| pack validation checks | `pack.py` の `validate_strategy_backtest_pack` 内部 | `src/sis/backtest/pack_validation.py` |
| artifact summary extraction | `artifact_summary.py` の個別関数群 | `src/sis/backtest/artifact_summary_registry.py` |
| CLI path resolution と echo | `strategy_authoring.py` | CLI wrapper に残す |

## 対象ファイル

新規作成:

- `src/sis/backtest/artifact_io.py`
- `src/sis/backtest/boundary.py`
- `src/sis/backtest/reporting.py`
- `src/sis/backtest/pack_contract.py`
- `src/sis/backtest/pack_runner.py`
- `src/sis/backtest/pack_validation.py`
- `src/sis/backtest/artifact_summary_registry.py`
- `tests/backtest/test_artifact_io.py`
- `tests/backtest/test_backtest_boundary.py`
- `tests/backtest/test_pack_contract.py`
- `tests/backtest/test_pack_runner.py`
- `tests/backtest/test_pack_validation_rules.py`
- `tests/backtest/test_artifact_summary_registry.py`

変更対象:

- `src/sis/commands/strategy_authoring.py`
- `src/sis/backtest/pack.py`
- `src/sis/backtest/artifact_summary.py`
- `src/sis/backtest/data_availability.py`
- `src/sis/backtest/baselines.py`
- `src/sis/backtest/no_lookahead.py`
- `src/sis/backtest/execution_simulation.py`
- `src/sis/backtest/assumptions.py`
- `src/sis/backtest/trial_ledger.py`
- `src/sis/backtest/stress.py`
- `src/sis/backtest/regime_split.py`
- `src/sis/backtest/rolling_stability.py`
- `src/sis/backtest/benchmark_relative.py`
- `src/sis/backtest/metric_extension.py`
- `src/sis/backtest/report_extension.py`
- `src/sis/backtest/portfolio_comparison.py`
- `src/sis/backtest/external.py`
- `src/sis/backtest/framework_run.py`
- `tests/backtest/test_completion_artifacts.py`
- `tests/strategy_authoring/test_cli_bundle.py`
- `docs/backtest/README.md`

schema は原則変更しない。schema 変更が必要になった場合だけ、対象 schema と対応 test を task 内に明記してから行う。

## 実装タスク

### R0: Baseline Snapshot を固定する

目的:
現行挙動を、責務分離前の比較基準として固定する。

対象ファイル:

- 変更なし

手順:

1. `uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv` を実行する。
2. `uv run sis strategy-backtest-pack-validate` を実行する。
3. `uv run sis strategy-backtest-artifact-summary` を実行し、次を記録する。
   - `pack_validation.decision`
   - `pack_validation.failed_count`
   - `data_availability.status`
   - `baseline_comparison.status`
   - `no_lookahead_diff.status`
   - `execution_simulation.status`
   - `trial_ledger.status`
   - `assumption_ledger.status`
4. `./scripts/check` を実行する。

完了条件:

- `pack_validation.decision=PASS`
- `pack_validation.failed_count=0`
- `./scripts/check` が通る
- 実装差分なし

### R1: Artifact I/O を共通化する

目的:
JSON 読み書き、sha256、artifact row、atomic ではない通常 artifact write を一箇所に集める。

対象ファイル:

- 新規: `src/sis/backtest/artifact_io.py`
- 新規: `tests/backtest/test_artifact_io.py`
- 変更: `src/sis/backtest/pack.py`
- 変更: `src/sis/backtest/artifact_summary.py`

実装内容:

1. `artifact_io.py` に次を実装する。
   - `sha256_file(path: Path) -> str`
   - `read_json_object(path: Path) -> dict[str, Any]`
   - `write_json_object(path: Path, payload: dict[str, Any]) -> Path`
   - `artifact_row(path: Path) -> dict[str, Any]`
   - `json_artifact_payload(path: Path) -> dict[str, Any] | None`
2. `pack.py` と `artifact_summary.py` から同等の private helper を置き換える。
3. 置き換え後も JSON の `ensure_ascii=False`, `indent=2`, `sort_keys=True`, 末尾 newline を維持する。

テスト:

```bash
uv run pytest tests/backtest/test_artifact_io.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
```

完了条件:

- artifact hash check が pack validation で通る。
- `strategy_backtest_pack.v1` と `strategy_backtest_pack_validation.v1` が schema-valid のまま。

### R2: Paper-only Boundary を共通化する

目的:
全 artifact の no-live 境界 field を共通定義にする。

対象ファイル:

- 新規: `src/sis/backtest/boundary.py`
- 新規: `tests/backtest/test_backtest_boundary.py`
- 変更: completion artifact builders と robustness artifact builders

実装内容:

1. `boundary.py` に次を実装する。
   - `BACKTEST_PAPER_ONLY_BOUNDARY: dict[str, bool]`
   - `with_backtest_boundary(payload: dict[str, Any]) -> dict[str, Any]`
   - `assert_backtest_boundary(payload: dict[str, Any]) -> None`
2. `BACKTEST_PAPER_ONLY_BOUNDARY` は次を固定する。
   - `paper_only: True`
   - `live_order_submitted: False`
   - `permits_live_order: False`
   - `live_conversion_allowed: False`
   - `wallet_used: False`
   - `exchange_write_used: False`
3. 各 builder の payload 作成時に `with_backtest_boundary` を使う。
4. `pack.py` の validation は既存 field の検査を維持する。

テスト:

```bash
uv run pytest tests/backtest/test_backtest_boundary.py tests/backtest/test_completion_artifacts.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
```

完了条件:

- completion artifact すべてで boundary field が変わらない。
- `strategy-backtest-pack-validate` が `decision=PASS`。

### R3: Markdown Report の最小共通 builder を追加する

目的:
各 module の `_write_report` が同じ mkdir/write_text パターンを持つ状態を減らす。

対象ファイル:

- 新規: `src/sis/backtest/reporting.py`
- 変更: `src/sis/backtest/data_availability.py`
- 変更: `src/sis/backtest/baselines.py`
- 変更: `src/sis/backtest/execution_simulation.py`
- 変更: `src/sis/backtest/assumptions.py`
- 変更: `src/sis/backtest/trial_ledger.py`

実装内容:

1. `reporting.py` に次を実装する。
   - `write_markdown_report(path: Path, lines: Iterable[str]) -> Path`
   - `bool_line(label: str, value: bool) -> str`
   - `kv_line(label: str, value: Any) -> str`
2. 初回は completion artifact 系だけ置き換える。
3. report の内容と path は変えない。

テスト:

```bash
uv run pytest tests/backtest/test_completion_artifacts.py
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
```

完了条件:

- `data/reports/*completion*` 相当の report が引き続き生成される。
- pack validation が PASS。

### R4: Pack Contract を作る

目的:
pack artifact key、default output path、external framework policy を一箇所で管理する。

対象ファイル:

- 新規: `src/sis/backtest/pack_contract.py`
- 新規: `tests/backtest/test_pack_contract.py`
- 変更: `src/sis/backtest/pack.py`
- 変更: `src/sis/commands/strategy_authoring.py`
- 変更: `tests/strategy_authoring/test_cli_bundle.py`

実装内容:

1. `pack_contract.py` に次を実装する。
   - `BacktestArtifactKey` または string 定数群
   - `PACK_COMPLETION_ARTIFACT_KEYS`
   - `PACK_REQUIRED_SUITE_METHODS`
   - `external_framework_policy() -> dict[str, Any]`
   - `default_pack_artifact_paths(data_dir: Path) -> dict[str, Path]`
2. `pack.py` の `_external_framework_policy` と required key list を移す。
3. `strategy_authoring.py` の pack command で artifact key を定数参照にする。
4. tests の期待値も `pack_contract.py` の policy と一致することを検査する。

テスト:

```bash
uv run pytest tests/backtest/test_pack_contract.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
```

完了条件:

- `external_framework_policy` の JSON 値が現行 artifact と一致する。
- completion artifact key の欠落検査が従来どおり動く。

### R5: Pack Runner を CLI から分離する

目的:
`strategy_authoring.py` の `strategy-backtest-pack` command を path 解決と echo に限定し、pack orchestration を backtest module へ移す。

対象ファイル:

- 新規: `src/sis/backtest/pack_runner.py`
- 新規: `tests/backtest/test_pack_runner.py`
- 変更: `src/sis/commands/strategy_authoring.py`
- 変更: `tests/strategy_authoring/test_cli_bundle.py`

実装内容:

1. `pack_runner.py` に dataclass を作る。
   - `StrategyBacktestPackRunInputs`
   - `StrategyBacktestPackRunResult`
2. `run_strategy_backtest_pack(inputs: StrategyBacktestPackRunInputs) -> StrategyBacktestPackRunResult` を実装する。
3. 現行 CLI 内の実行順序をそのまま移す。
4. CLI command は次だけを行う。
   - path resolve
   - spec/suite/bundle path を inputs へ渡す
   - result path を echo
   - validation decision が PASS でなければ exit 2
5. この task では artifact の中身を変えない。

テスト:

```bash
uv run pytest tests/backtest/test_pack_runner.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
```

完了条件:

- `strategy-backtest-pack` の stdout key が変わらない。
- `strategy-backtest-pack` で生成される artifact set が変わらない。
- `strategy-backtest-pack-validate` が PASS。

### R6: Pack Validation Rule を分離する

目的:
pack validation の check list を追加・削除しやすい形にする。

対象ファイル:

- 新規: `src/sis/backtest/pack_validation.py`
- 新規: `tests/backtest/test_pack_validation_rules.py`
- 変更: `src/sis/backtest/pack.py`
- 変更: `tests/strategy_authoring/test_backtest_pack_validation.py`
- 変更: `tests/strategy_authoring/test_cli_bundle.py`

実装内容:

1. `pack_validation.py` に次を実装する。
   - `PackValidationFinding`
   - `PackValidationContext`
   - rule 関数群
   - `run_pack_validation_rules(context) -> list[dict[str, Any]]`
2. `pack.py` の `validate_strategy_backtest_pack` は payload read/write と report write を担当し、finding 生成は `pack_validation.py` に委譲する。
3. check id は既存値を維持する。

テスト:

```bash
uv run pytest tests/backtest/test_pack_validation_rules.py tests/strategy_authoring/test_backtest_pack_validation.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
```

完了条件:

- `pack_validation.summary.check_count` が不用意に変わらない。変わる場合は、増減した check id と理由を test 名または assertion で明示する。
- 既存の `completion_artifacts_present` check が残る。

### R7: Artifact Summary Registry を導入する

目的:
artifact summary の追加時に、巨大な `build_strategy_backtest_artifact_summary` へ直接分岐を増やさない。

対象ファイル:

- 新規: `src/sis/backtest/artifact_summary_registry.py`
- 新規: `tests/backtest/test_artifact_summary_registry.py`
- 変更: `src/sis/backtest/artifact_summary.py`
- 変更: `tests/strategy_authoring/test_cli_bundle.py`

実装内容:

1. `artifact_summary_registry.py` に次を実装する。
   - `ArtifactSummarySpec`
   - `ARTIFACT_SUMMARY_SPECS`
   - `summarize_artifact(path: Path, spec: ArtifactSummarySpec) -> dict[str, Any]`
2. 既存の `_summarize_*` 関数は移動または registry から参照する。
3. `build_strategy_backtest_artifact_summary` は registry を順に評価する。
4. stdout JSON の top-level key は変えない。

テスト:

```bash
uv run pytest tests/backtest/test_artifact_summary_registry.py tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain
```

完了条件:

- `uv run sis strategy-backtest-artifact-summary` の top-level key が現行と一致する。
- 欠損 artifact は引き続き `exists=false` を返す。

### R8: Builder Modules の最小整理を行う

目的:
R1-R7 で作った共通部品を、completion artifact 以外の主要 builder に広げる。

対象ファイル:

- `src/sis/backtest/stress.py`
- `src/sis/backtest/regime_split.py`
- `src/sis/backtest/rolling_stability.py`
- `src/sis/backtest/benchmark_relative.py`
- `src/sis/backtest/metric_extension.py`
- `src/sis/backtest/report_extension.py`
- `src/sis/backtest/portfolio_comparison.py`
- `src/sis/backtest/external.py`
- `src/sis/backtest/framework_run.py`

実装内容:

1. JSON I/O と boundary field を共通 helper に置き換える。
2. report write を `reporting.py` に置き換える。
3. 各 module の public dataclass と public builder 関数名は変えない。
4. optional dependency の import behavior は変えない。

テスト:

```bash
uv run pytest tests/strategy_authoring/test_backtest_external.py tests/strategy_authoring/test_backtest_framework_run.py tests/strategy_authoring/test_backtest_portfolio_comparison.py tests/strategy_authoring/test_backtest_metric_extension.py tests/strategy_authoring/test_backtest_report_extension.py tests/strategy_authoring/test_backtest_stress.py tests/strategy_authoring/test_backtest_regime_split.py tests/strategy_authoring/test_backtest_rolling_stability.py tests/strategy_authoring/test_backtest_benchmark_relative.py
```

完了条件:

- optional framework が未インストールの通常環境で、skipped artifact が従来どおり生成される。
- no-live boundary がすべて維持される。

### R9: Docs と Operator Entry を更新する

目的:
責務分離後の読み方を docs に反映する。

対象ファイル:

- `docs/backtest/README.md`
- `docs/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md`

実装内容:

1. README にこの計画へのリンクを追加する。
2. 実装完了後、計画 doc の task status を更新する。
3. 既存 completion / future scope docs の意味を変えない。

テスト:

```bash
uv run python scripts/check_current_docs.py
```

完了条件:

- current docs checker が通る。
- README からこの計画へ到達できる。

### R10: Final Gate を実行する

目的:
責務分離が挙動変更を起こしていないことを確認する。

対象ファイル:

- 変更なし

手順:

```bash
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
uv run python scripts/check_current_docs.py
./scripts/check
```

完了条件:

- `strategy-backtest-pack-validate` が `decision=PASS`
- `strategy-backtest-artifact-summary` で completion artifact がすべて `exists=true`
- `./scripts/check` が通る
- `git diff --stat` が責務分離対象に限定される

## テスト方針

テストは task ごとに最小から広げる。

1. 新規 helper は `tests/backtest/` に direct unit test を追加する。
2. 既存 CLI の挙動は `tests/strategy_authoring/test_cli_bundle.py::test_strategy_backtest_pack_runs_standard_backtest_artifact_chain` で固定する。
3. optional dependency surface は実 import を必須にせず、既存 fake / skipped behavior を維持する。
4. schema validation は既存 schema を使う。schema version を上げない。
5. 最後に `./scripts/check` を必ず実行する。

## 完了条件

この計画全体は、次をすべて満たした時に完了とする。

- `strategy_authoring.py` の `strategy-backtest-pack` command が orchestration 本体を持たず、`pack_runner.py` を呼ぶ wrapper になっている。
- artifact I/O、boundary、reporting、pack contract、pack validation rule、artifact summary registry が独立 module になっている。
- public CLI 名、既定 path、schema version、artifact top-level key が維持されている。
- `strategy-backtest-pack-validate` が `decision=PASS`。
- `strategy-backtest-artifact-summary` が pack、pack validation、completion artifact、robustness artifact、comparison を表示する。
- `./scripts/check` が通る。
- docs current checker が通る。

## 抜け・漏れ・誤謬リスク対策

| リスク | 対策 |
|---|---|
| 共通化で artifact JSON の field order / formatting が変わる | `write_json_object` の formatting を固定し、pack validation と schema validation を必ず通す |
| CLI stdout key が変わる | `test_cli_bundle.py` の stdout assertion を維持する |
| validation check id が変わる | R6 では check id 維持を acceptance にする |
| optional dependency の skipped behavior が壊れる | R8 で optional framework tests をまとめて実行する |
| report path が変わる | 各 result dataclass の `report_path` assertion を残す |
| docs が実装より先に完成扱いになる | R9 は R1-R8 後に status 更新する |
| 強化タスクが混入する | no-lookahead 拡張、execution realism、trial ledger 粒度拡張、buy-and-hold / funding carry 実計算は別計画に分離する |

## 実装順序

実装順序は固定する。

1. R0
2. R1
3. R2
4. R3
5. R4
6. R5
7. R6
8. R7
9. R8
10. R9
11. R10

R5 より前に pack runner を作らない。R1-R4 の共通部品なしに orchestration を動かすと、移動後の差分が大きくなるためである。
