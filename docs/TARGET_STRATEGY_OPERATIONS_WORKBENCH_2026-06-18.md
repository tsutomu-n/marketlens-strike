<!--
作成日: 2026-06-18_19:47 JST
更新日: 2026-06-18_20:15 JST
-->

# Target Strategy Operations Workbench

## 結論

`marketlens-strike` の完成形は、完全自動売買 bot ではない。

完成形は、個人システムトレーダーが戦略を思いつきや単発 backtest で運用に出さないために、入力データ契約、戦略定義、backtest、過剰最適化の警戒、人間レビュー、paper smoke、通常 paper observation、backtest との差分確認、micro live 計画までを artifact と CLI で管理する Strategy Operations Workbench である。

短く言うと:

```text
MarketLens Strike
= 個人システムトレーダー向けの
  Human-in-the-loop Strategy Operations Workbench
```

日本語では:

```text
人間レビュー前提の戦略運用検証ワークベンチ
```

ここでいう operations は、本番売買の自動実行ではない。戦略を捨てる、直す、小さく paper に出す、通常観察を続ける、micro live 計画を作る、という判断を毎回 artifact として残す運用である。

## 正本

この文書は完成形の設計定義であり、現行実装済み surface の証明ではない。

現行状態の確認では次を正本にする:

1. code、tests、schemas、configs、scripts、lockfiles
2. `uv run sis --help`
3. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
4. [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md)
5. [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
6. [strategy_review/README.md](strategy_review/README.md)
7. [strategy_lifecycle/README.md](strategy_lifecycle/README.md)

`docs/archive/`、`plan/archive/`、古い runtime artifact、古い pass count は current proof として扱わない。

現行 Strategy Review の人間判断 vocabulary は `REJECT`、`NEEDS_FIX`、`REVIEWED_FOR_CONTEXT`、`PAPER_OBSERVATION_CANDIDATE` である。`PAPER_OBSERVATION_CANDIDATE` は validation candidate であり、paper execution permission ではない。

この文書で提案する `strategy_stage_policy.v1`、`strategy_stage_decision.v1`、`strategy_input_contract.v1` は完成形の候補であり、現行 CLI 実装済み surface とは分けて読む。

## 完成形の定義

完成形は、次の問いに毎日答えられる状態である。

```text
この戦略は、いま
1. 捨てるべきか
2. 修正すべきか
3. paper smoke に出すべきか
4. 通常 paper observation を続けるべきか
5. backtest との差分を review すべきか
6. micro live 計画を作るべきか
7. 小さく scale するか、止めるか
```

重要なのは、進行条件を固定値にしないこと。戦略タイプ、時間軸、銘柄、流動性、ユーザーの損失許容度によって、paper smoke、通常 paper、micro live plan の条件は変わる。

ただし、次の安全境界は固定する。

- live order を勝手に出さない。
- wallet / signing / exchange write を混入させない。
- artifact path、source hash、schema version を残す。
- stage 判定に使った policy id と policy hash を残す。
- user override がある場合は理由と reviewer を残す。
- paper smoke pass を通常 paper pass として扱わない。
- paper observation pass を live permission として扱わない。
- micro live plan ready を micro live execution として扱わない。

## 現実的な実務評価

この完成形は、個人システムトレーダー向けの実務 workflow としては有効だが、ドキュメントのナラティブだけで 100 点にはならない。

現時点の評価:

| 対象 | 点数 | 理由 |
|---|---:|---|
| 完成形の方向性 | 80 / 100 | 人間レビュー、paper smoke、drift review、stage policy、position limit の方向は実務的 |
| 現行実装に近い Strategy Review slice | 70 / 100 | read-only review と operator decision は良いが、paper / drift / stage policy までは未実装 |
| 旧い入力データ定義 | 55 / 100 | path / hash 中心で、`available_at`、execution reality、survivorship、revision policy が弱い |
| Strategy Input Contract 追加後の完成形定義 | 85 / 100 | 実務上の主な落とし穴を入口で止められるが、schema / CLI / validator 実装が必要 |

100 点に近づける条件:

- 入力データ契約を schema / validator / report にする。
- paper smoke と normal paper observation を artifact 上も分ける。
- paper と backtest の drift review を毎回残す。
- stage policy の override を記録し、後付けで条件を緩めたことを隠せないようにする。
- micro live は permission ではなく、まず計画 artifact と停止条件から始める。

この repo の完成形は「勝てる戦略を自動で作る機械」ではない。弱い候補を早く捨て、残った候補だけを小さく現実へ近づける運用装置である。

## Trade[XYZ] の扱い

Trade[XYZ] は破棄済みではない。ただし、完成形の主軸ではない。

現行 repo での扱い:

- Trade[XYZ] は実装済み code surface として残る。
- Trade[XYZ] は historical / read-only venue context として読む。
- Trade[XYZ] quote、registry、read-only execution state、data readiness、pure backtest v0.1 Python API は存在する。
- ただし、標準の開発主軸は backtest-first / venue-neutral である。
- Trade[XYZ] を default product axis、primary execution path、primary next action として扱わない。
- user が明示的に Trade[XYZ] を scope した時だけ、その surface を使う。

使ってよい場面:

- 既存 Trade[XYZ] artifact の読み取り。
- read-only data / quote / venue quality の確認。
- historical context としての比較。
- venue-specific execution reality を考える時の参考。
- `validate-artifacts --strict` など、既存 artifact chain の検査。

使わない場面:

- 新しい Strategy Operations Workbench の標準入力にすること。
- paper smoke / normal paper / micro live の標準 route にすること。
- Trade[XYZ] 前提の collector、readiness claim、order path を新しく増やすこと。
- Trade[XYZ] pure backtest v0.1 を public CLI の標準 backtest として扱うこと。
- `READ_ONLY_GO` や read-only execution state を live readiness と読むこと。

つまり、Trade[XYZ] は「捨てた」のではなく、「主軸から外し、read-only / historical / explicitly scoped surface として残す」が正しい。

古い gTrade / Ostium 系の計画や venue-probe 系の文脈は archive にある。archive は履歴資料であり、現行 next action の正本ではない。

## 100点を待たない進行設計

完成形は、100点になるまで進めない設計ではない。

実務では、一定ラインを超えたら小さく次段階に進める。

```text
Strategy Input Contract
  ↓
Idea Intake
  ↓
Backtest
  ↓
Review Packet
  ↓
Paper Smoke
  ↓
Runtime Observation Ingest
  ↓
Normal Paper Observation
  ↓
Drift Review
  ↓
Persistent Learning Loop
  ↓
Micro Live Plan Gate
  ↓
Micro Live Canary
  ↓
Scale / Revise / Retire
```

各段階の意味は違う。

| Stage | 目的 | 見るもの | 進んでよい意味 |
|---|---|---|---|
| Backtest | 明らかな地雷を落とす | 損益、DD、取引回数、cost、stress、no-lookahead | paper で観察する価値があるか |
| Review Packet | 人間が読む根拠を固定する | source hash、欠損、境界違反、lifecycle | 判断を記録できるか |
| Paper Smoke | 配線確認 | signal、intent、paper fill、ログ、サイズ暴走 | 短く paper で壊れないか |
| Runtime Observation Ingest | 実時間観測の取り込み | live/read-only market data、paper fills、no-fill、latency、spread | backtest と paper の差分を測れるか |
| Normal Paper Observation | 通常観察 | fill、no-fill、slippage、paper PnL、DD、日数 | 戦略として観察を続ける価値 |
| Drift Review | backtest と paper の差分確認 | signal drift、fill drift、cost drift、DD drift | 修正、継続、棄却、micro live plan |
| Persistent Learning Loop | 実践からの学習 | 仮説更新、失敗理由、改訂要求、policy調整 | 次の review / authoring に戻せるか |
| Micro Live Plan Gate | 実損失限定の計画確認 | 最大損失、最大注文、停止手順、監視 | micro live 計画を作れるか |
| Micro Live Canary | 最小実弾の実行差分確認 | 実約定、手数料、遅延、拒否、口座整合 | scale 検討に進めるか |

## Backtest の意味

この完成形では、backtest は儲かる証明ではない。

backtest は、戦略候補を棄却、修正、paper smoke 候補に分類するための一次証拠である。

backtest が答えられること:

- ルールが機械的に動くか。
- 過去データ上で致命的に破綻していないか。
- 取引回数が少なすぎないか。
- cost、slippage、stress に弱すぎないか。
- benchmark や regime split と比べて説明できるか。
- no-lookahead、data availability、source hash に問題がないか。

backtest が答えられないこと:

- 将来も勝てるか。
- paper で同じ価格で約定するか。
- live で同じ execution quality が出るか。
- 本番投入してよいか。
- ユーザーの資金管理上、耐えられるか。

良い backtest は採用理由ではなく、paper smoke に進める理由である。

## Strategy Input Contract の定義

入力データは、単なる path、hash、schema version の一覧では足りない。

完成形では、入力データを `Input Source Catalog` ではなく、`Strategy Input Contract` として扱う。

定義:

```text
Strategy Input Contract
= strategy decision 時点で利用可能だったことを証明できる
  market / feature / execution / event / risk / feedback / experiment metadata の束。
```

目的は、戦略が次の問いに答えられるようにすることである。

```text
この戦略は、
1. その時点で実際に知り得た情報だけで判断しているか
2. paper / live でも同じタイミングで取得できる情報か
3. 執行条件込みで検証できるか
4. 欠損、遅延、改訂、外れ値をどう扱うか
5. 後から同じ入力を再現できるか
6. 失敗した trial や parameter 探索も記録できるか
```

### 入力データの 9 分類

完成形では、入力を少なくとも次の 9 種類に分ける。

| 分類 | 例 | 欠けた時の主なリスク |
|---|---|---|
| Raw Market Data | OHLCV、quote、trade、order book、volume、spread | 価格だけの都合のよい backtest になる |
| Derived Feature Data | indicator、regime、signal candidate、factor、model output | feature 生成時の未来リークを見逃す |
| Temporal Availability | `observed_at`、`available_at`、decision time、source lag、timezone、market calendar | 判断時点で見えない情報を使う |
| Execution Reality | fee、spread、slippage、depth、min order、tick size、latency、no-fill、funding、borrow | 約定しない、cost で edge が消える |
| Universe / Instrument Definition | symbols、venue、listing / delisting、survivorship、contract rollover、corporate actions | 生き残り銘柄だけで勝ったように見える |
| External / Event Context | macro calendar、earnings、news、first_seen_ts、provider delay、revision policy | event data の後出し利用になる |
| Risk / Account Constraints | capital、leverage、max position、max order、max daily loss、kill switch | position size が暴走する |
| Runtime Observation Data | live/read-only market quotes、paper signals、paper orders、paper fills、no-fill、latency、spread、blocked reason | paper smoke 後の現実差分を取り込めない |
| Feedback / Experiment Metadata | trial ledger、parameter search history、failed ideas、operator notes、drift decision | 成功結果だけが残り overfitting を見逃す |

### 必須契約

`strategy_input_contract.v1` は、最低でも次を持つ。

```yaml
schema_version: strategy_input_contract.v1
input_contract_id: ndx-open-gap-v001
idea_id: ndx-open-gap-residual

decision_context:
  decision_ts_policy: t_open_plus_buffer
  timezone: America/New_York
  market_calendar: XNAS
  available_at_required: true

universe:
  instrument_type: equity_index_proxy
  symbols: [QQQ, SPY, SMH, VIX, DGS10]
  survivorship_policy: point_in_time_required
  symbol_mapping_policy: explicit_mapping_required

sources:
  - source_id: qqq_quotes
    kind: raw_market
    provider: local_parquet
    path: data/...
    sha256: ...
    granularity: 1m
    observed_at_field: ts
    available_at_policy: bar_close_plus_1m
    revision_policy: immutable_snapshot
    missingness_policy: fail_if_gap_gt_threshold

  - source_id: spread_estimate
    kind: execution_reality
    fields: [spread_bps, volume, liquidity_bucket]
    assumption_level: measured

  - source_id: paper_smoke_runtime_observation
    kind: runtime_observation
    path: data/paper_smoke/<session_id>/runtime_observation.jsonl
    sha256: ...
    observed_at_field: observed_at
    available_at_policy: observed_realtime
    includes_live_order: false
    includes_exchange_write: false
    fields: [signal_id, paper_order_id, paper_fill_id, no_fill_reason, spread_bps, latency_ms, blocked_reason]

features:
  - name: open_gap_residual
    source_ids: [qqq_quotes, spy_quotes, smh_quotes]
    max_source_ts_policy: <= decision_ts
    leakage_check_required: true

baselines:
  - simple_open_gap
  - broad_market_only

negative_controls:
  - shuffled_signal_time
  - target_only_without_cross_asset_confirmation

blockers:
  - missing_available_at
  - no_execution_cost_proxy
  - no_baseline
  - future_observed_event
```

### 入口で止める条件

次の条件に該当する戦略候補は、Strategy Authoring draft に進めない。

- `available_at` が未定義の入力を主要 signal に使っている。
- raw data と derived feature の hash がない。
- provider lag、revision policy、timezone、calendar が不明な event data を使っている。
- fee、spread、slippage、no-fill、funding、borrow などの execution reality がない。
- survivorship policy や symbol mapping が未定義の銘柄 universe を使っている。
- baseline と negative control がない。
- 失敗 trial、skipped trial、parameter sweep を残す場所がない。
- risk / account constraint がない。

### 既存 repo との接続

現行 repo には、入力データ契約の部品はすでにある。

- `data_snapshot_manifest.v1` は path、hash、symbol、venue、timestamp range、data quality を持つ。
- `feature_snapshot_manifest.v1` は feature cutoff、source ts、leakage check、missing rate を持つ。
- `research_temporal_availability.v1` は decision layer と forbidden future edge を表現している。
- backtest data availability、assumption ledger、trial ledger、no-lookahead diff は、後段で入力の妥当性を検査する。

ただし、これらはまだ 1 つの `strategy_input_contract.v1` として統合されていない。完成形では、Idea Intake、Strategy Authoring、Backtest、Paper Smoke、Runtime Observation Ingest、Drift Review が同じ input contract を参照する。

### Backtest / Paper との接続

`strategy_input_contract.v1` があると、各工程の意味が明確になる。

```text
Idea Intake
  入力が検証可能かを判定する

Strategy Authoring
  contract の source / feature / risk を使って draft spec を作る

Backtest
  available_at、execution reality、assumption level を読んで検証する

Paper Smoke
  想定 spread / no-fill / latency と paper 実測を比較する

Runtime Observation Ingest
  paper smoke 後の live/read-only market observation と paper runtime data を入力契約へ戻す

Drift Review
  input contract 上の想定と paper の現実差分を読む
```

この接続がないと、backtest が良く見える戦略ほど、後から「実はそのデータは判断時点で使えない」「paper では約定しない」「cost で消える」という落とし穴に落ちやすい。

## 戦略を作るとは何か

この完成形で「戦略を作る」とは、LLM や template が勝てるルールを自動発明することではない。

定義:

```text
戦略を作る
= Idea Intake と Strategy Input Contract をもとに、
  検証可能な Strategy Authoring draft を作り、
  baseline、invalidation、risk、execution assumptions、reject rule と一緒に固定すること。
```

作る対象は、売買ルールだけではない。

| 要素 | 内容 |
|---|---|
| Hypothesis | なぜその歪みや反応が存在する想定か |
| Universe | 対象市場、銘柄、venue、時間足 |
| Entry / Exit | 入る条件、出る条件、時間切れ条件 |
| No-trade condition | 取引しない regime、event、liquidity 条件 |
| Position / Risk | order size、position cap、stop、daily loss、kill condition |
| Input Contract | 使う raw / feature / execution / event data と `available_at` |
| Baseline | 比較する単純手法 |
| Negative Control | ランダム、target-only、遅延、shuffle などの反証 |
| Invalidation | どの結果なら仮説を捨てるか |
| Trial Ledger | 試した variant、失敗、skipped、parameter sweep |

最小の流れ:

```text
strategy memo
  ↓
strategy_idea.v1
  ↓
strategy_input_contract.v1
  ↓
strategy_authoring_spec.v1 draft
  ↓
static validation
  ↓
small backtest
  ↓
backtest pack
  ↓
review packet
```

やってはいけないこと:

- 良い backtest 結果に合わせて後から hypothesis を書く。
- threshold を何度も動かしたのに trial ledger を残さない。
- baseline に勝っていない複雑な戦略を「高度」として残す。
- execution cost を後で考える。
- LLM が出した YAML をそのまま採用する。
- Strategy Authoring draft を paper permission と読む。

最初に実装するなら、strategy factory よりも `strategy-intake-validate` と `strategy-input-contract-validate` が先である。戦略を増やすより、検証不能な候補を入口で落とす方が実務価値が高い。

## Idea Intake の再定義

Idea Intake は、戦略を作る入口だが、戦略生成器ではない。

定義:

```text
Idea Intake
= 戦略メモ、相場観、外部メモ、既存 backtest 断片を、
  そのまま実装せず、
  仮説、反証条件、入力データ契約、baseline、risk、重複、捨てる条件へ分解し、
  検証に送る価値がある候補だけを Strategy Authoring / Strategy Lab へ渡す入口。
```

目的は「アイデアを増やすこと」ではない。弱い候補を早く落とし、残った候補だけを実装可能な spec に進めることである。

現行 repo では、Idea Intake に近いものは [algo/strategy_factory/](algo/strategy_factory/) の docs と `Signal Candidate Sheet` である。ただしこれは docs 運用であり、CLI / schema / validator としてはまだ完成していない。

### 現実的に受け付ける入力

Idea Intake は、次のような入力を受け付ける。

- 自然文の戦略メモ
- 手動で書いた Signal Candidate Sheet
- 外部調査メモ
- 既存 backtest から派生した改善案
- paper observation や drift review から戻ってきた修正案
- 市場仮説、失敗メモ、棄却済み候補の再検討

ただし、SNS や動画や外部メモの勝率・利益主張は検証済み事実として扱わない。source note として保存し、hypothesis の材料に留める。

### 必須入力

最小の Idea Intake は、次を必須にする。

| 項目 | 意味 | 欠けた時の扱い |
|---|---|---|
| `idea_id` | 候補の安定 ID | 作れない |
| `one_sentence_hypothesis` | 何がなぜ効く想定か | `NEEDS_SPEC` |
| `archetype` | trend / pullback / breakout / mean-reversion など | `NEEDS_SPEC` |
| `market_universe` | 対象市場、銘柄群、時間足 | `NEEDS_SPEC` |
| `trigger` | 入る条件 | `NEEDS_SPEC` |
| `invalidation` | 仮説が壊れる条件 | `REJECT` 候補 |
| `baseline` | 何と比べるか | `REJECT` 候補 |
| `required_inputs` | 必要な価格、出来高、funding、spread など | `NEEDS_DATA_CHECK` |
| `input_contract_id` | 入力データ契約 ID | `NEEDS_DATA_CHECK` |
| `available_at_policy` | そのデータが判断時点で見えていたか | `LEAKAGE_RISK` |
| `no_trade_conditions` | 入らない条件 | `NEEDS_RISK_SPEC` |
| `risk_assumption` | 最大損失、position size、stop | `NEEDS_RISK_SPEC` |
| `duplicate_key` | 似た候補の統合キー | `DUPLICATE_RISK` |
| `reject_if` | どの条件なら捨てるか | `NEEDS_SPEC` |

この段階では、完璧な YAML にしない。まず「検証できる候補か」「そもそも捨てるべきか」を決める。

### 受け付けてはいけない入力

次は Idea Intake で止める。

- 「なんとなく上がりそう」だけで trigger がない。
- invalidation がない。
- baseline がない。
- 必要データが live execution しないと観測できない。
- decision time より後に確定するデータを使っている。
- 既存候補の threshold だけを変えたものを新戦略として出している。
- position size や stop がない。
- 期待利益だけで、失敗条件がない。
- backtest 結果に合わせて後付けされたルールだが、探索履歴がない。

### 出力 artifact

完成形では、Idea Intake は次を出す。

```text
data/strategy_intake/<idea_id>/
  strategy_idea.yaml
  intake_review.md
  intake_decision.json
```

`strategy_idea.yaml` は候補の構造化メモである。

`intake_review.md` は人間が読む入口資料である。

`intake_decision.json` は次に進めるかどうかの機械判定である。

判定は次に絞る。

```text
REJECT
DUPLICATE
NEEDS_SPEC
NEEDS_DATA_CHECK
NEEDS_RISK_SPEC
READY_FOR_AUTHORING_DRAFT
```

`READY_FOR_AUTHORING_DRAFT` は backtest ready ではない。Strategy Input Contract が最低限そろい、Strategy Authoring YAML の draft を作る価値がある、という意味だけである。

### Trading journal としての役割

Idea Intake は、将来の自分が「なぜこの戦略を作ったのか」を検証する trading journal でもある。

後で必要になるのは、良い結果ではなく、次の履歴である。

- 最初の仮説
- 最初の baseline
- 最初の reject rule
- 何を見て採用候補にしたか
- 何を理由に捨てたか
- どの parameter を後から変えたか
- 何個の variant を試したか
- どの外部メモを参照したか

この履歴がないと、backtest の良い結果が出た時に selection bias と overfitting を見逃しやすい。

### Idea Intake と後続工程の境界

Idea Intake は次をしない。

- backtest を実行しない。
- paper intent を作らない。
- paper smoke に進めない。
- live / wallet / signing / exchange write を扱わない。
- LLM の出力をそのまま strategy spec として採用しない。
- parameter optimization をしない。

Idea Intake がやるのは、候補を Strategy Authoring / Strategy Lab に渡せるだけの形へ絞ることだけである。

### CLI 候補

完成形では、次の薄い CLI から始める。

```bash
uv run sis strategy-intake-init \
  --idea-id <idea-id> \
  --out data/strategy_intake/<idea-id>/strategy_idea.yaml

uv run sis strategy-intake-validate \
  --idea data/strategy_intake/<idea-id>/strategy_idea.yaml

uv run sis strategy-intake-review \
  --idea data/strategy_intake/<idea-id>/strategy_idea.yaml \
  --out data/strategy_intake/<idea-id>

uv run sis strategy-intake-promote-to-authoring-draft \
  --idea data/strategy_intake/<idea-id>/strategy_idea.yaml \
  --out configs/strategies/drafts/<idea-id>.yaml
```

最初に作るなら、`strategy-intake-validate` が最も価値が高い。候補シートの未記入、baseline なし、invalidation なし、required inputs なし、duplicate key なし、risk なしを機械で落とせるためである。

## Paper Smoke の定義

Paper smoke は、勝てるかを見る工程ではない。

定義:

```text
Paper Smoke
= backtest で致命傷がない戦略を、
  小さく、短く、低リスク設定で paper に流し、
  signal、intent、paper fill、ログ、position size、禁止副作用が壊れないかを見る初回通電テスト。
```

見るもの:

- signal が想定通り出るか。
- entry / exit intent が作られるか。
- paper order や paper fill が記録されるか。
- no-fill だらけにならないか。
- spread / slippage 想定が極端に外れていないか。
- position size が暴走しないか。
- artifact と hash が残るか。
- stop condition が効くか。
- live / wallet / signing / exchange write が混入しないか。

Paper smoke は短い。例としては 1〜3 trading days、数 fill から始めてよい。

Paper smoke pass は、通常 paper observation pass ではない。勝率や収益性を判断しない。

## Runtime Observation Ingest の定義

Paper smoke 後は、live/read-only market observation と paper runtime data を入力へ戻す。

ここでいう live data は、原則として live order や exchange write ではない。実時間に観測した market data、paper signal、paper order、paper fill、no-fill、spread、latency、blocked reason のことである。

定義:

```text
Runtime Observation Ingest
= paper smoke / paper observation 中に実時間で観測した
  market, signal, paper order, paper fill, no-fill, latency, spread, block reason を
  次の Drift Review と次回 Strategy Input Contract へ戻す工程。
```

取り込むもの:

- live/read-only quote、trade、spread、depth、volume
- signal が出た時刻
- paper order intent
- paper fill
- no-fill
- rejected / blocked reason
- observed slippage
- observed latency
- data delay、欠損、重複
- stop condition 発火
- position size guard 発火
- operator memo

取り込まないもの:

- micro live gate 前の live order
- wallet secret
- signing event
- exchange write
- live execution permission

この工程がないと、paper smoke は一度通電して終わりになる。実務では、paper smoke 後の実時間観測こそが次の入力データになる。

artifact 候補:

```text
data/runtime_observations/<strategy_id>/<session_id>/
  runtime_observation_ledger.jsonl
  runtime_observation_manifest.json
  runtime_observation_summary.md
```

`runtime_observation_manifest.json` は、少なくとも次を持つ。

```yaml
schema_version: strategy_runtime_observation_manifest.v1
strategy_id: <strategy-id>
session_id: <session-id>
source_stage: paper_smoke
includes_live_order: false
includes_wallet: false
includes_signing: false
includes_exchange_write: false
market_data_sources:
  - source_id: live_read_only_quote
    path: data/runtime_observations/.../quotes.jsonl
    sha256: ...
paper_runtime_sources:
  - source_id: paper_fills
    path: data/runtime_observations/.../paper_fills.jsonl
    sha256: ...
summary:
  signals: 12
  paper_orders: 8
  paper_fills: 5
  no_fills: 3
  blocked: 1
  max_observed_spread_bps: 18.2
  max_observed_latency_ms: 420
```

Micro Live Canary 後は、別 artifact として actual live execution observation を取り込む。ただしこれは micro live gate を通過した後だけであり、paper smoke 後の runtime observation と混ぜない。

## よさそうな戦略ができた時の操作

よさそうな戦略ができた時に、すぐ採用しない。ただし、100 点になるまで止め続けもしない。

現実的な操作は次。

```text
1. Freeze
   idea、input contract、authoring spec、backtest artifact、policy hash を固定する。

2. Kill obvious lies
   no-lookahead、data availability、source hash、baseline、negative control、cost stress を見る。

3. Human review
   review packet を読み、REJECT / NEEDS_FIX / REVIEWED_FOR_CONTEXT / PAPER_OBSERVATION_CANDIDATE を記録する。

4. Paper Smoke
   小さい size、短い期間、低い order cap で配線とログと no-fill を見る。

5. Runtime Observation Ingest
   paper smoke 中に実時間で観測した market data、paper fill、no-fill、latency、spread を入力へ戻す。

6. Normal Paper Observation
   smoke とは別に、一定 fills / trading days / drift 条件で通常観察する。

7. Drift Review
   backtest 想定と paper 実測のズレを読む。

8. Micro Live Plan Gate
   実損失上限、最大注文、停止条件、監視手順、手動開始条件を artifact 化する。
```

進める条件は config で変えてよい。ただし、次は固定で守る。

- source hash なしで進めない。
- `available_at` 不明の主要 input で進めない。
- paper smoke pass を normal paper pass として扱わない。
- paper candidate を paper execution permission として扱わない。
- micro live plan を live execution permission として扱わない。
- position size / loss cap / kill switch なしで micro live plan を作らない。

## Normal Paper Observation の定義

Normal paper observation は、戦略としての再現性を見る段階である。

見るもの:

- paper PnL
- fill rate
- no-fill rate
- spread / slippage
- holding time
- drawdown
- signal frequency
- backtest との乖離
- market regime ごとの崩れ方
- timestamp quality
- open position age

ここで初めて、一定期間の観察をする。smoke pass を normal pass として数えない。

通常 threshold は固定ではなく、stage policy config で決める。

## Drift Review の定義

Drift Review は、backtest で想定した挙動と paper で実際に起きた挙動のズレを読み、続行、修正、棄却、micro live plan 候補を決める工程である。

drift は成績悪化だけを意味しない。想定と現実のズレを意味する。

見る drift:

- Signal drift: signal 数、entry / exit 頻度が違う。
- Fill drift: backtest では入れた想定なのに paper では no-fill が多い。
- Slippage / spread drift: 想定 cost より悪化して edge が消える。
- PnL drift: total return、平均損益、勝率、profit factor が大きく違う。
- Drawdown drift: paper DD が backtest 想定より早く深い。
- Holding-time drift: 想定より長く捕まる、または早く切られすぎる。
- Regime drift: 特定相場で壊れる。
- Operations drift: ログ欠損、artifact 欠損、時刻ズレ、重複注文、停止条件未発火。

判定:

- `PASS`: ズレは想定範囲内。通常観察継続または micro live plan gate へ進める。
- `REVISE`: 戦略仮説は残るが execution 条件、cost、risk、entry / exit を直す。
- `REJECT`: backtest と paper が別物。fill しない、cost で死ぬ、DD が深すぎる。
- `EXTEND`: 判断するには fills / trading days が足りない。

## Persistent Learning Loop の定義

持続的学習は、戦略が自動で自分を書き換えることではない。

定義:

```text
Persistent Learning Loop
= paper smoke、runtime observation、normal paper、drift review、micro live canary から得た実践データを、
  仮説、入力契約、execution assumption、risk limit、stage policy、改訂要求へ戻し、
  次回の Idea Intake / Strategy Authoring / Review に再利用できる形で残す仕組み。
```

学習するもの:

| 学習対象 | 例 |
|---|---|
| Hypothesis update | 想定した edge が残ったか、消えたか、別 regime だけで出たか |
| Input contract update | 必要だった data、不要だった data、遅延した data、欠損が多い data |
| Execution assumption update | spread、slippage、latency、no-fill、blocked reason の実測 |
| Risk update | DD、連敗、position cap、stop、kill condition の妥当性 |
| Stage policy update | paper smoke / normal paper / micro live gate の threshold が厳しすぎるか緩すぎるか |
| Authoring revision | entry、exit、no-trade condition、time stop、position sizing の修正要求 |
| Rejection pattern | 捨てた理由、再発防止、似た候補を次回 intake で落とす条件 |

学習しないもの:

- 自動で live に進めること。
- 自動で position size を増やすこと。
- 自動で strategy spec を上書きすること。
- 損益だけを見て parameter を最適化すること。
- 失敗 trial を消して、成功した variant だけを残すこと。
- LLM に観測結果を渡して、そのまま採用すること。

学習 loop:

```text
Runtime Observation
  ↓
Drift Review
  ↓
Learning Event
  ↓
Revision Request / Reject Pattern / Policy Adjustment Proposal
  ↓
Human Review
  ↓
New Idea Intake or Strategy Authoring Revision
  ↓
Backtest / Paper Smoke
```

### Learning Event

実践から学んだことは、`learning_event` として小さく残す。

```yaml
schema_version: strategy_learning_event.v1
strategy_id: ndx-open-gap-residual
source_stage: normal_paper_observation
source_artifacts:
  - path: data/runtime_observations/.../runtime_observation_manifest.json
    sha256: ...
  - path: data/strategy_reviews/.../drift_review.json
    sha256: ...
event_type: execution_assumption_update
finding: observed spread was consistently above backtest assumption during first 10 minutes
impact: backtest edge is likely overstated for early open entries
recommended_action: revise_no_trade_condition
requires_human_review: true
auto_applied: false
```

`auto_applied` は原則 `false` にする。学習は次の判断材料であり、自動変更ではない。

### Revision Request

改訂が必要な場合は、直接 spec を書き換えず、改訂要求を作る。

```yaml
schema_version: strategy_revision_request.v1
strategy_id: ndx-open-gap-residual
reason: spread_drift
source_learning_event_ids:
  - learn-20260618-001
requested_changes:
  - add no-trade condition for first 10 minutes after open
  - double slippage stress for open gap entries
  - require min observed liquidity bucket
decision_needed: REVIEW_AND_AUTHORING_UPDATE
```

これにより、「実践から学んだ」ことと「戦略を修正した」ことを分けられる。

### Learning Ledger

戦略ごとに learning ledger を持つ。

```text
data/strategy_learning/<strategy_id>/
  learning_ledger.jsonl
  learning_summary.md
  revision_requests/
    <revision_request_id>.yaml
```

ledger に残すもの:

- 何を観測したか。
- backtest 想定と何が違ったか。
- 仮説は強まったか、弱まったか。
- 棄却理由は何か。
- 次回 intake で同じ罠をどう止めるか。
- policy threshold を変える提案があるか。
- spec 改訂要求があるか。

### Strategy Case への反映

`strategy_case_lite.v1` は、review、paper status、drift review だけでなく、learning events も束ねる。

例:

```yaml
schema_version: strategy_case_lite.v1
strategy_id: ndx-open-gap-residual
reviews:
  - review_id: review-001
runtime_observations:
  - session_id: smoke-001
drift_reviews:
  - drift_review_id: drift-001
learning_events:
  - learning_event_id: learn-001
revision_requests:
  - revision_request_id: revise-001
current_state: NEEDS_AUTHORING_REVISION
```

この loop がないと、paper や micro live の経験が次の改善に残らず、毎回「良さそうな backtest を探す」作業へ戻ってしまう。

## Loop Modes

Persistent Learning Loop は基本形である。

完成形では、基本形に加えて Human-in-the-loop、AI-in-the-loop、Multi-AI review loop を持てるようにする。

ただし、すべての loop で最終判断は人間が持つ。AI は判断材料を作るが、permission、stage advance、paper execution、micro live、position size 増加を決めない。

### Basic Loop

Basic Loop は、外部 AI や追加レビュアーを使わない最小 loop である。

```text
Runtime Observation
  ↓
Drift Review
  ↓
Learning Event
  ↓
Revision Request
  ↓
Human Review
  ↓
Strategy Revision
```

Basic Loop だけでも運用できる。まずこの loop を artifact と CLI で成立させる。

### Human-in-the-loop

Human-in-the-loop は、operator が明示判断を残す loop である。

人間が判断するもの:

- idea を捨てるか。
- input contract の不明点を許容するか。
- review packet を読んで次段階へ進めるか。
- learning event を本当に採用するか。
- revision request を authoring へ反映するか。
- stage policy の override を許すか。
- micro live plan を作るか。

人間が残す artifact:

- `operator_strategy_review.v1`
- `strategy_revision_request_review.v1`
- `strategy_stage_decision.v1`
- `manual_override_reason`

Human-in-the-loop は、単なる画面上の承認ボタンではない。何を見て、なぜ進めたか、何を無視したかを残す仕組みである。

### AI-in-the-loop

AI-in-the-loop は、ChatGPT、Grok、Gemini などに review packet や learning ledger を読ませ、見落とし、反証、改善案、要約を出させる loop である。

AI がやってよいこと:

- Idea Intake の曖昧さを指摘する。
- Strategy Input Contract の欠落を探す。
- backtest の過剰最適化リスクを指摘する。
- paper smoke / runtime observation の違和感を要約する。
- Drift Review の見落としを探す。
- Learning Event の候補を提案する。
- Revision Request の候補を作る。
- stage policy が緩すぎる / 厳しすぎる可能性を指摘する。
- 人間が読む Daily Brief の要約を作る。

AI がやってはいけないこと:

- strategy spec を直接上書きする。
- stage decision を確定する。
- paper execution を許可する。
- micro live を許可する。
- position size を増やす。
- wallet、signing、exchange write、credential を扱う。
- secret、API key、account detail、private key を入力に含める。
- AI の推奨を検証済み事実として保存する。

AI review は必ず artifact 化する。

```yaml
schema_version: strategy_ai_review_note.v1
review_id: ai-review-20260618-001
strategy_id: ndx-open-gap-residual
provider: openai
model: gpt-5
review_role: red_team
input_artifacts:
  - path: data/strategy_reviews/review-001/review_manifest.json
    sha256: ...
  - path: data/runtime_observations/.../runtime_observation_manifest.json
    sha256: ...
prompt_hash: ...
created_at: 2026-06-18T20:15:00+09:00
findings:
  - severity: warning
    topic: slippage_assumption
    finding: observed open spread is wider than the backtest assumption
    suggested_action: require wider cost stress before next paper stage
limitations:
  - model output is advisory
  - no external validation performed
requires_human_review: true
auto_applied: false
```

`auto_applied` は常に `false` を既定にする。

AI の output は、`Learning Event` または `Revision Request` の候補にはできる。ただし、採用するには Human Review が必要である。

### Multi-AI Review Loop

複数 AI を使う場合は、同じ packet を別の役割で読ませる。

例:

| Reviewer | 役割 |
|---|---|
| ChatGPT | artifact contract、implementation consistency、risk boundary の確認 |
| Grok | market narrative、反対仮説、外部説明の粗探し |
| Gemini | 長文資料、外部 research note、イベント背景の整理 |

複数 AI の目的は、多数決ではない。違う失敗モードを見つけることである。

Multi-AI review では、比較 artifact を作る。

```yaml
schema_version: strategy_ai_review_bundle.v1
bundle_id: ai-bundle-20260618-001
strategy_id: ndx-open-gap-residual
input_packet_hash: ...
reviews:
  - ai_review_id: chatgpt-red-team
  - ai_review_id: grok-market-counter
  - ai_review_id: gemini-long-context
agreements:
  - all reviewers flagged execution cost risk
disagreements:
  - only one reviewer suggested regime split revision
human_resolution_required: true
```

この bundle も permission artifact ではない。

### LLM-safe Review Packet

AI に渡す入力は、通常の internal artifact そのものではなく、LLM-safe packet にする。

含めてよいもの:

- review.md
- review_manifest.json
- sanitized strategy idea
- sanitized input contract
- backtest summary
- runtime observation summary
- drift review summary
- learning ledger summary

含めないもの:

- API key
- wallet secret
- signing material
- account credential
- private address details
- raw personal note の不要部分
- exchange write endpoint 実行情報

artifact 候補:

```text
data/ai_review_packets/<strategy_id>/<packet_id>/
  ai_review_packet.md
  ai_review_packet_manifest.json
```

`ai_review_packet_manifest.json` は、元 artifact の path/hash と redaction policy を持つ。

この分離により、AI を使っても secret / live permission / account detail を外へ出さない。

## Stage Policy Config

完成形では、進行条件は config で定義する。

最小形:

```yaml
schema_version: strategy_stage_policy.v1
policy_id: personal_default_v1
description: Personal default stage policy for paper smoke, normal paper observation, and micro live planning.

fixed_safety:
  require_source_hashes: true
  require_schema_versions: true
  forbid_live_order_before_micro_live_gate: true
  forbid_wallet_before_micro_live_gate: true
  forbid_signing_before_micro_live_gate: true
  forbid_exchange_write_before_micro_live_gate: true
  require_manual_override_reason: true

stages:
  paper_smoke:
    min_fills: 3
    min_trading_days: 1
    max_no_fill_rate: 0.80
    max_slippage_bps: 50
    max_order_notional_usd: 100
    max_position_notional_usd: 300
    max_orders_per_day: 10
    stop_after_consecutive_errors: 2

  normal_paper_observation:
    min_fills: 20
    min_trading_days: 10
    max_no_fill_rate: 0.40
    max_slippage_bps: 20
    max_drawdown_vs_backtest_ratio: 2.0
    max_blocked_rate: 0.50
    max_consecutive_blocked: 3

  micro_live_plan:
    max_order_notional_usd: 50
    max_total_notional_usd: 100
    max_daily_loss_usd: 20
    max_total_loss_usd: 50
    max_runtime_days: 3
    require_manual_start: true
    require_kill_switch: true
    require_monitoring_plan: true
```

戦略タイプ別 profile も持つ。

```yaml
strategy_profiles:
  intraday_momentum:
    paper_smoke:
      min_fills: 10
      min_trading_days: 1
    normal_paper_observation:
      min_fills: 50
      min_trading_days: 5

  swing_mean_reversion:
    paper_smoke:
      min_fills: 2
      min_trading_days: 3
    normal_paper_observation:
      min_fills: 10
      min_trading_days: 20
```

stage decision artifact には次を必ず残す。

- `policy_id`
- `policy_hash`
- `selected_stage`
- `selected_profile`
- `source_artifact_hashes`
- `decision`
- `failed_conditions`
- `warning_conditions`
- `manual_overrides`
- `override_reason`
- `reviewer`
- `created_at`

## Position Size 暴走防止

Position size 暴走防止は、戦略やバグが想定以上の数量、金額、レバレッジでポジションを作らないようにする上限ガードである。

防ぐ例:

- 100 USD のつもりが 10,000 USD の注文になる。
- 同じ signal で連続注文する。
- 1 symbol のつもりが複数 symbol に同時 entry する。
- 1倍のつもりがレバレッジ換算で 5倍になる。
- 損切り後すぐ再 entry して損失を拡大する。

config 例:

```yaml
risk_limits:
  max_order_notional_usd: 50
  max_position_notional_usd: 100
  max_strategy_exposure_usd: 100
  max_total_exposure_usd: 300
  max_open_positions: 1
  max_orders_per_day: 3
  max_leverage: 1.0
  max_loss_per_trade_usd: 5
  max_daily_loss_usd: 15
  stop_after_consecutive_losses: 2
```

paper でも必要である。paper で暴走する strategy は live では危険である。

## 完成形の主要 artifact

完成形では、次の artifact が中心になる。

| Artifact | 役割 |
|---|---|
| `strategy_authoring_spec.v1` | 戦略ルール定義 |
| `strategy_backtest_pack.v1` | backtest artifact chain |
| `strategy_backtest_pack_validation.v1` | pack と no-live boundary の検査 |
| `strategy_backtest_html_report.v1` | 人間が読む backtest report |
| `strategy_review_manifest.v1` | review packet の根拠 manifest |
| `operator_strategy_review.v1` | 人間判断の記録 |
| `strategy_idea.v1` | Idea Intake の構造化候補 |
| `strategy_input_contract.v1` | 戦略判断に使う入力データ契約 |
| `strategy_intake_decision.v1` | Idea Intake の進行 / 棄却判定 |
| `strategy_stage_policy.v1` | stage ごとの進行条件 |
| `strategy_stage_decision.v1` | policy に基づく次段階判定 |
| `strategy_runtime_observation_manifest.v1` | paper smoke / paper observation 中の実時間観測 manifest |
| `paper_observation_session_manifest.v1` | paper session の source / threshold / ledger |
| `strategy_paper_observation_status.v1` | paper observation の現在地 |
| `paper_vs_backtest_drift_review.v1` | backtest と paper の差分 review |
| `strategy_learning_event.v1` | 実践から得た学習イベント |
| `strategy_learning_ledger.v1` | 戦略ごとの学習履歴 |
| `strategy_revision_request.v1` | 学習に基づく改訂要求 |
| `strategy_ai_review_note.v1` | AI reviewer の指摘、要約、改善案 |
| `strategy_ai_review_bundle.v1` | 複数 AI review の比較 |
| `ai_review_packet_manifest.v1` | LLM-safe packet の入力 hash と redaction policy |
| `micro_live_plan.v1` | 最小実弾テスト計画 |
| `micro_live_canary_report.v1` | 最小実弾テスト結果 |
| `strategy_case_lite.v1` | strategy ごとの履歴束ね |

`strategy_case_lite.v1` は、最初から大きな registry にしない。まずは strategy id ごとに review、operator decision、paper status、drift review、stage decision を束ねる軽量 manifest でよい。

## 完成形の CLI 候補

次の CLI は完成形候補であり、現行実装済みとは限らない。

```bash
uv run sis strategy-input-contract-validate \
  --contract data/strategy_inputs/<input-contract-id>/strategy_input_contract.yaml

uv run sis strategy-intake-validate \
  --idea data/strategy_intake/<idea-id>/strategy_idea.yaml

uv run sis strategy-intake-review \
  --idea data/strategy_intake/<idea-id>/strategy_idea.yaml \
  --out data/strategy_intake/<idea-id>

uv run sis strategy-stage-policy-validate \
  --policy configs/strategy_stage_policies/personal_default.yaml

uv run sis strategy-stage-decision \
  --strategy-id <strategy-id> \
  --stage paper_smoke \
  --policy configs/strategy_stage_policies/personal_default.yaml \
  --review-dir data/strategy_reviews/<review-id> \
  --out data/strategy_stage_decisions

uv run sis strategy-paper-smoke-plan \
  --strategy-id <strategy-id> \
  --policy configs/strategy_stage_policies/personal_default.yaml \
  --out data/paper_smoke_plans

uv run sis strategy-runtime-observation-ingest \
  --strategy-id <strategy-id> \
  --session-id <session-id> \
  --out data/runtime_observations

uv run sis strategy-drift-review \
  --strategy-id <strategy-id> \
  --backtest-pack data/research/backtest_pack/strategy_backtest_pack.json \
  --paper-status data/research/strategy_lifecycle/paper_observation_status.json \
  --out data/strategy_reviews

uv run sis strategy-learning-ledger-update \
  --strategy-id <strategy-id> \
  --drift-review data/strategy_reviews/<review-id>/drift_review.json \
  --runtime-observation data/runtime_observations/<strategy-id>/<session-id>/runtime_observation_manifest.json \
  --out data/strategy_learning

uv run sis strategy-revision-request-build \
  --strategy-id <strategy-id> \
  --learning-ledger data/strategy_learning/<strategy-id>/learning_ledger.jsonl \
  --out data/strategy_learning/<strategy-id>/revision_requests

uv run sis strategy-ai-review-packet-build \
  --strategy-id <strategy-id> \
  --review-dir data/strategy_reviews/<review-id> \
  --runtime-observation data/runtime_observations/<strategy-id>/<session-id>/runtime_observation_manifest.json \
  --out data/ai_review_packets

uv run sis strategy-ai-review-import \
  --packet data/ai_review_packets/<strategy-id>/<packet-id>/ai_review_packet_manifest.json \
  --review-note path/to/ai_review_note.yaml \
  --out data/ai_reviews

uv run sis strategy-ai-review-compare \
  --strategy-id <strategy-id> \
  --reviews data/ai_reviews/<strategy-id> \
  --out data/ai_reviews/<strategy-id>/bundle

uv run sis strategy-case-lite-update \
  --strategy-id <strategy-id> \
  --stage-decision data/strategy_stage_decisions/<id>.json \
  --out data/strategy_cases

uv run sis strategy-daily-brief \
  --data-dir data \
  --out data/reports/strategy_daily_brief.md
```

## Daily Brief

個人システムトレーダー向けには、Daily Brief が重要である。

目的は、artifact を探し回らずに、今日見るべきことを 1 枚にすること。

Daily Brief が答える問い:

- 今日、壊れている artifact はどれか。
- paper smoke に進める候補はあるか。
- normal paper observation を続けるべき戦略はどれか。
- latest normal requirement gaps は何か。
- drift review が必要な戦略はどれか。
- learning event や revision request が未処理の戦略はどれか。
- AI review note に未解決の warning / blocker はあるか。
- stop condition に近い戦略はどれか。
- micro live plan を作ってよい候補はあるか。
- live / wallet / signing / exchange write の禁止境界は守られているか。

Daily Brief は permission artifact ではない。読む順番と next action をまとめる report である。

## 完成形でやらないこと

少なくともこの完成形では、次を主目的にしない。

- 完全自動 live trading
- backtest だけでの自動採用
- paper pass だけでの live 移行
- human review なしの stage advance
- wallet / signing / exchange write の暗黙実行
- UI を artifact contract の正本にすること
- strategy factory による大量自動生成を最初から主軸にすること
- 100点の確信が出るまで永遠に進まないこと

進めるが、小さく進める。止めるが、止めすぎない。

## 実装優先順位

完成形へ近づけるなら、優先順位は次。

1. `strategy_input_contract.v1` と `strategy-input-contract-validate`
2. `strategy_idea.v1` と `strategy-intake-validate`
3. `strategy_stage_policy.v1` と policy validation
4. `strategy_stage_decision.v1` と `strategy-stage-decision`
5. Paper smoke plan / report
6. Runtime Observation Ingest
7. Paper vs Backtest Drift Review
8. Persistent Learning Loop / Revision Request
9. AI Review Packet / AI Review Note
10. Strategy Case Lite
11. Strategy Daily Brief
12. Micro Live Plan Gate
13. Micro Live Canary は最後。実行ではなく、まず計画と artifact contract から始める。

今すぐ UI を作るより、Strategy Input Contract、Daily Brief、stage policy を先に作る方が実務価値が高い。

## 抜け、漏れ、誤謬リスク

この定義のリスク:

- `paper smoke` が通常 paper pass と誤読される。
- `PAPER_OBSERVATION_CANDIDATE` が paper execution permission と誤読される。
- config を緩めることで、負け戦略を通すための後付け最適化が起きる。
- Idea Intake が「アイデア生成器」になり、仮説、反証、baseline、risk が薄いまま候補が増える。
- 入力データを path / hash の一覧だけで済ませ、`available_at`、execution reality、survivorship、revision policy を見落とす。
- drift review が paper PnL だけに寄り、fill / slippage / no-fill / operations drift を見落とす。
- 持続的学習が自動最適化や自動採用に化ける。
- AI review が permission や採用判断として誤読される。
- AI に secret、credential、account detail、live execution 情報を渡してしまう。
- stage policy が複雑になりすぎて、個人が毎日使えなくなる。
- micro live plan ready が live execution ready と誤読される。
- `data/` の runtime artifact を current truth として固定してしまう。

対策:

- stage decision には policy hash と override reason を必ず残す。
- intake decision には baseline、invalidation、required inputs、duplicate key、reject rule の欠落を必ず出す。
- input contract decision には `available_at`、source hash、execution reality、survivorship policy、baseline、negative control の欠落を必ず出す。
- smoke と normal を schema 上も report 上も分ける。
- runtime observation は paper smoke / normal paper / micro live canary で別 artifact にする。
- learning event は `auto_applied=false` を既定にし、改訂は revision request と human review を通す。
- AI review note も `auto_applied=false` を既定にし、LLM-safe packet だけを入力にする。
- AI review は provider、model、prompt hash、input artifact hash、limitations を必ず残す。
- permission と candidate を別 artifact にする。
- live / wallet / signing / exchange write は別 gate まで fixed false にする。
- Daily Brief は結論を短く出し、詳細 artifact へリンクする。
- current docs には runtime snapshot 値を固定しない。

## Readiness Verdict

仕様化 readiness: ready with assumptions

前提:

- 完成形の中心は `Strategy Operations Workbench` とする。
- 次の実装候補は UI や strategy factory ではなく、`Strategy Stage Policy Config` と `Strategy Stage Decision` とする。
- Idea Intake は docs 運用だけでは足りないため、`strategy_idea.v1` と `strategy-intake-validate` を早めに足す。
- paper smoke は勝敗判定ではなく配線確認として扱う。
- normal paper observation と drift review を経て、70〜80点で micro live plan gate に進める。
- micro live plan ready は live execution permission ではない。
