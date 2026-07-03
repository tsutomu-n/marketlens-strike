<!--
作成日: 2026-06-27_11:32 JST
更新日: 2026-07-03_13:03 JST
-->

# Final Summary

## Latest Addendum: Directional Shortlist Policy

Completed on branch `ai/profit-core-reality-check-impl-20260703-1157`.

Achieved:

- Updated `crypto-perp-risk-taker` shortlist policy so only `side_bias=long|short` candidates can be shortlisted for the C9 v0 directional authoring bridge path.
- Kept non-directional candidates in candidate inventory and search ledger as `REJECTED`; no candidate is silently dropped.
- Did not convert `both` or `no_trade` into an order direction.
- Regenerated BTCUSDT C9 dogfood candidate/bridge/reality-check artifacts under `data/profit_core_reality_check/dogfood/c9-directional-shortlist/`.

Dogfood facts:

- Candidate generation: 11 total, 5 shortlisted, 6 rejected.
- Non-directional rejected before shortlist: reversal `both`, basis `both`, liquidity `no_trade`, open-interest/liquidation `both`.
- C9 bridge: 4 `BRIDGED`, 1 `BLOCKED_MISSING_SOURCE_COLUMNS`.
- Reality check: `next_single_blocker_to_fix=MISSING_SOURCE_COLUMNS_DOMINATES`.
- Permission boundary remains false: no credentials, exchange write, production exchange write, live order, or live permission.

Verification:

- `uv run pytest tests/strategy_idea_candidates/test_perp_profile.py -q` -> 3 passed.
- `uv run python scripts/check_current_docs.py` -> checked 199 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2866 passed`.

Remaining work:

- `liquidation_notional` source support is still absent.
- `docs/action-required.md` records `AR-2026-07-03-002` for choosing a real liquidation notional source or keeping reversal-after-liquidation blocked.
- Profit-readiness still stops at missing real event / matured outcome / actual cash source.

Destructive change:

No.

Dependency change:

No.

Rollback:

Revert the `generator.py` shortlist policy change, focused test, and docs updates.

## Latest Addendum: Source Blocker Priority

Completed on branch `ai/profit-core-reality-check-impl-20260703-1157`.

Achieved:

- Added `NO_SYMBOL_DATA_DOMINATES` and `MISSING_SOURCE_COLUMNS_DOMINATES` to `profit-core-reality-check` deterministic next-blocker priority.
- Added focused tests proving source blockers rank before `BRIDGED_TECHNICAL_ONLY`.
- Updated the Reality Check pipeline trace priority list to match code.
- Re-ran the C9 dogfood reality check after RC2. Current result still chooses `UNSUPPORTED_SIDE_BIAS_DOMINATES` first, but now shows `MISSING_SOURCE_COLUMNS_DOMINATES` as the second top blocker instead of hiding it behind technical bridge status.

Verification:

- `uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q` -> 7 passed.
- Dogfood `profit-core-reality-check` -> `next_single_blocker_to_fix=UNSUPPORTED_SIDE_BIAS_DOMINATES`; top blockers include `MISSING_SOURCE_COLUMNS_DOMINATES`.
- `uv run python scripts/check_current_docs.py` -> checked 198 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2865 passed`.

Remaining work:

- `side_bias=both` behavior is still undefined and remains the current first blocker.
- Explicit liquidation source support is still absent.

Destructive change:

No.

Dependency change:

No.

Rollback:

Revert the `NEXT_BLOCKER_PRIORITY` additions, focused tests, and pipeline trace update.

## Latest Addendum: C9 Reversal Family Fail-Closed

Completed on branch `ai/profit-core-reality-check-impl-20260703-1157`.

Achieved:

- Added fail-closed C9 bridge recognition for `perp_reversal_after_liquidation_move`.
- Kept bridgeable family scope unchanged: only `perp_momentum_continuation` and `perp_funding_rate_carry_filter` generate Strategy Authoring spec / suite / bundle / backtest pack.
- Changed reversal blockers from generic `BLOCKED_UNSUPPORTED_FAMILY_MAPPING` to precise blockers:
  - `side_bias=both` -> `BLOCKED_UNSUPPORTED_SIDE_BIAS`
  - directional reversal without liquidation source -> `BLOCKED_MISSING_SOURCE_COLUMNS`
- Documented that reversal is recognized only as a blocker path until explicit `liquidation_notional` source support exists.
- Updated Reality Check plan docs so future `UNSUPPORTED_FAMILY_DOMINATES` work is driven by actual `blocked_by_family` counts, not the stale `perp_basis_mark_index_spread` first-candidate note.

Dogfood facts:

- Existing BTCUSDT C9 dogfood bridge after the change: 3 `BRIDGED`, 1 `BLOCKED_UNSUPPORTED_SIDE_BIAS`, 1 `BLOCKED_MISSING_SOURCE_COLUMNS`.
- `profit-core-reality-check` now returns `next_single_blocker_to_fix=UNSUPPORTED_SIDE_BIAS_DOMINATES`.
- `UNSUPPORTED_FAMILY_DOMINATES` is no longer the next blocker for this dogfood slice.
- This is not profit evidence and not a live/paper permission improvement.

Generated runtime artifacts:

- `data/profit_core_reality_check/dogfood/c9-reversal-fail-closed/authoring_bridge/strategy_idea_candidate_authoring_bridge_manifest.json`
- `data/profit_core_reality_check/dogfood/c9-reversal-fail-closed/summary/profit_core_reality_check.json`
- `data/profit_core_reality_check/dogfood/c9-reversal-fail-closed/summary/profit_core_reality_check.md`

Verification:

- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q` -> 7 passed.
- `strategy-idea-candidates-authoring-bridge` dogfood stdout -> `status=pass`, `bridged_count=3`, `blocked_count=2`.
- `profit-core-reality-check` dogfood stdout -> `status=blocked`, `next_single_blocker_to_fix=UNSUPPORTED_SIDE_BIAS_DOMINATES`.
- `uv run python scripts/check_current_docs.py` -> checked 197 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2863 passed`.

Remaining work:

- Define how C9 should represent `side_bias=both` without inventing orders.
- Add an explicit liquidation source adapter before any reversal candidate can be `BRIDGED`.
- Profit-readiness still stops at missing real event / matured outcome / actual cash source.

User decisions required:

None for this fail-closed correction.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the reversal-specific blocker mapping, focused test, and docs update.

## Latest Addendum: Profit Core Reality Check Dogfood

Completed on branch `ai/profit-core-reality-check-impl-20260703-1157`.

Achieved:

