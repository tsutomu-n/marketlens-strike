<!--
作成日: 2026-06-17_10:00 JST
更新日: 2026-06-17_19:24 JST
-->

# Next Direction Current

## 結論

現時点の現実的な方向は、backtest-first / venue-neutral を維持しながら、Strategy Review の人間判断記録と paper observation の通常threshold状態を次段検証の土台にすることです。

これは確定ロードマップではありません。実装済み surface と未実装候補を混ぜず、次に狙いやすい方向、追加候補、優先しないことを分けるための current doc です。

## 正本

この文書は次を正本として読む:

- code: `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
- CLI help: `uv run sis --help`, `uv run sis strategy-review-record --help`
- current docs: `docs/CURRENT_STATE.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`, `docs/strategy_review/README.md`
- plan handoff: `plan/0609ここからの計画/03_venue_read_only_capability_probe/`
- implementation sequence: `docs/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md`

次は current proof として扱わない:

- stale plan
- historical audit
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

## Completed / Paused Candidate

### Strategy Review dogfood

`strategy-review-build` / `strategy-review-record` の dogfood は `dogfood-operator-current` で実行済み。tracked 記録は [strategy_review/DOGFOOD_REVIEW_2026-06-16.md](strategy_review/DOGFOOD_REVIEW_2026-06-16.md) に残す。

これは paper / live permission ではない。runtime hash は tracked doc に固定せず、`operator_review.yaml` と `strategy-review-record --validate-existing` で確認する。

### Paper observation status artifact

`strategy-paper-observation-status` は実装済み。出力は `data/research/strategy_lifecycle/paper_observation_status.json` と `data/reports/paper_observation_status.md`。

2026-06-17_19:11 JST の local run では `observation_state=needs_more_normal_paper_observation`、`next_action=continue_normal_paper_observation`、`normal_session_count=3`、`latest_normal_session_id=local-paper-20260617-190737`、`normal_thresholds_met=false`、`smoke_pass_present=true`、`smoke_pass_counts_as_normal_pass=false`。

### `venue-read-only-probe`

`venue-read-only-probe` は実装済みで、dogfood decision は `NO_ACTION`。

これは Bitget / Hyperliquid production readiness、credentialed read-only network readiness、paper readiness、live readiness を証明しない。

### Operations / audit / remediation refresh

2026-06-17_19:24 JST に `refresh-operations-artifacts` はローカル生成物の再計算として実行済み。latest snapshot は operations dashboard `overall_status=degraded`、`monitoring_status=degraded`、`execution_venue_count=2`、`execution_comparison_all_registries_present=false`、readiness snapshot `operations_ready=false`。

これは read-only / paper gate の失敗ではない。`phase-gate-review` は `READ_ONLY_GO` / `phase2_entry_allowed=true` のままだが、execution readiness と live readiness は未達。

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
