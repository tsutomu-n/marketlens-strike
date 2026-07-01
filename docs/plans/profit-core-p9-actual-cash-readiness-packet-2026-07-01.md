<!--
作成日: 2026-07-01_16:08 JST
更新日: 2026-07-01_16:08 JST
-->

# Profit Core P9 Actual Cash Readiness Packet Plan

## チェックポイントID

P9: Actual Cash Readiness Packet

## 目的

tiny actual-cash measurement の前に、candidate lineage、実行前条件、上限、credential 境界、jurisdiction 再確認、rollback、flat reconciliation、kill switch、stop condition を 1 つの packet に固定する。

この packet は human approval の入力であり、actual cash 実行許可ではない。

## 現状

- P6 `profit_core_evidence_packet.v1` は protocol / candidate / bridge / multiplicity / backtest kill gate / virtual gate / optional risk review refs を束ねる。
- P7 `profit_core_adversarial_review.v1` は machine/manual adversarial finding を記録し、LLM API / external send / approval permission を false に固定する。
- P8 `profit_core_risk_taker_sprint_isolation.v1` は `risk_taker_sprint` output を `SPECULATIVE_SPRINT` として隔離し、actual-cash direct promotion を禁止する promotion debt を持つ。
- 既存 Crypto Perp actual-cash report gate は actual cash rows を report/gate 化する後段であり、P9 の readiness packet ではない。

## 制約

- external service write、credentialed write、order submit、wallet、signing、live/tiny-live/actual-cash execution は行わない。
- venue terms / jurisdiction は legal clearance と読まない。実行直前の current docs / official docs / user-provided account conditions 再確認項目として記録する。
- secret 値や credential 値を artifact に保存しない。
- `demo` / `testnet` / `paper` / `virtual` を actual cash proof と読まない。
- `risk_taker_sprint` artifact が付く場合、promotion debt が残る限り actual-cash readiness は blocked とする。

## 対象ファイル

- `schemas/profit_core_actual_cash_readiness_packet.v1.schema.json`
- `src/sis/edge_candidates/actual_cash_readiness.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_actual_cash_readiness.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`

## 実装方針

`edge-candidate-actual-cash-readiness-packet-build` を追加し、以下を入力にする。

- `--evidence-packet`: P6 `profit_core_evidence_packet.v1`
- `--adversarial-review`: P7 `profit_core_adversarial_review.v1`
- `--readiness-plan`: local JSON/YAML readiness plan
- `--risk-sprint-isolation`: optional P8 `profit_core_risk_taker_sprint_isolation.v1`

readiness plan は、max notional、max daily loss、isolated margin、withdrawal disabled、IP restriction、flat reconciliation、kill switch、stop condition、venue terms/jurisdiction recheck、operator approval requirement を持つ。

出力 packet は次を固定する。

- `actual_cash_execution_allowed=false`
- `tiny_live_allowed=false`
- `paper_execution_allowed=false`
- `credential_created=false`
- `credential_used=false`
- `credential_use_allowed=false`
- `exchange_write_used=false`
- `exchange_write_allowed=false`
- `live_order_submitted=false`
- `wallet_used=false`
- `signing_used=false`
- `external_send_performed=false`
- `requires_human_approval=true`
- `packet_is_execution_permission=false`

## 実装手順

1. RED tests を追加する。
2. schema と Pydantic model を追加する。
3. readiness plan parser と secret key scan を実装する。
4. P6/P7/P8 input validation と source refs を実装する。
5. CLI command を追加する。
6. CLI catalog と final summary を更新する。
7. focused tests、ruff、CLI catalog、current docs、full check を実行する。

## テスト方針

- complete readiness plan で `PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL` になる。
- missing controls は packet を作るが `BLOCKED_READINESS_CONTROLS` になる。
- secret-like key や credential values はエラーにして artifact を書かない。
- P7 hard blocker があれば `BLOCKED_ADVERSARIAL_REVIEW` になる。
- P8 sprint isolation が付けば promotion debt により `BLOCKED_PROMOTION_DEBT` になる。
- CLI stdout は network / credential / exchange write / live order / actual-cash execution false を出す。
- schema validation が通る。

## 完了条件

- `profit_core_actual_cash_readiness_packet.v1` schema と local model がある。
- CLI で packet を生成できる。
- packet が P6/P7/P8 lineage ref と sha256 を持つ。
- P9 必須 controls が明示される。
- actual-cash execution permission と credential / external write が全て false に固定される。
- focused tests、CLI catalog、current docs、full check が通る。

## 失敗条件

- packet が execution approval / order permission / legal clearance と読める。
- secret 値が artifact に入る。
- P7 hard blocker または P8 promotion debt を無視して complete status を出す。
- missing flat reconciliation / stop condition / kill switch を許容して complete status を出す。

## 影響範囲

Profit Core edge candidate workflow の artifact surface と CLI catalog に限定する。Crypto Perp actual cash ledger/report gate、external venue adapters、credentials、network I/O、order path は変更しない。

## ロールバック方針

追加した schema、module、test、CLI registration、docs addendum を削除または revert する。既存 P6-P8 artifacts と Crypto Perp actual-cash gate は変更対象外。

## 代替案

- 既存 `crypto-perp-actual-cash-report-gate` を流用する案: P9 は事前 readiness packet で、既存 gate は actual cash rows 後の report gate なので却下。
- credential preflight を実装する案: P9 の範囲を超え、secret / external state / account condition に触れるため却下。
- human approval artifact をここで発行する案: packet が approval そのものに見えるため却下。

## 未解決事項

なし。venue terms / jurisdiction は実行直前の current verification 項目として packet に残す。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-p9-actual-cash-readiness-20260701-1606`

## 移行手順

なし。