- Ran `profit-core-reality-check` against existing C9 BTCUSDT real-data artifacts under `data/strategy_idea_candidates/c9-btcusdt-realdata-20260628T045945Z/`.
- Built a local `crypto-perp-profit-readiness-inventory` artifact from `data/crypto_perp`; it correctly stopped at `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Confirmed the reality check result is `status=blocked` with `next_single_blocker_to_fix=UNSUPPORTED_FAMILY_DOMINATES`.
- Fixed `blocker_summary.top_blockers` to sort by the same priority as `next_single_blocker_to_fix`, so the report does not visually over-prioritize later actual-cash blockers when counts tie.

Dogfood facts:

- Candidate generation: 11 total, 5 shortlisted, 6 rejected.
- C9 bridge: 3 `BRIDGED`, 2 `BLOCKED_UNSUPPORTED_FAMILY_MAPPING`.
- Blocked family: `perp_reversal_after_liquidation_move` with 2 blocked candidates.
- Profit readiness: no real event, no matured outcome, no cash ledger, no source availability, no actual-cash rows.
- Permission boundary: network, credentials, exchange write, production exchange write, live order, and live permission all false.

Generated runtime artifacts:

- `data/profit_core_reality_check/dogfood/c9-btcusdt-realdata-20260628T045945Z/profit_readiness_inventory/inventory.json`
- `data/profit_core_reality_check/dogfood/c9-btcusdt-realdata-20260628T045945Z/summary/profit_core_reality_check.json`
- `data/profit_core_reality_check/dogfood/c9-btcusdt-realdata-20260628T045945Z/summary/profit_core_reality_check.md`

Verification:

- `uv run pytest tests/profit_core_reality_check -q` -> 5 passed.
- Reality check dogfood stdout -> `status=blocked`, `next_single_blocker_to_fix=UNSUPPORTED_FAMILY_DOMINATES`.
- `profit_core_reality_check.json` schema validation -> passed.
- `git diff --check` -> passed.

Remaining work:

- Next PR should fix exactly one C9 bridge blocker: add support for `perp_reversal_after_liquidation_move`, or explicitly reject it earlier if that family is not worth supporting.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the `top_blockers` ordering change and the focused test assertion.

## Latest Addendum: Profit Core Reality Check

Completed on branch `ai/profit-core-reality-check-impl-20260703-1157`.

Achieved:

- Added `profit-core-reality-check` as a read-only local CLI over existing candidate, search ledger, C9 bridge, profit-readiness, risk review, and actual-cash artifacts.
- Added `profit_core_reality_check.v1` JSON schema, Pydantic model, Markdown report, and focused tests.
- Preserved permission boundaries: no network, credentials, exchange write, production exchange write, live order, demo/testnet lifecycle, actual-cash fabrication, or missing-artifact generation.
- Removed the unrelated `.serena/project.yml` final-state change from the implementation result.

Main files changed:

- `src/sis/profit_core_reality_check/`
- `src/sis/commands/profit_core_reality_check.py`
- `src/sis/cli.py`
- `schemas/profit_core_reality_check.v1.schema.json`
- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/CURRENT_STATE.md`

Verification:

- `uv run pytest tests/profit_core_reality_check -q` -> 5 passed.
- `uv run sis profit-core-reality-check --help` -> help rendered.
- `uv run python scripts/check_cli_catalog.py` -> checked 232 public CLI commands.
- `uv run python scripts/check_current_docs.py` -> checked 196 current docs.
- `git diff --check` -> passed.
- `./scripts/check` -> passed, including `2862 passed`.

Remaining work:

- PR #18 is still open as a stale docs-only branch even though GitHub `main` now points at the implemented reality-check state.

User decisions required:

- Decide whether to close or retarget stale PR #18 after reviewing GitHub branch state.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the `profit-core-reality-check` CLI registration, `src/sis/profit_core_reality_check/`, the schema, focused tests, and the current-doc/catalog updates.

## Latest Addendum: Full Check Green CP3

Completed on branch `ai/risk-taker-review-artifact-20260628-1721`.

Achieved:

- Fixed the remaining pyrefly blocker after CP2 by annotating `prompt_hash_by_candidate_id` as `dict[str, str | None]`.
- Fixed the CP1 risk-taker command registration test to use `support.cli.normalized_stdout` instead of raw `result.stdout`.
- Preserved AI import ledger behavior and CLI registration behavior.
- Full `./scripts/check` is green.
- Left pre-existing untracked `codex_diag.sh` untouched.

Main files changed:

- `src/sis/strategy_idea_candidates/ai.py`
- `tests/crypto_perp/test_risk_taker_review_command_registration.py`
- `docs/plans/pyrefly-prompt-hash-type-fix-2026-06-29.md`

Verification:

- `uv run pyrefly check src/sis/strategy_idea_candidates/ai.py` -> 0 errors.
- `uv run ty check src/sis/strategy_idea_candidates/ai.py` -> passed.
- `uv run ruff check src/sis/strategy_idea_candidates/ai.py` -> passed.
- `uv run ruff format --check src/sis/strategy_idea_candidates/ai.py` -> passed.
- `uv run pytest tests/strategy_idea_candidates/test_ai_packet_import.py -q` -> 7 passed.
- `uv run pytest tests/test_cli_help_contract.py tests/crypto_perp/test_risk_taker_review_command_registration.py -q` -> 5 passed.
- `./scripts/check` -> passed, including `2857 passed`.

Remaining work:

None for the full-check cleanup.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the CP2 format-only diffs, the `ai.py` type annotation, the normalized stdout test update, and the CP2/CP3 plan/work-summary additions.

## Latest Addendum: Full Check Format Cleanup CP2

Completed the scoped format cleanup on branch `ai/risk-taker-review-artifact-20260628-1721`, but full `./scripts/check` is still not green because a later non-format pyrefly failure remains.

Achieved:

- Applied Ruff formatting to exactly the 8 files that blocked `ruff format --check`.
- Left pre-existing untracked `codex_diag.sh` untouched.
- Added CP2 work records and a plan document for this format cleanup.
- Moved `./scripts/check` past the Ruff format gate.

Main files changed:

- `src/sis/strategy_idea_candidates/authoring_preflight.py`
- `src/sis/strategy_idea_candidates/perp_bridge.py`
- `src/sis/strategy_idea_candidates/perp_costs.py`
- `src/sis/strategy_idea_candidates/prep_watchdeck_source.py`
- `src/sis/strategy_idea_candidates/selection_metrics.py`
- `src/sis/strategy_idea_candidates/splits.py`
- `tests/strategy_idea_candidates/test_candidate_cli.py`
- `tests/strategy_idea_candidates/test_metrics_costs_bridge.py`
- `docs/plans/full-check-format-cleanup-2026-06-29.md`

Verification:

- `uv run ruff format --check src/sis/strategy_idea_candidates/authoring_preflight.py src/sis/strategy_idea_candidates/perp_bridge.py src/sis/strategy_idea_candidates/perp_costs.py src/sis/strategy_idea_candidates/prep_watchdeck_source.py src/sis/strategy_idea_candidates/selection_metrics.py src/sis/strategy_idea_candidates/splits.py tests/strategy_idea_candidates/test_candidate_cli.py tests/strategy_idea_candidates/test_metrics_costs_bridge.py` -> passed.
- `uv run ruff check src/sis/strategy_idea_candidates/authoring_preflight.py src/sis/strategy_idea_candidates/perp_bridge.py src/sis/strategy_idea_candidates/perp_costs.py src/sis/strategy_idea_candidates/prep_watchdeck_source.py src/sis/strategy_idea_candidates/selection_metrics.py src/sis/strategy_idea_candidates/splits.py tests/strategy_idea_candidates/test_candidate_cli.py tests/strategy_idea_candidates/test_metrics_costs_bridge.py` -> passed.
- `./scripts/check` -> failed at `uv run pyrefly check` after passing sync, Python version, Ruff lint, Ruff format, current-docs check, and CLI catalog check.
- `git diff --check` -> passed.

Remaining work:

- Fix the non-format pyrefly type error at `src/sis/strategy_idea_candidates/ai.py:359`: `dict[str, str]` is passed where `dict[str, str | None] | None` is expected.

User decisions required:

