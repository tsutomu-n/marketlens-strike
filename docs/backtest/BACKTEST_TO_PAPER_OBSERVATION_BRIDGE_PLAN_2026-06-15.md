<!--
作成日: 2026-06-15_18:42 JST
更新日: 2026-06-18_01:22 JST
-->

# Backtest To Paper Observation Bridge Plan

## 結論

次にやるべきことは、新しい paper observation gate を作ることではない。

現行 repo にはすでに `strategy-paper-observation-cycle`、`strategy-lifecycle-review`、`research-ndx-paper-observation-gate`、`research-ndx-operator-promotion`、`research-ndx-paper-observation-review` がある。したがって現実的な次の作業は、完成済みの `strategy-backtest-pack` / `strategy-backtest-artifact-summary` を、既存 Strategy Lifecycle / paper observation の入力としてどう扱うかを確認する bridge audit である。

この plan の完了条件は「paper observation を開始する」ではなく、「backtest pack のどの証拠が既存 lifecycle artifact のどこに入るか、入らないなら最小 adapter が必要かを決める」こと。

2026-06-15_19:01 JST の BP0 追加調査では、既存 route がすでに `CONTINUE_PAPER_OBSERVATION` まで到達していることを確認した。詳細は
[../archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md](../archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md)
を見る。この evidence map は当時の artifact 値を含む履歴資料であり、現行状態は `uv run sis strategy-paper-observation-status` で確認する。現時点で bridge adapter は必須ではない。

## 現在確認できた事実

| 項目 | 現在の事実 | 根拠 |
|---|---|---|
| Backtest pack | `data/research/backtest_pack/strategy_backtest_pack.json` は存在し、pack validation は `PASS` | `uv run sis strategy-backtest-artifact-summary` |
| Safety boundary | `paper_only=true`, `permits_live_order=false`, `wallet_used=false`, `exchange_write_used=false` | `strategy-backtest-artifact-summary` の `pack_validation` |
| External framework policy | 標準 engine は `strategy_authoring_native`、完成線は `complete_without_locked_external_dependency` | `strategy-backtest-artifact-summary` の `external_framework_policy` |
| Strategy Lifecycle | backtest acceptance、paper observation cycle、lifecycle review の CLI が実装済み | `uv run sis strategy-lifecycle-review --help`, `uv run sis strategy-paper-observation-cycle --help` |
| NDX paper route | NDX paper gate、operator promotion、paper observation review の CLI が実装済み | `uv run sis research-ndx-paper-observation-gate --help`, `uv run sis research-ndx-operator-promotion --help`, `uv run sis research-ndx-paper-observation-review --help` |
| Candidate / promotion inputs | `strategy-paper-observation-cycle` は `PaperCandidatePack` と `PromotionDecision` を入力にする | `src/sis/research/strategy_lifecycle/paper_observation_cycle.py` |
| Backtest acceptance input | `strategy-lifecycle-review` は `strategy_backtest_acceptance_decision.v1` を入力にする | `schemas/strategy_lifecycle_review.v1.schema.json`, `src/sis/research/strategy_lifecycle/review.py` |

## 修正した前提

以前の「次は paper observation gate」という言い方は粗い。コードを正にすると、paper observation gate はすでに存在する。

正しい次ステップは次のどちらかを実証で選ぶこと。

1. 既存の `strategy-backtest-acceptance`、`strategy-paper-observation-cycle`、`strategy-lifecycle-review` をそのまま使える。
2. backtest pack の追加証拠を既存 lifecycle に渡すため、薄い adapter か evidence map だけを足す必要がある。

最初から新しい gate、schema、CLI を作るのは避ける。

## 現実的なギャップ

| ギャップ | 実務上の意味 | 先にやる確認 |
|---|---|---|
| `strategy-backtest-pack` は rich artifact だが、`strategy-lifecycle-review` の標準入力は `strategy_backtest_acceptance_decision.v1` | pack の robustness 証拠が lifecycle review に直接入っているとは限らない | pack artifact field と lifecycle input field の対応表を作る |
| `strategy-paper-observation-cycle` は `PaperCandidatePack` / `PromotionDecision` を要求する | backtest pack manifest はそのまま paper candidate pack ではない | 既存 `build-paper-candidate-pack` / `build-promotion-decision` 経路で足りるか確認する |
| NDX route は NDX 専用の gate / promotion / review である | venue-neutral backtest pack を NDX 専用 route に無条件で流してはいけない | 対象 strategy / symbol / artifact lineage が NDX route と一致するか確認する |
| `--smoke` は local verification 用で、production paper pass ではない | smoke pass を paper observation 完了や live readiness と誤読できる | smoke 結果を計画上の合格証拠にしない |
| pack validation PASS は no-live boundary と artifact integrity の証拠である | alpha、paper pass、live canary 許可ではない | lifecycle の次 action は別 artifact で判定する |

## Non-Goals

この bridge plan では次をしない。

- Bitget / Hyperliquid の direct schema widening はしない。
- Coinalyze collector は作らない。
- live、wallet、signing、exchange write は実装しない。
- NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio は採用しない。
- replay-style simulation から market impact を主張しない。
- alpha ready、paper pass、live ready を backtest pack だけで主張しない。

## 実装計画

### BP0: Bridge audit を作る

目的: コード変更前に、backtest pack の証拠が既存 lifecycle / paper observation 入力へ対応しているかを表にする。

対象:

