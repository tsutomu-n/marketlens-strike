<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# File-by-file Implementation Map

## 1. 既存ファイル変更

| ファイル | Task | 変更 |
|---|---|---|
| `pyproject.toml` | M01 | dev dependencyに`hypothesis`。optional dependencyは採用判断後のみ |
| `uv.lock` | M01 | lock更新 |
| `src/sis/cli.py` | M01/M09 | `register_crypto_perp_commands`、live commandは別registration |
| `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` | M01以降 | 実装済みcommandのみ追加 |
| `scripts/check_current_docs.py` | M00/M11 | 新current docs directory/filesをallowlistへ |
| `docs/CURRENT_STATE.md` | M00/M11 | 未実装/実装済み境界を更新 |
| `docs/NEXT_DIRECTION_CURRENT.md` | M00/M11 | 本計画への導線、旧計画superseded |
| `docs/IMPLEMENTED_SURFACES.md` | M11 | 完成surfaceのみ追加 |
| `docs/strategy_research_lab/README.md` | M00/M11 | current handoffへのリンク |
| `plan/README.md` | M00 | 旧計画をhistorical扱い |
| `src/sis/strategy_workbench_viewer/service.py` | M11 optional | crypto summaryのcompact fieldsだけ。Parquet直接scanは追加しない |
| `docs/strategy_workbench_viewer/README.md` | M11 | crypto reportの読み方 |

## 2. Core package

| ファイル | Task | 責務 |
|---|---|---|
| `src/sis/crypto_perp/__init__.py` | M01 | public exports最小化 |
| `src/sis/crypto_perp/config.py` | M01 | YAML load、Pydantic config |
| `src/sis/crypto_perp/models.py` | M01 | 共通boundary/provenance/IDs。肥大化したらartifact別分割 |
| `src/sis/crypto_perp/io.py` | M01 | JSON/YAML/Parquet read/write helper |
| `src/sis/crypto_perp/clock.py` | M01 | UTC、server offset、finalized bar判定 |
| `src/sis/crypto_perp/reason_codes.py` | M01 | StrEnum reason code vocabulary |
| `src/sis/crypto_perp/raw_store.py` | M02 | immutable REST raw response保存 |
| `src/sis/crypto_perp/universe.py` | M03 | universe snapshot/diff/eligibility |
| `src/sis/crypto_perp/heartbeat.py` | M03 | one-shot refresh orchestration |
| `src/sis/crypto_perp/bars.py` | M03 | candle pagination/normalization/finalization |
| `src/sis/crypto_perp/quality.py` | M03 | gap/duplicate/OHLC/stale検査 |
| `src/sis/crypto_perp/features.py` | M04 | event feature計算。I/O禁止 |
| `src/sis/crypto_perp/events.py` | M04 | detector/dedupe/event artifact |
| `src/sis/crypto_perp/event_card.py` | M04 | JSON/MD summary model |
| `src/sis/crypto_perp/rendering.py` | M04 | Rich/HTML rendering、escape |
| `src/sis/crypto_perp/recorder.py` | M05 | candidate capture orchestration |
| `src/sis/crypto_perp/ws_protocol.py` | M05 | Bitget WS frame/ping/subscription parser |
| `src/sis/crypto_perp/book.py` | M05 | snapshot/diff/checksum/depth metrics |
| `src/sis/crypto_perp/segments.py` | M05 | gzip segment rotation/atomic commit/recovery |
| `src/sis/crypto_perp/decisions.py` | M06 | prospective immutable decision |
| `src/sis/crypto_perp/outcomes.py` | M06 | matured horizon/MFE/MAE/ambiguity |
| `src/sis/crypto_perp/order_preview.py` | M08 | direction-neutral order normalization/preflight |
| `src/sis/crypto_perp/idempotency.py` | M08 | deterministic clientOid/attempt registry |
| `src/sis/crypto_perp/tiny_live.py` | M09 | one-shot measurement state machine |
| `src/sis/crypto_perp/reconciliation.py` | M09 | orders/fills/positions/flat確認 |
| `src/sis/crypto_perp/cash_ledger.py` | M10 | lifetime cash accounting |
| `src/sis/crypto_perp/replay.py` | M10 | direction-neutral BBO/depth replay |
| `src/sis/crypto_perp/calibration.py` | M10 | actual vs simulated bias |
| `src/sis/crypto_perp/tournament.py` | M11 | competing branch report |
| `src/sis/crypto_perp/workbench_bridge.py` | M11 | Strategy Input Contract export |

## 3. Bitget adapter

| ファイル | Task | 責務 |
|---|---|---|
| `src/sis/crypto_perp/bitget/__init__.py` | M02 | exports |
| `src/sis/crypto_perp/bitget/client.py` | M02/M08 | async HTTP/signing transport、retry policy |
| `src/sis/crypto_perp/bitget/public_api.py` | M02 | v3 public endpoints |
| `src/sis/crypto_perp/bitget/normalizers.py` | M02 | native payload -> domain row |
| `src/sis/crypto_perp/bitget/probe.py` | M02 | capability artifact |
| `src/sis/crypto_perp/bitget/auth.py` | M08 | HMAC signing/secret redaction |
| `src/sis/crypto_perp/bitget/account.py` | M08 | assets/info/fee/positions/open orders read-only |
| `src/sis/crypto_perp/bitget/orders.py` | M09 | place/query/cancel/close primitives。strategy logic禁止 |

