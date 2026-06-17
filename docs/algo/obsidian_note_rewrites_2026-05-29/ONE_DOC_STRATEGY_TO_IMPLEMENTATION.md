<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-18_02:42 JST
-->

# One Doc: Strategy To Implementation

この文書は、戦略部品から Strategy Research Lab の artifact chain までを一気通貫で読むための現行版です。旧版の `data/research/signals.csv`, `DecisionContext`, `ExecutionPlan` 中心の説明は legacy paper path として扱い、現行 Strategy Lab の正本にはしません。

## 結論

戦略は直接 order にしません。

```text
戦略仮説
  -> StrategyExperimentSpec
  -> StrategySignalRecord
  -> EvaluationPlan
  -> TrialRecord
  -> TradeCandidate
  -> PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview
  -> paper-from-intents
  -> paper orders/fills/positions only
```

この chain は、戦略アイデアを「検証可能な signal」と「paper-only の仮注文意図」まで落とすためのものです。live order、wallet、exchange write、profitability claim は含めません。

## 1. 戦略部品を定義する

戦略は最低でも次の部品に分けます。

| Part | Question | Example |
|---|---|---|
| universe | 何を対象にするか | `XYZ100` execution, `QQQ` real market |
| hypothesis | なぜ edge があると思うか | trend continuation after low-vol pullback |
| features | 何を観測するか | return, moving average, VIX proxy, venue quality |
| trigger | いつ signal が出るか | close above trend filter |
| side | long / short / none の条件 | long only when trend and quality pass |
| confidence | signal の信頼度 | source confidence, rank score |
| invalidation | いつ捨てるか | no out-of-sample edge, low source quality |
| evaluation | どう評価するか | purged walk-forward, cost stress |
| promotion | paper に進める条件 | evidence + human decision |

よい戦略部品は、入力、出力、停止条件が分離されています。悪い戦略部品は、「AIが判断する」「勝てそうなら買う」のように、観測と判断と注文が混ざっています。

## 2. StrategyExperimentSpec に落とす

`StrategyExperimentSpec` は戦略仮説と実験条件を固定する schema です。売買候補ではありません。

最低限決めるもの:

```text
strategy_id
strategy_family
strategy_version
symbol_bindings
generator_id
parameter_grid
evaluation_plan_id
run_profile_id
forbidden_claims
```

例:

```text
strategy_id=equity_index_momentum_v0
strategy_family=momentum
strategy_version=v0
generator_id=qqq_trend_rates_vix
symbol_bindings=[
  execution_venue=trade_xyz,
  execution_symbol=XYZ100,
  real_market_symbol=QQQ,
  asset_class=basket_index
]
parameter_grid={
  min_source_confidence=[0.70, 0.80],
  trend_window=[20, 50]
}
evaluation_plan_id=initial_walkforward
run_profile_id=strategy_lab
```

禁止:

- `profitability_claimed=true`
- `paper_ready_claimed=true`
- `tiny_live_ready_claimed=true`
- `live_ready_claimed=true`
- wallet / signing / exchange write の指定
- order quantity の確定

現行 claim 名は `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed` で、すべて forbidden claim として扱います。

## 3. Signal を作る

Signal の canonical artifact は `data/research/strategy_signals.parquet` です。

現行 command:

```bash
uv run sis strategy-preview
```

