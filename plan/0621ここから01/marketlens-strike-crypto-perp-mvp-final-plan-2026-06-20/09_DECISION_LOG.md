<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# Decision Log

## D01 — 旧巨大計画を置換

理由: 個人向けMVPに対しschema/artifact/venue拡張が多すぎ、市場から学ぶまでが遅い。

決定: MVP-A/B/Cへ縮約。

## D02 — 全損許容はedgeではない

理由: risk preferenceは負期待値を正にしない。

決定: market lossは隔離budget内で許容。primaryはactual cash。

## D03 — Pump shortを前提にしない

理由: momentum、新情報、squeeze、流動性消失が競合する。

決定: reversal short / continuation long / no-trade / unknownを同格に保存。

## D04 — 15m broad、1m/trade/book candidate-only

理由: 全銘柄L2は過剰。15mだけではtime ordering不足。

決定: 広域screeningは15m、event後だけ高解像度。

## D05 — public firstだがliveを遠ざけすぎない

理由: OHLCV backtestではactual fillが分からない。

決定: M08後、明示承認の5〜25 USD measurementで早期較正。

## D06 — live riskとoperational riskを分離

決定: experiment budget全損は許容。duplicate/wrong-side/cross-margin/secret leakは不可。

## D07 — OSSはaccelerator

決定:

```text
Hypothesis adopt now
Tardis fixture
pybotters spike
Freqtrade external
Hummingbot reference
hftbacktest conditional
VectorBT limited
River deferred
```

## D08 — direction-neutral schema

旧問題: `entry_bid_vwap`, `exit_ask_vwap`はshort固定。

決定: `side`, `entry_vwap`, `exit_vwap`, `entry_book_side`, `exit_book_side`。

## D09 — Strategy Lab v2を延期

理由: public event captureに不要。

決定: 既存Strategy Input Contract/Viewerへread-only export。venue schema wideningは実需発生後。

## D10 — Market cap hard gateを延期

理由: point-in-time supply/symbol/delist品質が重い。

決定: listing age、turnover、spread、min order、OI raw、depthをlabelとして使う。hard cap exclusionは後段。

## D11 — Human vetoも仮説

決定: outcome前にtimestamp/hash/review secondsを保存し、save/missed winnerを評価。

## D12 — Competitionからprotocolだけ借りる

決定: discovery/private future window、config freeze、online available-data-only。winner modelはコピーしない。

## D13 — M09は自動戦略executionではない

決定: operator-confirmed one-shot measurement。successしてもauto trading permissionを生まない。