- `data/research/backtest_pack/strategy_backtest_pack.json`
- `data/research/backtest_pack/strategy_backtest_pack_validation.json`
- `uv run sis strategy-backtest-artifact-summary`
- `schemas/strategy_backtest_acceptance_decision.v1.schema.json`
- `schemas/strategy_lifecycle_review.v1.schema.json`
- `schemas/paper_observation_session_manifest.v1.schema.json`
- `schemas/promotion_decision.v1.schema.json`
- `schemas/ndx_paper_observation_gate_decision.v1.schema.json`
- `schemas/ndx_operator_promotion_decision.v1.schema.json`
- `schemas/ndx_paper_observation_review_decision.v1.schema.json`

成果物:

- `docs/archive/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_YYYY-MM-DD.md`

受入条件:

- 各 field を `already-consumed`, `available-but-not-consumed`, `not-applicable`, `missing` に分類する。
- `available-but-not-consumed` がある場合、既存 lifecycle が意図的に無視してよい証拠か、adapter が必要な証拠かを分ける。
- この段階では schema / CLI / runtime behavior を変えない。

検証:

```bash
uv run sis strategy-backtest-artifact-summary
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-acceptance --help
uv run sis strategy-paper-observation-cycle --help
uv run sis strategy-lifecycle-review --help
uv run sis research-ndx-paper-observation-gate --help
uv run sis research-ndx-operator-promotion --help
uv run sis research-ndx-paper-observation-review --help
uv run python scripts/check_current_docs.py
```

### BP1: 既存 route で足りるか決める

目的: 新規実装せずに、既存 artifact chain で実務判断できるかを決める。

優先順:

1. `strategy-backtest-acceptance` で backtest acceptance decision を作る。
2. 既存 `PaperCandidatePack` / `PromotionDecision` を作る。
3. `strategy-paper-observation-cycle` で paper-only session manifest / ledger を作る。
4. `strategy-lifecycle-review` で次 action を判定する。
5. NDX 固有なら NDX gate / operator promotion / paper review を併用する。

受入条件:

- `strategy_backtest_acceptance_decision.v1` が pack validation PASS と矛盾しない。
- `PaperCandidatePack` / `PromotionDecision` は `paper_ready_claimed=false`, `live_ready_claimed=false`, `wallet_used=false`, `exchange_write_used=false` を維持する。
- NDX route を使う場合、対象 artifact が NDX / QQQ の前提と一致する。
- bridge audit で必要と判定された証拠だけが次段に渡る。

### BP2: 足りない場合だけ薄い bridge を足す

目的: BP0 / BP1 で既存 route だけでは重要な証拠が落ちると判明した場合に限り、最小 adapter を追加する。

候補:

- `src/sis/research/strategy_lifecycle/backtest_pack_bridge.py`
- 既存 command module への小さな CLI 追加、または既存 command の optional input 追加
- 必要な場合だけ schema 追加
- `tests/research/test_backtest_pack_bridge.py`

制約:

- 新 schema は、既存 schema で表現できないことが evidence map で示された場合だけ作る。
- 新 CLI は、既存 `strategy-backtest-artifact-summary` / `strategy-backtest-acceptance` / `strategy-lifecycle-review` で代替できない場合だけ作る。
- live、wallet、signing、exchange write の field は常に false / disabled として扱う。
- dependency 追加はしない。

受入条件:

- bridge output は source path / source hash / schema version / safety boundary を持つ。
- mismatch、欠損、schema violation は fail closed になる。
- adapter は paper observation を許可しない。既存 lifecycle review の判断材料を作るだけにする。

検証:

```bash
uv run pytest -q tests/research/test_strategy_lifecycle_backtest_acceptance.py tests/research/test_strategy_lifecycle_review.py tests/research/test_strategy_paper_observation_cycle.py
uv run pytest -q tests/research/test_backtest_pack_bridge.py
uv run python scripts/check_current_docs.py
./scripts/check
```

### BP3: Operator recipe を更新する

目的: 実装または非実装の判断後、operator が迷わない最短手順にする。

候補更新先:

- `docs/backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md`
- `docs/strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md`
- `docs/strategy_lifecycle/README.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`

受入条件:

- backtest pack PASS から paper observation review までの手順が一本につながる。
- smoke と production paper observation の違いを明記する。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live order 許可ではないと明記する。

### BP4: 最終 review

目的: plan が理想論に戻っていないかを確認する。

確認項目:

- 新 gate を重複作成していない。
- existing CLI / schema / tests を優先している。
- Non-Goals を開いていない。
- backtest pack PASS を paper pass / live readiness と誤記していない。
- NDX 専用経路と venue-neutral backtest pack を混同していない。

## Stop Conditions

次が見えたら実装を止める。

- live order、wallet、signing、exchange write に触れる必要が出た。
- direct venue schema widening が必要になった。
- Coinalyze collector が必要になった。
- 新 dependency 採用が必要になった。
- backtest artifact だけで alpha / paper pass / live readiness を主張する文言が出た。
- NDX 固有の前提を venue-neutral strategy に流用しそうになった。

## 推奨する次の一手

BP0 だけを先に実行する。

理由は単純で、現時点では paper observation gate が未実装なのではなく、完成済み backtest pack が既存 lifecycle のどの入力に対応するかが未整理だから。ここを飛ばすと、必要ない CLI / schema / gate を増やすリスクが高い。

BP0 の結果で「既存 route で十分」と分かれば、実装は不要で operator recipe 更新だけでよい。逆に重要な証拠が落ちるなら、その時点で初めて BP2 の最小 bridge を作る。

2026-06-15_19:01 JST 時点の BP0 結果では、既存 route で paper observation 継続判断までは十分である。pack validation を lifecycle の mandatory input に昇格したい場合だけ、BP2 を検討する。