出力:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signals.jsonl`
- `data/research/signals.csv`
- `data/reports/strategy_signals_preview.md`

重要:

- `strategy_signals.parquet` が Strategy Lab 正本です。
- `signals.csv` は legacy export です。
- 現行 `build_signals()` は default generator `qqq_trend_rates_vix` を使います。
- `strategy-experiment-run --spec` で `StrategyExperimentSpec` YAML/JSON を読み込めます。`parameter_grid` は safe cartesian sweep として展開され、built-in generator は `min_source_confidence`, `max_vix_level` / `vix_gate`, `min_research_return_1d`, `timeframe` を signal 条件または出力 timeframe として消費できます。任意式 eval や任意 Python plugin は実行しません。

Signal row に必要な意味:

- `side`: 候補方向。order action ではない。
- `rank_score`: 候補比較用の相対 score。
- `confidence`: signal 自体の信頼度。
- `source_confidence`: real market source の品質。
- `venue_quality_score`: execution venue の品質。
- `reason_codes`: なぜ signal が出たか。
- `block_reasons`: なぜ止めるべきか。

## 4. EvaluationPlan で評価条件を固定する

`EvaluationPlan` は、評価窓、purge / embargo、必要データ、コスト stress、合格 metric を固定します。

見るべき項目:

- split method: `single_window`, `walk_forward`, `purged_walk_forward`
- horizon: `label_horizon_minutes`
- leakage guard: `purge_minutes`, `embargo_minutes`
- quality guard: `require_tracking_gate`, `require_source_confidence`, `require_venue_quality`
- cost guard: `cost_stress_multiplier`, `slippage_stress_multiplier`
- sample guard: `min_trade_count`
- turnover guard: `max_turnover`

評価でやってはいけないこと:

- 同じ期間で何度も最適化して best trial だけ記録する。
- cost / slippage を無視する。
- source confidence が低いデータを勝手に通す。
- venue quality が低い時間帯の signal を同じ重みで扱う。

## 5. TrialRecord に全 trial を残す

Command:

```bash
uv run sis evaluate-strategy-lab
```

出力:

- `data/research/trial_ledger.jsonl`
- `data/reports/strategy_trial_report.md`

`TrialRecord` は全 trial の記録です。best だけではありません。

重要 field:

- `trial_id`
- `trial_group_id`
- `parameter_hash`
- `data_snapshot_id`
- `feature_snapshot_id`
- `metrics`
- `selected_for_next_stage`
- `rejection_reasons`

`selected_for_next_stage=true` は paper candidate に進める候補という意味です。paper-ready や live-ready ではありません。

## 6. TradeCandidate に変換する

Command:

```bash
uv run sis build-paper-candidate-pack
```

出力:

- `data/research/paper_candidate_pack.json`
- `data/reports/paper_candidate_pack.md`

`TradeCandidate` は売買候補ですが、order ではありません。

候補に必要な情報:

- どの signal / trial 由来か。
- どの strategy 由来か。
- execution symbol と real market symbol は何か。
- side は何か。
- confidence / rank / tail bucket は何か。
- なぜ候補になったか。
- なぜ block / reject されたか。

order と混ぜない情報:

- wallet
- exchange write
- live order submitted
- live-ready claim
- profitability claim

## 7. PaperCandidatePack を review する

`PaperCandidatePack` は候補束です。

見る場所:

- `candidates`
- `selected_candidate_ids`
- `rejected_candidate_ids`
- candidate-level `status`
- candidate-level `block_reasons`
- pack-level `selection_policy`

現行 code には top-level `blocked_candidate_ids` はありません。blocked は candidate status と block reasons で表します。

レビュー観点:

- selected ID は candidates に存在するか。
- selected 候補の lineage は追えるか。
- rejected 理由は次の候補量産に使えるか。
- selection policy は同じ結果を再現できる程度に具体的か。
- paper-only guard が false 以外になっていないか。

## 8. PromotionDecision を作る

Command:

```bash
uv run sis promotion-decision --decision hold
```

通常はまず `hold` で止めます。

`promote` する場合:

```bash
uv run sis promotion-decision --decision promote
```

`PromotionDecision` は人間判断 artifact です。`promote` は paper observation へ進める判断で、live-ready ではありません。

`promote` には以下が必要です。

- `required_evidence` がすべて `observed_evidence` にある。
- `approval_reasons` がある。
- `wallet_used=false`。
- `exchange_write_used=false`。
- `live_ready_claimed=false`。

## 9. PaperIntentPreview を作る

Command:

```bash
uv run sis build-paper-intent-preview
```

出力:

- `data/bot/paper_intent_preview.json`
- `data/reports/paper_intent_preview.md`

`PaperIntentPreview` は paper-only の仮注文意図です。

必須 guard:

```text
requires_revalidation=true
paper_only=true
live_conversion_allowed=false
live_order_submitted=false
wallet_used=false
exchange_write_used=false
```

ここで `action=enter` などが出ますが、live order ではありません。

## 10. paper-from-intents で再検証する

Command:

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

必要 artifact:

- `data/normalized/quotes.parquet`

paper runner は preview をそのまま信用しません。

再検証:

- intent expiry
- latest quote existence
- market status / tradable flag
- halt policy
- paper broker fill validation

block reason:

- `INTENT_EXPIRED`
- `LATEST_QUOTE_MISSING`
- `PAPER_BROKER_REVALIDATION_BLOCKED`

出力:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

## 11. 戦略量産の実務 loop

```text
1. strategy_factory で候補を書く
2. StrategyExperimentSpec に落とす
3. signal generator を選ぶ
4. strategy_signals.parquet を作る
5. EvaluationPlan で評価条件を固定する
6. TrialRecord を ledger に残す
7. TradeCandidate に変換する
8. PaperCandidatePack を review する
9. PromotionDecision で hold / reject / promote を決める
10. PaperIntentPreview を生成する
11. paper-from-intents で再検証する
12. paper observation ledger を review する
13. rejected / blocked reason を strategy_factory に戻す
```

## 12. 最低限の合格条件

paper observation に進める前:

- signal と order が分離されている。
- `execution_symbol` と `real_market_symbol` が分離されている。
- source confidence と venue quality の扱いが明記されている。
- evaluation window と leakage guard が明記されている。
- candidate の selected / rejected / blocked 理由が残っている。
- PromotionDecision が存在する。
- PaperIntentPreview は paper-only guard を満たす。

## 13. 参照する正本

- [../../strategy_research_lab/README.md](../../strategy_research_lab/README.md)
- [../../strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md](../../strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md)
- [../../strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md](../../strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md)
- [../../strategy_research_lab/05_OPERATOR_RUNBOOK.md](../../strategy_research_lab/05_OPERATOR_RUNBOOK.md)
- [../../strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md](../../strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md)
- [../../strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md](../../strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md)
