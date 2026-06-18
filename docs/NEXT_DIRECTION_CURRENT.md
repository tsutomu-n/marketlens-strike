<!--
作成日: 2026-06-17_10:00 JST
更新日: 2026-06-18_19:47 JST
-->

# Next Direction Current

## 結論

現時点の現実的な方向は、backtest-first / venue-neutral を維持しながら、Strategy Review の人間判断記録と paper observation の通常threshold状態を次段検証の土台にすることです。

これは確定ロードマップではありません。実装済み surface と未実装候補を混ぜず、次に狙いやすい方向、追加候補、優先しないことを分けるための current doc です。

完成形の設計定義は [TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md](TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md) を読む。これは current implementation proof ではなく、個人システムトレーダー向けに stage policy、paper smoke、drift review、micro live plan gate をどう位置づけるかの target definition です。

## 正本

この文書は次を正本として読む:

- code: `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
- CLI help: `uv run sis --help`, `uv run sis strategy-review-record --help`
- current docs: `docs/CURRENT_STATE.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`, `docs/strategy_review/README.md`

次は current proof として扱わない:

- stale plan
- historical audit
- archived plan handoff
- archived implementation-sequence snapshot: `docs/archive/2026-06-17-doc-routing/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md`
- `data/` runtime artifact
- old pass count / public command count snapshot

## Near-Term Practical Direction

1. Backtest-first / venue-neutral を継続する。
2. Strategy Review の `strategy-review-build` / `strategy-review-record` を、既存 artifact を人間が読み、判断記録を残すための土台として使う。
3. `PAPER_OBSERVATION_CANDIDATE` は validation candidate としてのみ扱い、paper 実行許可や paper intent 生成許可とは読まない。
4. paper observation は normal threshold と smoke threshold を分けて読む。smoke pass は normal paper observation pass ではない。
5. future venue は `venue-read-only-probe` dogfood 済みで、現時点では `NO_ACTION`。schema や paper path は広げない。

## Implementation-Ready Candidate

### Normal threshold paper observation continuation

次に実行価値がある候補は、通常thresholdの paper observation 継続です。Strategy Review dogfood は [strategy_review/DOGFOOD_REVIEW_2026-06-16.md](strategy_review/DOGFOOD_REVIEW_2026-06-16.md) に記録済みで、paper observation status artifact も `strategy-paper-observation-status` として実装済みです。

目的:

- `needs_more_normal_paper_observation` の間は、通常thresholdの observation を続ける。
- `--smoke` の pass を normal pass として扱わない。
- lifecycle の `CONTINUE_PAPER_OBSERVATION` を live readiness と読まない。

実務上の注意:

- ここでいう「継続」は、新しい通常観察の証拠を積むことです。同じ trading day の artifact を rerun しても `10 trading days` の代替証拠にはならない。
- 現在の不足量は固定値としてこの文書に写さず、`strategy-paper-observation-status` の `latest_normal_requirement_gaps.fills` と `latest_normal_requirement_gaps.trading_days` を読む。
- fills が満たされていても trading days が残っている場合、必要なのは同日 fill の水増しではなく、別 trading day を含む通常観察です。
- 既存 session に追記する場合は `strategy-paper-observation-append` を使う。新規 session を切る場合も、`latest_normal_requirement_gaps` が進んだかを `strategy-paper-observation-status` で確認する。

実行候補:

```bash
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-id <normal-session-id>
```

## Needs A New Explicit Plan

次は、進める前に別の明示計画が必要です。

- paper bridge validation
- Strategy Case registry
- UI
- credentialed Bitget read-only network probe
- credentialed Hyperliquid read-only network probe
- Bitget demo order lifecycle
- production venue schema widening

## External Input Restart Checklist

外部入力が揃った場合だけ、次の順で read-only 再確認する。ここでの再確認は execution readiness の観測であり、paper / live 許可ではない。

### Trade[XYZ] read-only execution state

必要な入力:

- `SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>`
- `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1`

再確認コマンド:

```bash
uv run sis execution-read-only-surfaces
uv run sis execution-snapshot --venue trade_xyz
uv run sis execution-drift-overview
uv run sis phase-gate-review
```

期待する読み方:

- public user address と opt-in がない状態では external API を呼ばず、`trade_xyz_execution_state_user_address_missing` または opt-in required として止まる。
- public user address と opt-in がある場合だけ account state / open orders / fills を read-only で読む。
- 成功しても wallet、signing、exchange write、live order の許可にはならない。

### Bitget demo read-only smoke

必要な入力:

- `BITGET_DEMO_API_KEY`
- `BITGET_DEMO_API_SECRET`
- `BITGET_DEMO_PASSPHRASE`

再確認コマンド:

```bash
uv run sis bitget-demo-smoke
uv run sis execution-read-only-surfaces
uv run sis execution-drift-overview
uv run sis phase-gate-review
```

期待する読み方:

- demo credentials は production Bitget futures readiness ではない。
- `bitget_demo` は demo 検証用 surface であり、Strategy Lab の正式 production venue ではない。
- smoke 成功は live order lifecycle や exchange write 許可ではない。

### Normal paper observation

必要な入力:

- 新しい trading day を含む通常 paper observation evidence。
- 同じ trading day の artifact rerun や fill 水増しは `10 trading days` の代替にしない。

再確認コマンド:

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

期待する読み方:

- `latest_normal_requirement_gaps.trading_days` が進んだかを見る。
- `smoke_pass_counts_as_normal_pass=false` を維持する。
- `normal_thresholds_met=true` になるまで live readiness と読まない。

## Completed / Paused Candidate

### Strategy Review dogfood

`strategy-review-build` / `strategy-review-record` の dogfood は `dogfood-operator-current` で実行済み。tracked 記録は [strategy_review/DOGFOOD_REVIEW_2026-06-16.md](strategy_review/DOGFOOD_REVIEW_2026-06-16.md) に残す。

これは paper / live permission ではない。runtime hash は tracked doc に固定せず、`operator_review.yaml` と `strategy-review-record --validate-existing` で確認する。

### Paper observation status artifact

`strategy-paper-observation-status` は実装済み。出力は `data/research/strategy_lifecycle/paper_observation_status.json` と `data/reports/paper_observation_status.md`。

確認時は次を再実行し、`observation_state`、`next_action`、`normal_thresholds_met`、`latest_normal_requirement_gaps`、`smoke_pass_counts_as_normal_pass`、`live_conversion_allowed` を読む。

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

注意: `normal_session_count` は通常sessionの数であり、通常threshold達成の代替証拠ではない。現行 review logic では、最新の通常session自体が `min_fills_for_pass` と `min_trading_days_for_pass` を満たした時だけ `normal_thresholds_met=true` になる。同じ trading day の fill を増やしても、10 trading days の代替証拠にはならない。

### `venue-read-only-probe`

`venue-read-only-probe` は実装済みで、dogfood decision は `NO_ACTION`。

これは Bitget / Hyperliquid production readiness、credentialed read-only network readiness、paper readiness、live readiness を証明しない。

実装計画と dogfood 記録は `plan/archive/2026-06-17-plan-routing/0609ここからの計画/03_venue_read_only_capability_probe/` に archive 済み。現行 next action としては読まない。

### Operations / audit / remediation refresh

operations / audit / remediation 系の生成物は runtime artifact なので、この文書に固定値を写さない。確認時は次を再実行し、生成物の `overall_status`、`monitoring_status`、execution gap、readiness gap、`strict_validation_issue_count` を読む。

```bash
uv run sis refresh-operations-artifacts
uv run sis operations-dashboard
uv run sis readiness-snapshot
uv run sis execution-snapshot --venue trade_xyz
uv run sis execution-drift-overview
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

