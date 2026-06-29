<!--
作成日: 2026-06-29_22:07 JST
更新日: 2026-06-29_22:07 JST
-->

# Appendix: Risks, Omissions, And Corrections

## 結論

最大リスクは「攻撃的に見えるが、実際は p-hacking と実行不能候補を増やすだけ」になること。

この package の Better 案は、攻撃モードを止めることではない。攻撃モードを **本命成績から隔離し、actual cash へ直行させず、検証 throughput を壊さない形で残す** こと。

## 修正した論点

| 元の論点 | 修正 |
|---|---|
| Edge Candidate Factory + Virtual Execution Gate + Multiplicity Accounting を同時実装 | full 同時実装は重い。最小同時実装は protocol manifest、multiplicity account、thin kill gate |
| `event_count >= 100` | 一律禁止。family-specific policy にする |
| BH/FDR を gate KPI | 単独合格条件にしない。effective trial count と family cluster を必須にする |
| PBO を KPI | fold outcome matrix がある時だけ。無ければ `NOT_ESTIMABLE` |
| LLM negative-veto | 自動 KILL ではなく adversarial finding。machine-checkable 欠落だけ hard blocker |
| Bitget demo / Hyperliquid / GRVT を同時検討 | venue explosion を避ける。初期 virtual gate は local/mock lifecycle |
| C9 bridge を Core と呼ぶ | Core は Candidate-to-Backtest Bridge。C9 は v0 の Core補助 |

## Risk register

| risk | symptom | mitigation |
|---|---|---|
| false positive factory | candidate 数と winner だけ増える | all trial ledger、success-only report 禁止、multiplicity account |
| validation leakage | OOS を見て修正し、同じ OOS で再評価する | validation peek count、rerank count、sealed holdout untouched flag |
| execution-ineligible explosion | backtest は良いが venue制約で実行できない | execution-aware grammar、unexecutable_reason_count、virtual gate |
| BRIDGED overclaim | C9 bridge 成功を alpha proof と読む | `BRIDGED_TECHNICAL_ONLY` へ分解 |
| virtual PnL overclaim | demo/testnet/paper を actual cash と混ぜる | `actual_cash=false` と `cash_metric_basis=virtual_exchange` を必須化 |
| LLM overreach | LLM が良い戦略や許可を出す | LLM status を adversarial finding に限定 |
| venue/legal mismatch | demo/testnet docs を legal clearance と読む | external venue docs は付録情報、実行前再確認必須 |
| mode contamination | sprint winner を default performance に混ぜる | mode isolation、re-register under default before promotion |
| too-heavy first PR | schema/CLI/venue/LLM を一気に作る | first slice を CP1-CP3 に限定 |

## Better 案

### 1. 攻撃モードに `promotion debt` を持たせる

`risk_taker_sprint` で見つけた候補は、昇格前に不足項目を持つ。

```text
promotion_debt:
  - re-register under verification_throughput
  - sealed holdout not reused
  - multiplicity account attached
  - backtest kill gate pass under default thresholds
  - virtual execution gate pass
  - risk-taker review pass without live permission
```

debt が残っている限り actual cash へ進めない。

### 2. `event_count_policy` を family に持たせる

一律閾値ではなく、familyごとに扱う。

```text
common_signal:
  min_event_count_default: 100
event_driven_medium_frequency:
  min_event_count_default: 30
rare_dislocation:
  min_event_count_default: null
  insufficient_data_state: SPECULATIVE_RESEARCH_ONLY
```

rare candidate は即 KILL ではなく、position も permission も持たない研究棚へ置く。

### 3. `unexecutable_rate` を candidate factory KPI にする

候補生成器の品質は raw score ではなく、実行不能率でも測る。

```text
unexecutable_rate <= 5% for verification_throughput
unexecutable_rate reported, not hidden, for risk_taker_sprint
```

### 4. LLM は二重レビューではなく差分検査に寄せる

LLM に同じ packet を読ませて意見を出すより、machine summary と claims を比較させる。

```text
input:
  - machine-readable gate summary
  - human-facing claims
output:
  - claim unsupported by artifact
  - missing required comparison
  - basis mismatch
  - overclaim severity
```

この方が hallucination リスクを抑えられる。

## 明示的に割愛したこと

- 実 schema 設計の完全版。
- CLI コマンド名の最終決定。
- DB / storage migration。
- external venue adapter 実装。
- live / tiny-live execution runbook。
- dependency 採用判断。
- Workbench UI design。

割愛理由は、最初の実装 slice を太らせないため。今回の目的は dedicated docs package であり、実装は後続 checkpoint で扱う。

## 完了判定で見落としやすいこと

- docs ができても implementation はできていない。
- current-doc checker が通っても、仕様が正しいとは限らない。
- mode enum を作っても mode isolation を検証しなければ意味がない。
- `NOT_ESTIMABLE` は failure ではなく正しい停止結果。
- `NO_ADDITIONAL_BLOCKER_FOUND` は approval ではない。
- `SHORTLIST_FOR_VIRTUAL` は trading permission ではない。
