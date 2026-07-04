<!--
作成日: 2026-07-04_10:47 JST
更新日: 2026-07-04_18:00 JST
-->

# Progress To 90 Roadmap

## 結論

90%に近づける長期の主戦場は、機能追加ではなく **actual cash evidence loop** である。

Research / backtest / docs / CLI / schema / tests はすでに厚い。ここから進捗を大きく上げるには、`ACTUAL_CASH_SOURCE_MISSING` を解消し、actual cash basis の rows、report、gate、Reality Check、human risk review までをつなぐ必要がある。

ただし、これは「少し actual cash rows を作れば90%」という意味ではない。1 event の actual cash rows は疎通確認であり、実務上の利益判断には足りない。90%に近いと言えるのは、複数 event、同一 event set の3 action比較、non-actual混入拒否、sample不足やNO_TRADE leaderを正しく blocker として出せる状態になってからである。

当面 actual cash を実装しない方針では、この文書の actual cash evidence loop は実行対象ではなく長期ロードマップとして読む。短期の実行対象は [crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md](crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md) に従い、pre-actual-cash の候補を `KILL` / `REVISE_EVENT_DEFINITION` / `COLLECT_MORE_SOURCES` / `HOLD_FOR_FUTURE_ACTUAL_CASH` に落とすことだけに限定する。

長期ルートは次の順番。

1. manual cash ledger plus explicit assignment を actual cash source の最小仕様にする。
2. `crypto-perp-actual-cash-rows-build` に渡せる最小サンプルを作る。
3. `crypto-perp-actual-cash-report-gate` で non-actual basis を拒否しつつ actual cash report を判定する。
4. `profit-core-reality-check` の blocker を `ACTUAL_CASH_SOURCE_MISSING` から次の blocker へ進める。
5. actual cash basis の tournament / risk review / human decision を作る。
6. その後に tiny-live shadow と human approval を扱う。

## 90%の意味

この文書の90%は、利益保証ではない。市場で勝てる確率でもない。

ここでの90%は、次の意味で使う。

| 軸 | 90%に近い状態 |
|---|---|
| Research / backtest platform | fresh checkout から代表 workflow を再現でき、失敗時に blocker が出る |
| Profit Core | actual cash source から rows / report / gate / Reality Check / risk review までつながる |
| Crypto Perp Truth-Cycle | real event / matured outcome / actual cash basis tournament が同一 event set で回る |
| Human decision | promote / continue / kill / collect_more を artifact として残せる |
| Tiny-live preparation | explicit approval 前は絶対に live/order/write に進まない |

production live trading まで含めた90%は、この文書の主対象ではない。そこへ進むには actual cash evidence loop の後に、credential、exchange write、wallet/signing、flat reconciliation、kill switch、monitoring、audit を別 gate で扱う。

## 現実監査

このロードマップは、次の現物確認で補正して読む。

- `crypto-perp-cash-ledger` は `--entries`、`--ledger-id`、`--observed-at` を要求する。
- `crypto-perp-actual-cash-rows-build` は `--ledger` と `--assignment` を要求する。
- `crypto-perp-actual-cash-report-gate` は `--rows`、`--report-id`、`--min-events` を要求する。
- `profit-core-reality-check` は optional input として `--actual-cash-rows-summary` と `--actual-cash-report-gate` を読む。
- `crypto_perp_cash_ledger.v1` と `crypto_perp_actual_cash_rows_summary.v1` schema は存在する。
- `actual cash assignment` は現行コードでは `ActualCashAssignmentRow` Pydantic model として読まれるが、独立した tracked JSON Schema file は確認できない。
- `crypto-perp-cash-ledger` の `source_refs` は entries file を参照するが、取引所明細、broker statement、スクリーンショット、API response などの外部証跡を必須にはしていない。
- 現行 `data/crypto_perp` には `profit_event_outcome_inputs` の event/outcome/run artifact はあるが、actual cash ledger / actual cash rows / actual-cash report gate artifact は確認できない。
- `crypto-perp-actual-cash-report-gate --min-events` を満たさない場合、actual cash basis でも gate は `NEEDS_MORE_EVIDENCE` 系で止まる。