## 4. Commands

| ファイル | Task | Commands |
|---|---|---|
| `src/sis/commands/crypto_perp.py` | M01-M08/M10-M11 | config/probe/refresh/watchdeck/record/review/settle/account/preview/report |
| `src/sis/commands/crypto_perp_live.py` | M09 | live-measure/reconcile/closeのみ |

Command wrapperはparse/resolve/call/renderだけ。domain logicを書かない。

## 5. Configs

```text
configs/crypto_perp/bitget_personal_edge_lab.yaml
configs/crypto_perp/tiny_live_measurement.yaml
configs/crypto_perp/reason_code_descriptions.yaml  # optional、UI説明だけ
```

Secretはconfigへ書かない。

## 6. Schemas

```text
schemas/crypto_perp_lab_config.v1.schema.json
schemas/crypto_perp_provider_probe.v1.schema.json
schemas/crypto_perp_universe_snapshot.v1.schema.json
schemas/crypto_perp_market_snapshot.v1.schema.json
schemas/crypto_perp_event.v1.schema.json
schemas/crypto_perp_capture_manifest.v1.schema.json
schemas/crypto_perp_decision.v1.schema.json
schemas/crypto_perp_outcome.v1.schema.json
schemas/crypto_perp_account_snapshot.v1.schema.json
schemas/crypto_perp_order_preview.v1.schema.json
schemas/crypto_perp_live_measurement.v1.schema.json
schemas/crypto_perp_cash_ledger.v1.schema.json
schemas/crypto_perp_execution_replay.v1.schema.json
schemas/crypto_perp_tournament_report.v1.schema.json
```

## 7. Tests

```text
tests/crypto_perp/test_config.py
tests/crypto_perp/test_bitget_client.py
tests/crypto_perp/test_bitget_normalizers.py
tests/crypto_perp/test_provider_probe.py
tests/crypto_perp/test_universe.py
tests/crypto_perp/test_heartbeat.py
tests/crypto_perp/test_bars.py
tests/crypto_perp/test_quality.py
tests/crypto_perp/test_features.py
tests/crypto_perp/test_events.py
tests/crypto_perp/test_event_card.py
tests/crypto_perp/test_recorder.py
tests/crypto_perp/test_ws_protocol.py
tests/crypto_perp/test_book.py
tests/crypto_perp/test_segments.py
tests/crypto_perp/test_decisions.py
tests/crypto_perp/test_outcomes.py
tests/crypto_perp/test_bitget_auth.py
tests/crypto_perp/test_account_snapshot.py
tests/crypto_perp/test_order_preview.py
tests/crypto_perp/test_tiny_live.py
tests/crypto_perp/test_reconciliation.py
tests/crypto_perp/test_cash_ledger.py
tests/crypto_perp/test_replay.py
tests/crypto_perp/test_calibration.py
tests/crypto_perp/test_tournament.py
tests/crypto_perp/test_workbench_bridge.py

tests/crypto_perp/property/test_common_invariants.py
tests/crypto_perp/property/test_decision_time.py
tests/crypto_perp/property/test_rounding.py
tests/crypto_perp/property/test_order_state_machine.py
```

## 8. Fixtures

```text
tests/fixtures/crypto_perp/bitget/public/instruments.json
tests/fixtures/crypto_perp/bitget/public/tickers.json
tests/fixtures/crypto_perp/bitget/public/candles.json
tests/fixtures/crypto_perp/bitget/public/open_interest.json
tests/fixtures/crypto_perp/bitget/public/funding_history.json
tests/fixtures/crypto_perp/bitget/ws/trades.ndjson
tests/fixtures/crypto_perp/bitget/ws/books_snapshot.ndjson
tests/fixtures/crypto_perp/bitget/ws/books_gap.ndjson
tests/fixtures/crypto_perp/bitget/ws/books_checksum_fail.ndjson
tests/fixtures/crypto_perp/bitget/private/account.json
tests/fixtures/crypto_perp/bitget/private/order_states.ndjson
tests/fixtures/crypto_perp/tardis/PROVENANCE.md
```

Private fixtureはsynthetic/redactedのみ。

## 9. Tools / validation sidecars

```text
tools/oss_spikes/pybotters_bitget/
tools/external_validation/freqtrade/
scripts/download_tardis_bitget_fixture.py
docs/references/crypto_perp/
```

## 10. Module boundary

- 新規/大幅編集Pythonは800行以下。
- 目安400行で分割を検討。
- `models.py`が肥大化したら`contracts/`へartifact別分割。
- adapterとdomain logicを分離。
- live write primitivesとstrategy/event logicを同一moduleへ置かない。
