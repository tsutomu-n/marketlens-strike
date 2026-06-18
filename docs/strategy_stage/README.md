<!--
作成日: 2026-06-18_23:25 JST
更新日: 2026-06-19_00:46 JST
-->

# Strategy Stage

## 結論

Strategy Stage は、paper smoke、normal paper observation、drift review、micro live plan の進行条件を local policy と decision artifact で確認する first slice です。

これは paper execution permission でも live permission でもありません。`READY_FOR_PAPER_SMOKE_PLAN` や `READY_FOR_MICRO_LIVE_PLAN` は、次の計画 artifact を作るための evidence 判定であり、注文実行を許可しません。

## できること

- `strategy_stage_policy.v1` で、stage ごとの閾値と fixed safety を定義する。
- `strategy-stage-policy-validate` で、policy の schema、fixed safety、no-live boundary を検査する。
- `strategy-stage-decision` で、policy、operator review、paper observation status を読み、次 stage の計画に進める証拠があるかを判定する。
- decision artifact に `policy_id`、`policy_hash`、`selected_stage`、`selected_profile`、source artifact hash、passed / failed condition を残す。
- `normal_paper_observation`、`drift_review`、`micro_live_plan` では、paper status から `paper_evidence_summary` を作り、smoke pass と normal paper evidence を分けて残す。

## Command

```bash
uv run sis strategy-stage-policy-validate \
  --policy configs/strategy_stage_policies/<policy>.yaml \
  --out data/strategy_stage_policies/<policy-id>

uv run sis strategy-stage-decision \
  --strategy-id <strategy-id> \
  --stage paper_smoke \
  --policy configs/strategy_stage_policies/<policy>.yaml \
  --review-dir data/strategy_reviews/<review-id> \
  --out data/strategy_stage_decisions/<strategy-id>-paper-smoke
```

`normal_paper_observation`、`drift_review`、`micro_live_plan` では、必要に応じて `--paper-observation-status` に `strategy_paper_observation_status.v1` JSON を渡します。

## Artifact

- `strategy_stage_policy_validation.json`
- `strategy_stage_policy_validation.md`
- `strategy_stage_decision.json`
- `strategy_stage_decision.md`

`strategy_stage_decision.json` の `paper_evidence_summary` は、通常 paper observation の十分性を読むための要約です。

主な項目:

- `paper_status_present`
- `smoke_pass_present`
- `smoke_pass_counts_as_normal_pass`
- `normal_thresholds_met`
- `normal_fills.observed / required / remaining / met`
- `normal_trading_days.observed / required / remaining / met`

`smoke_pass_present=true` でも `normal_thresholds_met=false` または normal gap が残る場合、`drift_review` には進めません。paper smoke は配線・時刻・paper fill の最小確認であり、通常 paper observation の代替ではありません。

`data/` 配下の artifact は runtime / generated state です。fresh checkout では再生成してください。

## 次の Artifact

`READY_FOR_PAPER_SMOKE_PLAN` の stage decision から paper smoke の実行計画を作る場合は、[strategy_paper_smoke/README.md](../strategy_paper_smoke/README.md) を読む。

## 境界

- wallet、signing、exchange write、live order は使わない。
- `READY_FOR_PAPER_SMOKE_PLAN` は paper smoke plan の候補であり、paper order 実行許可ではない。
- `READY_FOR_NORMAL_PAPER_OBSERVATION` は通常 paper observation の候補であり、live readiness ではない。
- `READY_FOR_DRIFT_REVIEW` は drift review を作る候補であり、micro live permission ではない。
- `READY_FOR_MICRO_LIVE_PLAN` は micro live plan の候補であり、micro live execution permission ではない。
- manual override は記録されるが、failed evidence を自動で合格にしない。
