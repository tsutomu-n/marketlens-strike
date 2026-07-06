<!--
作成日: 2026-07-06_17:55 JST
更新日: 2026-07-06_17:55 JST
-->

# Next No-Cash Backtest To Paper Plan 2026-07-06

## 結論

次にやることは、Paper Trade へ進むことではありません。

次の実装目標は、Crypto Perp の no-cash backtest 段階について、Paper Observation に進んでよいかを判定する前段 gate を機械化することです。

現在の goal は、実際のお金を使わない backtest evidence pack までです。その次が Paper Observation、その後が Actual Cash です。

この計画は、no-cash backtest evidence quality を厚くし、`BACKTEST_COLLECT_MORE_DATA` と `BACKTEST_CANDIDATE_HOLD` の読み違いを防ぐためのものです。

## 現在地

現在の current goal は、`crypto-perp-backtest-candidate-pack` を actual cash なしの短期終着点として使い、candidate / event / source ごとに欠損、timestamp、費用、`NO_TRADE` 比較を残すことです。

現在の local result は `BACKTEST_COLLECT_MORE_DATA` であり、Paper Observation へ進む状態ではありません。

## 目的

Codex は次を実装する。

1. no-cash backtest evidence を Paper Observation 手前で評価する gate artifact を追加する。
2. `BACKTEST_CANDIDATE_HOLD` でも Paper Permission ではないことを維持する。
3. Paper Observation に進むための不足を、candidate / event / source / metric 単位で machine-readable に出す。
4. books / trades / replay / measured slippage / sample size / PBO / rolling stability / `NO_TRADE` 比較の不足を 0 埋めせず blocker として残す。
5. Actual Cash、wallet、signing、exchange write、production order readiness は扱わない。

## 制約

- actual cash source を要求しない。
- cash ledger を作らない。
- exchange write をしない。
- wallet / signing を使わない。
- credentialed read を暗黙に使わない。
- missing source を 0 埋めしない。
- `NO_TRADE` が leader の時に trade action へ差し替えない。
- backtest result を profit proof と呼ばない。
- Paper Observation への最終許可を出さない。出すのは `READY_FOR_PAPER_REVIEW` ではなく、`NO_CASH_BACKTEST_HOLD` または blocker まで。

## 対象ファイル

新規候補:

- `src/sis/crypto_perp/no_cash_backtest_gate.py`
- `src/sis/commands/crypto_perp_no_cash_backtest_gate.py`
- `schemas/crypto_perp_no_cash_backtest_gate.v1.schema.json`
- `tests/crypto_perp/test_no_cash_backtest_gate.py`
- `docs/crypto_perp/NO_CASH_BACKTEST_GATE_V1.md`

更新候補:

