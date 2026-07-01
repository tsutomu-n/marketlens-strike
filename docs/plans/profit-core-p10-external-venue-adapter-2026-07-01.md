<!--
作成日: 2026-07-01_16:45 JST
更新日: 2026-07-01_16:45 JST
-->

# Profit Core P10 External Virtual Venue Adapter Plan

## チェックポイントID

P10: External Virtual Venue Adapter

## 目的

P5 `virtual_execution_gate.v1` を通過した candidate だけを、Bitget public read-only の external venue evidence record に接続する。

この checkpoint は external venue adapter の証跡 surface を作るだけであり、credential、demo order、paper order、live order、actual cash execution、wallet、signing、exchange write は行わない。

## 現状

- P5 `virtual_execution_gate.v1` は local/mock lifecycle を検査し、`LOCAL_MOCK_VERIFIED` の candidate を外部 lifecycle 検査候補にできる。
- 既存 `src/sis/strategy_idea_candidates/bitget_public_source.py` は Bitget public market data を明示 network opt-in で扱う。
- 既存 `src/sis/execution/bitget_demo_adapter.py` は Bitget demo adapter の mock-first surface と credential env boundary を持つ。
- P10 の long-horizon contract は 1 venue ずつ実装し、official docs、rate limit、permission scope、terms、jurisdiction、credential handling の current verification を要求している。

## Current Official Docs Verification

2026-07-01_16:38 JST に Bitget 公式 docs を確認した。

- Bitget Demo Trading REST API: `https://www.bitget.com/api-doc/common/demotrading/restapi`
  - Demo API は Demo API Key と `paptrading: 1` header が必要。
- Bitget Request Interaction: `https://www.bitget.com/api-doc/common/signature-samaple/interaction`
  - Public market information interface の unified rate limit は最大 20 requests/sec。
  - 過剰 request は 429 になり得る。
- Bitget Terms of Use: `https://www.bitget.com/support/articles/360014944032-terms-of-use`
  - Last Updated は June 16, 2026。
  - jurisdiction / eligibility は実行直前に user-provided account conditions と合わせて再確認する。

## 制約

- venue は Bitget のみ。Hyperliquid / GRVT は実装しない。
- adapter mode は `public_read_only` のみ。
- CLI は外部 network を実行しない。明示 opt-in と recorded request/response を検証・保存する。
- recorded request/response に secret-like header、param、body key があれば artifact を書かずに失敗する。
- demo/testnet/read-only result は actual cash ではない。
- `LOCAL_MOCK_VERIFIED` でない virtual gate は P10 complete にしない。

## 対象ファイル

- `schemas/profit_core_external_venue_adapter_run.v1.schema.json`
- `src/sis/edge_candidates/external_venue_adapter.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_external_venue_adapter.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`

## 実装方針

`edge-candidate-external-venue-adapter-record` を追加する。

入力:

- `--virtual-gate`: P5 `virtual_execution_gate.v1`
- `--adapter-plan`: local JSON/YAML plan with Bitget official docs verification, network opt-in flag, and recorded request/response summaries

出力:

- `profit_core_external_venue_adapter_run.json`
- status:
  - `RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW`
  - `BLOCKED_NETWORK_OPT_IN`
  - `BLOCKED_RECORDED_RESPONSE_MISSING`
  - `BLOCKED_OFFICIAL_DOCS_VERIFICATION`
  - `BLOCKED_LOCAL_VIRTUAL_GATE`
  - `BLOCKED_BOUNDARY_VIOLATION`

固定 boundary:

- `venue=bitget`
- `adapter_mode=public_read_only`
- `actual_cash=false`
- `demo_or_testnet_result_is_actual_cash=false`
- `profit_evidence=false`
- `credentials_used=false`
- `credential_values_redacted=true`
- `network_attempted=false`
- `external_write_used=false`
- `exchange_write_allowed=false`
- `order_submit_allowed=false`
- `live_order_submitted=false`
- `wallet_used=false`
- `signing_used=false`

## 実装手順

1. RED tests を追加する。
2. schema と Pydantic model を追加する。
3. adapter plan parser、official doc requirement check、recorded request/response redaction check を実装する。
4. P5 virtual gate validation を実装する。
5. CLI command を追加する。
6. CLI catalog と final summary を更新する。
7. focused tests、ruff、CLI catalog、current docs、full check を実行する。

## テスト方針

- Bitget official docs refs、network opt-in、recorded response がある時に `RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW` になる。
- network opt-in がない時は `BLOCKED_NETWORK_OPT_IN`。
- recorded request/response がない時は `BLOCKED_RECORDED_RESPONSE_MISSING`。
- required official docs が不足する時は `BLOCKED_OFFICIAL_DOCS_VERIFICATION`。
- virtual gate が `LOCAL_MOCK_VERIFIED` でない時は `BLOCKED_LOCAL_VIRTUAL_GATE`。
- unredacted secret-like header / param / body key はエラー。
- CLI stdout が network / credential / exchange write / order / actual-cash false を出す。
- schema validation が通る。

## 完了条件

- Bitget-only P10 artifact schema/model/CLI がある。
- P5 virtual gate lineage ref と sha256 を持つ。
- official docs verification refs と recorded request/response refs を持つ。
- external read/write boundary、network opt-in、redaction、recorded request/response artifact が固定される。
- demo/testnet/read-only result が actual cash ではないことを schema/model/stdout で固定する。
- focused tests、CLI catalog、current docs、full check が通る。

## 失敗条件

- Bitget demo/read-only を production readiness と読む。
- recorded response なしで complete status を出す。
- old docs memory を根拠にする。
- secret / credential / signature 値を artifact に保存する。
- order submit / exchange write / wallet / signing / live order を許可する。

## 影響範囲

Profit Core edge candidate workflow の artifact surface と CLI catalog に限定する。既存 Bitget public source fetcher、Bitget demo adapter、Crypto Perp actual cash ledger/report gate、external venue order path は変更しない。

## ロールバック方針

追加した schema、module、test、CLI registration、docs addendum を削除または revert する。既存 P5-P9 artifacts、Bitget public source、Bitget demo adapter は変更対象外。

## 代替案

- Bitget demo order lifecycle を直接実行する案: credential/API key と order write を伴うため P10 では却下。
- Hyperliquid read-only を同時実装する案: P10 は 1 venue ずつのため却下。
- `bitget_public_source` に統合する案: candidate source refresh と Profit Core external adapter evidence の責務が混ざるため却下。

## 未解決事項

なし。jurisdiction / account conditions は P10 artifact に current recheck requirement として残す。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-p10-external-venue-adapter-20260701-1638`

## 移行手順

なし。
