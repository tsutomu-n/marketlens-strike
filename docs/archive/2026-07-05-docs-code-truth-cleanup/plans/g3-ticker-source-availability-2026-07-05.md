<!--
作成日: 2026-07-05_11:25 JST
更新日: 2026-07-05_11:25 JST
-->

# G3 Ticker Source Availability Adapter Plan

## Checkpoint ID

G3

## Purpose

`strategy-idea-candidates-bitget-source-refresh --out <dir>` が生成する `<dir>/source_root/data/ticker_rows/.../ticker_rows.parquet` を読み、Crypto Perp event の `information_cutoff_at` 時点でローカルに受信済みだった ticker だけを `crypto_perp_source_availability.v1` の `ticker` source に反映する。

## Current State

- `crypto-perp-source-availability` は `--available-source` と `--row-count` による手動指定だけを持つ。
- `build_source_availability()` は `reason` を自動生成するが、外部 adapter が計算した missing/stale reason を受け取る引数はない。
- `source_availability_matrix` と `known_gaps_by_source` は `SourceAvailabilityStatus.reason` と `metadata` を既に読む。
- Bitget public source refresh は `ticker_rows.parquet` と `ticker_manifest.json` を生成済み。

## Constraints

- available 判定は `ts_received_ms <= information_cutoff_at` を主条件にする。
- stale 判定の既定値は 900 秒。
- `ticker_manifest.json` の `window.end_ms` は `ts_exchange_ms` 由来なので available 判定に使わない。
- ticker row の `funding_rate` は `funding` source を満たす根拠にしない。
- 現在取得した ticker を過去 event に後付けして available 扱いしない。
- 新 public pre-actual-cash CLI、actual cash、tiny-live、live、ML、外部 API client は追加しない。
- 手元 runtime data に `ticker_rows.parquet` がない場合、実データ比較は完了条件にしない。

## Target Files

- `src/sis/crypto_perp/ticker_source.py`
- `src/sis/crypto_perp/source_availability.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `tests/crypto_perp/test_source_availability.py`
- `.ai-work/state.md`
- `docs/final-summary.md`

## Implementation Approach

1. テストで as-of、future、stale、funding 非昇格、cost-adjusted gating、CLI help を固定する。
2. `ticker_source.py` に、symbol と cutoff に対する ticker source status helper を追加する。
3. `build_source_availability()` に optional `source_reasons` を追加し、schema は変えず status の `reason` に反映する。
4. `crypto-perp-source-availability` に `--ticker-source-root` と `--ticker-max-staleness-seconds` を追加する。
5. CLI は adapter 結果を `row_counts`、`source_refs`、`source_metadata`、`source_reasons` として builder に渡す。

## Test Plan

- `uv run pytest tests/crypto_perp/test_source_availability.py -q`
- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q`
- `uv run ruff check src/sis/crypto_perp tests/crypto_perp`
- `uv run python scripts/check_current_docs.py`

## Done Conditions

- `crypto-perp-source-availability --ticker-source-root <source_root>` が ticker-aware artifact を生成できる。
- cutoff 後の ticker と stale ticker が available にならない。
- missing/stale reason が `source_availability_matrix` と `known_gaps_by_source` で読める。
- Backtest Candidate Pack は生成済み source availability artifact の ticker 状態差分を読むだけで反映できる。
- G3 を profit proof、actual cash readiness、tiny-live readiness、live readiness と読ませる変更がない。

## Failure Conditions

- `ticker_manifest.json` の exchange-time window で availability を判定している。
- ticker row の `funding_rate` により `funding.available=true` になる。
- CLI がネットワーク取得、外部書き込み、live/order 系に触れる。
- schema 変更が必要になる。

## Impact

Local source availability artifact generation only. Existing manually supplied `--available-source` and `--row-count` paths remain supported.

## Rollback

Revert the new adapter file, source availability reason threading, CLI option wiring, and focused tests. Generated runtime artifacts are not required for rollback.

## Alternatives

- `--ticker-manifest` を `crypto-perp-source-availability` に流用する案は不採用。manifest count は as-of 判定ではなく、過去 event への後付けを防げない。
- Backtest Candidate Pack builder に直接 ticker read を入れる案は不採用。Pack は source availability artifact を読む境界を維持する。

## Open Items

- 完了後の plan doc は existing docs policy に合わせて archive へ移す。

## Destructive Change

No.

## Branch

`ai/ticker-source-availability-20260705-1125`