これにより、次の結論になる。

- actual cash CLI surface はある。
- actual cash artifact はまだない。
- manual ledger は実損益を入力する器であって、外部証跡そのものではない。
- assignment 入力の運用仕様は doc 化が足りない。
- 1 event の疎通確認は必要だが、90%に近い evidence ではない。
- 90%化は「actual cash source を1つ置く」ではなく、「actual cash basis の比較と blocker 判定を複数 event で回す」ことである。

## FATAL FLAWS

ロードマップが理想論に寄る最大の失敗パターンは次。

- `manual cash ledger plus explicit assignment` を、実損益の出所確認なしに便利な手入力フォーマットとして扱う。
- ledger entries file だけを外部証跡と誤認する。
- 1 event の actual cash rows 生成を、Profit Core の実務進捗として過大評価する。
- `--min-events` を満たさない blocked report を「gateが通った」と読む。
- assignment の独立 schema / sample / validation doc がないまま、別の作業者が迷わず入力できると期待する。
- actual cash rows ができただけで、NO_TRADE比較、loss concentration、sample size、operator time、bias guard が済んだように扱う。
- human risk review を approval と誤読し、tiny-live / live permission に近づいたように見せる。

これらが残る限り、見た目のartifact数は増えても90%には近づかない。

## BURDEN ANALYSIS

新しいCLIやviewerを増やす負担は、今は利益が薄い。現行 repo はすでに CLI / schema / docs / tests が多く、追加 surface は保守負担と誤読リスクを増やす。

今の価値が高い負担は、次の狭いものだけ。

- assignment 入力の仕様化。
- actual cash ledger sample と、その元になった外部証跡の扱いを分ける。
- actual cash rows build の negative test / sample。
- report gate が `NEEDS_MORE_EVIDENCE`、`NEEDS_ACTUAL_CASH`、`READY_FOR_HUMAN_TINY_LIVE_REVIEW` を正しく分ける確認。
- Reality Check が actual cash rows summary と report gate manifest を読んで、次 blocker を出す確認。

これ以外の拡張は、actual cash blocker が解消するまで後回しでよい。

## 現在地

現行評価は [FINAL_STATE_PROGRESS_ASSESSMENT_2026-07-04.md](FINAL_STATE_PROGRESS_ASSESSMENT_2026-07-04.md) を正本とする。

| チャンク | 現在評価 | 90%への主作業 |
|---|---:|---|
| Research / backtest platform | 75%前後 | 代表 workflow を少数に絞り、one-command 再現と acceptance を固める |
| Profit Core | 50%前後 | `ACTUAL_CASH_SOURCE_MISSING` を解消する |
| Crypto Perp Truth-Cycle | 70%前後 | event/outcome を増やし、actual cash basis tournament に接続する |
| Actual cash evidence | 20%前後 | manual ledger plus explicit assignment で実損益 rows を作る |
| Human risk review | surface あり | actual cash basis の report と risk packet を読ませる |
| Tiny-live / production | 20%未満 | actual cash evidence loop の後に shadow / approval / credential boundary を扱う |

## Chunk 1: Research / Backtest Platform

目的:

Strategy Lab、Strategy Authoring、backtest、review、stage decision を、代表 workflow として安定再現できる状態にする。

やること:

1. 代表 workflow を 2-3 本に絞る。
2. `strategy-author-*`、`strategy-backtest-*`、`strategy-review-*`、`strategy-stage-*` の順序を runbook に固定する。
3. 各 workflow に golden fixture と expected artifact を置く。
4. HTML report、Workbench Viewer、Daily Brief から次 action が読めるようにする。
5. `PASS` を alpha proof や live permission と読ませない tests / docs を維持する。

90%条件:

- fresh checkout から代表 strategy の検証、review、stage decision まで再現できる。
- 失敗時に blocker が stdout と artifact に残る。
- `uv run python scripts/check_current_docs.py`、`uv run python scripts/check_cli_catalog.py`、`./scripts/check` が通る。