Trade[XYZ] は read-only execution state collector contract 実装済みだが、通常実行では external API を使わず、public user address 未設定として止まる。未設定時の execution gap は `trade_xyz_execution_state_user_address_missing` と `set_trade_xyz_execution_state_public_user_address` を見る。Bitget demo は demo credentials と read-only network probe の有無を別に確認する。

これは read-only / paper gate の失敗とは別に読む。`phase-gate-review` が通過系に見えても、それは execution readiness や live readiness の証明ではない。`check-go-no-go` と evidence card は補助 report であり、live readiness の正本ではない。

## Not On Current Roadmap

次は現行 roadmap には入れません。実施するなら別計画、承認、stop condition が必要です。

- production live trading
- wallet / signing
- exchange write
- Bitget futures / Hyperliquid perp を Strategy Lab schema に入れること
- backtest pass から paper ready / live ready を主張すること
- `READ_ONLY_GO` を live ready と読むこと
- `catalog known` を venue enabled と読むこと
- `read-only probe` を network readiness と読むこと

## 誤読防止

- `計画あり` は `実装決定` ではない。
- `catalog known` は `venue enabled` ではない。
- `read-only probe` は `network readiness` ではない。
- `PAPER_OBSERVATION_CANDIDATE` は paper 実行許可ではない。
- `READ_ONLY_GO` は live ready ではない。
- fixed public command count は current truth ではない。確認時点で `uv run sis --help` を再実行する。
