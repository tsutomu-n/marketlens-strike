<!--
作成日: 2026-07-11_13:36 JST
更新日: 2026-07-11_18:53 JST
-->

# Crypto Perp Fail-Closed Decision Chain Plan

> **Status: SUPERSEDED / HISTORICAL.** この文書は`bias_guard=BLOCKED`伝播修正時点の計画・検証記録です。後続のwarning semanticsとprofit-evidence hardeningにより、現在の停止理由・artifact contractは変わっています。
>
> 現行chainはguard `BLOCKED`、PBO `NOT_ESTIMABLE`、candidate/gate REJECT、kill/leaderboard KILL、strict v2 12-input packet `BLOCKED_BY_BIAS_GUARD`です。専用PBO証跡producerとposition accountingは未実装です。
>
> 現行計画: [CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md](CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md)

## Checkpoint ID

`FAIL-CLOSED-DECISION-CHAIN-2026-07-11`

## Purpose

`bias_guard=BLOCKED` が candidate pack、no-cash gate、kill report、leaderboard、human review packet を通過しないようにし、現在の30-event artifactを `BLOCKED_BY_BIAS_GUARD` で停止させる。

## Current State

- Branch: `ai/human-review-packet-20260709-2200`
- Start HEAD: `9c8de64`
- `bias_guard=BLOCKED`に対し、candidate packとgateがHOLD、packetがREADYになっている。
- bias guard再利用条件はevent count一致のみで、tournament rowsの同一性を保証していない。

## Constraints

- 既存のbias guard閾値と`stress_cash_non_negative`の意味は変えない。
- Paper、actual cash、wallet、signing、exchange write、live orderのフラグはfalseを維持する。
- Runtime artifactはGit管理対象にしない。
- Commit、push、merge、`9c8de64`の単独cherry-pickは行わない。

## Implementation

1. BLOCKED、missing、unknown、lineage mismatchの失敗テストを先に追加する。
2. Tournament rowsのevent setとfile SHA-256が一致するbias guardだけを再利用する。
3. Candidate packはBLOCKEDをREJECT、missing/unknownをCOLLECT_MORE_DATAにする。
4. No-cash gateは`bias_guard_status`を独立検査する。
5. Kill reportに必須`--gate`を追加し、leaderboardとpacketまで停止理由を伝播する。
6. 現在の30-event入力からruntime artifactを再生成し、期待する停止連鎖を確認する。
7. Public docsとCLI catalogを更新し、focused/full checksを実行する。

## Test Strategy

Focused tests:

```bash
uv run pytest \
  tests/crypto_perp/test_bias_guards.py \
  tests/crypto_perp/test_backtest_candidate_pack.py \
  tests/crypto_perp/test_no_cash_backtest_gate.py \
  tests/crypto_perp/test_no_trade_kill_report.py \
  tests/crypto_perp/test_candidate_leaderboard.py \
  tests/crypto_perp/test_human_review_packet.py \
  -q
```

Final checks:

```bash
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
uv run sis --help
./scripts/check
```

## Completion Conditions

- Candidate pack: `BACKTEST_REJECT`
- No-cash gate: `NO_CASH_BACKTEST_REJECT`
- Kill report: `KILL_UPSTREAM_GATE_REJECTED`
- Leaderboard: `KILL`
- Human review packet: `BLOCKED_BY_BIAS_GUARD`
- `next_action=FIX_REVIEW_PACKET_BLOCKERS`
- Full checkが成功し、branchがmerge holdのままである。

## Failure Conditions

- BLOCKEDまたはmissing/unknown guardがHOLD/READYに進む。
- 異なるtournament rowsのguardをevent countだけで再利用する。
- 安全フラグのいずれかがtrueになる。
- Runtime artifactまたは`.ai-work` がcommit対象に入る。

## Impact And Migration

`crypto-perp-no-trade-kill-report` の`--gate PATH`を必須化する。旧呼び出しは明示的に失敗するため、repo内docsとテストを同時に更新する。JSON schemaは既存artifactの読取互換性を保つadditive変更とする。

## Rollback

本修正の未commit差分だけを取り除き、runtime artifactを`9c8de64`時点のコマンドで再生成する。既存の2commitは変更しない。

## Alternatives Rejected

- Gateだけを修正する: candidate packの誤判定が残る。
- Kill reportのgate入力を任意にする: 弱い経路が残る。
- Bias guard閾値を変える: 判定伝播修正と戦略意味の変更が混在する。

## Verification Result

- Current 30-event artifact produced the expected stopped chain through `BLOCKED_BY_BIAS_GUARD`.
- `BIAS_GUARD_FAILED_stress_cash_non_negative` propagated through every downstream artifact.
- Focused suite: 54 passed.
- Full `./scripts/check`: 2969 passed; all lint, format, docs, catalog, and type checks passed.
- No runtime artifact, `.ai-work`, commit, push, merge, or cherry-pick was added to the tracked diff.
- Merge hold remained active pending an explicit decision on the bias guard contract.

## Follow-up 2026-07-11

The separate warning-semantics plan retained all fail-closed routing, changed only `stress_cash_non_negative` to a warning, invalidated reuse of old-contract guards, and regenerated the current chain to READY-for-planning with the warning preserved. This historical plan remains evidence of the earlier stopped state, not the current artifact decision.