None for the format cleanup. A separate minimal checkpoint should handle the pyrefly type fix.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the 8 format-only code diffs and remove the CP2 plan/work-summary additions.

## Latest Addendum: Crypto Perp Risk-Taker Review Artifact

Completed on branch `ai/risk-taker-review-artifact-20260628-1721`.

Achieved:

- Added `crypto-perp-risk-taker-review` as a local-only CLI over `crypto_perp_tournament_rows.v2`, `crypto_perp_source_availability.v1`, and `crypto_perp_bias_guard.v1`.
- Added `crypto_perp_risk_taker_review.v1` with jurisdiction, source freshness, source availability, NO_TRADE comparison, after-cost edge, stress edge, dollars per hour, largest loss, profit concentration, liquidation buffer, conditions, known gaps, and false-only boundary.
- Kept `crypto-perp-tournament-gate` semantics unchanged.
- Made estimate-only positive edge stop at `NEEDS_ACTUAL_CASH`, not `READY_FOR_HUMAN_RISK_REVIEW`.
- Kept network, credential, wallet, signing, exchange-write, tiny-live, and live-order permission false.

Main files changed:

- `src/sis/crypto_perp/risk_taker_review.py`
- `src/sis/commands/crypto_perp_risk_taker_review.py`
- `src/sis/commands/crypto_perp.py`
- `schemas/crypto_perp_risk_taker_review.v1.schema.json`
- `tests/crypto_perp/test_risk_taker_review.py`
- `tests/crypto_perp/test_risk_taker_review_command_registration.py`
- `docs/plans/risk-taker-review-artifact-2026-06-28.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/CURRENT_STATE.md`

Verification:

- `uv run pytest tests/crypto_perp/test_risk_taker_review.py tests/crypto_perp/test_risk_taker_review_command_registration.py tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_tournament_rows.py -q` -> 25 passed.
- `uv run sis crypto-perp-risk-taker-review --help` -> command help rendered.
- `uv run python scripts/check_cli_catalog.py` -> checked 231 public CLI commands.
- `uv run python scripts/check_current_docs.py` -> checked 180 current docs.
- `uv run ruff check src/sis/crypto_perp/risk_taker_review.py src/sis/commands/crypto_perp_risk_taker_review.py src/sis/commands/crypto_perp.py tests/crypto_perp/test_risk_taker_review.py tests/crypto_perp/test_risk_taker_review_command_registration.py` -> passed.
- `uv run ruff format --check src/sis/crypto_perp/risk_taker_review.py src/sis/commands/crypto_perp_risk_taker_review.py src/sis/commands/crypto_perp.py tests/crypto_perp/test_risk_taker_review.py tests/crypto_perp/test_risk_taker_review_command_registration.py` -> passed.
- `uv run ty check src/sis/crypto_perp/risk_taker_review.py src/sis/commands/crypto_perp_risk_taker_review.py tests/crypto_perp/test_risk_taker_review.py tests/crypto_perp/test_risk_taker_review_command_registration.py` -> passed.
- `uv run pyrefly check src/sis/crypto_perp/risk_taker_review.py src/sis/commands/crypto_perp_risk_taker_review.py tests/crypto_perp/test_risk_taker_review.py tests/crypto_perp/test_risk_taker_review_command_registration.py` -> 0 errors.
- `git diff --check` -> passed.

Remaining work:

None for this local artifact slice.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No runtime migration is required. Existing profit-readiness local outputs can be fed into the new review CLI when the required inputs exist.

Rollback:

Remove the risk-taker review model, command, schema, tests, docs plan, and CLI registration entry.

## Latest Addendum: C9 Bridge Relative Out Bug Fix

Completed on branch `ai/post-c9-bitget-source-20260628-1113`.

Achieved:

- Fixed C9 authoring bridge generation so relative `--out` paths can still produce `BRIDGED` candidates.
- Wrote absolute generated data artifact paths into the bridge-generated Strategy Authoring spec.
- Passed absolute bridge-local spec, suite, bundle, output, reports, and runtime data paths to the backtest pack runner before its repo-root `chdir`.
- Removed stale `bridge_blocker.json` from a candidate directory after that candidate successfully becomes `BRIDGED`.
- Kept public CLI, schema, manifest fields, and the general Strategy Authoring path resolver unchanged.

Main files changed:

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `tests/strategy_idea_candidates/test_authoring_bridge.py`

Verification:

- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py::test_authoring_bridge_relative_out_uses_existing_artifact_paths_and_clears_stale_blocker` -> 1 passed after the fix.
- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py` -> 6 passed.
- `uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py::test_generated_source_root_can_feed_authoring_bridge` -> 1 passed.
- `uv run ruff check src/sis/strategy_idea_candidates/authoring_bridge.py tests/strategy_idea_candidates/test_authoring_bridge.py` -> passed.
- `uv run ruff format --check src/sis/strategy_idea_candidates/authoring_bridge.py tests/strategy_idea_candidates/test_authoring_bridge.py` -> passed.

Remaining work:

None for this bug fix.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No runtime migration is required. Existing successful bridge outputs do not need regeneration unless the relative `--out` bug affected that run.

Rollback:

Revert the authoring bridge path resolution changes and the added regression test.

## Latest Addendum: C9 Bitget Public Source Refresh

Completed on branch `ai/c9-prep-watchdeck-bridge-20260628-1016`.

Achieved:

- Added `strategy-idea-candidates-bitget-source-refresh` to generate a C9 bridge compatible source root at `--out/source_root/`.
- Added repo-native Bitget public REST fetching for contracts, tickers, and paginated closed 5m history candles.
- Wrote `data/scanner.duckdb`, `data/candles_5m/date=*/candles.parquet`, `var/snapshots/latest.json`, and a refresh manifest with network / credential / exchange-write boundaries.
- Kept private API, wallet, signing, order, position, balance, websocket, deep backfill, orderbook depth, measured slippage, paper permission, and live permission out of scope.

Main files changed:

- `src/sis/strategy_idea_candidates/bitget_public_source.py`
- `src/sis/crypto_perp/bitget/public_api.py`
- `src/sis/crypto_perp/bitget/normalizers.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `tests/strategy_idea_candidates/test_bitget_public_source.py`
- `docs/plans/strategy-idea-candidates-c9-bitget-public-source-refresh-2026-06-28.md`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

Verification:

- `uv run pytest tests/strategy_idea_candidates/test_bitget_public_source.py -q` -> 5 passed.
- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py -q` -> 5 passed.
- `uv run pytest tests/strategy_idea_candidates -q` -> 54 passed.
- `uv run pytest tests/crypto_perp/test_bitget_normalizers.py tests/crypto_perp/test_bitget_client.py -q` -> 10 passed.
- `uv run sis strategy-idea-candidates-bitget-source-refresh --help` -> command help rendered.
- `uv run python scripts/check_cli_catalog.py` -> checked 230 public CLI commands.
- `uv run python scripts/check_current_docs.py` -> checked 174 current docs.
- `uv run ruff check src/sis/strategy_idea_candidates/bitget_public_source.py src/sis/crypto_perp/bitget/public_api.py src/sis/crypto_perp/bitget/normalizers.py src/sis/commands/strategy_idea_candidates.py tests/strategy_idea_candidates/test_bitget_public_source.py` -> passed.
- `uv run ruff format --check src/sis/strategy_idea_candidates/bitget_public_source.py src/sis/crypto_perp/bitget/public_api.py src/sis/crypto_perp/bitget/normalizers.py src/sis/commands/strategy_idea_candidates.py tests/strategy_idea_candidates/test_bitget_public_source.py` -> passed.
- `uv run ty check src/sis/strategy_idea_candidates/bitget_public_source.py src/sis/crypto_perp/bitget/normalizers.py src/sis/crypto_perp/bitget/public_api.py src/sis/commands/strategy_idea_candidates.py` -> passed.
- `uv run pyrefly check src/sis/strategy_idea_candidates/bitget_public_source.py src/sis/crypto_perp/bitget/normalizers.py src/sis/crypto_perp/bitget/public_api.py src/sis/commands/strategy_idea_candidates.py` -> 0 errors.
- `git diff --check` -> passed.

