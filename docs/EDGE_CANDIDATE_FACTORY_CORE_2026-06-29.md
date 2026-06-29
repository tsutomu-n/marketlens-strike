<!--
作成日: 2026-06-29_21:44 JST
更新日: 2026-06-29_21:44 JST
-->

# Edge Candidate Factory Core

## 結論

Profit Core は 3 層で扱う。

```text
Discovery Core
  = Edge Candidate Factory
Validation Core
  = C9 bridge + candidate-scoped backtest / robustness kill gate
Execution Evidence Core
  = virtual execution gate
  + risk-taker review
  + LLM adversarial evidence review
  + human risk approval
  + tiny live actual cash
  + actual cash report gate
```

Edge Candidate Factory は Core だが、利益証拠ではない。役割は、実データから大量の未検証 edge candidate を作り、全候補、全探索履歴、全棄却理由、全 metric summary を保存し、shortlist だけを次段へ渡すことに限定する。

## Core再定義

| 層 | 目的 | 利益証拠か |
|---|---|---|
| Discovery Core | 候補を広く作り、探索と棄却の記録を残す | いいえ |
| Validation Core | candidate-scoped backtest と robustness で弱い候補を殺す | いいえ |
| Execution Evidence Core | 仮想約定から actual cash までの実行証拠を段階的に集める | actual cash から |

Core は「候補を増やすもの」と「候補を証拠で殺すもの」と「実損益に接続するもの」を混ぜない。Discovery Core は探索漏れを減らす。Validation Core は過剰適合や費用負けを落とす。Execution Evidence Core は paper / demo / tiny live / actual cash の境界を壊さない。

## Edge Candidate Factoryの役割

Edge Candidate Factory は、best だけを見せる仕組みではない。

- 実データから未検証 candidate を大量に作る。
- 採用候補だけでなく、棄却候補も保存する。
- 探索した parameter、親子関係、objective components、metric summary を保存する。
- 棄却理由を保存する。
- 次段に渡すのは shortlist だけにする。
- 候補生成を profit evidence と呼ばない。

この層で欲しいのは「儲かる候補」ではなく、「後で検査できる candidate inventory」と「探索していない場所を見える化する ledger」。

## 入力データ

v0 の取引対象は crypto perps に固定する。入力は crypto perp native と cross-market context に分ける。

| カテゴリ | 入力 |
|---|---|
| crypto perp native | OHLCV、mark/index、funding、OI、liquidation、spread、bid/ask、depth、trade prints、fee/funding/slippage estimate、venue/symbol metadata |
| cross-market context | Nasdaq / QQQ / SPY / NY market proxy、Nikkei proxy、gold / silver、US rates、VIX、DXY、USDJPY など |

外部市場は v0 では取引対象にしない。crypto perps の regime / context feature としてだけ使う。

## 出力artifact案

| artifact | 役割 |
|---|---|
| candidate inventory | 全 candidate、parameter、source dataset、feature family、生成 phase |
| search ledger | 探索履歴、親子関係、random seed、Latin Hypercube bucket、GA lineage、objective components |
| rejection ledger | 棄却理由、kill rule、duplicate / no-trade / liquidity / cost / robustness failure |
| metric summary | candidate-level metric の集計。canonical PnL ではない |
| shortlist export | 次段の Validation Core に渡す候補だけ |
| input evidence manifest | どの source、期間、venue、symbol、quality guard を使ったか |

この artifact 群は review と再実行のための材料であり、actual cash proof ではない。

## 4種類のサンプル

| sample | 意味 | 利益証拠か |
|---|---|---|
| candidate sample | 未検証候補数 | いいえ |
| event sample | 候補が実データ上で発火した市場イベント数 | いいえ |
| virtual forward sample | demo / testnet / paper account で execution lifecycle を見る仮想約定サンプル | いいえ |
| actual cash sample | 実 fill、実 fee、funding、cash ledger に接続する実損益 | はい。利益証拠として扱える最初の層 |

candidate sample と event sample が増えても、利益が増えたとは読まない。virtual forward sample は lifecycle、latency、fill model、stop condition、operator burden を見るための層であり、actual cash ではない。

## 候補生成Phase A-D

### Phase A: 古典ルール大量生成

RSI、breakout、funding、basis、liquidation、volatility、OI、spread などの古典ルールを大量に生成する。目的は有望候補の発見だけではなく、どの古典ルール群が費用や robustness で死ぬかを記録すること。

### Phase B: typed grammar-based search

