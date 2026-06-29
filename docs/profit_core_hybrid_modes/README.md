<!--
作成日: 2026-06-29_22:07 JST
更新日: 2026-06-29_22:07 JST
-->

# Profit Core Hybrid Modes

## 結論

採用する設計は **Verification-Throughput Core を default、Risk-Taker Sprint を隔離された attack mode** とする hybrid。

```text
default mode = verification_throughput
attack mode  = risk_taker_sprint
```

攻撃モードは安全装置を外すモードではない。探索幅を広げ、候補を速く作り、速く殺すための隔離モード。`actual_cash`、`NO_TRADE`、search accounting、virtual / actual cash 境界、LLM の negative-veto 制約は緩めない。

## このフォルダーの位置づけ

このフォルダーは docs-only の decision package。ここに書いた artifact、CLI、schema、mode はまだ実装済みとは限らない。実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、CLI help、runtime artifact。

既存の current scope は [../EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md](../EDGE_CANDIDATE_FACTORY_CORE_2026-06-29.md) と [../PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md](../PROFIT_CORE_SCOPE_DEVELOPER_2026-06-29.md) を正とし、このフォルダーは「本命 + 攻撃案の hybrid 実装方針」を具体化する。

## 読む順番

1. [DEVELOPER_SPEC.md](DEVELOPER_SPEC.md): Core 定義、mode、artifact、禁止事項。
2. [IMPLEMENTATION_CHECKPOINTS.md](IMPLEMENTATION_CHECKPOINTS.md): 最初に実装する順番と完了条件。
3. [APPENDIX_RISKS_AND_OMISSIONS.md](APPENDIX_RISKS_AND_OMISSIONS.md): 抜け漏れ、誤謬リスク、Better 案。
4. [APPENDIX_RESEARCH_EVIDENCE.md](APPENDIX_RESEARCH_EVIDENCE.md): repo evidence、論文、外部 venue docs。

## Core 再定義

```text
Core =
  Edge Candidate Factory
  + Multiplicity / Search Accounting
  + Candidate-to-Backtest Bridge
  + Backtest Kill Gate
  + Thin Virtual Execution Gate
  + Risk-Taker Review
  + Actual Cash Report Gate
```

`Risk-Taker Review` と `Actual Cash Report Gate` は後段の判定器として残す。ただし、それだけでは候補を作れない。次に必要なのは、候補生成、探索会計、検証 bridge、kill gate、virtual execution gate を一体で薄くつなぐこと。

## Mode 方針

| mode | 目的 | 使い方 | profit evidence |
|---|---|---|---|
| `verification_throughput` | default の検証 throughput を上げる | classical + limited grammar、保守的 gate、実装正本に昇格しやすい | no |
| `risk_taker_sprint` | 小口・高リスク向けに探索幅を広げる | classical + grammar + limited random / light GA、隔離 ledger、再検証必須 | no |

どちらの mode でも、actual cash sample 以外は profit evidence ではない。

## 最初の実装スライス

最初に作るべきものは次の 3 つだけ。

```text
1. candidate_protocol_manifest.v1
2. trial_multiplicity_account.v1
3. backtest_kill_gate.v1 thin
```

Virtual Execution Gate、LLM adversarial review、Risk-Taker Sprint の広い candidate generation は後続。ここを飛ばして候補生成を増やすと、false positive と unexecutable candidate を増やすだけ。

## 明示的モード切替案

将来 CLI 化する場合の shape:

```bash
uv run sis edge-candidate-factory-run \
  --mode verification-throughput \
  --protocol configs/edge_candidate/protocol.yaml \
  --out data/edge_candidates/run-001
```

```bash
uv run sis edge-candidate-factory-run \
  --mode risk-taker-sprint \
  --protocol configs/edge_candidate/protocol.yaml \
  --risk-budget-usd 25 \
  --out data/edge_candidates/sprint-001
```

これは提案であり、現時点の public CLI 実装ではない。

## 絶対に崩さない境界

- `candidate sample` は profit evidence ではない。
- `event sample` は profit evidence ではない。
- `virtual forward sample` は profit evidence ではない。
- `actual cash sample` だけが profit evidence の最初の層。
- `NO_TRADE` は失敗ではなく正式 action。
- `BRIDGED` は技術接続 status。経済的合格ではない。
- LLM は approval engine ではない。
- attack mode は live / tiny-live / actual cash への直行を許可しない。