Remaining work:

- Real public network refresh still requires explicit `SIS_ALLOW_PUBLIC_NETWORK=1` or `--network`.
- Orderbook depth, measured slippage, actual cash proof, paper permission, and live permission remain outside this slice.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No runtime migration is required. Existing C9 authoring bridge keeps `--prep-watchdeck-root` as the compatible root input.

Rollback:

Remove the new source refresh module and tests, unregister `strategy-idea-candidates-bitget-source-refresh`, and revert the additive Bitget public API / normalizer / docs updates.

## Latest Addendum: Strategy Candidate Metrics And Perp Bridge

Completed on branch `ai/strategy-candidate-metrics-bridge-20260628-0931`.

Achieved:

- Fast-forward merged `ai/perp-hypothesis-factory-20260628-0904` into local `main`, then created `ai/strategy-candidate-metrics-bridge-20260628-0931`.
- Added a local selection-adjusted metrics engine. It emits `AVAILABLE` only when raw p-values allow Benjamini-Hochberg FDR, and `NOT_ESTIMABLE` when DSR / PBO / White Reality Check inputs are missing.
- Added local Perp cost estimate artifacts for funding, fee, slippage, stress slippage, leverage, liquidation buffer, max loss, and actual-cash absence.
- Added split materialization sidecar preserving train / validation / sealed windows and `uses_sealed_test_for_selection=false`.
- Added richer JSON / Markdown review packet with metric status, cost estimate summary, split summary, rejection reasons, and human review template.
- Added Strategy Authoring preflight artifact that records `strategy_idea.v1` export availability while keeping authoring, backtest, paper, and live readiness false.
- Added `strategy-idea-candidates-perp-estimate` to build candidate-scoped `crypto_perp_tournament_rows.v2` estimate artifacts from shortlisted Perp candidates and local outcome artifacts.
- Kept actual-cash, wallet, signing, exchange write, paper permission, and live order boundaries false.

Main files changed:

- `src/sis/strategy_idea_candidates/selection_metrics.py`
- `src/sis/strategy_idea_candidates/perp_costs.py`
- `src/sis/strategy_idea_candidates/splits.py`
- `src/sis/strategy_idea_candidates/review_packet.py`
- `src/sis/strategy_idea_candidates/authoring_preflight.py`
- `src/sis/strategy_idea_candidates/perp_bridge.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `src/sis/strategy_idea_candidates/ai.py`
- `src/sis/strategy_idea_candidates/generator.py`
- `src/sis/strategy_idea_candidates/models.py`
- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

Verification:

- `uv run pytest tests/strategy_idea_candidates tests/strategy_ai_review tests/crypto_perp -q` -> 246 passed.
- `uv run ruff check src/sis/strategy_idea_candidates src/sis/commands/strategy_idea_candidates.py tests/strategy_idea_candidates -q` -> passed.
- `uv run sis strategy-idea-candidates-perp-estimate --help` -> command help rendered.
- `uv run python scripts/check_cli_catalog.py` -> checked 228 public CLI commands.
- `uv run python scripts/check_current_docs.py` -> checked 172 current docs.
- `git diff --check` -> passed.

Remaining work:

- Full Strategy Lab / backtest bridge remains outside this slice.
- Real exchange-measured Perp funding / fee / slippage / liquidation evaluator remains outside this slice.
- DSR / PBO / White Reality Check remain `NOT_ESTIMABLE` unless future artifacts supply required return distributions, fold outcome matrices, or bootstrap-ready series.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No runtime migration is required. Fresh `strategy_idea_candidate_set.v1` artifacts may emit additive `NOT_ESTIMABLE` status.

Rollback:

Revert the strategy idea candidate metrics / Perp cost / bridge modules, unregister `strategy-idea-candidates-perp-estimate`, and revert the additive enum/doc/test changes.

## Latest Addendum: Perp Hypothesis Factory

Completed on branch `ai/perp-hypothesis-factory-20260628-0904`.

Achieved:

- Added `strategy-idea-candidates-build`, `strategy-idea-candidates-ai-packet-build`, and `strategy-idea-candidates-ai-import` public CLI surfaces.
- Added Bitget USDT-FUTURES `crypto-perp-risk-taker` generation flow with isolated margin, USDT margin coin, leverage cap 3x, funding / fee / slippage / liquidation buffer metadata, and Perp shortlist constraints.
- Added JSONL search ledger output for all candidate decisions, including rejected, cap-exceeded, duplicate, and AI-imported candidate rows.
- Added local/manual AI packet and import flow. It does not call an AI API, and imported AI candidates remain `UNVERIFIED_CANDIDATE` requiring human shortlist.
- Preserved the strict `strategy_idea.v1` boundary and existing sidecar manifest export. Candidate provenance remains outside the strategy idea draft.
- Added regression coverage that `crypto-perp-tournament-report` keeps rejecting preview / estimate rows as non-actual-cash evidence.

Main files changed:

- `src/sis/commands/strategy_idea_candidates.py`
- `src/sis/cli.py`
- `src/sis/strategy_idea_candidates/generator.py`
- `src/sis/strategy_idea_candidates/policies.py`
- `src/sis/strategy_idea_candidates/ai.py`
- `src/sis/strategy_idea_candidates/ledger.py`
- `tests/strategy_idea_candidates/`
- `tests/crypto_perp/test_tournament_rows.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

Verification:

- `uv run pytest tests/strategy_idea_candidates -q` -> 39 passed.
- `uv run pytest tests/strategy_idea_candidates tests/strategy_ai_review tests/crypto_perp -q` -> 241 passed.
- `uv run ruff check src/sis/commands/strategy_idea_candidates.py src/sis/strategy_idea_candidates tests/strategy_idea_candidates tests/crypto_perp/test_tournament_rows.py` -> passed.
- `uv run python scripts/check_current_docs.py` -> checked 171 current docs.
- `uv run python scripts/check_cli_catalog.py` -> checked 227 public CLI commands.
- `git diff --check` -> passed.

Remaining work:

- Selection-adjusted metrics engine remains unimplemented and is still recorded as `NOT_IMPLEMENTED`.
- Real Perp funding / fee / slippage / liquidation evaluator remains outside this slice.
- Strategy Lab / backtest full bridge remains outside this slice.

User decisions required:

None.

Destructive change:

No.

Dependency change:

No.

Migration:

No runtime migration is required. Existing candidate set / strategy idea schemas remain compatible.

Rollback:

Remove `src/sis/commands/strategy_idea_candidates.py`, unregister the commands from `src/sis/cli.py`, and revert the strategy idea candidate AI / ledger / Perp profile changes plus related docs and tests.

## Latest Addendum: Crypto Perp Plan Archive