型付き grammar で signal expression を探索する。自由文 signal は実行しない。grammar は入力 feature、operator、window、threshold、regime condition、no-trade condition を明示し、任意 Python、任意 eval、LLM 生成の未検査コードを実行しない。

### Phase C: random / Latin Hypercube / GA

random search、Latin Hypercube、GA を使える。ただし、探索履歴、親子、mutation、objective components、seed、棄却理由を必ず保存する。best-only report は禁止する。

### Phase D: ML / ensemble

ML / ensemble は direct trading signal ではなく、ranking、interaction discovery、regime classifier、meta-labeling、no-trade filter、disagreement filter に限定する。ML の output は候補の優先順位や検査対象を絞る材料であり、単独の trade permission ではない。

## Cross-market contextの扱い

Nasdaq / QQQ / SPY / NY proxy、Nikkei proxy、gold / silver、US rates、VIX、DXY、USDJPY は、crypto perps の regime / context feature として接続できる。

v0 では外部市場を standalone trade path にしない。NDX/QQQ as standalone trade path は Add-on であり、Discovery Core の context feature とは別物として扱う。

## Backtest / Robustness Kill Gate

Validation Core は candidate-scoped backtest と robustness kill gate に寄せる。

- shortlist candidate だけを対象にする。
- `NO_TRADE` を first-class outcome として残す。
- fee、funding、spread、slippage、latency、operator burden を入れる。
- same-day rerun や proxy gain を過大評価しない。
- positive estimate を actual cash proof と呼ばない。
- robustness failure、cost failure、data quality failure、duplicate exposure、leakage suspicion を kill / wait に落とす。

Validation Core の通過は profit evidence ではない。Execution Evidence Core に進める候補を減らすための gate。

## Virtual Forward Execution Gate

Virtual Forward Execution Gate は demo / testnet / paper account で execution lifecycle を見る。ここでは、order intent、fill simulation、partial fill、cancel / replace、flat reconciliation、latency、operator step、stop condition を検査する。

virtual PnL は actual cash ではない。virtual forward sample は「実行の形が破綻していないか」を見る材料であり、利益証拠ではない。

## LLM Adversarial Evidence Review

LLM は adversarial reviewer。許可者ではない。

LLM に使ってよいこと:

- 集計結果の監査。
- 矛盾検出。
- 抜け漏れ検出。
- 過剰主張検出。
- structured findings 作成。

LLM にさせないこと:

- canonical PnL の算出。
- official metric の決定。
- actual_cash 判定。
- live / tiny-live 許可。
- order 作成。
- strategy 自動編集。

LLM status は次に限定する。

- `LLM_BLOCK`
- `LLM_REVISE`
- `LLM_NEEDS_MORE_EVIDENCE`
- `LLM_HUMAN_REVIEW_REQUIRED`
- `LLM_NO_ADDITIONAL_BLOCKER_FOUND`

`LLM_NO_ADDITIONAL_BLOCKER_FOUND` も許可ではない。単に LLM が追加 blocker を見つけなかったという記録。

## やってはいけないこと

- best candidate だけを見せる。
- 棄却候補と探索履歴を捨てる。
- candidate sample を利益証拠として数える。
- event sample を独立した利益機会として数える。
- virtual PnL を actual cash と読む。
- paper / demo / testnet の結果を実損益と混ぜる。
- LLM に order、metric、permission、strategy rewrite を任せる。
- 外部市場 context を v0 の取引対象にすり替える。
- `PASS`、`READY_FOR_HUMAN_REVIEW`、`READ_ONLY_GO` を alpha / paper / live readiness と読む。

## v0実装順

1. 入力 evidence manifest を固定する。
2. Phase A の古典ルール candidate inventory と rejection ledger を作る。
3. shortlist export を candidate-scoped backtest に接続する。
4. robustness kill gate を作る。
5. Virtual Forward Execution Gate で lifecycle を見る。
6. risk-taker review と LLM adversarial evidence review を入れる。
7. human risk approval の記録を分ける。
8. tiny live actual cash は別承認、上限、credential、flat reconciliation、stop condition が揃った時だけ扱う。
9. actual cash report gate で simulation / virtual / actual cash を分離して報告する。

## 現Repoとの接続

現 repo には Strategy Lab、Strategy Authoring、candidate set contract、backtest pack、Crypto Perp Truth-Cycle、risk-taker review、tiny-live shadow gate などの部品がある。ただし、この doc は実装済み宣言ではない。今回は docs-only の scope-control であり、schema、CLI、依存関係、外部 API 連携は変更しない。

実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、CLI help、runtime artifact。docs は current scope と誤読防止の入口として扱う。
