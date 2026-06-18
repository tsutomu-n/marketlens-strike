<!--
作成日: 2026-06-18_23:39 JST
更新日: 2026-06-18_23:39 JST
-->

# Strategy Paper Smoke

## 結論

Strategy Paper Smoke は、`READY_FOR_PAPER_SMOKE_PLAN` の stage decision から、既存 `strategy-paper-observation-cycle --smoke` を安全に実行するための plan artifact を作る first slice です。

これは paper execution permission ではありません。`strategy-paper-smoke-plan` は paper order を実行せず、必要 source artifact、hash、smoke threshold、実行コマンド preview、no-live boundary を JSON / Markdown に固定します。

## できること

- `strategy_stage_decision.v1` が `READY_FOR_PAPER_SMOKE_PLAN` か確認する。
- `strategy_stage_policy.v1` から paper smoke threshold を読む。
- backtest acceptance、paper candidate pack、promotion decision、operator promotion の source artifact が存在するか確認する。
- `strategy_paper_smoke_plan.v1` と Markdown report を出す。
- `strategy-paper-observation-cycle --smoke` の実行 preview を残す。
- source artifact が足りない場合も、`NEEDS_SOURCE_ARTIFACTS` として plan artifact に残す。

## Command

```bash
uv run sis strategy-paper-smoke-plan \
  --stage-decision data/strategy_stage_decisions/<strategy-id>-paper-smoke/strategy_stage_decision.json \
  --policy configs/strategy_stage_policies/<policy>.yaml \
  --session-id <smoke-session-id> \
  --out data/strategy_paper_smoke/<strategy-id>
```

## Artifact

- `strategy_paper_smoke_plan.json`
- `strategy_paper_smoke_plan.md`

`data/` 配下の artifact は runtime / generated state です。fresh checkout では再生成してください。

## Status

- `READY_TO_RUN_SMOKE_CYCLE`: 必要 source artifact が揃い、smoke cycle を手動実行できる計画状態。
- `NEEDS_SOURCE_ARTIFACTS`: stage は通っているが、既存 cycle に必要な source artifact が足りない。
- `NEEDS_STAGE_APPROVAL`: stage decision が paper smoke plan ready ではない。
- `BLOCKED_BOUNDARY_VIOLATION`: live / wallet / signing / exchange write 系の禁止境界に触れている。

## 境界

- `strategy-paper-smoke-plan` は paper order を実行しない。
- `READY_TO_RUN_SMOKE_CYCLE` は paper smoke cycle の実行計画であり、通常 paper observation pass ではない。
- smoke pass は normal paper observation pass として数えない。
- wallet、signing、exchange write、live order は使わない。
- 実際に paper smoke を走らせる場合は、生成された execution preview を読み、人間が明示的に `strategy-paper-observation-cycle --smoke` を実行する。
