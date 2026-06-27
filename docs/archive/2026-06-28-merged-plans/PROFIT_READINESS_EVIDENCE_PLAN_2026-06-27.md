<!--
作成日: 2026-06-27_19:01 JST
更新日: 2026-06-27_19:01 JST
-->

# Crypto Perp Profit-Readiness Evidence Plan

## 目的

既存の Crypto Perp Truth-Cycle MVP を作り直さず、その出力を利益判断に耐える local evidence へ薄く変換する。

確認したい問いは次の1点。

```text
同じevent setで REVERSAL_SHORT / CONTINUATION_LONG / NO_TRADE を比較し、
fee / funding / slippage / operator time / data gap を含めても、
NO_TRADEを上回る行動候補が残るか。
```

この文書は live order permission ではない。実発注、自動売買、production Bitget live order、daemon、credentialed write は対象外。

## 実装境界

- 現行の Crypto Perp Truth-Cycle MVP は実装済み surface として扱う。
- 旧 M00-M11 plan package は historical implementation contract であり、新規実装指示として扱わない。
- 既存の `replay.py`, `features.py`, `tournament_rows.py`, `tournament.py`, `tournament_gate.py`, `tiny_live.py`, `workbench_bridge.py` を優先し、必要な薄い隣接 module だけ追加する。
- `actual_cash_result_usd` は実fill・実fee・実funding・cash ledger または live measurement artifact に接続した時だけ使う。
- replay / preview / simulation は `cost_adjusted_cash_estimate_usd`, `stress_cash_estimate_usd`, `evidence_level` を使う。
- OFI / trade sign / depth は source がある時だけ計算し、欠損を0埋めしない。
- `NO_TRADE` は失敗ではなく、正式な競合actionとして扱う。
- Tiny-live shadow は実発注しない測定surfaceであり、`exchange_write_used=false`, `live_order_submitted=false`, `permits_live_order=false` を必須にする。
- PBO は event数が足りない場合に無理に計算せず、`pbo_status=NOT_ESTIMABLE` を正式結果にする。
- 依存追加、外部API送信、credential生成・変更、`git push` は行わない。

## 実装チェックポイント

1. PR-00: current plan / inventory / vocabulary / docs routing
2. PR-A0: Source Availability Matrix
3. PR-A1: Minimal Replay Slice
4. PR-A2: Minimal Feature Pack
5. PR-B: Deterministic Edge Scorer
6. PR-C: Cost-aware Tournament Rows v2
7. PR-D: Bias Guards and Walk-forward Minimum
8. PR-E: Operator Decision Surface
9. PR-F: Tiny-live Shadow Measurement

## 完了条件

- current plan / inventory / vocabulary が docs に固定されている。
- `actual cash / cost-adjusted estimate / before-cost proxy` が明確に分離されている。
- eventごとの source availability artifact が作れる。
- 欠損sourceが0埋めされず、known gaps として downstream に伝播する。
- replay slice が future data を読まず、source refs / hashes / cutoff / gaps を保持する。
- feature pack が entry action を決めない。
- edge scorer が deterministic rule として `REVERSAL_SHORT / CONTINUATION_LONG / NO_TRADE / UNKNOWN` を比較する。
- cost-aware tournament rows v2 が 3action を同一event setで出す。
- before-cost proxy を actual cash と誤表示しない。
- bias guard が sample不足を `NOT_ESTIMABLE` として出せる。
- operator surface で next command / stop reason / known gaps が読める。
- tiny-live shadow artifact が作れる。
- tiny-live shadow は `exchange_write_used=false`, `live_order_submitted=false`, `permits_live_order=false` を満たす。
- 実発注、exchange write、自動売買、production live order が発生しない。

## 停止条件

- source availability が不明。
- books / trades 欠損を0扱いしている。
- before-cost proxy を actual cash と表示している。
- `NO_TRADE` row が欠けている。
- lookahead violation または recursive warmup violation がある。
- sample insufficient を隠して PBO を推定済みにしている。
- `stress_cash_estimate_usd < 0` の行動候補を進めている。
- profit concentration が高すぎる。
- operator time cost が利益候補を上回る。
- tiny-live shadow で 25 USD 上限を超える。
- secret / credential がartifactに混ざる。
- exchange write または live order 呼び出しが発生する。
