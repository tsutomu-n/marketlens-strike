# Current State

この文書は `marketlens-strike` の tracked docs 側の current truth を短く読むための入口です。最終的な正本はコード、設定、tests、生成 artifact です。

## 結論

- `plan/archive/PR-00_to_PR-08_implementation_plan.md` の PR-00 から PR-08 まで、コードとテストの実装は完了している。
- repo の主軸は `Trade[XYZ] / real market / tracking / venue-gated paper / micro live canary` へ移っている。
- PR9a-PR12 の read-only smoke と P2 gate restore まで完了しており、最新 phase gate は `READ_ONLY_GO`。
- Trade[XYZ] の対象銘柄は fee mode / taker fee / maker fee を registry と raw quote row に持つ。`fee_mode_unknown_rate` は current gate blocker ではない。
- Strategy Research Lab の schema / model / CLI surface は実装済み。`StrategyExperimentSpec` から `PaperIntentPreview` までを研究、候補生成、評価、paper昇格判断として扱う。
- `gtrade` / `ostium` の legacy source, sidecar, raw data, registry, 専用テストは ZIP 化済みで、展開済み file tree は active repo から削除済み。
- 実 live order integration はまだ opt-in safety surface 止まりで、現行の public CLI surface には micro live 実行コマンドを出していない。execution drift は live-readiness blocker として残る。

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
- `Trade[XYZ]` fee mode resolution through `configs/fee_model.trade_xyz.yaml`, registry rows, raw quote rows, diagnostics, and phase gate
- `bot-preview` による read-only HOLD decision / orders preview artifact 生成
- `real_market` feature builder、Alpaca provider、free-source quality gating
- `tracking` layer による real-market vs venue 判定
- venue quality gate 付き paper fill / fee model / paper report
- `Trade[XYZ]` micro live safety adapter / policy / canary code path
- read-only execution surfaces, operations dashboard, remediation chain, daemon loop, notification outbox
- Strategy Research Lab models and commands: `StrategyExperimentSpec`, `StrategySignalRecord`, `EvaluationPlan`, `TrialRecord`, `TradeCandidate`, `PaperCandidatePack`, `PromotionDecision`, `PaperIntentPreview`
- Strategy Lab JSON schema files under `schemas/`; full runtime validation is in `src/sis/research/strategy_lab/` and `src/sis/research_protocol/`

## Important Boundaries

- 新規実装の主 venue は `trade_xyz`。legacy venue は `archive/gtrade_ostium_legacy_archive_*.zip` 内の履歴参照として扱う。
- `micro_live` はコードと tests では存在するが、標準の operator CLI にはまだ exposed していない。
- `collect-trade-xyz-quotes` は public CLI command として exposed している。
- `data/` は git 管理外。再開時は artifact を再生成する。
- `bot-preview` の `data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` は実行時生成 artifact。現 checkout に無い場合は `uv run sis bot-preview` で再生成する。
- Strategy Lab の canonical signal artifact は `data/research/strategy_signals.parquet`。旧 `data/research/signals.csv` は Strategy Lab 正本ではなく legacy export として読む。
- `PaperIntentPreview` は paper-only の仮注文意図。`live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` を守り、live order として扱わない。
- Alpaca live fetch は credentials が必要。credentials なしでは明示的に unavailable として失敗するため、silent empty data と混同しない。
- `ostium-python-sdk` は active dependency から削除済み。

## Verification Status

2026-05-28 時点で確認済み:

- `./scripts/check`: pass
- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass, 0 errors
- `uv run pytest -q`: 294 passed
- P2 targeted verification: Trade[XYZ] / diagnostics / phase gate / Alpaca / tracking tests pass
- `uv run sis validate-artifacts --strict`: `checked_files=12`, `issues=0`
- latest PR12 smoke: `310` raw rows, `3673.995702` observed seconds, 5 symbols x 62 rows
- latest current quote collection summary: `11` Trade[XYZ] active rows in `data/raw/quotes/trade_xyz/2026-05-28.jsonl`
- latest `uv run sis phase-gate-review`: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`, `next_actions=[]`
- latest diagnostics show Trade[XYZ] `fee_mode_unknown_rate=0.0` for `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT`
- latest phase gate can be `READ_ONLY_GO` while execution lineage remains degraded. Current classification is `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6`; read-only/paper readiness and live execution readiness are separate surfaces.
- latest phase gate remediation order is `none` when only live-readiness blockers remain. Do not run `refresh-operations-artifacts` as a P2 remediation loop for those blockers.

PR-08 専用確認:

- `tests/test_trade_xyz_live_order_policy.py`
- `tests/test_trade_xyz_adapter_safety.py`
- `tests/test_micro_live_canary.py`

上記は `./scripts/check` に含まれる。

## What Is Still Not Proven

- production live order smoke
- signing / wallet / exchange write integration
- live order preview / 注文候補生成の正式 command surface
- Alpaca credentials ありの API connectivity smoke。historical IEX bar で `provider_connectivity_status=pass`, `data_availability_status=pass` は確認済み。fresh 15m は `BLOCK_ALPACA_NO_BARS` で blocked になり得るため、live `status=pass` は市場時間中の fresh bar 取得で再確認する
- `check-go-no-go` / `build-evidence-card` は補助reportであり、Bot前の現行判定正本は `phase-gate-review`

## Recommended Read Order

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/DOCUMENT_AUDIT_2026-05-30.md`
4. `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
5. `docs/strategy_research_lab/README.md`
6. `docs/strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md`
7. `docs/OPERATIONS_RUNBOOK.md`
8. `docs/ARCHITECTURE_AND_PHASES.md`
9. `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md`
10. `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md`
11. `docs/trade_xyz_bot_beginner_guide.html`
12. `plan/archive/PR-00_to_PR-08_implementation_plan.md` を historical migration contract として読む

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
uv run sis bot-preview
```