Completed on branch `ai/docs-code-truth-triage-20260628-0818`.

Achieved:

- Moved Crypto Perp profit-readiness evidence plan and run plan to `docs/archive/2026-06-28-merged-plans/`.
- Updated `docs/CURRENT_STATE.md`, `docs/NEXT_DIRECTION_CURRENT.md`, `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`, and `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md` so current routing uses runbook, vocabulary, surface inventory, CLI help, schema, and tests instead of old plan docs.
- Updated docs triage and archive README with the new archive routing.

Verification:

- `uv run python scripts/check_current_docs.py` -> checked 170 current docs.
- `uv run python scripts/check_cli_catalog.py` -> checked 224 public CLI commands.
- `git diff --check` -> passed.

Remaining work:

None for the Crypto Perp plan-doc residual risk.

User decisions required:

None.

Destructive change:

No. Files were moved to archive, not deleted.

Dependency change:

No.

Migration:

No runtime migration is required.

Rollback:

Move the archived Crypto Perp plan docs back to `docs/crypto_perp/` and revert the current-routing updates.

## Latest Addendum: Strategy AI Review Plan Archive

Completed on branch `ai/docs-code-truth-triage-20260628-0818`.

Achieved:

- Moved the completed Strategy AI Review implementation plan to `docs/archive/2026-06-28-merged-plans/`.
- Updated `docs/strategy_ai_review/README.md` so the current guide points to CLI help, schema, tests, and implemented behavior instead of treating the plan as the next action.
- Updated docs triage and archive README with the new archive routing.

Verification:

- `uv run python scripts/check_current_docs.py` -> checked 172 current docs.
- `uv run python scripts/check_cli_catalog.py` -> checked 224 public CLI commands.
- `git diff --check` -> passed.

Remaining work:

- Crypto Perp plan docs still need a separate reference check before archive movement.

User decisions required:

None.

Destructive change:

No. The plan was moved to archive, not deleted.

Dependency change:

No.

Migration:

No runtime migration is required.

Rollback:

Move the archived Strategy AI Review plan back to `docs/strategy_ai_review/` and revert the README / triage / archive README updates.

## Latest Addendum: Docs Triage Cleanup

Completed on branch `ai/docs-triage-cleanup-20260628-0808`.

Achieved:

- Moved completed 2026-06-28 `docs/plans/` work plans to `docs/archive/2026-06-28-merged-plans/`.
- Updated `docs/archive/README.md` with the 2026-06-28 archived plan paths.
- Updated `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` so docs / CLI counts are confirmation-time values, not fixed current truth.
- Removed stale wording that treated `docs/plans/` as having no tracked files; it is now described as an active implementation plan staging area whose completed plans move to archive.
- Left older Crypto Perp plan docs in place because they still need a separate reference check against the current runbook and implemented surfaces.

Main files changed:

- `docs/archive/2026-06-28-merged-plans/actual-cash-semantic-repair-2026-06-28.md`
- `docs/archive/2026-06-28-merged-plans/cash-metric-legacy-migration-2026-06-28.md`
- `docs/archive/2026-06-28-merged-plans/crypto-perp-profit-readiness-local-automation-2026-06-28.md`
- `docs/archive/2026-06-28-merged-plans/docs-triage-refresh-2026-06-28.md`
- `docs/archive/2026-06-28-merged-plans/docs-triage-cleanup-2026-06-28.md`
- `docs/archive/README.md`
- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/final-summary.md`

Verification:

- `uv run python scripts/check_current_docs.py` -> checked 173 current docs.
- `uv run python scripts/check_cli_catalog.py` -> checked 224 public CLI commands.
- `git diff --check` -> passed.
- `find docs/plans -maxdepth 1 -type f -name '*.md'` -> no files printed.

Remaining work:

- Separately decide whether the older Crypto Perp plan docs under `docs/crypto_perp/` should be archived after checking their current runbook references.

User decisions required:

None.

Destructive change:

No. Files were moved to archive, not deleted.

Dependency change:

No.

Migration:

No runtime migration is required. Historical plan readers should use `docs/archive/2026-06-28-merged-plans/`.

Rollback:

Move the archived 2026-06-28 plan files back to `docs/plans/` and revert the docs wording updates from this addendum.

## Latest Addendum: Crypto Perp Profit-Readiness Local Automation

Completed on branch `ai/crypto-perp-profit-readiness-local-automation-20260628-0000`.

Achieved:

- Added local inventory and planner artifacts for Crypto Perp profit-readiness.
- Added a local chain runner that writes source availability, replay slice, feature pack, edge score, rows-v2, bias guard, and run manifest in one run directory.
- Added `crypto-perp-cash-ledger` CLI around the existing cash ledger builder.
- Added ledger plus assignment based actual-cash rows builder. Trade actions require matching ledger entries; `NO_TRADE` can be explicit cash 0.
- Added actual-cash report/gate helper, tiny-live human review packet builder, and tiny-live shadow readiness checker.
- Added schemas for inventory, plan, run, actual-cash rows summary, actual-cash report/gate run, review packet, and shadow readiness.
- Updated runbook, implemented surfaces, and CLI catalog.

Main files changed:

- `src/sis/crypto_perp/profit_readiness.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `schemas/crypto_perp_profit_readiness_inventory.v1.schema.json`
- `schemas/crypto_perp_profit_readiness_plan.v1.schema.json`
- `schemas/crypto_perp_profit_readiness_run.v1.schema.json`
- `schemas/crypto_perp_actual_cash_rows_summary.v1.schema.json`
- `schemas/crypto_perp_actual_cash_report_gate_run.v1.schema.json`
- `schemas/crypto_perp_tiny_live_review_packet.v1.schema.json`
- `schemas/crypto_perp_tiny_live_shadow_readiness.v1.schema.json`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/plans/crypto-perp-profit-readiness-local-automation-2026-06-28.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`

Verification run:

- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q`

Remaining work:

- Real event, matured outcome, and actual cash evidence collection remains outside this local automation slice.
- If current `data/crypto_perp` only contains dogfood/status/viewer artifacts, inventory and plan intentionally stop with blocker status.

User decisions required:

None for this local automation slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the new profit-readiness module, command additions, schemas, tests, and docs changes from this branch.

## Latest Addendum: PR-I1b Cash Metric Legacy Migration

Completed on branch `ai/cash-metric-legacy-migration-20260628-0721`.

Achieved:

- Added `cash_metric_value_usd` as the canonical tournament row / score comparison value.
- Kept legacy actual-cash rows readable by migrating missing `cash_metric_value_usd` from `actual_cash_result_usd` during validation.
- Made generated non-actual rows use `actual_cash_result_usd=null`.
- Moved tournament scoring and leader summaries to `cash_metric_value_usd`.
- Kept `actual_cash_result_usd` and `leader_actual_cash_result_usd` populated only for actual cash basis.
- Kept `crypto-perp-tournament-report` actual-cash-only and continued rejecting preview / non-actual rows.
- Updated v1 schemas with optional `cash_metric_value_usd` and nullable legacy actual-cash aliases.
- Updated runbook, vocabulary, implemented/current docs, Workbench README, and this summary.

Main files changed:

- `src/sis/crypto_perp/tournament.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `schemas/crypto_perp_tournament_report.v1.schema.json`
- `schemas/crypto_perp_tournament_rows_preview.v1.schema.json`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `docs/plans/cash-metric-legacy-migration-2026-06-28.md`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/final-summary.md`