注意:

ここを磨いても、actual cash evidence がなければ Profit Core の進捗は大きく上がらない。

## Chunk 2: Profit Core

目的:

Reality Check の最大 blocker である `ACTUAL_CASH_SOURCE_MISSING` を解消し、利益判断の入口を before-cost / estimate から actual cash basis へ進める。

やること:

1. actual cash source の最小仕様を manual cash ledger plus explicit assignment にする。
2. `crypto-perp-actual-cash-rows-build` の入力に必要な file、field、assignment を明示する。
3. `crypto-perp-actual-cash-report-gate` が non-actual basis を拒否することを確認する。
4. `profit-core-reality-check` を再実行し、blocker が次へ進むことを確認する。
5. 次 blocker を sample size、loss concentration、NO_TRADE leader、bias guard、source shortage のような実評価 blocker として扱う。

90%条件:

- `ACTUAL_CASH_SOURCE_MISSING` が消える。
- actual cash rows、actual-cash report gate、Reality Check が一連で動く。
- before-cost proxy、cost-adjusted estimate、virtual、dogfood、backtest、public candle-only outcome が actual cash に混ざらない。

最初に作るべき artifact:

- cash ledger
- event / outcome への explicit assignment
- actual cash rows
- actual-cash report gate result
- Reality Check result

実務上の注意:

- assignment は独立 JSON Schema がないため、最初に sample と field contract を書く。
- manual ledger は外部証跡の代替ではない。entries file、外部証跡、event/action assignment を分けて保管する。
- `NO_TRADE` は現行 rows build では cash `0` として扱われる。これを「何もしないので常に安全」と読まない。
- `--min-events 1` は疎通確認には使えるが、実務判断には弱い。
- `--min-events` を上げると、最初の report は blocked になる可能性が高い。それは失敗ではなく正しい停止である。

## Chunk 3: Crypto Perp Truth-Cycle

目的:

real event、matured outcome、actual cash basis tournament を、同一 event set で比較できる状態にする。

やること:

