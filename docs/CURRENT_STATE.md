# Current State

この文書は `marketlens-strike` の tracked docs 側の current truth を短く読むための入口です。最終的な正本はコード、設定、tests、生成 artifact です。

## 結論

- `plan/archive/PR-00_to_PR-08_implementation_plan.md` の PR-00 から PR-08 まで、コードとテストの実装は完了している。
- repo の主軸は `Trade[XYZ] / real market / tracking / venue-gated paper / micro live canary` へ移っている。
- ただし運用系 artifact chain の一部は、archive 済み `gtrade` / `ostium` read-only collector をまだ参照する。migration 完了と operational cutover 完了は同義ではない。
- 実 live order integration はまだ opt-in safety surface 止まりで、現行の public CLI surface には micro live 実行コマンドを出していない。

## Source Of Truth

優先順位:

1. `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
2. generated runtime artifacts under `data/ops/` and `data/reports/`
3. tracked docs under `docs/`
4. `plan/` historical migration contracts
5. `docs/archive/`

`docs/archive/` は historical context です。現行判断の正本にはしません。

## Implemented Surfaces

現行コードで確認できる主要 surface:

- Python 3.13 前提の runtime / lock / CI
- root CLI split: `src/sis/cli.py` は command registration と `main()` が中心で、command 実装は `src/sis/commands/` に分割済み
- legacy `gtrade` / `ostium` の archive 化
- `Trade[XYZ]` registry builder, universe report, quote collector, quote normalizer
- `real_market` feature builder と free-source quality gating
- `tracking` layer による real-market vs venue 判定
- venue quality gate 付き paper fill / fee model / paper report
- `Trade[XYZ]` micro live safety adapter / policy / canary code path
- read-only execution surfaces, operations dashboard, remediation chain, daemon loop, notification outbox

## Important Boundaries

- 新規実装の主 venue は `trade_xyz`。legacy venue は archive / read-only evidence として扱う。
- `micro_live` はコードと tests では存在するが、標準の operator CLI にはまだ exposed していない。
- `collect-trade-xyz-quotes` は public CLI command として exposed している。
- `data/` は git 管理外。再開時は artifact を再生成する。
- `ostium-python-sdk` は active dependency から削除済み。archive collector 側の optional read-only evidence としてのみ言及が残る。

## Verification Status

2026-05-26 時点で確認済み:

- `./scripts/check`: pass
- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass, 0 errors
- `uv run pytest -q`: 300 passed

PR-08 専用確認:

- `tests/test_trade_xyz_live_order_policy.py`
- `tests/test_trade_xyz_adapter_safety.py`
- `tests/test_micro_live_canary.py`

上記は `./scripts/check` に含まれる。

## What Is Still Not Proven

- 実ネットワークを使う manual live smoke
- signing / wallet / exchange write integration
- `trade_xyz` を主軸にした operations artifact chain への全面 cutover
- fresh live evidence を使った operational Go/No-Go 再判定

## Recommended Read Order

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/OPERATIONS_RUNBOOK.md`
4. `docs/ARCHITECTURE_AND_PHASES.md`
5. `plan/archive/PR-00_to_PR-08_implementation_plan.md` を historical migration contract として読む

その後、必要に応じて:

1. `data/reports/current_state_index.md`
2. `data/reports/readiness_snapshot.md`
3. `data/reports/phase_gate_review.md`
4. `data/reports/operations_dashboard.md`

artifact が古い場合:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```
