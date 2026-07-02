<!--
作成日: 2026-07-02_20:55 JST
更新日: 2026-07-02_20:55 JST
-->

# T8 Implementation Plan

## 結論

T8では `virtual_execution_gate.v1` を生成するfixture-only Virtual Execution Gateを追加する。demo/testnet network modeは実装せず、order lifecycleとflat reconciliationの検査結果をlocal artifactとして保存する。virtual passはactual cash passに変換しない。

## チェックポイントID

CP7 / PR #17 T8

## 目的

actual cash前に、注文preview、accept/reject reason、partial fill、cancel、reduce-only close、flat reconciliation、fee/funding-like fields、duplicate order防止をfixtureで検査し、失敗時はvirtual gateで止める。

## 現状

- CP1で `VirtualExecutionGate` model/schemaは追加済み。
- `edge_candidate_factory` CLIには build と backtest kill gate がある。
- Virtual gateのruntime moduleと public command は未実装。

## 制約

- v0はfixture modeだけにする。
- Bitget demo network、Hyperliquid testnet、GRVT testnetは実装しない。
- wallet、signing、production exchange write、live order、paper executionは使わない。
- virtual PnLやvirtual lifecycleをactual cash evidenceにしない。
- 既存 `virtual_execution_gate.v1` schema/modelに合わせる。

## 対象ファイル

新規:

- `docs/plans/2026-07-02-profit-core-smart-priors/11_T8_IMPLEMENTATION_PLAN.md`
- `src/sis/edge_candidate_factory/virtual_execution_gate.py`
- `tests/edge_candidate_factory/test_virtual_execution_gate.py`

変更:

- `src/sis/commands/edge_candidate_factory.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `tests/edge_candidate_factory/test_cli.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `build_virtual_execution_gate()` は fixture inputs から `VirtualExecutionGate` を返す。
2. required condition idは `VIRTUAL_EXECUTION_GATE_REQUIRED_CONDITION_IDS` を満たす。
3. source不足は `VIRTUAL_BLOCKED_SOURCE`、execution precheck不足は `VIRTUAL_BLOCKED_EXECUTION_PRECHECK`。
4. order lifecycle failureは `VIRTUAL_FAILED_ORDER_LIFECYCLE`。
5. flat reconciliation mismatchは `VIRTUAL_FAILED_RECONCILIATION`。
6. 全条件passでも `actual_cash=false`、`cash_metric_basis=virtual_exchange`、`permits_live_order=false` を固定する。
7. public command `edge-candidate-virtual-execution-gate` はfixture-only optionでJSON artifactを書き、stdoutに安全境界を出す。

## 実装手順

1. RED: `test_virtual_execution_gate.py` と CLI help/write testを追加する。
2. GREEN: `virtual_execution_gate.py` を追加する。
3. GREEN: CLI commandとcatalogを追加する。
4. VERIFY: focused tests、schema validation、CLI catalog、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_virtual_execution_gate.py tests/edge_candidate_factory/test_cli.py -q
uv run pytest tests/edge_candidate_factory -q
uv run sis edge-candidate-virtual-execution-gate --help
uv run python scripts/check_cli_catalog.py
uv run ruff check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py tests/edge_candidate_factory
uv run ruff format --check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py tests/edge_candidate_factory
uv run pyrefly check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py
uv run ty check src/sis/edge_candidate_factory src/sis/commands/edge_candidate_factory.py --python-version 3.13 --output-format concise
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## 完了条件

- virtual passがactual cash passにならない。
- fixture modeでorder lifecycleの正常系と異常系が検証される。
- reconciliation mismatchは `VIRTUAL_FAILED_RECONCILIATION` になる。
- CLI stdoutに `production_exchange_write_used=false`, `live_order_submitted=false` が出る。
- artifactが `virtual_execution_gate.v1` schemaに適合する。

## 失敗条件

- demo/testnet network modeをv0に混ぜる。
- `exchange_write_used=true` をfixtureで許す。
- virtual gateをactual cash、paper/live、profit proofとして扱う。
- required condition idを欠いた artifact を書く。

## 影響範囲

edge_candidate_factoryのVirtual Execution Gate module、既存command moduleへのcommand追加、CLI catalog、testsのみ。

## ロールバック方針

T8追加module/tests、command registration、CLI catalog行、plan docを戻す。

## 代替案

- 代替案A: Bitget demo modeを同時実装する。ネットワーク、認証、外部副作用の境界が増えるためT8 v0では不採用。
- 代替案B: `virtual_execution_gate.v1` をdocs-onlyで終える。runtime artifactが無くT8完了条件を満たさない。
- 採用案: deterministic fixture-only gateを先に実装する。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- fixture passはexecution lifecycleの形だけを検査する。実測fillやactual cashではないため、`known_gaps` にactual cash未確認を残す。
- conditionをboolean summaryだけにするとschema契約を満たしてもreview不能になる。各conditionに observed/required/source_ref を入れる。
- reconciliation mismatchはorder lifecycle failureより後段のhard failureとして分ける。

## 批判レビュー2

- stdout safety fieldsが無いとCLI利用者がactual/live readinessを誤読する。既存 `_echo_safe_stdout_prefix()` を使う。
- demo/testnetは明示opt-in以前にvenue moduleが必要になるため、T8からは除外する。
- `VIRTUAL_PASSED_EXECUTION_LIFECYCLE` はactual cash passではない。artifact boundaryとstdoutで二重に false を出す。