- `src/sis/commands/crypto_perp.py`
- `src/sis/crypto_perp/backtest_candidate_pack_models.py`
- `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- `docs/crypto_perp/EVIDENCE_QUALITY_REALITY_CHECK_2026-07-05.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/final-summary.md`

## CLI design

追加する command:

```bash
uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/no_cash_backtest_gate/latest
```

CLI stdout must include:

```text
network_attempted=false
exchange_write_used=false
live_order_submitted=false
actual_cash_used=false
paper_permission_granted=false
status=pass|blocked
gate_decision=<decision>
blocker_count=<n>
gate_path=<path>
```

## Gate decision

Schema enum:

- `NO_CASH_BACKTEST_COLLECT_MORE_DATA`
- `NO_CASH_BACKTEST_REVISE`
- `NO_CASH_BACKTEST_REJECT`
- `NO_CASH_BACKTEST_HOLD`

Do not use names such as `PROMOTE_TO_PAPER`, `READY_FOR_PAPER_ORDER`, or `READY_FOR_LIVE`.

## Input rules

Codex must implement deterministic rules.

### Hard blockers

Return `NO_CASH_BACKTEST_COLLECT_MORE_DATA` if any are true:

- decision input is missing or invalid.
- source availability ledger is missing or invalid.
- `decision.decision == BACKTEST_COLLECT_MORE_DATA`.
- `evidence_grade_summary.overall_grade == insufficient_source_for_local_simulation`.
- `critical_missing_count > 0`.
- `future_signal_source_count > 0`.
- books / trades / replay are missing and required threshold policy marks them required.
- event_count < `min_events_for_gate`.
- rolling stability status is `sample_insufficient`.
- PBO status is `NOT_ESTIMABLE` or missing.

Return `NO_CASH_BACKTEST_REJECT` if any are true:

- backtest total after cost <= 0.
- stress total <= 0.
- `NO_TRADE` beats all trade actions on the same event set.
- drawdown exceeds configured threshold.
- largest loss / total result concentration exceeds configured threshold.

Return `NO_CASH_BACKTEST_REVISE` if any are true:

- executable simulated trade count is 0.
- selected action has UNKNOWN rows.
- action rows are missing for selected actions.
- candidate has unsupported family mapping that can be fixed by authoring/source work.

Return `NO_CASH_BACKTEST_HOLD` only if all are true:

- source availability has no critical missing source.
- no future signal source.
- event_count >= `min_events_for_gate`.
- rolling stability is not sample insufficient.
- PBO is estimable and not failed.
- after-cost backtest total > 0.
- stress total > 0.
- `NO_TRADE` is not leader on the same event set.
- no actual cash, paper order, wallet, signing, or exchange write is involved.

## Config defaults

Add constants in the new module, not hidden magic numbers:

- `min_events_for_gate = 30`
- `min_simulated_trades = 10`
- `max_largest_loss_to_total_result_ratio = 0.5`
- `require_books_trades_replay = false` for initial implementation

If `require_books_trades_replay=false`, missing books/trades/replay must still be reported as known gaps. Do not mark them pass silently.

## Output artifact

Write:

- `no_cash_backtest_gate.json`
- `no_cash_backtest_gate.md`

JSON must include:

- `schema_version`
- `artifact_id`
- `created_at`
- `producer`
- `source_refs`
- `boundary`
- `gate_decision`
- `reason_codes`
- `blockers`
- `known_gaps`
- `thresholds`
- `summary`
- `input_artifacts`
- `permits_paper_order=false`
- `permits_live_order=false`
- `actual_cash_used=false`

## Tests

Add tests for at least these cases:

1. Legacy decision without `evidence_grade_summary` does not crash, but returns collect-more-data with compatibility reason.
2. Current `BACKTEST_COLLECT_MORE_DATA` returns `NO_CASH_BACKTEST_COLLECT_MORE_DATA`.
3. Critical missing source returns collect-more-data.
4. Future signal source returns collect-more-data.
5. Rolling stability sample insufficient returns collect-more-data.
6. `NO_TRADE` leader returns reject or collect-more-data according to available metrics, but never hold.
7. Existing-artifact local simulation with enough events and positive backtest/stress can return `NO_CASH_BACKTEST_HOLD`.
8. Output schema validates.
9. CLI writes JSON and Markdown and prints all boundary flags as false.
10. Missing optional books/trades/replay are reported as known gaps when `require_books_trades_replay=false`.

## Documentation updates

Update docs to say the stage order is:

```text
No-cash backtest evidence pack
  -> no-cash backtest gate
  -> human review for paper observation
  -> Paper Observation
  -> Actual Cash evidence
```

Do not document direct movement from `BACKTEST_CANDIDATE_HOLD` to Paper Observation.

## Verification

Minimum:

```bash
uv run pytest tests/crypto_perp/test_no_cash_backtest_gate.py -q
uv run pytest tests/crypto_perp/test_backtest_candidate_pack.py -q
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```

Full:

```bash
./scripts/check
```

## 完了条件

- New CLI command is registered and appears in CLI catalog checker.
- New schema validates output.
- New tests pass.
- Current docs checker passes.
- Full `./scripts/check` passes.
- No artifact or stdout claims profit proof, actual cash readiness, paper execution permission, live readiness, wallet/signing use, or exchange write.
- The plan does not require user input, API credentials, wallet, signing, or exchange write.

## Codex final report format

Codex must report:

```text
状態: 完了 / 未完了
結果:
いま使えるか:
反映タイミング:
変更点:
検証:
残リスク:
次にやること:
```