Verification:

- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py`
- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_workbench_bridge.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q`

Pending final verification in this work session:

- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`

User decisions required:

None.

Destructive change:

No schema version bump and no required dependency change. Generated non-actual artifacts no longer populate `actual_cash_result_usd`; consumers should read `cash_metric_value_usd` plus `cash_metric_basis`.

Dependency change:

No.

Migration:

New producers should emit `cash_metric_value_usd`. Old actual-cash rows without that field remain accepted and are migrated from `actual_cash_result_usd`.

Rollback:

Revert this checkpoint's model/schema/test/docs changes. PR-I1a remains valid without I1b.

## Latest Addendum: PR-I1a Cash Metric Semantic Hotfix

Completed on branch `ai/actual-cash-semantic-repair-20260628-0645`.

Achieved:

- Added `cash_metric_basis` to `TournamentEventResult`, defaulting to `actual_cash` for backward compatibility.
- Made preview rows emit `cash_metric_basis=before_cost_proxy` in JSON and JSONL.
- Added `cash_metric_basis`, `primary_metric_display_name`, `actual_cash`, `leader_cash_metric_value_usd`, and `leader_actual_cash_result_usd` to `crypto_perp_tournament_report.v1` generation.
- Kept schema version v1 and added fields as optional schema extensions so older artifacts remain readable.
- Made report generation mark proxy / estimate known gaps as non-actual cash and mixed row basis as `INCONCLUSIVE_DATA`.
- Kept `crypto-perp-tournament-report` actual-cash-only by rejecting preview schema, proxy / estimate known gaps, and `cash_metric_basis != actual_cash` rows with `PREVIEW_ROWS_NOT_ACTUAL_CASH`.
- Made tournament gate block `actual_cash=false` or `cash_metric_basis != actual_cash` as `NEEDS_ACTUAL_CASH`.
- Made Workbench bridge and viewer carry cash basis summary fields and avoid treating non-actual basis as fills/slippage-included evidence.
- Updated runbook, vocabulary, surface inventory, implemented/current docs, Workbench README, and this summary.

Main files changed:

- `src/sis/crypto_perp/tournament.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/crypto_perp/tournament_gate.py`
- `src/sis/crypto_perp/workbench_bridge.py`
- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `src/sis/strategy_workbench_viewer/summary_fields.py`
- `schemas/crypto_perp_tournament_report.v1.schema.json`
- `schemas/crypto_perp_tournament_rows_preview.v1.schema.json`
- `schemas/strategy_workbench_viewer.v1.schema.json`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `tests/crypto_perp/test_tournament_gate.py`
- `tests/crypto_perp/test_workbench_bridge.py`
- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/strategy_workbench_viewer/README.md`
- `docs/final-summary.md`

Verification:

- `uv run pytest tests/crypto_perp/test_tournament_rows.py tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_gate.py tests/crypto_perp/test_workbench_bridge.py tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q`

Pending final verification in this work session:

- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`

User decisions required:

None.

Destructive change:

No. CLI behavior remains stricter for invalid non-actual cash report input, but no schema version was bumped and no existing artifact field was removed.

Dependency change:

No.

Migration:

Operators should include `cash_metric_basis=actual_cash` in manual actual-cash JSONL rows. Existing rows without the field are still interpreted as actual cash for compatibility, but preview / estimate rows must not be fed to `crypto-perp-tournament-report`.

Rollback:

Revert the cash basis model/schema/test/report/gate/Workbench changes from this addendum.

## Latest Addendum: Actual Cash Semantic Repair

Completed on branch `ai/actual-cash-semantic-repair-20260628-0645`.

Achieved:

- Added a `PREVIEW_ROWS_NOT_ACTUAL_CASH` guard to `crypto-perp-tournament-report`.
- Rejected `crypto_perp_tournament_rows_preview.v1` and rows carrying `OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH` before report generation.
- Kept caller-owned actual-cash JSONL / `TournamentEventResult` input working.
- Updated preview Markdown to display `outcome_before_cost_proxy_usd` instead of `actual_cash_result_usd`.
- Updated current docs and runbook wording so preview rows are display / dogfood only and cannot feed `crypto-perp-tournament-report`.

Main files changed:

- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md`
- `docs/plans/actual-cash-semantic-repair-2026-06-28.md`
- `docs/final-summary.md`

Verification:

- `uv run pytest tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_rows.py`
- `git diff --check`

Not fully passed:

- `uv run python scripts/check_current_docs.py` failed on existing tracked plan routing: `plan/0628から/0628-0623.md: tracked plan file is outside current root plan or archive routing`. This file was not changed in this checkpoint.

Remaining work:

- Resolve the pre-existing plan routing checker failure separately if full current-doc validation is required.

User decisions required:

None.

Destructive change:

No. CLI behavior is stricter for invalid preview input, but no data or schema was deleted.

Dependency change:

No.

Migration:

Operators must stop feeding `tournament_rows_preview.json` into `crypto-perp-tournament-report`. Use actual-cash rows for reports and `crypto-perp-tournament-rows-v2` for estimates.

Rollback:

Revert the guard, test, preview Markdown wording, and docs changes from this addendum.

## Latest Addendum: Docs Triage Refresh

Completed on branch `main`.

Achieved:

- Refreshed `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` as the current docs triage artifact.
- Added explicit 判定基準 for 更新できる / 古い内容がある / 作り直したほうがいい / 削除・アーカイブしてもよい docs.
- Added next cleanup candidates without deleting, moving, or archiving files.
- Expanded the 抜け・漏れ・誤謬リスク section around docs checker limits, CLI catalog limits, runtime snapshots, archive docs, and intentionally thin low-level helper docs.
- Kept historical docs as context only and did not re-promote `docs/archive/**` or `plan/archive/**` into current proof.

Main files changed:

- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/plans/docs-triage-refresh-2026-06-28.md`
- `docs/final-summary.md`

Verification:

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

Not run:

- Full `./scripts/check`; this checkpoint only updated docs and did not change code, schema, CLI routing, or checker allowlists.

Remaining work:

- Execute cleanup candidates only as a separate task.

User decisions required:

None.

Destructive change:

No. No docs were deleted, moved, or archived.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert this docs triage refresh and remove the checkpoint plan.

## Latest Addendum: Docs Archive Triage Cleanup

Completed on branch `ai/docs-archive-triage-20260627-2341`.

Achieved:

- Moved superseded root audit docs to `docs/archive/2026-06-27-doc-routing/`.
- Moved completed 2026-06-27 work plans from `docs/plans/` to `docs/archive/2026-06-27-merged-plans/`.
- Updated current docs routing so `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md` is the current docs triage entry.
- Removed archived audit docs from `scripts/check_current_docs.py` current-doc allowlist.
- Kept archive docs as historical snapshots, not current proof.

Main files changed:

- `README.md`
- `docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md`
- `docs/DOCS_LINT_POLICY_2026-05-30.md`
- `docs/archive/README.md`
- `docs/final-summary.md`
- `scripts/check_current_docs.py`
- `docs/archive/2026-06-27-doc-routing/`
- `docs/archive/2026-06-27-merged-plans/`

Verification:

- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

Not run:

- Full `./scripts/check`; this cleanup only moved docs and updated docs routing.

Remaining work:

- None for this cleanup.

User decisions required:

None.

Destructive change:

No. Files were moved to archive, not deleted.

Dependency change:

No.

Rollback:

Move the archived docs back to their previous paths and restore the current-doc allowlist entries.

## Latest Addendum: Crypto Perp Profit-Readiness Evidence Run Plan

Completed on branch `ai/crypto-perp-profit-readiness-20260627-1901`.

Achieved:

- Added `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md`.
- Confirmed the current local `data/crypto_perp` inventory has dogfood / status / Daily Brief / Workbench Viewer artifacts, but no real event, outcome, source availability, rows-v2, cash ledger, or live measurement artifact.
- Recorded the stop result as `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Kept dogfood / status artifacts out of profit evidence and actual cash evidence.
- Kept manual outcome prices, estimates, and actual cash result boundaries explicit.
- Did not run public network, credentialed read-only, exchange write, live order, tiny-live measurement, or automatic trading operations.

