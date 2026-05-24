# Current Phase Status And Next Gate

## Purpose

この文書は、**2026-05-24 JST 時点** の `marketlens-strike` の進行可能フェーズを明文化する。

特に、次の混同を防ぐことを目的とする。

- 実装済みコードがあること
- live evidence が十分に取得できていること
- 次フェーズへ進んでよいこと
- 次フェーズが完成していること

## Executive Conclusion

**現時点で進めてよいのは Phase 1 までである。**

Phase 2 の本実装着手は、まだ許可しない。

理由は単純で、現時点では **実データの取得が適切に完了していない** ためである。  
この repo はコード上の Phase 1 実装を多く持っているが、Phase 1 の判定に必要な live evidence quality gate がまだ閉じていない。

## Current Timestamp

この判断は次の時刻基準で固定する。

- 判定日時: `2026-05-24 19:10:03 JST`
- 次の再判定予定: **2026-05-25 月曜日 夜 JST**

ここでいう「月曜日の夜」は、QQQ / SPY / XAU の live evidence を取り直すための次の実運用ウィンドウを指す。

## Current Repository Status

現 repo は、概念的には次の状態にある。

```txt
Phase 1:
  実装は概ね存在する
  ただし live evidence quality gate は未通過

Phase 2:
  設計はある
  完了条件文書はある
  まだ実装着手フェーズではない

Phase 3 以降:
  対象外
```

より実務的に言うと、今の repo は

- Venue Evidence Engine のコード本体はある
- strict artifact validation コマンドもある
- signal CSV 互換 backtest bridge もある
- しかし live evidence が十分ではない

という状態である。

## Evidence Behind This Decision

この判断の根拠は、現行監査文書にある。

`docs/ACCEPTANCE_AUDIT.md` では、最新 Go/No-Go が次のままである。

```txt
CONDITIONAL_GO_NEEDS_LIVE_WINDOW
```

また、未解消 blocker は少なくとも次の 2 点である。

1. `stale_rate` が threshold を満たしていない
2. `tradable_rate` が threshold を満たしていない

したがって、コードが存在していても、Phase 1 は完了扱いにできない。

## What "Can Progress Up To Phase 1" Means

「いま進めるのは Phase 1 まで」とは、次の意味である。

### Allowed Now

今すぐ進めてよいもの:

- Phase 1 の live evidence 再収集準備
- runbook 整理
- handoff 文書整理
- Phase 2 完成条件の明文化
- task breakdown
- review-only の設計検討
- 実データ収集を伴わない docs 整理

### Not Allowed Now

今は止めるべきもの:

- Phase 2 を「実装開始済み」と見なして進めること
- research provider 実装を完了扱いにすること
- Paper Trading 実装
- Execution Adapter 実装
- Live order placement
- high leverage logic
- new venue expansion

つまり、**設計と文書は進めてよいが、フェーズ判定としてはまだ Phase 1 に留まる**、ということ。

## Why Waiting Until Monday Night Is Correct

今回の停止判断は消極的ではなく、技術的に妥当である。

理由は次のとおり。

1. 現在の blocker はコード不足ではなく、live evidence quality 不足である。
2. `stale_rate` と `tradable_rate` は、適切な収集ウィンドウで再取得しないと評価が確定しない。
3. Phase 2 は研究用データ層であり、Phase 1 の venue viability が曖昧なまま進めると前提が崩れる。
4. `CONDITIONAL_GO_NEEDS_LIVE_WINDOW` のまま進めると、あとで「研究層の前提にした venue 品質」が実測とズレるリスクがある。

したがって、**2026-05-25 月曜日 夜 JST まで待ち、そこで再収集して再判定する** のが正しい。

## Exact Gate Before Phase 2

Phase 2 に入ってよいのは、次の gate を通ったときだけである。

1. `P1-003` collect live evidence
2. `P1-005` review diagnose output
3. `P1-004` validate artifacts --strict
4. `uv run sis check-go-no-go`
5. `uv run sis build-evidence-card`

