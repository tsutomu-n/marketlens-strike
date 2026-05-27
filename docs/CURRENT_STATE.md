# Current State

この文書は `marketlens-strike` の tracked docs 側の current truth を短く読むための入口です。最終的な正本はコード、設定、tests、生成 artifact です。

## 結論

- `plan/archive/PR-00_to_PR-08_implementation_plan.md` の PR-00 から PR-08 まで、コードとテストの実装は完了している。
- repo の主軸は `Trade[XYZ] / real market / tracking / venue-gated paper / micro live canary` へ移っている。
- PR9a-PR12 の read-only smoke まで完了しており、最新 phase gate は `READ_ONLY_GO`。
- `gtrade` / `ostium` の legacy source, sidecar, raw data, registry, 専用テストは ZIP 化済みで、展開済み file tree は active repo から削除済み。
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
- legacy `gtrade` / `ostium` の ZIP archive 化と active file tree からの削除
- `Trade[XYZ]` registry builder, universe report, quote collector, quote normalizer
- `Trade[XYZ]` `perpDexs` fallback による HIP-3 `asset_id` 解決
- `Trade[XYZ]` quote collection summary / report / strict artifact validation
- `Trade[XYZ]` diagnostics / strict validation / phase gate cutover for read-only PR12
- `real_market` feature builder と free-source quality gating
- `tracking` layer による real-market vs venue 判定
- venue quality gate 付き paper fill / fee model / paper report
- `Trade[XYZ]` micro live safety adapter / policy / canary code path
- read-only execution surfaces, operations dashboard, remediation chain, daemon loop, notification outbox

## Important Boundaries

- 新規実装の主 venue は `trade_xyz`。legacy venue は `archive/gtrade_ostium_legacy_archive_*.zip` 内の履歴参照として扱う。
- `micro_live` はコードと tests では存在するが、標準の operator CLI にはまだ exposed していない。
- `collect-trade-xyz-quotes` は public CLI command として exposed している。
- `data/` は git 管理外。再開時は artifact を再生成する。
- `ostium-python-sdk` は active dependency から削除済み。

## Verification Status

2026-05-27 時点で確認済み:

- `./scripts/check`: pass
- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass, 0 errors
- `uv run pytest -q`: 275 passed
- targeted PR9a-PR12 verification: `19 passed`
- `uv run sis validate-artifacts --strict`: `checked_files=11`, `issues=0`
- latest PR12 smoke: `310` raw rows, `3673.995702` observed seconds, 5 symbols x 62 rows
- latest `uv run sis phase-gate-review`: `READ_ONLY_GO`, `next_actions=[]`

PR-08 専用確認:

- `tests/test_trade_xyz_live_order_policy.py`
- `tests/test_trade_xyz_adapter_safety.py`
- `tests/test_micro_live_canary.py`

上記は `./scripts/check` に含まれる。

## What Is Still Not Proven

- production live order smoke
- signing / wallet / exchange write integration
- `bot_decision.json` / live order preview の正式 command surface
- `check-go-no-go` / `build-evidence-card` は補助reportであり、Bot前の現行判定正本は `phase-gate-review`

## Recommended Read Order

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/OPERATIONS_RUNBOOK.md`
4. `docs/ARCHITECTURE_AND_PHASES.md`
5. `docs/trade_xyz_bot_beginner_guide.html`
6. `plan/archive/PR-00_to_PR-08_implementation_plan.md` を historical migration contract として読む

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
