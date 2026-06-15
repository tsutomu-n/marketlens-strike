<!--
作成日: 2026-06-15_19:01 JST
更新日: 2026-06-15_19:01 JST
-->

# Backtest To Paper Observation Evidence Map

## 結論

BP0 の追加調査結果は次の通り。

- 既存 route はすでに機能している。現在 artifact 上は `PASS_BACKTEST_ACCEPTANCE`、NDX paper review は `NEEDS_MORE_PAPER_OBSERVATION`、Strategy Lifecycle は `CONTINUE_PAPER_OBSERVATION` まで進んでいる。
- したがって、今すぐ新しい paper observation gate や bridge adapter を作る必要はない。
- ただし、`strategy-backtest-pack` / `strategy-backtest-pack-validate` の rich evidence は、現行 `strategy-lifecycle-review` の標準入力には直接消費されていない。pack validation を lifecycle の必須 gate にするなら、その時だけ最小 bridge か schema 変更を検討する。
- 前回 plan の artifact path 例に誤りがあった。正しい pack path は `data/research/backtest_pack/strategy_backtest_pack.json` であり、`strategy_backtest_pack_manifest.json` ではない。

実務上の次手は、bridge 実装ではなく、paper observation を継続して `min_fills_for_pass=20` と `min_trading_days_for_pass=10` を満たすこと。pack validation PASS は operator preflight として保持する。

## 現在の artifact 状態

| Artifact | 現在値 | 読み |
|---|---:|---|
| `data/research/backtest_pack/strategy_backtest_pack.json` | `schema_version=strategy_backtest_pack.v1`, `artifact_count=43`, `suite_method_count=5`, `suite_run_count=5` | 完成済み backtest pack |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `decision=PASS`, `check_count=198`, `failed_count=0` | pack integrity / no-live boundary は PASS |
| `data/research/strategy_lifecycle/backtest_acceptance_decision.json` | `decision=PASS_BACKTEST_ACCEPTANCE` | Strategy Lifecycle 用 backtest acceptance は PASS |
| `data/research/paper_candidate_pack.json` | `selected_candidate_count=1`, `paper_ready_claimed=false`, `live_ready_claimed=false` | paper candidate は作成済み |
| `data/research/promotion_decision.json` | `decision=promote`, `required_evidence=[trial_ledger,paper_candidate_pack]` | generic promotion は paper observation へ promote |
| `data/research/ndx/paper_observation_gate_decision.json` | `decision=APPROVE_PAPER_OBSERVATION_REVIEW` | NDX paper review gate は通過 |
| `data/research/ndx/operator_promotion_decision.json` | `decision=promote_to_paper_observation` | NDX operator promotion は paper observation を許可 |
| `data/research/ndx/paper_observation_review_decision.json` | `decision=NEEDS_MORE_PAPER_OBSERVATION`, `fills_count=1`, `trading_day_count=1` | 失敗ではなく観測不足 |
| `data/research/strategy_lifecycle/strategy_lifecycle_review.json` | `decision=CONTINUE_PAPER_OBSERVATION`, `LIVE_READINESS_BLOCKER=5` | 次は paper observation 継続。live ではない |

## Evidence Map

| Evidence | Current consumer | Status | 実務判断 |
|---|---|---|---|
| `strategy_backtest_metrics.json` の `summary.backtest_passed`, `pass_min_trade_count`, `pass_all_thresholds` | `strategy-backtest-acceptance` | already-consumed | lifecycle の backtest acceptance 判定に使われている |
| `strategy_backtest_acceptance_decision.v1` | `strategy-paper-observation-cycle`, `paper_observation_session_manifest.v1`, `strategy-lifecycle-review` | already-consumed | paper session と lifecycle の主要 input |
| `strategy_backtest_pack.v1` の suite count / artifact hashes / external framework policy | `strategy-backtest-pack-validate`, `strategy-backtest-artifact-summary` | available-but-not-consumed | lifecycle は直接読まない。operator preflight として扱う |
| `strategy_backtest_pack_validation.v1` の `decision=PASS` / `failed_count=0` | `strategy-backtest-artifact-summary` | available-but-not-consumed | lifecycle の必須条件にしたい場合だけ bridge 候補 |
| robustness artifacts: stress / regime split / rolling stability / benchmark relative / baseline / no-lookahead / execution simulation / assumption ledger / trial ledger | pack / compare / artifact summary | available-but-not-consumed | paper observation 開始条件ではなく研究 evidence。採用条件にするなら別 gate が必要 |
| `backtest_data_availability_ledger.v1` の enabled local rows | pack validation / artifact summary | available-but-not-consumed | local data preflight として有効。paper review の runtime evidence ではない |
| Bitget / Hyperliquid / Coinalyze future rows | none | not-applicable | direct schema widening / collector は future scope のまま |
| `paper_candidate_pack.v1` | `strategy-paper-observation-cycle`, session manifest source hash | already-consumed | paper intent preview の入力 |
| `promotion_decision.v1` | `strategy-paper-observation-cycle`, session manifest source hash | already-consumed | `decision=promote` の時だけ intent が生成される |
| `ndx_paper_observation_gate_decision.v1` | NDX operator promotion | already-consumed | NDX 専用 gate。venue-neutral pack と混同しない |
| `ndx_operator_promotion_decision.v1` | paper candidate pack provenance, paper observation session, NDX paper review | already-consumed | paper observation の operator approval evidence |
| `paper_observation_session_manifest.v1` | NDX paper observation review | already-consumed | source hash replay に使われる |
| `ndx_paper_observation_review_decision.v1` | `strategy-lifecycle-review` | already-consumed | 現在は `NEEDS_MORE_PAPER_OBSERVATION` |
| `phase_gate_review_summary.json` | `strategy-lifecycle-review` | already-consumed | live-readiness blocker が残るため live へ進めない |
| `--smoke` paper cycle result | local verification only | not-applicable | production paper pass evidence に使わない |