Main files changed:

- `docs/crypto_perp/PROFIT_READINESS_EVIDENCE_RUN_PLAN_2026-06-27.md`
- `docs/final-summary.md`

Verification:

- `uv run python scripts/check_current_docs.py`
- `git diff --check`

Not run:

- `uv run pytest tests/crypto_perp -q`, because no Crypto Perp implementation code changed.
- `uv run python scripts/check_cli_catalog.py`, because no CLI catalog or command implementation changed.
- External/public/credentialed/live operations.

Remaining work:

- Create or provide real event and matured outcome artifacts before trying source availability, replay slice, feature pack, rows-v2, or bias guard evidence generation.
- Decide separately whether to approve a public Bitget probe with `SIS_ALLOW_PUBLIC_NETWORK=1`.

User decisions required:

- Public probe approval is required before any network-backed Crypto Perp evidence collection.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Remove the new run plan and this addendum.

## Latest Addendum: Crypto Perp Profit-Readiness Evidence Layer

Completed on branch `ai/crypto-perp-profit-readiness-20260627-1901`.

Achieved:

- Added current plan, surface inventory, and acceptance vocabulary under `docs/crypto_perp/`.
- Added local source availability, replay slice, feature pack, deterministic edge score, cost-aware tournament rows v2, bias guard, and tiny-live shadow surfaces.
- Added public local CLI entries: `crypto-perp-source-availability`, `crypto-perp-replay-slice`, `crypto-perp-feature-pack`, `crypto-perp-edge-score`, `crypto-perp-tournament-rows-v2`, `crypto-perp-bias-guard`, and `crypto-perp-tiny-live-shadow`.
- Kept `actual_cash_result_usd` separate from `before_cost_proxy_usd`, `cost_adjusted_cash_estimate_usd`, and `stress_cash_estimate_usd`.
- Kept missing OFI / trade sign / depth sources as known gaps instead of zero-filling them.
- Added `operator_decision` summary support to `crypto_perp_truth_cycle_status.v1`.
- Updated Workbench bridge execution reality so proxy-gap reports are not marked as including fills/slippage.
- Updated current docs, CLI catalog, and the Crypto Perp runbook.
- Did not add dependencies, external API calls, credential writes, exchange writes, live orders, daemon behavior, or automatic trading.

Main files changed:

- `docs/crypto_perp/`
- `docs/archive/2026-06-27-merged-plans/crypto_perp_profit_readiness_execution_2026-06-27.md`
- `src/sis/crypto_perp/source_availability.py`
- `src/sis/crypto_perp/replay.py`
- `src/sis/crypto_perp/features.py`
- `src/sis/crypto_perp/edge_scorer.py`
- `src/sis/crypto_perp/tournament_rows.py`
- `src/sis/crypto_perp/bias_guards.py`
- `src/sis/crypto_perp/tiny_live_shadow.py`
- `src/sis/crypto_perp/truth_cycle_status.py`
- `src/sis/crypto_perp/workbench_bridge.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `schemas/crypto_perp_*.schema.json`
- `tests/crypto_perp/`

Verification:

- `uv run pytest tests/crypto_perp -q` -> 177 passed.
- `uv run python scripts/check_cli_catalog.py` -> checked 216 public CLI commands.
- `uv run python scripts/check_current_docs.py` -> checked 184 current docs.
- `uv run sis crypto-perp-source-availability --help`
- `uv run sis crypto-perp-tournament-rows-v2 --help`
- `uv run sis crypto-perp-tiny-live-shadow --help`
- `uv run sis crypto-perp-truth-cycle-status --help`
- `git diff --check`
- `./scripts/check` -> 2803 passed.

Not run:

- External Bitget/public network probes.
- Credentialed read-only calls.
- Exchange writes or live order calls.
- Real tiny-live measurement.

Remaining work:

- Feed real event/outcome/cash-ledger artifacts through the new estimate surfaces before any human tiny-live review.
- Use actual cash evidence only when cash ledger or live measurement artifacts exist.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required. Existing Truth-Cycle MVP v1 artifacts remain valid; profit-readiness artifacts are additional local surfaces.

Rollback:

Revert the profit-readiness docs, schema, model, CLI, tests, and status/workbench summary changes from this addendum.

## Latest Addendum: PR-AI-LOOP-01 Structured AI Review Findings

Completed on branch `ai/strategy-ai-review-structured-findings-20260627-1822`.

Achieved:

- Added `strategy_ai_review_structured_findings.v1` as a companion artifact to `strategy_ai_review_note.v1`.
- Added typed evidence refs with `ref_type`, `index`, and optional `entry_key`; arbitrary JSON pointers are not accepted.
- Split `severity` from `review_impact`.
- Added `strategy-ai-review-findings-structure` with `--structured-finding-json` as the main input path.
- Added note / packet lineage validation before recording structured findings.
- Auto-assigns `finding-001`, `finding-002`, etc. when `finding_id` is omitted.
- Kept `auto_applied=false`, `permission_allowed=false`, `paper_execution_allowed=false`, and `live_allowed=false`.
- Did not copy `model_reasoning_effort` into structured findings.
- Did not call external AI APIs, auto-classify AI output, auto-edit Strategy Authoring YAML, or connect to operator / stage / paper / live permission.

Main files changed:

- `schemas/strategy_ai_review_structured_findings.v1.schema.json`
- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/NEXT_DIRECTION_CURRENT.md`
- `docs/archive/2026-06-27-merged-plans/strategy_ai_review_structured_findings_2026-06-27.md`

Verification:

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-findings-structure --help`
- `uv run python scripts/check_cli_catalog.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`
- `./scripts/check`

Not run:

- External AI API calls.
- Automatic prompt execution.
- Paper/live operations.

Remaining work:

- Use at least one real recorded AI note as dogfood input before designing downstream viewer / daily brief structured findings display.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required. Existing packet and note artifacts remain valid.

Rollback:

Revert the `strategy_ai_review_structured_findings.v1` schema/model/service/rendering/CLI/test/docs changes and this addendum.

## Latest Addendum: Strategy AI Review Reasoning Effort

Completed on branch `ai/strategy-ai-review-reasoning-effort-20260627-1748`.

Achieved:

- Added optional `model_reasoning_effort` to `strategy_ai_review_note.v1`.
- Added `--model-reasoning-effort medium|xhigh` to `strategy-ai-review-note-record`.
- Kept `model` as the model id, for example `gpt-5.5`.
- Updated note Markdown rendering to show `model_reasoning_effort`.
- Re-recorded the local PR-AI-LOOP-00 runtime note as `provider=codex-cli`, `model=gpt-5.5`, `model_reasoning_effort=xhigh`.
- Kept `auto_applied=false`, `permission_allowed=false`, `paper_execution_allowed=false`, and `live_allowed=false`.

Main files changed:

- `schemas/strategy_ai_review_note.v1.schema.json`
- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`
- `docs/archive/2026-06-27-merged-plans/strategy_ai_review_reasoning_effort_2026-06-27.md`

