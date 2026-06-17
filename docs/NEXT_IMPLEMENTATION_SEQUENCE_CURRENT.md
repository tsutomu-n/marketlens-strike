<!--
作成日: 2026-06-17_12:00 JST
更新日: 2026-06-17_12:00 JST
-->

# Next Implementation Sequence Current

## 結論

PR単位を置かずに進める場合でも、次は venue / live / external network ではありません。

現実的な実装順は次です。

1. Strategy Review dogfood の tracked decision を残す。
2. paper observation の通常thresholdと smoke threshold を混同しない status artifact を追加する。
3. status artifact を見て、通常thresholdの paper observation を継続するか、文言修正だけで止めるかを決める。
4. lifecycle が paper observation insufficient から進んだ場合だけ、次の local preflight を考える。

この順序は、`venue-read-only-probe` の `NO_ACTION` と、追加調査で確認した Strategy Lifecycle の `CONTINUE_PAPER_OBSERVATION` / `PAPER_OBSERVATION_INSUFFICIENT` を前提にする。

## 追加調査で分かったこと

### Strategy Review dogfood は実行可能

次は repo 内の path で実行できる。

```bash
uv run sis strategy-review-build \
  --review-id <review_id> \
  --out data/strategy_reviews \
  --pack-path data/research/backtest_pack/strategy_backtest_pack.json \
  --validation-path data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --lifecycle-review data/research/strategy_lifecycle/strategy_lifecycle_review.json

uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/<review_id> \
  --decision REVIEWED_FOR_CONTEXT \
  --reviewer local-dogfood \
  --rationale "local dogfood; no paper or live permission"

uv run sis strategy-review-record \
  --review-dir data/strategy_reviews/<review_id> \
  --validate-existing
```

ただし、`--out /tmp/...` は不可。Strategy Review は artifact path を repo-relative に制限するため、repo 外の output は fail closed する。dogfood は `data/strategy_reviews/<review_id>/` に出す。

### 現行 lifecycle は paper observation 継続

現行 `data/research/strategy_lifecycle/strategy_lifecycle_review.json` の要点:

```text
decision=CONTINUE_PAPER_OBSERVATION
decision_reasons=PAPER_OBSERVATION_INSUFFICIENT
next_actions=Continue paper observation until thresholds are met.
P2_BLOCKER=0
LIVE_READINESS_BLOCKER=5
permits_live_order=false
wallet_used=false
exchange_write_used=false
```

これは live に近づいたという意味ではない。paper observation が通常thresholdに足りていないという意味。

### Smoke pass は通常 paper observation pass ではない

現行 artifact には次がある。

- normal session: `NEEDS_MORE_PAPER_OBSERVATION`
- smoke session: `PASS_PAPER_OBSERVATION_REVIEW`

smoke session は `min_fills_for_pass=1` / `min_trading_days_for_pass=1` なので、production paper observation pass として扱わない。

### 既存 `paper-cycle-history` は別軸

`uv run sis paper-cycle-history` は paper operations cycle の履歴を読む。NDX Strategy Lifecycle の paper observation session と smoke / normal threshold の区別を主目的にした artifact ではない。

そのため、次に足す価値があるのは Strategy Lifecycle 用の paper observation status artifact である。

## 実装順

### 1. Strategy Review Dogfood Decision

目的:

- Strategy Review の review packet が実務上読めることを1回確認する。
- `operator_review.yaml` が hash 付きで再検証できることを確認する。
- review packet を paper / live permission と誤読しない判断を tracked doc に残す。

対象:

- 入力 artifact:
  - `data/research/backtest_pack/strategy_backtest_pack.json`
  - `data/research/backtest_pack/strategy_backtest_pack_validation.json`
  - `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- 出力 artifact:
  - `data/strategy_reviews/<review_id>/review.md`
  - `data/strategy_reviews/<review_id>/review_manifest.json`
  - `data/strategy_reviews/<review_id>/operator_review.yaml`
- tracked decision:
  - `docs/strategy_review/STRATEGY_REVIEW_DOGFOOD_CURRENT.md`

Decision の既定:

- `REVIEWED_FOR_CONTEXT`

`PAPER_OBSERVATION_CANDIDATE` は既定にしない。現行 lifecycle が `CONTINUE_PAPER_OBSERVATION` であり、paper observation が不足しているため。

完了条件:

- `strategy-review-build` が `READY_FOR_HUMAN_REVIEW` を出す。
- `strategy-review-record` が `status=pass` を出す。
- `--validate-existing` が `status=pass` を出す。
- tracked decision に review hash、operator review hash、lifecycle decision、non-claims を残す。

停止条件:

- `review_status` が `BLOCKED_BOUNDARY_VIOLATION`。
- `source_safety.status` が `PASS` でない。
- `pack_validation_pass_is_readiness_proof` が `false` でない。
- `operator_review.yaml` が `live_allowed=false` / `paper_execution_allowed=false` を守らない。
- output を repo 外に置こうとして path guard に失敗する。

### 2. Paper Observation Status Artifact

目的:

- 現行 paper observation が「通常thresholdで不足」なのか「smokeだけpass」なのかを1枚で読めるようにする。
- Strategy Review dogfood 後の次判断を、paper observation の実状態に寄せる。

追加候補:

- command: `strategy-paper-observation-status`
- pure builder: `src/sis/research/strategy_lifecycle/paper_observation_status.py`
- CLI wiring: `src/sis/commands/research.py`
- schema: `schemas/strategy_paper_observation_status.v1.schema.json`
- tests:
  - `tests/research/test_strategy_paper_observation_status.py`

入力:

- `data/research/ndx/paper_observation_review_decision.json`
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- `data/paper/observations/*/paper_observation_session_manifest.json`
- `data/paper/observations/*/paper_observation_review_decision.json`
- optional: `data/paper/observations/*/paper_observation_cycle_summary.json`

出力:

- `data/research/strategy_lifecycle/paper_observation_status.json`
- `data/reports/paper_observation_status.md`

必須 field:

```text
schema_version
generated_at
status
canonical_review_decision
lifecycle_decision
normal_session_count
smoke_session_count
latest_normal_session_id
latest_normal_decision
latest_smoke_session_id
latest_smoke_decision
normal_thresholds_met
smoke_pass_present
smoke_pass_counts_as_normal_pass
permits_live_order
wallet_used
signing_used
exchange_write_used
venue_write_used
next_action
sessions[]
```

固定境界:

- `smoke_pass_counts_as_normal_pass=false`
- `permits_live_order=false`
- `wallet_used=false`
- `signing_used=false`
- `exchange_write_used=false`
- `venue_write_used=false`

Decision logic:

- normal latest が `PASS_PAPER_OBSERVATION_REVIEW`: `status=normal_observation_passed_not_live_ready`
- normal latest が `NEEDS_MORE_PAPER_OBSERVATION`: `status=needs_more_normal_paper_observation`
- normal latest が `STOP_PAPER_OBSERVATION`: `status=paper_observation_stopped`
- normal session がなく smoke だけ pass: `status=smoke_only_not_normal_pass`
- canonical review / lifecycle が欠損: `status=incomplete_artifacts`

完了条件:

- status artifact が schema validate できる。
- normal と smoke が別 count / 別 latest として出る。
- smoke pass を normal pass と読めない。
- live / wallet / signing / exchange write は常に false。

停止条件:

- status artifact が paper order を実行する。
- paper observation ledger を改変する。
- smoke pass を normal pass に昇格する。
- `PASS_PAPER_OBSERVATION_REVIEW` を live ready と表現する。

### 3. 通常thresholdの Paper Observation 継続

目的:

- status artifact が `needs_more_normal_paper_observation` の場合だけ、通常thresholdで paper observation を継続する。

実行候補:

```bash
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-id <normal-session-id>
```

禁止:

- `--smoke` の結果を通常 pass と扱うこと。
- paper observation から live canary へ直行すること。
- wallet / signing / exchange write。

完了条件:

- session manifest が `smoke=false`。
- thresholds が default または明示した通常threshold。
- `research-ndx-paper-observation-review` と `strategy-lifecycle-review` が更新される。
- lifecycle decision を再度 Strategy Review dogfood に渡せる。

停止条件:

- backtest acceptance が missing / fail。
- operator promotion hash mismatch。
- paper review が `STOP_PAPER_OBSERVATION`。
- boundary violation。

### 4. 再Review

通常thresholdの paper observation を進めた場合だけ、Strategy Review を再実行する。

目的:

- lifecycle decision が変わったか確認する。
- paper observation が不足したままか、次の local preflight へ進めるかを記録する。

ここでも `PAPER_OBSERVATION_CANDIDATE` は慎重に扱う。paper execution permission ではない。

## 後回しにするもの

次は、現時点ではまだ早い。

- Strategy Case Registry
- Paper Bridge Validation
- credentialed Bitget read-only network probe
- credentialed Hyperliquid read-only network probe
- Bitget demo order lifecycle
- production venue schema widening
- live canary plan

理由:

- Strategy Case Registry は複数 strategy review の運用実績が出てからでよい。
- Paper Bridge Validation は paper observation status が整理されてからでよい。
- credentialed network probe と venue widening は、直近の venue dogfood が `NO_ACTION` なので根拠がない。
- live canary は lifecycle が paper observation insufficient の間は対象外。

## 検証方針

Strategy Review dogfood:

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
uv run sis strategy-review-build --review-id <review_id> --out data/strategy_reviews
uv run sis strategy-review-record --review-dir data/strategy_reviews/<review_id> --decision REVIEWED_FOR_CONTEXT --reviewer local-dogfood --rationale "local dogfood; no paper or live permission"
uv run sis strategy-review-record --review-dir data/strategy_reviews/<review_id> --validate-existing
```

Paper observation status implementation:

```bash
uv run pytest -q tests/research/test_strategy_paper_observation_status.py
uv run sis strategy-paper-observation-status --help
uv run sis strategy-paper-observation-status
uv run python scripts/check_current_docs.py
git diff --check
```

Full gate:

```bash
./scripts/check
```

## 現実的なゴール

短期ゴール:

- review packet と paper observation status を、誰が読んでも同じ結論になる形にする。

中期ゴール:

- 通常thresholdの paper observation を継続できる状態にする。

非ゴール:

- live trading。
- Bitget / Hyperliquid production対応。
- external network readiness。
- paper pass から live ready を主張すること。