## 見落とし修正

### 1. pack path の誤り

誤り:

```text
data/research/backtest_pack/strategy_backtest_pack_manifest.json
```

正:

```text
data/research/backtest_pack/strategy_backtest_pack.json
```

`strategy_backtest_pack_validation.v1` の `pack_path` も `data/research/backtest_pack/strategy_backtest_pack.json` を指している。

### 2. bridge adapter は現時点の必須ではない

現在の artifact chain は次まで到達している。

```text
PASS_BACKTEST_ACCEPTANCE
-> promote / promote_to_paper_observation
-> NEEDS_MORE_PAPER_OBSERVATION
-> CONTINUE_PAPER_OBSERVATION
```

これは「paper observation が未実装」でも「bridge がないため停止」でもない。単に paper observation の fill / trading day が足りない状態。

### 3. pack validation PASS は lifecycle decision の直接入力ではない

`strategy-lifecycle-review` は backtest acceptance、paper review、phase gate を読む。`strategy_backtest_pack_validation.json` は現時点で lifecycle review の必須 input ではない。

これを欠陥と見るかどうかは方針次第。

- operator preflight で十分なら、実装不要。
- lifecycle decision に pack validation PASS を強制したいなら、schema / CLI / tests を伴う小変更が必要。

## 推奨判断

現実的には、まず実装しない。

理由:

- 既存 route はすでに paper observation 継続状態まで動いている。
- pack validation を lifecycle に直接入れても、現在の next action は `CONTINUE_PAPER_OBSERVATION` から変わらない。
- 新 schema / CLI は、paper observation 継続という実務上のボトルネックを解消しない。

ただし、operator 手順では次を明示するのがよい。

1. `strategy-backtest-pack`
2. `strategy-backtest-pack-validate`
3. `strategy-backtest-acceptance`
4. `build-paper-candidate-pack`
5. `promotion-decision --decision promote`
6. `strategy-paper-observation-cycle` without `--smoke`
7. `strategy-lifecycle-review`

## Bridge が必要になる条件

次のいずれかを採用するなら、BP2 を実装する。

- `strategy_lifecycle_review.v1` が pack validation PASS を必須入力として記録する。
- promotion decision の `required_evidence` に `backtest_pack_validation` を必ず含める。
- paper observation session manifest に `source_backtest_pack_validation_path/hash` を必須化する。
- pack の robustness artifacts を paper observation 開始条件として fail-closed にする。

この場合の最小実装候補:

- `strategy-lifecycle-review` に optional `--backtest-pack-validation-path` を追加する。
- `strategy_lifecycle_review` artifact に source path/hash と `pack_validation_present`, `pack_validation_passed` を記録する。
- `tests/research/test_strategy_lifecycle_review.py` に pack validation PASS / FAIL / missing の focused case を追加する。
- schema version を維持できるかは `schemas/strategy_lifecycle_review.v1.schema.json` の追加プロパティ方針を確認して決める。互換性が曖昧なら v2 を検討する。

## 現時点の結論

仕様化 readiness: ready with assumptions

前提:

- pack validation PASS は operator preflight として扱い、lifecycle の mandatory input にはまだ昇格しない。
- paper observation の次手は実装ではなく、non-smoke observation の継続である。
- live、wallet、signing、exchange write、direct venue schema widening、Coinalyze collector、新 dependency adoption は引き続き範囲外。