この 5 点のうち、実質 gate として重要なのは 2 つある。

- live evidence quality が許容範囲であること
- Go/No-Go が `CONDITIONAL_GO_NEEDS_LIVE_WINDOW` から脱していること

## Phase 2 Entry Outcomes

### Enter Phase 2

次のいずれかなら、Phase 2 に進める。

- `GO`
- `CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST`

### Do Not Enter Phase 2

次の状態なら、Phase 2 に進めない。

- `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- `NO_GO_STALE`
- `NO_GO_SESSION`
- `NO_GO_COST`
- その他、live evidence 品質不足が main blocker の判定

## Monday Night Recheck Procedure

**2026-05-25 月曜日 夜 JST** の再判定では、少なくとも次の順で実行する。

```bash
bash scripts/refresh_live_evidence.sh --duration-minutes 120 --metadata-interval-seconds 60 --force
uv run sis diagnose-quotes --venue gtrade --symbol QQQ
uv run sis diagnose-quotes --venue gtrade --symbol SPY
uv run sis diagnose-quotes --venue gtrade --symbol XAU
uv run sis validate-artifacts --strict
uv run sis check-go-no-go
uv run sis build-evidence-card
```

必要なら先に preflight として次も使う。

```bash
bash scripts/refresh_live_evidence.sh --duration-minutes 120 --metadata-interval-seconds 60 --dry-run
```

## Decision Rule After Monday Night

### Case A: Gate Clears

次が確認できた場合:

- `stale_rate` が許容範囲
- `tradable_rate` が許容範囲
- missing mark/index が許容範囲
- strict validation 成功
- Go/No-Go が `GO` か `CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST`

この場合のみ、Phase 2 実装に進める。

### Case B: Gate Does Not Clear

次のいずれかが残る場合:

- `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- `NO_GO_STALE`
- `NO_GO_SESSION`
- `NO_GO_COST`

この場合、まだ Phase 1 を継続する。  
Phase 2 へ逃がさず、Phase 1 blocker を分解する。

## What Can Be Done While Waiting

月曜夜までの待機中にやってよい作業を明示する。

### Safe To Do

- `docs/ENGINEERING_HANDOFF_NOTE.md` の作成
- `docs/PHASE2_COMPLETION_DEFINITION.md` のレビュー
- ZIP task の棚卸し
- Phase 2 の細分化計画
- test strategy の整理
- CLI naming の整理
- provider fallback policy の文書化

### Do Not Treat As Progressed Phase

次はやってもよい review / planning だが、フェーズ進行とは数えない。

- `yfinance` 採用方針の議論
- `fredapi` の取り回し設計
- feature column の議論
- event blackout policy の詳細化

これらは設計準備であって、**Phase 2 started** を意味しない。

## Important Distinction

次の 3 つは別物である。

### 1. Implementation Exists

コードや CLI が存在すること。

### 2. Gate Is Open

実測データが十分で、次フェーズへ進んでよいこと。

### 3. Phase Is Complete

そのフェーズの artifact と acceptance が揃っていること。

現時点の `marketlens-strike` は、

```txt
Phase 1 implementation:
  mostly yes

Phase 1 gate:
  not yet

Phase 2 implementation:
  not yet
```

という理解が正しい。

## Operational Summary

要約すると、現時点の運用判断は次の 1 行に集約できる。

> As of 2026-05-24 JST, marketlens-strike must remain in Phase 1 operationally, and must not be treated as ready to enter Phase 2 until live evidence is recollected and re-evaluated on Monday night, 2026-05-25 JST.

## Related Documents

- `docs/ACCEPTANCE_AUDIT.md`
- `docs/PHASE2_COMPLETION_DEFINITION.md`
- `docs/LIVE_EVIDENCE_RUNBOOK.md`
- `docs/marketlens_strike_engineering_handoff.zip`

