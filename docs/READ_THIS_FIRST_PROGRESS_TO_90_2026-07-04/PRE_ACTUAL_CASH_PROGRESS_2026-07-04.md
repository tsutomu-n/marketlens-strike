<!--
作成日: 2026-07-04_13:08 JST
更新日: 2026-07-04_13:08 JST
-->

# Pre Actual Cash Progress

## 結論

actual cash以前の状態だけを見ると、進捗は **70%前後** と見る。

理由は、CLI、schema、tests、docs、event / outcome、profit-readiness inventory / plan / run-local artifact までは揃っている一方で、現物の evidence はまだ **1 event / 1 outcome / public 5m candles only** であり、trades、books、replay、cash ledger、live measurement、actual cash はないため。

つまり、actual cash に入る前の「器」はかなりできているが、「この戦略候補は現実に強い」と言える前段 evidence はまだ薄い。

## この文書の範囲

この文書は、actual cash evidence を入れる前の進捗だけを扱う。

扱うもの:

- Strategy / backtest / review の土台
- Crypto Perp Truth-Cycle
- real market event
- matured outcome
- source availability
- replay / feature / edge / rows-v2 / bias guard
- profit-readiness inventory / plan / run-local
- Reality Check が actual cash 前で止まる状態

扱わないもの:

- actual cash ledger
- actual cash rows
- actual-cash report gate
- live measurement
- tiny-live execution
- production live trading
- wallet / signing / exchange write

## 現在の到達点

確認時点: `2026-07-04_13:08 JST`

| 領域 | 状態 | 評価 |
|---|---|---:|
| CLI / schema / tests / docs | public CLI、schema、docs checker、full check が通る | 90%前後 |
| Strategy / backtest platform | Strategy Lab、Authoring、backtest、review、stage decision は広く実装済み | 75%前後 |
| Crypto Perp Truth-Cycle surface | event / decision / outcome / tournament / gate / truth-cycle status の surface は実装済み | 75%前後 |
| Real event / matured outcome | 1 event / 1 outcome は存在 | 50%前後 |
| Source availability | bars 等はあるが trades / books / replay / cash ledger / live measurement が欠ける | 45%前後 |
| Local profit-readiness run | artifact は出るが `status=blocked` | 50%前後 |
| Bias / robustness | bias guard はあるが sample insufficient | 40%前後 |
| Actual cash handoff直前 | actual cash source がないため未到達 | 20%前後 |

総合すると、actual cash以前の仕組みは進んでいるが、evidence はまだ薄い。したがって **70%前後** が現実的な見方。

## 現物確認

現行 `data/crypto_perp/profit_event_outcome_inputs/c9_btcusdt_20260627_1950/` には、次が存在する。

- `events/*.json`
- `outcomes/*.json`
- `inventory/inventory.json`
- `plan/plan.json`
- `run/source_availability.json`
- `run/replay_slice.json`
- `run/feature_pack.json`
- `run/edge_score.json`
- `run/tournament_rows_v2.json`
- `run/bias_guard.json`
- `run/manifest.json`
- `source_availability/source_availability.json`

確認した status:

| Artifact | Status / value |
|---|---|
| inventory | `READY_FOR_LOCAL_PLAN` |
| inventory event count | `1` |
| inventory outcome count | `1` |
| plan | `READY_FOR_LOCAL_RUN` |
| plan runnable commands | `1` |
| run manifest | `status=blocked` |
| run known gap count | `16` |
| source availability | `can_compute_actual_cash=false` |
| source availability known gap count | `6` |

## できていること

### 1. Local validation の器

できている:

- current docs checker がある。
- CLI catalog checker がある。
- `./scripts/check` が通る。
- schema と tests が広い。
- permission boundary を false に保つ設計がある。

意味:

この段階では、作った artifact を repo の local contract に沿って検証できる。

限界:

local validation は、利益証拠ではない。

### 2. Event / outcome 入力

できている:

- `market_window_v1` event を record できる。
- `crypto-perp-event-record` がある。
- `crypto-perp-outcome-record --settled-at` がある。
- validated public candle CSV から 1 event / 1 outcome ができている。

意味:

以前の「real event / matured outcome がない」状態は一段進んだ。

限界:

1 event だけなので、sample としては弱い。public 5m candles だけなので、fills、slippage、fees、trade tape、order book は証明しない。

### 3. Profit-readiness inventory / plan

できている:

- inventory は `READY_FOR_LOCAL_PLAN`。
- plan は `READY_FOR_LOCAL_RUN`。
- runnable command が出る。

意味:

event と outcome の pairing は local run へ進める程度に揃っている。

限界:

plan が ready でも、profit evidence が ready という意味ではない。

### 4. Local run artifacts

できている:

- source availability
- replay slice
- feature pack
- edge score
- tournament rows v2
- bias guard
- run manifest

意味:

actual cash に入る前の technical chain は一通り回る。

限界:

run manifest は `status=blocked`。known gaps は 16 件あり、actual cash 以前にも source 品質の不足が残っている。

### 5. Safety boundary

できている:

- network attempted false。
- exchange write false。
- live order false。
- actual cash を proxy / estimate と混同しない guard がある。

意味:

安全に止まる設計はできている。

限界:

止まることは重要だが、止まるだけでは利益判断は進まない。

## まだ弱いこと

### 1. Evidence が1 eventに偏っている

1 event / 1 outcome は疎通確認としては十分だが、実務上の判断には弱い。

不足:

- sample size
- event diversity
- time-of-day diversity
- volatility regime diversity
- repeated outcome comparison

### 2. Public 5m candles only

現行 event / outcome は public 5m candle ベース。

不足:

- trades source
- books source
- replay source
- fill / slippage evidence
- fees / funding の実測
- ordering ambiguity の解消

### 3. Cost-adjusted estimate もまだ強くない

`tournament_rows_v2` はあるが、known gaps に `EDGE_SCORE_UNKNOWN_COST_ADJUSTED_INPUTS_MISSING` や `ESTIMATE_NOT_ACTUAL_CASH` が残る。

これは、actual cash以前の estimate としても、まだ荒いという意味。

### 4. Bias guard は sample不足

known gaps に `PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT` がある。

この状態で「候補がよい」とは言えない。言えるのは「bias guard が sample不足を正しく止めている」まで。

### 5. Reality Check は actual cash source で止まる

`profit-core-reality-check` の次 blocker は `ACTUAL_CASH_SOURCE_MISSING`。

これは、pre-actual-cash chain の終端に到達したというより、actual cash evidence へ進むための入力がないという状態。

## 現実的な進捗評価

### 甘い見方

「CLIもschemaもrunもある。event/outcomeもできた。だから actual cash以前はほぼ完了」

この見方は甘い。

理由:

- 1 event しかない。
- run は blocked。
- source gaps が多い。
- cost / slippage / fills がない。
- bias guard は sample不足。

### 厳しめの見方

「actual cash がないなら全部だめ」

この見方も雑。

理由:

- actual cash以前の validation chain は確実に進んでいる。
- event / outcome 入力は実際に作れている。
- missing source を 0 埋めせず gap として出せている。
- next blocker が明確に出る。

### 現実的な見方

actual cash以前は **70%前後**。

根拠:

- 仕組みは 80-90%近い。
- 実データ evidence は 50-60%程度。
- source / sample / cost-adjusted estimate の弱さが残る。
- actual cash 直前の handoff は未完成。

## actual cash前にやるべきこと

actual cashへ進む前に、まず次をやる。

1. event / outcome を増やす。
2. public 5m candles only の限界を明示したまま、source availability の gaps を潰す。
3. trades / books / replay の少なくともどれを次に入れるか決める。
4. `tournament_rows_v2` の estimate 入力不足を減らす。
5. bias guard が sample insufficient 以外の判定をできる件数まで増やす。
6. NO_TRADE を含む同一 event set 比較を複数 event で読む。
7. それでも勝ち筋がないなら actual cash へ進まず kill / revise する。

## actual cashへ進んでよい条件

最低条件:

- 複数 event / outcome がある。
- source availability の known gaps が説明可能。
- estimate は estimate として扱われ、actual cash と混同されない。
- NO_TRADE 比較で候補が全滅していない。
- largest loss / concentration / operator time が読める。
- bias guard が sample不足だけで止まっていない、または sample不足を明示したまま小額検証に進む理由がある。
- human review が「actual cashへ進む理由」と「進まない条件」を明記している。

これを満たさないなら、actual cash に進むより、event/source/evidence を増やす方が実務的。

## やらないこと

actual cash以前の進捗をよく見せるために、次はやらない。

- blocked run を complete と読む。
- public candle outcome を profit evidence と読む。
- before-cost proxy を cash result と読む。
- estimate を actual cash と読む。
- 1 event を十分な sample と読む。
- NO_TRADE leader を失敗扱いして無理に action candidate を選ぶ。
- source gaps を 0 埋めする。
- viewer / status / dogfood artifact を evidence と読む。

## 次の現実的な1本

次にやるなら、actual cash ではなく、まず **pre-actual-cash evidence pack v1** を作る。

内容:

1. 既存 event / outcome を起点にする。
2. event / outcome を追加する。
3. source availability を全 event でまとめる。
4. known gaps を source type 別に集計する。
5. rows-v2 / bias guard を複数 event で回す。
6. NO_TRADE 比較を含めた pre-actual-cash review を作る。
7. 結論を `KILL`、`REVISE_EVENT_DEFINITION`、`COLLECT_MORE_SOURCES`、`READY_TO_DESIGN_ACTUAL_CASH_SOURCE` のどれかに落とす。

この1本が通れば、actual cash以前の進捗は 70%前後から 80%台へ上がる。

actual cash source を入れるのは、その後でよい。