Verification:

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-note-record --help`
- `uv run python scripts/check_current_docs.py`
- `uv run python` schema validation for `data/strategy_ai_reviews/pr-ai-loop-00/strategy_ai_review_note.json`
- `./scripts/check`

Not run:

- External AI API calls.
- Automatic prompt execution beyond this manual Codex review session.
- Paper/live operations.

Remaining work:

- Decide whether PR-AI-LOOP-01 should promote `model_reasoning_effort` into structured findings metadata or keep it note-level only.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required. Existing notes without `model_reasoning_effort` remain valid.

Rollback:

Revert the `model_reasoning_effort` schema/model/service/CLI/rendering/test/docs changes and this addendum.

## Latest Addendum: PR-AI-LOOP-00 Safe AI Review Context Sections

Completed on branch `ai/strategy-idea-candidates-20260627-1116`.

Achieved:

- Added `context_sections` to `strategy_ai_review_packet.v1`.
- Added first allowlist extractor for `strategy_case_lite.v1` summary context only.
- Kept full source payload out of packet output.
- Kept unknown schema payload out of `context_sections`.
- Kept sensitive source behavior as `BLOCKED_SENSITIVE_SOURCE`.
- Kept `paper_execution_allowed=false`, `live_allowed=false`, and `permission_allowed=false`.
- Did not execute external AI API calls, auto prompt runs, auto fixes, paper operations, live operations, wallet, signing, or exchange write.

Main files changed:

- `schemas/strategy_ai_review_packet.v1.schema.json`
- `src/sis/strategy_ai_review/models.py`
- `src/sis/strategy_ai_review/service.py`
- `src/sis/strategy_ai_review/rendering.py`
- `src/sis/commands/strategy_ai_review.py`
- `tests/strategy_ai_review/`
- `docs/strategy_ai_review/README.md`
- `docs/archive/2026-06-27-merged-plans/strategy_ai_review_context_sections_pr_ai_loop_00_2026-06-27.md`

Verification:

- `uv run pytest tests/strategy_ai_review -q`
- `uv run ruff check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run ruff format --check src/sis/strategy_ai_review src/sis/commands/strategy_ai_review.py tests/strategy_ai_review`
- `uv run sis strategy-ai-review-packet-build --help`
- `uv run python scripts/check_current_docs.py`
- `uv run sis strategy-ai-review-packet-build --source data/strategy_cases/pr-ai-loop-00/strategy_case_lite.json --review-question "What should a human inspect next?" --out data/strategy_ai_reviews/pr-ai-loop-00`
- `./scripts/check`

Not run:

- `strategy-ai-review-note-record` execution.
- External AI API calls.

Remaining work:

- Decide later whether additional known schemas should get explicit `context_sections` allowlists.
- Note recording remains a separate step after an AI response exists.

User decisions required:

None for this slice.

Destructive change:

No.

Dependency change:

No.

Migration:

No migration is required.

Rollback:

Revert the `strategy_ai_review` context section model/schema/service/rendering/test/docs changes and this addendum.

## Goal

Implement the first safe slices of the Strategy Idea Candidate Generation Pipeline: candidate-set contract, Python validation, C4 deterministic generator Python API, C5 split/leakage policy validation API, C6 metric disclosure in reports, C10 operator review Markdown surface, C11 fixture E2E, deterministic JSON/Markdown writer, input-evidence blocking, shortlist export sidecar, docs, and focused tests.

This summary covers the implemented candidate pipeline through `strategy-intake-validate`. It does not claim the downstream C9 Strategy Authoring / backtest / Strategy Review bridge is implemented.

## Branch

`ai/strategy-idea-candidates-20260627-1116`

## Achieved

- Added `strategy_idea_candidate_set.v1` JSON Schema and Pydantic models.
- Added `strategy_idea_candidate_export_manifest.v1` sidecar manifest schema and models.
- Added validation for count mismatch, selected/rejected ID mismatch, selected-only inventory, non-PASS input evidence, missing source summaries, sealed-test selection, and paper/live/auto-promote/final boundary flags.
- Added deterministic candidate-set JSON/Markdown writer.
- Added C4 deterministic generator Python API with fixed family IDs, finite parameter grids, stable `parameter_grid_hash`, candidate cap recording, duplicate rejection recording, and full candidate inventory.
- Added a PASS source evidence guard so inconsistent source-level evidence cannot produce a BUILT candidate set.
- Added `parameter_grids`, `candidate_cap`, and `cap_rejection_count` to `strategy_idea_candidate_set.v1`.
- Added C5 split/leakage policy validation API for time-window ordering, sealed-test non-use, source available-at boundary, and purge / embargo policy records.
- Added C6 report disclosure separating `raw_validation_metrics` from `selection_adjusted_metrics_status` and avoiding proof language.
- Added C10 operator review Markdown surface for exploration counts, rejection reasons, selection policy, known gaps, policy validation, and false boundary flags.
- Added C11 fixture E2E from input evidence through candidate set write, policy validation, operator review, shortlist export, and intake validation.
- Added blocked input-evidence candidate set builder for non-PASS input contract validation.
- Added shortlist export to strict `strategy_idea.v1` draft JSON while keeping candidate set path/hash in the sidecar manifest.
- Added tests for schema validation, Python invariant validation, writer determinism, export, and intake validation integration.
- Added docs for the implemented candidate contract and corrected the checkpoint doc so C3 starts with canonical JSON/Markdown only.

## Main Files Changed

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `schemas/strategy_idea_candidate_export_manifest.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c4_generator_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c5_policy_validation_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c6_metric_disclosure_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c10_operator_review_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_c11_fixture_e2e_2026-06-27.md`
- `docs/archive/2026-06-27-merged-plans/strategy_idea_candidates_p0a_c2_c3_c8_2026-06-27.md`
- `docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `scripts/check_current_docs.py`

## Verification Run

- `uv run pytest tests/strategy_idea_candidates`
- `uv run ruff check src/sis/strategy_idea_candidates tests/strategy_idea_candidates`
- `uv run ruff format --check src/sis/strategy_idea_candidates tests/strategy_idea_candidates`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`
- `./scripts/check`

## Not Run

None for this slice.

## Remaining Work

- JSONL / CSV search ledger rows after generator output exists.
- C5 full split engine beyond policy validation API.
- C6 selection-adjusted metrics beyond `NOT_IMPLEMENTED`.
- C9 Strategy Lab / backtest bridge.
- C10 richer review packet beyond Markdown surface.
- Public CLI after Python API behavior is stable.

## User Decisions Required

None for this slice.

## Destructive Change

No.

## Destructive Change Reason

Not applicable.

## Dependency Change

No dependency change. `pyproject.toml` and `uv.lock` were not modified.

## Migration

No migration is required.

## Rollback

Revert the new `strategy_idea_candidates` package, candidate schemas, tests, docs, and `scripts/check_current_docs.py` routing additions.

## Next Considerations

Start C5/C6 only after reviewing whether policy-record-only split/leakage fields are sufficient for the next bridge.