1. real event / matured outcome の件数を増やす。
2. `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を同一 event set で比較する。
3. `crypto-perp-source-availability` で bars / ticker / funding / trades / books / replay / cash ledger / live measurement の欠損を記録する。
4. 欠損 source を 0 埋めしない。
5. `crypto-perp-tournament-rows-v2` は estimate として扱い、actual cash とは分ける。
6. actual cash rows ができた後に `crypto-perp-tournament-report` と `crypto-perp-tournament-gate` を actual cash basis で通す。

90%条件:

- event / decision / outcome / tournament / gate / truth-cycle status が local artifact chain として安定する。
- `NO_TRADE` が leader でも失敗扱いしない。
- actual cash basis 以外は gate で止まる。

## Chunk 4: Actual Cash Evidence

目的:

実損益の出所と event への割当を追跡できる状態にする。

やること:

1. manual cash ledger format を確定する。
2. event/outcome への explicit assignment を必須にする。
3. fee、slippage、funding、operator time の扱いを決める。
4. 最小 1 event で actual cash rows の疎通確認をする。
5. mixed basis、missing assignment、preview rows 混入を tests で落とす。
6. 複数 event に増やし、`--min-events` を満たすか、満たさない理由を gate に出す。

90%条件:

- actual cash の出所が artifact で追える。
- どの event にどの cash result を割り当てたか追える。
- non-actual rows が report / gate に混ざらない。
- Reality Check が actual cash source を認識する。

この chunk が進むと、全体進捗は最も大きく上がる。

## Chunk 5: Human Risk Review

目的:

actual cash basis の結果を、人間が進めるか止めるか判断できる packet にする。

やること:

1. actual cash basis の tournament report を `crypto-perp-risk-taker-review` に渡す。
2. largest loss、profit concentration、sample size、operator time、NO_TRADE 比較を review packet に出す。
3. `READY_FOR_HUMAN_RISK_REVIEW` を live permission と読ませない。
4. human decision を `promote`、`continue`、`kill`、`collect_more` のような判断記録として残す。

90%条件:

- 人間が「進める / 止める / 追加収集」を判断できる。
- 判断が artifact として残る。
- live permission と分離されている。

## Chunk 6: Tiny-Live / Production

目的:

actual cash evidence loop が通った後に、小額実測や production 境界を扱える状態にする。

やること:

1. tiny-live shadow で max notional cap、isolated、flat、order preview ready を確認する。
2. withdrawal disabled API key、IP restriction、credentialed read-only smoke を別 gate にする。
3. demo / testnet lifecycle と production write boundary を分ける。
4. kill switch、monitoring、reconciliation、audit を runbook に閉じる。
5. live order 実行は別の explicit approval を必須にする。

90%条件:

- explicit approval なしに live/order/write に進めない。
- tiny-live は小額、分離、停止可能。
- production は別 gate として扱う。

この chunk は最後でよい。actual cash evidence loop がない状態で進めても、利益判断の90%には近づかない。

## 推奨実行順

長期で actual cash を再開する場合の最短順は次。当面の実行順は、この表ではなく pre-actual-cash evidence pack を優先する。

| 順番 | 作業 | 完了条件 |
|---:|---|---|
| 1 | actual cash source 最小仕様を決める | entries file、外部証跡、manual ledger、assignment の責任境界が決まる |
| 2 | 最小 sample を作る | 1 event に対して actual cash rows の疎通確認ができる |
| 3 | actual-cash report gate を通す | non-actual basis を拒否し、min-events不足なら blocked として出る |
| 4 | Reality Check を再実行する | `ACTUAL_CASH_SOURCE_MISSING` 以外の blocker に進む |
| 5 | event 数を増やす | sample size / concentration / NO_TRADE 比較が読める |
| 6 | risk review を作る | promote / continue / kill / collect_more を判断できる |
| 7 | tiny-live shadow を扱う | live permission false のまま事前条件だけ確認する |

## ULTIMATUM

90%へ近づける長期作業で厳密に必要なのは **Actual Cash Evidence chunk** である。

ただし、当面 actual cash を実装しない方針では、これを次の実装対象にしない。短期の実装対象は actual cash source ではなく、内部 builder / schema surface で候補を4択 decision に落とすことである。

将来 actual cash を再開する場合は、次の1本だけを実装対象にする。

1. assignment sample / field contract
2. ledger sample
3. actual cash rows build
4. actual-cash report gate
5. Reality Check の blocker遷移確認

これが通らない限り、90%ロードマップは見た目だけの進捗になる。当面はこの段階へ進まず、pre-actual-cash の候補判断に留める。

## 後回しにすること

次は優先度を下げる。

- pre-actual-cash evidence pack と関係ない public CLI をさらに増やす。
- docs を増やすだけの整理。
- backtest 指標だけを増やす。
- viewer だけを磨く。
- production live trading の設計を先に広げる。
- credential / exchange write / live order へ先に進む。

理由:

これらは土台の改善にはなるが、現在の最大 blocker である actual cash evidence を解消しない。

## 絶対に混ぜないこと

次は actual cash evidence として扱わない。

- preview rows
- before-cost proxy
- cost-adjusted estimate
- stress estimate
- virtual exchange
- dogfood artifact
- status / viewer artifact
- backtest pass
- public candle-only outcome
- paper permission
- human review readiness

これらを混ぜると、進捗は上がったように見えるが、実利益判断には近づかない。

## 完了の見え方

90%に近づいた状態では、次が読める。

- どの event に対して、どの outcome があり、どの cash result が割り当てられたか。
- `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` の actual cash basis 比較。
- report / gate が non-actual basis を拒否した証拠。
- Reality Check の blocker が actual cash source ではない次段階へ進んだ証拠。
- risk review が promote / continue / kill / collect_more を判断できる packet。
- live permission はまだ false のまま維持されている証拠。

この状態なら、repo は「検証の器がある」から「実損益を安全に読む仕組みがある」へ進む。
